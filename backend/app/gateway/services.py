"""Run lifecycle service layer.

Centralizes the business logic for creating runs, formatting SSE
frames, and consuming stream bridge events.  Router modules
(``thread_runs``, ``runs``) are thin HTTP handlers that delegate here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request
from langchain_core.messages import HumanMessage

from app.gateway.banned_words_client import (
    BannedWordsClient,
    BannedWordsCheckResult,
    random_banned_word_reply,
)
from app.gateway.deps import get_checkpointer, get_run_context, get_run_manager, get_stream_bridge
from app.gateway.tenant import normalize_tenant_id
from app.gateway.usage_reporter import UsageReporter, UsageSettlement, UsageSettlementMessage
from app.gateway.utils import sanitize_log_param
from app.gateway.visibility import sanitize_user_visible_payload
from deerflow.runtime import (
    END_SENTINEL,
    HEARTBEAT_SENTINEL,
    ConflictError,
    DisconnectMode,
    RunManager,
    RunRecord,
    RunStatus,
    StreamBridge,
    UnsupportedStrategyError,
    run_agent,
    serialize,
)

logger = logging.getLogger(__name__)
_OCEANENGINE_REQUEST_RE = re.compile(r"本地推|营销页|巨量|OceanEngine|oceanengine|本地推账号|视频素材|图文素材|素材库")
_USER_VISIBLE_UNSAFE_STREAM_MODES = {"messages", "messages-tuple"}


# ---------------------------------------------------------------------------
# SSE formatting
# ---------------------------------------------------------------------------


def format_sse(event: str, data: Any, *, event_id: str | None = None) -> str:
    """Format a single SSE frame.

    Field order: ``event:`` -> ``data:`` -> ``id:`` (optional) -> blank line.
    This matches the LangGraph Platform wire format consumed by the
    ``useStream`` React hook and the Python ``langgraph-sdk`` SSE decoder.
    """
    payload = json.dumps(sanitize_user_visible_payload(data), default=str, ensure_ascii=False)
    parts = [f"event: {event}", f"data: {payload}"]
    if event_id:
        parts.append(f"id: {event_id}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Input / config helpers
# ---------------------------------------------------------------------------


def normalize_stream_modes(raw: list[str] | str | None) -> list[str]:
    """Normalize the stream_mode parameter to a list.

    Default matches what ``useStream`` expects: values + messages-tuple.
    """
    if raw is None:
        return ["values", "messages-tuple"]
    if isinstance(raw, str):
        return [raw]
    return raw if raw else ["values", "messages-tuple"]


def _message_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            for key in ("text", "content"):
                value = block.get(key)
                if isinstance(value, str):
                    parts.append(value)
    return "\n".join(parts)


def _input_text(raw_input: dict[str, Any] | None) -> str:
    if not isinstance(raw_input, dict):
        return ""
    messages = raw_input.get("messages")
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for message in messages:
        if isinstance(message, dict):
            parts.append(_message_content_text(message.get("content")))
        else:
            parts.append(_message_content_text(getattr(message, "content", None)))
    return "\n".join(parts)


def constrain_stream_modes_for_user_visible_safety(stream_modes: list[str], raw_input: dict[str, Any] | None) -> list[str]:
    """Avoid streaming internal scratchpad text for OceanEngine requests."""
    if not _OCEANENGINE_REQUEST_RE.search(_input_text(raw_input)):
        return stream_modes
    constrained = [mode for mode in stream_modes if mode not in _USER_VISIBLE_UNSAFE_STREAM_MODES]
    return constrained or ["values"]


def normalize_input(raw_input: dict[str, Any] | None) -> dict[str, Any]:
    """Convert LangGraph Platform input format to LangChain state dict."""
    if raw_input is None:
        return {}
    messages = raw_input.get("messages")
    if messages and isinstance(messages, list):
        converted = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", "user"))
                content = msg.get("content", "")
                if role in ("user", "human"):
                    converted.append(HumanMessage(content=content))
                else:
                    # TODO: handle other message types (system, ai, tool)
                    converted.append(HumanMessage(content=content))
            else:
                converted.append(msg)
        return {**raw_input, "messages": converted}
    return raw_input


_DEFAULT_ASSISTANT_ID = "lead_agent"


def resolve_agent_factory(assistant_id: str | None):
    """Resolve the agent factory callable from config.

    Custom agents are implemented as ``lead_agent`` + an ``agent_name``
    injected into ``configurable`` or ``context`` — see
    :func:`build_run_config`.  All ``assistant_id`` values therefore map to the
    same factory; the routing happens inside the lead-agent builder when it
    reads ``cfg["agent_name"]``.

    The public ``make_lead_agent(config)`` wrapper intentionally keeps a
    LangGraph Server-compatible single-argument signature. Gateway's embedded
    runtime needs to inject ``app_config`` and request-scoped middlewares, so it
    must use the internal builder instead.
    """
    from deerflow.agents.lead_agent.agent import _build_lead_agent

    return _build_lead_agent


def ensure_langfuse_session_id(
    config: dict[str, Any],
    *,
    thread_id: str | None,
) -> dict[str, Any]:
    """Ensure RunnableConfig metadata carries a Langfuse session id.

    Explicit caller-provided ``metadata.langfuse_session_id`` always wins.
    When absent, we default to the current thread id so all traces spawned
    within the same conversation can be grouped under one Langfuse Session.
    """
    config_metadata = config.setdefault("metadata", {})
    if thread_id and (
        not isinstance(config_metadata.get("langfuse_session_id"), str)
        or not config_metadata.get("langfuse_session_id", "").strip()
    ):
        config_metadata["langfuse_session_id"] = thread_id
    return config


def build_run_config(
    thread_id: str,
    request_config: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    *,
    assistant_id: str | None = None,
) -> dict[str, Any]:
    """Build a RunnableConfig dict for the agent.

    When *assistant_id* refers to a custom agent (anything other than
    ``"lead_agent"`` / ``None``), the name is forwarded as ``agent_name`` in
    whichever runtime options container is active: ``context`` for
    LangGraph >= 0.6.0 requests, otherwise ``configurable``.
    ``make_lead_agent`` reads this key to load the matching
    ``agents/<name>/SOUL.md`` and per-agent config — without it the agent
    silently runs as the default lead agent.

    This mirrors the channel manager's ``_resolve_run_params`` logic so that
    the LangGraph Platform-compatible HTTP API and the IM channel path behave
    identically.
    """
    config: dict[str, Any] = {"recursion_limit": 100}
    if request_config:
        # LangGraph >= 0.6.0 introduced ``context`` as the preferred way to
        # pass thread-level data and rejects requests that include both
        # ``configurable`` and ``context``.  If the caller already sends
        # ``context``, honour it and skip our own ``configurable`` dict.
        if "context" in request_config:
            if "configurable" in request_config:
                logger.warning(
                    "build_run_config: client sent both 'context' and 'configurable'; preferring 'context' (LangGraph >= 0.6.0). thread_id=%s, caller_configurable keys=%s",
                    thread_id,
                    list(request_config.get("configurable", {}).keys()),
                )
            context_value = request_config["context"]
            if context_value is None:
                context = {}
            elif isinstance(context_value, Mapping):
                context = dict(context_value)
            else:
                raise ValueError("request config 'context' must be a mapping or null.")
            config["context"] = context
        else:
            configurable = {"thread_id": thread_id}
            configurable.update(request_config.get("configurable", {}))
            config["configurable"] = configurable
        for k, v in request_config.items():
            if k not in ("configurable", "context"):
                config[k] = v
    else:
        config["configurable"] = {"thread_id": thread_id}

    # Inject custom agent name when the caller specified a non-default assistant.
    # Honour an explicit agent_name in the active runtime options container.
    if assistant_id and assistant_id != _DEFAULT_ASSISTANT_ID:
        normalized = assistant_id.strip().lower().replace("_", "-")
        if not normalized or not re.fullmatch(r"[a-z0-9-]+", normalized):
            raise ValueError(
                f"Invalid assistant_id {assistant_id!r}: must contain only letters, digits, and hyphens after normalization."
            )
        if "configurable" in config:
            target = config["configurable"]
        elif "context" in config:
            target = config["context"]
        else:
            target = config.setdefault("configurable", {})
        if target is not None and "agent_name" not in target:
            target["agent_name"] = normalized
    if metadata:
        config.setdefault("metadata", {}).update(metadata)
    return ensure_langfuse_session_id(config, thread_id=thread_id)


def _as_user_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _user_context_from_request(request: Request) -> dict[str, Any]:
    user = getattr(getattr(request, "state", None), "user", None)
    if user is None:
        return {}

    context: dict[str, Any] = {}
    tenant_id = normalize_tenant_id(getattr(user, "tenant_id", None))
    user_id = _as_user_id(getattr(user, "user_id", None))
    if tenant_id is not None:
        context["tenant_id"] = tenant_id
    if user_id is not None:
        context["user_id"] = user_id
    for key in ("username", "nickname", "dept_id", "business_code"):
        value = getattr(user, key, None)
        if value is not None and str(value).strip():
            context[key] = value
    return context


def _pick_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _first_dept_id(value: Any) -> str | None:
    if isinstance(value, list | tuple):
        if not value:
            return ""
        return str(value[0]).strip()
    if value is None:
        return None
    return str(value).strip()


def _normalize_user_context(context: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(context)
    tenant_id = normalize_tenant_id(
        _pick_first(context, ("tenant_id", "tenantId", "tenantID"))
    )
    user_id = _as_user_id(_pick_first(context, ("user_id", "userId", "id")))
    business_code = _pick_first(
        context, ("business_code", "businessCode", "bizCode", "BUSINESS_CODE")
    )
    nickname = _pick_first(context, ("nickname",))
    dept_id = _first_dept_id(
        context.get("deptIds")
        if "deptIds" in context
        else _pick_first(context, ("dept_id", "deptId", "dept_ids"))
    )
    if tenant_id is not None:
        normalized["tenant_id"] = tenant_id
    if user_id is not None:
        normalized["user_id"] = user_id
    if isinstance(business_code, str) and business_code.strip():
        normalized["business_code"] = business_code.strip()
    if isinstance(nickname, str) and nickname.strip():
        normalized["nickname"] = nickname.strip()
    if dept_id is not None:
        normalized["dept_id"] = dept_id
    return normalized


def merge_gateway_context(
    config: dict[str, Any], request: Request, context: dict[str, Any] | None
) -> None:
    """Merge DeerFlow gateway context into RunnableConfig.configurable.

    Billing identity is always taken from authenticated request state when it
    is available. ``context.user_context`` remains supported as a fallback for
    standalone LangGraph-compatible clients.
    """
    configurable = config.setdefault("configurable", {})

    if context:
        configurable_keys = {
            "model_name",
            "mode",
            "thinking_enabled",
            "reasoning_effort",
            "inference_mode",
            "is_plan_mode",
            "subagent_enabled",
            "max_concurrent_subagents",
            "agent_name",
            "is_bootstrap",
        }
        for key in configurable_keys:
            if key in context:
                configurable.setdefault(key, context[key])

    body_user_context = {}
    if context and isinstance(context.get("user_context"), dict):
        body_user_context = _normalize_user_context(context["user_context"])

    request_user_context = _user_context_from_request(request)
    merged_user_context = _normalize_user_context(
        {**body_user_context, **request_user_context}
    )

    tenant_id = normalize_tenant_id(merged_user_context.get("tenant_id"))
    user_id = _as_user_id(merged_user_context.get("user_id"))
    if tenant_id is not None:
        configurable["tenant_id"] = tenant_id
        merged_user_context["tenant_id"] = tenant_id
    if user_id is not None:
        configurable["user_id"] = user_id
        merged_user_context["user_id"] = user_id
    if merged_user_context:
        configurable["user_context"] = merged_user_context


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------


async def start_run(
    body: Any,
    thread_id: str,
    request: Request,
) -> RunRecord:
    """Create a RunRecord and launch the background agent task.

    Parameters
    ----------
    body : RunCreateRequest
        The validated request body (typed as Any to avoid circular import
        with the router module that defines the Pydantic model).
    thread_id : str
        Target thread.
    request : Request
        FastAPI request — used to retrieve singletons from ``app.state``.
    """
    bridge = get_stream_bridge(request)
    run_mgr = get_run_manager(request)
    run_ctx = get_run_context(request)

    disconnect = (
        DisconnectMode.cancel
        if body.on_disconnect == "cancel"
        else DisconnectMode.continue_
    )

    try:
        record = await run_mgr.create_or_reject(
            thread_id,
            body.assistant_id,
            on_disconnect=disconnect,
            metadata=body.metadata or {},
            kwargs={"input": body.input, "config": body.config},
            multitask_strategy=body.multitask_strategy,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UnsupportedStrategyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    try:
        # Upsert thread metadata so the thread appears in /threads/search,
        # even for threads that were never explicitly created via POST /threads
        # (e.g. stateless runs).
        try:
            existing = await run_ctx.thread_store.get(thread_id)
            if existing is None:
                await run_ctx.thread_store.create(
                    thread_id,
                    assistant_id=body.assistant_id,
                    metadata=body.metadata,
                )
            else:
                await run_ctx.thread_store.update_status(thread_id, "running")
        except Exception:
            logger.warning(
                "Failed to upsert thread_meta for %s (non-fatal)",
                sanitize_log_param(thread_id),
            )

        agent_factory = resolve_agent_factory(body.assistant_id)
        graph_input = normalize_input(body.input)
        config = build_run_config(
            thread_id, body.config, body.metadata, assistant_id=body.assistant_id
        )

        merge_gateway_context(config, request, getattr(body, "context", None))

        stream_modes = constrain_stream_modes_for_user_visible_safety(
            normalize_stream_modes(body.stream_mode),
            body.input,
        )

        # -- Banned-words input check (gateway-only, no core-package change) --
        banned_result = await _check_input_banned_words(config, graph_input)
        if banned_result is not None and banned_result.hit:
            checkpointer = get_checkpointer(request)
            await _handle_banned_word_hit(
                bridge=bridge,
                run_mgr=run_mgr,
                record=record,
                run_ctx=run_ctx,
                graph_input=graph_input,
                config=config,
                thread_id=thread_id,
                stream_modes=set(stream_modes),
                banned_result=banned_result,
                checkpointer=checkpointer,
            )
            return record

        task = asyncio.create_task(
            run_agent(
                bridge,
                run_mgr,
                record,
                ctx=run_ctx,
                agent_factory=agent_factory,
                graph_input=graph_input,
                config=config,
                stream_modes=stream_modes,
                stream_subgraphs=body.stream_subgraphs,
                interrupt_before=body.interrupt_before,
                interrupt_after=body.interrupt_after,
            )
        )

        # -- Banned-words output check (post-run, gateway-layer only) --
        checkpointer = get_checkpointer(request)
        asyncio.create_task(
            _check_output_banned_words_after_run(
                task=task,
                config=config,
                thread_id=thread_id,
                checkpointer=checkpointer,
            )
        )
    except Exception as exc:
        await run_mgr.set_status(record.run_id, RunStatus.error, error=str(exc))
        raise

    record.task = task

    return record


# ---------------------------------------------------------------------------
# Banned-words helpers (gateway-layer only, deerflow core is untouched)
# ---------------------------------------------------------------------------


def _extract_last_human_message_id(graph_input: dict[str, Any]) -> str | None:
    """Extract the id from the last human message in graph_input."""
    messages = graph_input.get("messages")
    if not isinstance(messages, list) or not messages:
        return None
    for message in reversed(messages):
        role = (
            message.get("role", message.get("type", ""))
            if isinstance(message, dict)
            else getattr(message, "type", "")
        )
        if role in ("user", "human") or isinstance(message, HumanMessage):
            raw_id = (
                message.get("id") if isinstance(message, dict) else getattr(message, "id", None)
            )
            if raw_id is not None:
                text = str(raw_id).strip()
                return text or None
            return None
    return None


def _extract_last_human_text(graph_input: dict[str, Any]) -> str:
    """Extract text from the last human message in graph_input."""
    messages = graph_input.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""
    for message in reversed(messages):
        content = (
            message.get("content")
            if isinstance(message, dict)
            else getattr(message, "content", None)
        )
        role = (
            message.get("role", message.get("type", ""))
            if isinstance(message, dict)
            else getattr(message, "type", "")
        )
        if role in ("user", "human") or isinstance(message, HumanMessage):
            return _message_content_text(content)
    return ""


async def _check_input_banned_words(
    config: dict[str, Any],
    graph_input: dict[str, Any],
) -> BannedWordsCheckResult | None:
    """Call lumax-service to check the latest human message for banned words."""
    client = BannedWordsClient.get_instance()
    if not client.enabled:
        return None

    configurable = config.get("configurable", {})
    tenant_id = normalize_tenant_id(configurable.get("tenant_id"))
    if tenant_id is None:
        return None

    text = _extract_last_human_text(graph_input)
    if not text.strip():
        return None

    return await client.check_text(
        tenant_id=tenant_id, text=text, trigger_mode="input"
    )


async def _handle_banned_word_hit(
    *,
    bridge: StreamBridge,
    run_mgr: RunManager,
    record: RunRecord,
    run_ctx: Any,
    graph_input: dict[str, Any],
    config: dict[str, Any],
    thread_id: str,
    stream_modes: set[str],
    banned_result: BannedWordsCheckResult,
    checkpointer: Any,
) -> None:
    """Push a canned reply via SSE, persist checkpoint, and report the hit.

    Entirely in the gateway layer — ``worker.py`` and the deerflow core
    package are not involved.
    """
    from langchain_core.messages import AIMessage

    run_id = record.run_id
    reply = random_banned_word_reply()
    ai_message = AIMessage(content=reply, id=f"{run_id}:banned-word")

    user_text = _extract_last_human_text(graph_input)
    user_message_id = _extract_last_human_message_id(graph_input) or f"{run_id}:user-input"

    messages = graph_input.setdefault("messages", [])
    messages.append(ai_message)

    # Resolve title: keep existing checkpoint title, fall back to the reply.
    title = str(graph_input.get("title") or "").strip() or reply

    # 1. Mark running
    await run_mgr.set_status(run_id, RunStatus.running)

    # 2. Metadata (useStream needs run_id + thread_id)
    await bridge.publish(run_id, "metadata", {"run_id": run_id, "thread_id": thread_id})

    # 3. Messages event
    if "messages-tuple" in stream_modes or "messages" in stream_modes:
        await bridge.publish(
            run_id,
            "messages",
            serialize((ai_message, {}), mode="messages"),
        )

    # 4. Values event
    if "values" in stream_modes:
        graph_input["title"] = title
        await bridge.publish(run_id, "values", serialize(graph_input, mode="values"))

    # 5. Persist checkpoint so the banned-word reply survives page refresh.
    await _persist_banned_word_checkpoint(
        checkpointer=checkpointer,
        thread_id=thread_id,
        messages=messages,
        title=title,
    )

    # 6. Update thread title
    try:
        await run_ctx.thread_store.update_display_name(thread_id, title)
    except Exception:
        logger.debug("Failed to update thread title for banned-word run", exc_info=True)

    # 7. Mark success + end stream
    await run_mgr.set_status(run_id, RunStatus.success)
    await bridge.publish_end(run_id)
    asyncio.create_task(bridge.cleanup(run_id, delay=60))

    # 7.5. Create neutral feedback entry so user can rate this response
    feedback_repo = getattr(run_ctx, "feedback_repo", None)
    if feedback_repo is not None:
        try:
            await feedback_repo.ensure_neutral_for_run(
                run_id=run_id,
                thread_id=thread_id,
                user_id=str(config.get("configurable", {}).get("user_id") or ""),
                message_id=ai_message.id or f"{run_id}:banned-word",
                agent_id=record.assistant_id or "lead_agent",
                agent_name=str(config.get("configurable", {}).get("agent_name") or ""),
            )
        except Exception:
            logger.debug("Failed to create neutral feedback for banned-word run %s", run_id, exc_info=True)

    # 8. Report settlement so conversation + messages are persisted to DB
    configurable = config.get("configurable", {})
    tenant_id = str(configurable.get("tenant_id") or "")
    user_id = str(configurable.get("user_id") or "")
    user_context = configurable.get("user_context") or {}
    username = str(user_context.get("username") or user_context.get("nickname") or "")
    dept_id = str(user_context.get("dept_id") or "")
    model_name = str(configurable.get("model_name") or "")
    agent_name = str(configurable.get("agent_name") or "")

    conversation_id = await _report_banned_word_settlement(
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        dept_id=dept_id,
        thread_id=thread_id,
        run_id=run_id,
        model_name=model_name,
        agent_name=agent_name,
        title=title,
        user_text=user_text,
        user_message_id=user_message_id,
        ai_reply=reply,
        ai_message_id=ai_message.id or f"{run_id}:banned-word",
    )

    # 9. Fire-and-forget hit reports
    client = BannedWordsClient.get_instance()
    for match in banned_result.matched_words:
        logger.warning(
            "Banned word hit: tenant=%s trigger=input word=%r mode=%s sentence=%r",
            tenant_id, match.word, match.matched_mode, match.matched_sentence,
        )
        asyncio.create_task(
            client.report_hit(
                tenant_id=tenant_id,
                user_id=user_id,
                word_id=match.word_id,
                category_id=match.category_id,
                thread_id=thread_id,
                conversation_id=conversation_id,
                matched_word=match.word,
                matched_sentence=match.matched_sentence,
                trigger_source="input",
                matched_mode=match.matched_mode,
            )
        )


async def _report_banned_word_settlement(
    *,
    tenant_id: str,
    user_id: str,
    username: str,
    dept_id: str,
    thread_id: str,
    run_id: str,
    model_name: str,
    agent_name: str,
    title: str,
    user_text: str,
    user_message_id: str,
    ai_reply: str,
    ai_message_id: str,
) -> None:
    """Report a zero-token settlement so conversation + messages are persisted."""
    normalized_tenant = normalize_tenant_id(tenant_id)
    if normalized_tenant is None:
        logger.warning(
            "Banned-word settlement skipped: invalid tenant_id=%r",
            tenant_id,
        )
        return

    logger.debug(
        "Banned-word settlement metering ids client user_msg=%r ai_msg=%r",
        user_message_id,
        ai_message_id,
    )

    # Short deterministic DB ids (VARCHAR(255)); avoids silent ON CONFLICT skips with long client ids.
    compact = run_id.replace("-", "")
    settlement_messages: list[UsageSettlementMessage] = []
    if user_text.strip():
        settlement_messages.append(
            UsageSettlementMessage(
                message_id=f"bws{compact}u",
                role="user",
                content=user_text,
                message_index=0,
            )
        )
    settlement_messages.append(
        UsageSettlementMessage(
            message_id=f"bws{compact}a",
            role="assistant",
            content=ai_reply,
            message_index=1 if user_text.strip() else 0,
        )
    )

    settlement = UsageSettlement(
        idempotency_key=f"deerflow:{run_id}:banned-word-settlement",
        tenant_id=normalized_tenant,
        user_id=user_id,
        username=username,
        dept_id=dept_id,
        thread_id=thread_id,
        run_id=run_id,
        model_name=model_name,
        agent_name=agent_name,
        title=title,
        tokens_in=0,
        tokens_out=0,
        tokens_total=0,
        status="completed",
        messages=settlement_messages,
    )
    try:
        result = await UsageReporter.get_instance().report_settlement(settlement)
        conversation_id = result.get("conversationId") if isinstance(result, dict) else None
        logger.info(
            "Banned-word settlement reported: thread=%s run=%s messages=%d conversation_id=%s",
            thread_id, run_id, len(settlement_messages), conversation_id,
        )
        return conversation_id
    except Exception:
        logger.warning(
            "Failed to report banned-word settlement for thread %s",
            thread_id,
            exc_info=True,
        )
        return None


async def _check_output_banned_words_after_run(
    *,
    task: asyncio.Task,
    config: dict[str, Any],
    thread_id: str,
    checkpointer: Any,
) -> None:
    """Wait for the agent run to finish, then check the AI reply for banned words."""
    try:
        await task
    except Exception:
        return

    configurable = config.get("configurable", {})
    tenant_id = normalize_tenant_id(configurable.get("tenant_id"))
    if tenant_id is None:
        return

    ai_text = await _extract_last_ai_text(checkpointer, thread_id)
    if not ai_text.strip():
        return

    client = BannedWordsClient.get_instance()
    if not client.enabled:
        return

    result = await client.check_text(
        tenant_id=tenant_id, text=ai_text, trigger_mode="output"
    )
    if result is None or not result.hit:
        return

    user_id = str(configurable.get("user_id") or "")
    for match in result.matched_words:
        logger.warning(
            "Banned word hit (output): tenant=%s word=%r mode=%s sentence=%r",
            tenant_id, match.word, match.matched_mode, match.matched_sentence,
        )
        asyncio.create_task(
            client.report_hit(
                tenant_id=tenant_id,
                user_id=user_id,
                word_id=match.word_id,
                category_id=match.category_id,
                thread_id=thread_id,
                matched_word=match.word,
                matched_sentence=match.matched_sentence,
                trigger_source="output",
                matched_mode=match.matched_mode,
            )
        )


async def _extract_last_ai_text(checkpointer: Any, thread_id: str) -> str:
    """Read the latest AI message text from the thread checkpoint."""
    if checkpointer is None:
        return ""
    try:
        ckpt_tuple = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        )
        if ckpt_tuple is None:
            return ""
        channel_values = getattr(ckpt_tuple, "checkpoint", {}).get("channel_values", {})
        if not isinstance(channel_values, dict):
            return ""
        messages = channel_values.get("messages")
        if not isinstance(messages, list) or not messages:
            return ""
        for msg in reversed(messages):
            role = getattr(msg, "type", None) or (msg.get("type") if isinstance(msg, dict) else None)
            if role in ("ai", "assistant"):
                content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                return _message_content_text(content) if content else ""
        return ""
    except Exception:
        logger.debug("Failed to extract AI text for output check on thread %s", thread_id, exc_info=True)
        return ""


async def _persist_banned_word_checkpoint(
    *,
    checkpointer: Any,
    thread_id: str,
    messages: list[Any],
    title: str,
) -> None:
    """Write a minimal checkpoint so the banned-word reply appears in history."""
    if checkpointer is None:
        return

    try:
        from langgraph.checkpoint.base import empty_checkpoint

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint: dict[str, Any] = empty_checkpoint()
        channel_values: dict[str, Any] = {}
        channel_versions: dict[str, Any] = {}
        metadata: dict[str, Any] = {"source": "input", "step": 0}

        ckpt_tuple = await checkpointer.aget_tuple(config)
        if ckpt_tuple is not None:
            existing_checkpoint = getattr(ckpt_tuple, "checkpoint", {})
            if isinstance(existing_checkpoint, dict):
                checkpoint = {**checkpoint, **existing_checkpoint}
            existing_values = checkpoint.get("channel_values", {})
            if isinstance(existing_values, dict):
                channel_values.update(existing_values)
            existing_versions = checkpoint.get("channel_versions", {})
            if isinstance(existing_versions, dict):
                channel_versions.update(existing_versions)
            existing_metadata = getattr(ckpt_tuple, "metadata", {})
            if isinstance(existing_metadata, dict):
                metadata.update(existing_metadata)
                metadata["step"] = int(existing_metadata.get("step", -1) or -1) + 1

        # Merge messages without duplicates
        existing_messages = channel_values.get("messages")
        channel_values["messages"] = _merge_checkpoint_messages(
            existing_messages if isinstance(existing_messages, list) else [],
            messages,
        )
        channel_values["title"] = title

        checkpoint["channel_values"] = channel_values
        channels_to_bump = ["messages", "title"]
        new_versions = _next_checkpoint_versions(
            checkpointer, channel_versions, tuple(channels_to_bump)
        )
        channel_versions.update(new_versions)
        checkpoint["channel_versions"] = channel_versions

        await checkpointer.aput(config, checkpoint, metadata, new_versions)
    except Exception:
        logger.warning(
            "Failed to persist checkpoint for banned-word response on thread %s",
            thread_id,
            exc_info=True,
        )


def _next_checkpoint_versions(
    checkpointer: Any,
    current_versions: dict[str, Any],
    channels: tuple[str, ...],
) -> dict[str, Any]:
    next_version = getattr(checkpointer, "get_next_version", None)
    versions: dict[str, Any] = {}
    for channel in channels:
        current = current_versions.get(channel)
        if callable(next_version):
            versions[channel] = next_version(current, None)
        elif isinstance(current, int):
            versions[channel] = current + 1
        elif isinstance(current, str):
            try:
                prefix = int(current.split(".", 1)[0])
            except (TypeError, ValueError):
                versions[channel] = current
            else:
                versions[channel] = str(prefix + 1)
        else:
            versions[channel] = 1
    return versions


def _merge_checkpoint_messages(
    existing: list[Any], current_turn: list[Any]
) -> list[Any]:
    """Append current-turn messages to existing checkpoint messages without duplicates."""
    merged = list(existing)
    seen_ids = {
        message_id
        for message in merged
        if (message_id := _message_id(message)) is not None
    }
    for message in current_turn:
        message_id = _message_id(message)
        if message_id is not None and message_id in seen_ids:
            continue
        merged.append(message)
        if message_id is not None:
            seen_ids.add(message_id)
    return merged


def _message_id(message: Any) -> str | None:
    raw_id = getattr(message, "id", None)
    if raw_id is None and isinstance(message, dict):
        raw_id = message.get("id")
    if raw_id is None:
        return None
    text = str(raw_id).strip()
    return text or None


async def sse_consumer(
    bridge: StreamBridge,
    record: RunRecord,
    request: Request,
    run_mgr: RunManager,
):
    """Async generator that yields SSE frames from the bridge.

    The ``finally`` block implements ``on_disconnect`` semantics:
    - ``cancel``: abort the background task on client disconnect.
    - ``continue``: let the task run; events are discarded.
    """
    last_event_id = request.headers.get("Last-Event-ID")
    try:
        async for entry in bridge.subscribe(record.run_id, last_event_id=last_event_id):
            if await request.is_disconnected():
                break

            if entry is HEARTBEAT_SENTINEL:
                yield ": heartbeat\n\n"
                continue

            if entry is END_SENTINEL:
                yield format_sse("end", None, event_id=entry.id or None)
                return

            data = entry.data
            if entry.event in ("values", "messages-tuple", "messages", "updates"):
                data = sanitize_user_visible_payload(data)
            yield format_sse(entry.event, data, event_id=entry.id or None)

    finally:
        if record.status in (RunStatus.pending, RunStatus.running):
            if record.on_disconnect == DisconnectMode.cancel:
                await run_mgr.cancel(record.run_id)
