"""Background agent execution.

Runs an agent graph inside an ``asyncio.Task``, publishing events to
a :class:`StreamBridge` as they are produced.

Uses ``graph.astream(stream_mode=[...])`` which gives correct full-state
snapshots for ``values`` mode, proper ``{node: writes}`` for ``updates``,
and ``(chunk, metadata)`` tuples for ``messages`` mode.

Note: ``events`` mode is not supported through the gateway — it requires
``graph.astream_events()`` which cannot simultaneously produce ``values``
snapshots.  The JS open-source LangGraph API server works around this via
internal checkpoint callbacks that are not exposed in the Python public API.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
import json
import logging
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from langchain_core.messages import HumanMessage

from fastapi import HTTPException

from deerflow.config import get_tracing_config
from deerflow.config.app_config import AppConfig
from deerflow.metering import (
    MeteringRunContext,
    reset_metering_context,
    set_metering_context,
)
from deerflow.runtime.serialization import serialize
from deerflow.runtime.stream_bridge import StreamBridge
from deerflow.runtime.tenant import normalize_tenant_id

from .manager import RunManager, RunRecord
from .schemas import RunStatus

logger = logging.getLogger(__name__)

# Valid stream_mode values for LangGraph's graph.astream()
_VALID_LG_MODES = {
    "values",
    "updates",
    "checkpoints",
    "tasks",
    "debug",
    "messages",
    "custom",
}

try:
    from langfuse import propagate_attributes
except (
    Exception
):  # pragma: no cover - exercised in environments without langfuse installed
    propagate_attributes = None


@dataclass(frozen=True)
class RunContext:
    """Infrastructure dependencies for a single agent run.

    Groups checkpointer, store, and persistence-related singletons so that
    ``run_agent`` (and any future callers) receive one object instead of a
    growing list of keyword arguments.
    """

    checkpointer: Any
    store: Any | None = field(default=None)
    event_store: Any | None = field(default=None)
    run_events_config: Any | None = field(default=None)
    thread_store: Any | None = field(default=None)
    app_config: AppConfig | None = field(default=None)
    feedback_repo: Any | None = field(default=None)


def _compute_agent_factory_supports_app_config(agent_factory: Any) -> bool:
    try:
        return "app_config" in inspect.signature(agent_factory).parameters
    except (TypeError, ValueError):
        return False


@lru_cache(maxsize=128)
def _cached_agent_factory_supports_app_config(agent_factory: Any) -> bool:
    return _compute_agent_factory_supports_app_config(agent_factory)


def _agent_factory_supports_app_config(agent_factory: Any) -> bool:
    try:
        return _cached_agent_factory_supports_app_config(agent_factory)
    except TypeError:
        # Some callable instances are unhashable; fall back to a direct check.
        return _compute_agent_factory_supports_app_config(agent_factory)


def _langfuse_run_context(config: dict[str, Any]):
    metadata = config.get("metadata")
    session_id = (
        metadata.get("langfuse_session_id") if isinstance(metadata, dict) else None
    )

    if (
        not isinstance(session_id, str)
        or not session_id
        or propagate_attributes is None
        or not get_tracing_config().langfuse.is_configured
    ):
        return nullcontext()

    return propagate_attributes(session_id=session_id)


async def run_agent(
    bridge: StreamBridge,
    run_manager: RunManager,
    record: RunRecord,
    *,
    ctx: RunContext,
    agent_factory: Any,
    graph_input: dict,
    config: dict,
    stream_modes: list[str] | None = None,
    stream_subgraphs: bool = False,
    interrupt_before: list[str] | Literal["*"] | None = None,
    interrupt_after: list[str] | Literal["*"] | None = None,
) -> None:
    """Execute an agent in the background, publishing events to *bridge*."""

    # Unpack infrastructure dependencies from RunContext.
    checkpointer = ctx.checkpointer
    store = ctx.store
    feedback_repo = ctx.feedback_repo

    run_id = record.run_id
    thread_id = record.thread_id
    requested_modes: set[str] = set(stream_modes or ["values"])
    pre_run_checkpoint_id: str | None = None
    pre_run_snapshot: dict[str, Any] | None = None
    snapshot_capture_failed = False
    metering_context: MeteringRunContext | None = None
    metering_token: Any | None = None
    force_zero_settlement = False

    journal = None

    journal = None

    # Track whether "events" was requested but skipped
    if "events" in requested_modes:
        logger.info(
            "Run %s: 'events' stream_mode not supported in gateway (requires astream_events + checkpoint callbacks). Skipping.",
            run_id,
        )

    try:
        # 0. Pre-execution identity and quota check via lumax-service.
        # This must happen before any LangChain call, otherwise a rejected user
        # could still consume tokens.
        configurable = config.setdefault("configurable", {})
        tenant_id = normalize_tenant_id(configurable.get("tenant_id"))
        user_id = _as_user_id(configurable.get("user_id"))
        if tenant_id is None or user_id is None:
            raise HTTPException(
                status_code=401, detail="AI调用需要已认证的用户上下文。"
            )

        reporter = _get_usage_reporter_class().get_instance()
        quota_result = await reporter.check_quota(tenant_id, user_id)
        if not quota_result.get("allowed", False):
            raise HTTPException(
                status_code=429,
                detail=quota_result.get("message")
                or "Token quota exceeded. Please upgrade your plan or contact your administrator.",
            )

        user_context = (
            configurable.get("user_context")
            if isinstance(configurable.get("user_context"), dict)
            else {}
        )
        metering_context = MeteringRunContext(
            run_id=run_id,
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            username=str(
                user_context.get("nickname") or user_context.get("username") or ""
            ),
            dept_id=str(user_context.get("dept_id") or ""),
            agent_name=str(configurable.get("agent_name") or ""),
            skill_name=str(configurable.get("skill_name") or ""),
            model_name=str(
                configurable.get("model_name")
                or config.get("metadata", {}).get("model_name")
                or ""
            ),
            inference_mode=str(configurable.get("inference_mode") or "online"),
        )
        metering_token = set_metering_context(metering_context)

        # 1. Mark running
        await run_manager.set_status(run_id, RunStatus.running)

        # Snapshot the latest pre-run checkpoint so rollback can restore it.
        if checkpointer is not None:
            try:
                config_for_check = {
                    "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
                }
                ckpt_tuple = await checkpointer.aget_tuple(config_for_check)
                if ckpt_tuple is not None:
                    ckpt_config = getattr(ckpt_tuple, "config", {}).get(
                        "configurable", {}
                    )
                    pre_run_checkpoint_id = ckpt_config.get("checkpoint_id")
                    pre_run_snapshot = {
                        "checkpoint_ns": ckpt_config.get("checkpoint_ns", ""),
                        "checkpoint": copy.deepcopy(
                            getattr(ckpt_tuple, "checkpoint", {})
                        ),
                        "metadata": copy.deepcopy(getattr(ckpt_tuple, "metadata", {})),
                        "pending_writes": copy.deepcopy(
                            getattr(ckpt_tuple, "pending_writes", []) or []
                        ),
                    }
            except Exception:
                snapshot_capture_failed = True
                logger.warning(
                    "Could not capture pre-run checkpoint snapshot for run %s",
                    run_id,
                    exc_info=True,
                )

        # 2. Publish metadata — useStream needs both run_id AND thread_id
        await bridge.publish(
            run_id,
            "metadata",
            {
                "run_id": run_id,
                "thread_id": thread_id,
            },
        )

        # 3. Build the agent
        from langchain_core.runnables import RunnableConfig
        from langgraph.runtime import Runtime

        # Inject runtime context so middlewares can access thread_id
        # (langgraph-cli does this automatically; we must do it manually)
        runtime = Runtime(
            context={"thread_id": thread_id, "run_id": run_id}, store=store
        )
        # If the caller already set a ``context`` key (LangGraph >= 0.6.0
        # prefers it over ``configurable`` for thread-level data), make
        # sure ``thread_id`` is available there too.
        if "context" in config and isinstance(config["context"], dict):
            config["context"].setdefault("thread_id", thread_id)
            config["context"].setdefault("run_id", run_id)
        config.setdefault("configurable", {})["__pregel_runtime"] = runtime

        # Inject RunJournal as a LangChain callback handler.
        # on_llm_end captures token usage; on_chain_start/end captures lifecycle.
        if journal is not None:
            config.setdefault("callbacks", []).append(journal)

        runnable_config = RunnableConfig(**config)
        _custom_mws = configurable.pop("__custom_middlewares", None)
        if ctx.app_config is not None and _agent_factory_supports_app_config(
            agent_factory
        ):
            agent = agent_factory(
                config=runnable_config,
                app_config=ctx.app_config,
                custom_middlewares=_custom_mws,
            )
        else:
            agent = agent_factory(
                config=runnable_config, custom_middlewares=_custom_mws
            )

        # 4. Attach checkpointer and store
        if checkpointer is not None:
            agent.checkpointer = checkpointer
        if store is not None:
            agent.store = store

        # 5. Set interrupt nodes
        if interrupt_before:
            agent.interrupt_before_nodes = interrupt_before
        if interrupt_after:
            agent.interrupt_after_nodes = interrupt_after

        # 6. Build LangGraph stream_mode list
        #    "events" is NOT a valid astream mode — skip it
        #    "messages-tuple" maps to LangGraph's "messages" mode
        lg_modes: list[str] = []
        for m in requested_modes:
            if m == "messages-tuple":
                lg_modes.append("messages")
            elif m == "events":
                # Skipped — see log above
                continue
            elif m in _VALID_LG_MODES:
                lg_modes.append(m)
        if not lg_modes:
            lg_modes = ["values"]

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for m in lg_modes:
            if m not in seen:
                seen.add(m)
                deduped.append(m)
        lg_modes = deduped

        logger.info(
            "Run %s: streaming with modes %s (requested: %s)",
            run_id,
            lg_modes,
            requested_modes,
        )

        # 7. Stream using graph.astream. When Langfuse sessions are configured,
        # propagate the session_id at the run boundary so root observations and
        # their children are grouped consistently in Langfuse Sessions.
        with _langfuse_run_context(config):
            if len(lg_modes) == 1 and not stream_subgraphs:
                # Single mode, no subgraphs: astream yields raw chunks
                single_mode = lg_modes[0]
                async for chunk in agent.astream(
                    graph_input, config=runnable_config, stream_mode=single_mode
                ):
                    if record.abort_event.is_set():
                        logger.info("Run %s abort requested — stopping", run_id)
                        break
                    sse_event = _lg_mode_to_sse_event(single_mode)
                    await bridge.publish(
                        run_id, sse_event, serialize(chunk, mode=single_mode)
                    )
            else:
                # Multiple modes or subgraphs: astream yields tuples
                async for item in agent.astream(
                    graph_input,
                    config=runnable_config,
                    stream_mode=lg_modes,
                    subgraphs=stream_subgraphs,
                ):
                    if record.abort_event.is_set():
                        logger.info("Run %s abort requested — stopping", run_id)
                        break

                    mode, chunk = _unpack_stream_item(item, lg_modes, stream_subgraphs)
                    if mode is None:
                        continue

                    sse_event = _lg_mode_to_sse_event(mode)
                    await bridge.publish(run_id, sse_event, serialize(chunk, mode=mode))

        # 8. Final status
        if record.abort_event.is_set():
            action = record.abort_action
            if action == "rollback":
                await run_manager.set_status(
                    run_id, RunStatus.error, error="Rolled back by user"
                )
                try:
                    await _rollback_to_pre_run_checkpoint(
                        checkpointer=checkpointer,
                        thread_id=thread_id,
                        run_id=run_id,
                        pre_run_checkpoint_id=pre_run_checkpoint_id,
                        pre_run_snapshot=pre_run_snapshot,
                        snapshot_capture_failed=snapshot_capture_failed,
                    )
                    logger.info(
                        "Run %s rolled back to pre-run checkpoint %s",
                        run_id,
                        pre_run_checkpoint_id,
                    )
                except Exception:
                    logger.warning(
                        "Failed to rollback checkpoint for run %s",
                        run_id,
                        exc_info=True,
                    )
            else:
                await run_manager.set_status(run_id, RunStatus.interrupted)
        else:
            await run_manager.set_status(run_id, RunStatus.success)
            if feedback_repo is not None:
                try:
                    configurable = (
                        config.get("configurable", {})
                        if isinstance(config, dict)
                        else {}
                    )
                    context = (
                        config.get("context", {}) if isinstance(config, dict) else {}
                    )
                    runtime_options = {
                        **(configurable if isinstance(configurable, dict) else {}),
                        **(context if isinstance(context, dict) else {}),
                    }
                    await feedback_repo.ensure_neutral_for_run(
                        run_id=run_id,
                        thread_id=thread_id,
                        user_id=_as_user_id(runtime_options.get("user_id")),
                        message_id=await _extract_feedback_message_id(
                            checkpointer=checkpointer,
                            thread_id=thread_id,
                            fallback_messages=graph_input.get("messages", []),
                        ),
                        agent_id=record.assistant_id or "lead_agent",
                        agent_name=str(runtime_options.get("agent_name") or ""),
                    )
                except Exception:
                    logger.warning(
                        "Run %s neutral feedback creation failed", run_id, exc_info=True
                    )

    except asyncio.CancelledError:
        action = record.abort_action
        if action == "rollback":
            await run_manager.set_status(
                run_id, RunStatus.error, error="Rolled back by user"
            )
            try:
                await _rollback_to_pre_run_checkpoint(
                    checkpointer=checkpointer,
                    thread_id=thread_id,
                    run_id=run_id,
                    pre_run_checkpoint_id=pre_run_checkpoint_id,
                    pre_run_snapshot=pre_run_snapshot,
                    snapshot_capture_failed=snapshot_capture_failed,
                )
                logger.info("Run %s was cancelled and rolled back", run_id)
            except Exception:
                logger.warning(
                    "Run %s cancellation rollback failed", run_id, exc_info=True
                )
        else:
            await run_manager.set_status(run_id, RunStatus.interrupted)
            logger.info("Run %s was cancelled", run_id)

    except Exception as exc:
        error_msg = f"{exc}"
        logger.exception("Run %s failed: %s", run_id, error_msg)
        await run_manager.set_status(run_id, RunStatus.error, error=error_msg)
        await bridge.publish(
            run_id,
            "error",
            {
                "message": error_msg,
                "name": type(exc).__name__,
            },
        )

    finally:
        if metering_context is not None:
            try:
                await _report_lumax_settlement(
                    metering_context=metering_context,
                    record=record,
                    checkpointer=checkpointer,
                    graph_input=graph_input,
                    force_zero_tokens=force_zero_settlement,
                )
            except Exception as exc:
                logger.exception("Run %s usage settlement failed: %s", run_id, exc)
            finally:
                if metering_token is not None:
                    reset_metering_context(metering_token)
        await bridge.publish_end(run_id)
        asyncio.create_task(bridge.cleanup(run_id, delay=60))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_user_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _usage_reporter_module() -> Any:
    return import_module("app.gateway.usage_reporter")


def _get_usage_reporter_class() -> Any:
    return _usage_reporter_module().UsageReporter


def _usage_settlement_class() -> Any:
    return _usage_reporter_module().UsageSettlement


def _usage_settlement_message_class() -> Any:
    return _usage_reporter_module().UsageSettlementMessage


async def _report_lumax_settlement(
    *,
    metering_context: MeteringRunContext,
    record: RunRecord,
    checkpointer: Any,
    graph_input: dict,
    force_zero_tokens: bool = False,
) -> None:
    messages = await _extract_settlement_messages(
        checkpointer=checkpointer,
        thread_id=metering_context.thread_id,
        run_id=metering_context.run_id,
        fallback_messages=graph_input.get("messages", []),
    )
    logger.info(
        "Run %s settlement: thread=%s messages_count=%d force_zero=%s",
        metering_context.run_id,
        metering_context.thread_id,
        len(messages),
        force_zero_tokens,
    )
    if not messages:
        raw_msgs = await _extract_final_messages(
            checkpointer=checkpointer,
            thread_id=metering_context.thread_id,
            fallback_messages=graph_input.get("messages", []),
        )
        logger.warning(
            "Run %s settlement has 0 messages! raw_messages_count=%d roles=%s",
            metering_context.run_id,
            len(raw_msgs),
            [_message_role(m) for m in raw_msgs[-6:]],
        )
    status = _to_settlement_status(record.status)
    error_message = record.error or "; ".join(metering_context.errors) or None
    title = await _extract_settlement_title(
        checkpointer=checkpointer, thread_id=metering_context.thread_id
    )
    settlement = _usage_settlement_class()(
        idempotency_key=f"deerflow:{metering_context.run_id}:settlement",
        tenant_id=metering_context.tenant_id,
        user_id=metering_context.user_id,
        username=metering_context.username,
        dept_id=metering_context.dept_id,
        thread_id=metering_context.thread_id,
        run_id=metering_context.run_id,
        model_name=metering_context.model_name,
        title=title,
        agent_name=metering_context.agent_name,
        skill_name=metering_context.skill_name,
        tokens_in=0 if force_zero_tokens else metering_context.usage.input_tokens,
        tokens_out=0 if force_zero_tokens else metering_context.usage.output_tokens,
        tokens_total=0
        if force_zero_tokens
        else metering_context.usage.as_dict()["total_tokens"],
        cache_read_tokens=0
        if force_zero_tokens
        else metering_context.usage.cache_read_tokens,
        cache_write_tokens=0
        if force_zero_tokens
        else metering_context.usage.cache_write_tokens,
        reasoning_tokens=0
        if force_zero_tokens
        else metering_context.usage.reasoning_tokens,
        inference_mode=metering_context.inference_mode,
        tool_calls_count=0 if force_zero_tokens else metering_context.tool_calls_count,
        response_time_ms=metering_context.duration_ms,
        status=status,
        error_message=error_message,
        messages=messages,
    )
    await _get_usage_reporter_class().get_instance().report_settlement(settlement)


async def _extract_settlement_title(*, checkpointer: Any, thread_id: str) -> str:
    if checkpointer is None or not thread_id:
        return ""
    try:
        ckpt_tuple = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        )
    except Exception:
        logger.debug(
            "Failed to read final checkpoint title for thread %s",
            thread_id,
            exc_info=True,
        )
        return ""
    if ckpt_tuple is None:
        return ""
    channel_values = getattr(ckpt_tuple, "checkpoint", {}).get("channel_values", {})
    if not isinstance(channel_values, dict):
        return ""
    title = channel_values.get("title")
    return str(title).strip() if title is not None else ""


async def _extract_settlement_messages(
    *,
    checkpointer: Any,
    thread_id: str,
    run_id: str,
    fallback_messages: list[Any],
) -> list[Any]:
    raw_messages = await _extract_final_messages(
        checkpointer=checkpointer,
        thread_id=thread_id,
        fallback_messages=fallback_messages,
    )

    current_turn_messages = _current_turn_messages(raw_messages)
    settlement_messages: list[Any] = []
    settled_index = 0
    for message in current_turn_messages:
        role = _message_role(message)
        if role not in {"user", "assistant"}:
            continue
        canonical = _message_id(message)
        if canonical:
            storage_message_id = f"{run_id}:{role}:{canonical}"
        else:
            storage_message_id = f"{run_id}:{role}:{settled_index}"
        settlement_messages.append(
            _usage_settlement_message_class()(
                message_id=storage_message_id,
                role=role,
                content=_message_content(message),
                message_index=settled_index,
            )
        )
        settled_index += 1
    return settlement_messages


async def _extract_feedback_message_id(
    *,
    checkpointer: Any,
    thread_id: str,
    fallback_messages: list[Any],
) -> str | None:
    raw_messages = await _extract_final_messages(
        checkpointer=checkpointer,
        thread_id=thread_id,
        fallback_messages=fallback_messages,
    )
    for message in reversed(_current_turn_messages(raw_messages)):
        if _message_role(message) == "assistant":
            return _message_id(message)
    return None


async def _extract_final_messages(
    *,
    checkpointer: Any,
    thread_id: str,
    fallback_messages: list[Any],
) -> list[Any]:
    raw_messages = fallback_messages
    if checkpointer is not None:
        try:
            ckpt_tuple = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
            )
            if ckpt_tuple is not None:
                checkpoint_data = getattr(ckpt_tuple, "checkpoint", {})
                channel_values = checkpoint_data.get(
                    "channel_values", {}
                ) if isinstance(checkpoint_data, dict) else {}
                checkpoint_messages = channel_values.get("messages")
                if isinstance(checkpoint_messages, list) and checkpoint_messages:
                    raw_messages = checkpoint_messages
                else:
                    cv_keys = (
                        list(channel_values.keys())
                        if isinstance(channel_values, dict)
                        else type(channel_values).__name__
                    )
                    msg_t = (
                        type(checkpoint_messages).__name__
                        if checkpoint_messages is not None
                        else "None"
                    )
                    logger.warning(
                        "Checkpoint for thread %s has no messages: "
                        "checkpoint_type=%s channel_values_keys=%s messages_type=%s",
                        thread_id,
                        type(checkpoint_data).__name__,
                        cv_keys,
                        msg_t,
                    )
            else:
                logger.warning(
                    "No checkpoint tuple found for thread %s, using fallback (%d msgs)",
                    thread_id,
                    len(fallback_messages),
                )
        except Exception:
            logger.warning(
                "Failed to read final checkpoint messages for thread %s",
                thread_id,
                exc_info=True,
            )
    return raw_messages


def _current_turn_messages(messages: list[Any]) -> list[Any]:
    if not messages:
        return []
    start_index = 0
    for index, message in enumerate(messages):
        if _message_role(message) == "user":
            start_index = index
    return messages[start_index:]


def _message_role(message: Any) -> str:
    raw_role = getattr(message, "type", None) or getattr(message, "role", None)
    if raw_role is None and isinstance(message, dict):
        raw_role = message.get("type") or message.get("role")
    role = str(raw_role or "").lower()
    if role in {"human", "user"}:
        return "user"
    if role in {"ai", "assistant"}:
        return "assistant"
    return role or "unknown"


def _message_id(message: Any) -> str | None:
    value = getattr(message, "id", None)
    if value is None and isinstance(message, dict):
        value = message.get("id") or message.get("message_id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _message_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content", "")
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except TypeError:
        return str(content)


def _message_text_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text")
                if isinstance(value, str):
                    parts.append(value)
                    continue
                value = item.get("content")
                if isinstance(value, str):
                    parts.append(value)
        return " ".join(parts)
    return str(content or "")


def _to_settlement_status(status: RunStatus) -> str:
    if status is RunStatus.success:
        return "completed"
    if status is RunStatus.interrupted:
        return "cancelled"
    if status is RunStatus.error:
        return "failed"
    return "running"


async def _call_checkpointer_method(
    checkpointer: Any, async_name: str, sync_name: str, *args: Any, **kwargs: Any
) -> Any:
    """Call a checkpointer method, supporting async and sync variants."""
    method = getattr(checkpointer, async_name, None) or getattr(
        checkpointer, sync_name, None
    )
    if method is None:
        raise AttributeError(f"Missing checkpointer method: {async_name}/{sync_name}")
    result = method(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def _rollback_to_pre_run_checkpoint(
    *,
    checkpointer: Any,
    thread_id: str,
    run_id: str,
    pre_run_checkpoint_id: str | None,
    pre_run_snapshot: dict[str, Any] | None,
    snapshot_capture_failed: bool,
) -> None:
    """Restore thread state to the checkpoint snapshot captured before run start."""
    if checkpointer is None:
        logger.info(
            "Run %s rollback requested but no checkpointer is configured", run_id
        )
        return

    if snapshot_capture_failed:
        logger.warning(
            "Run %s rollback skipped: pre-run checkpoint snapshot capture failed",
            run_id,
        )
        return

    if pre_run_snapshot is None:
        await _call_checkpointer_method(
            checkpointer, "adelete_thread", "delete_thread", thread_id
        )
        logger.info("Run %s rollback reset thread %s to empty state", run_id, thread_id)
        return

    checkpoint_to_restore = None
    metadata_to_restore: dict[str, Any] = {}
    checkpoint_ns = ""
    checkpoint = pre_run_snapshot.get("checkpoint")
    if not isinstance(checkpoint, dict):
        logger.warning(
            "Run %s rollback skipped: invalid pre-run checkpoint snapshot", run_id
        )
        return
    checkpoint_to_restore = checkpoint
    if checkpoint_to_restore.get("id") is None and pre_run_checkpoint_id is not None:
        checkpoint_to_restore = {**checkpoint_to_restore, "id": pre_run_checkpoint_id}
    if checkpoint_to_restore.get("id") is None:
        logger.warning(
            "Run %s rollback skipped: pre-run checkpoint has no checkpoint id", run_id
        )
        return
    metadata = pre_run_snapshot.get("metadata", {})
    metadata_to_restore = metadata if isinstance(metadata, dict) else {}
    raw_checkpoint_ns = pre_run_snapshot.get("checkpoint_ns")
    checkpoint_ns = raw_checkpoint_ns if isinstance(raw_checkpoint_ns, str) else ""

    channel_versions = checkpoint_to_restore.get("channel_versions")
    new_versions = dict(channel_versions) if isinstance(channel_versions, dict) else {}

    restore_config = {
        "configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns}
    }
    restored_config = await _call_checkpointer_method(
        checkpointer,
        "aput",
        "put",
        restore_config,
        checkpoint_to_restore,
        metadata_to_restore if isinstance(metadata_to_restore, dict) else {},
        new_versions,
    )
    if not isinstance(restored_config, dict):
        raise RuntimeError(
            f"Run {run_id} rollback restore returned invalid config: expected dict"
        )
    restored_configurable = restored_config.get("configurable", {})
    if not isinstance(restored_configurable, dict):
        raise RuntimeError(
            f"Run {run_id} rollback restore returned invalid config payload"
        )
    restored_checkpoint_id = restored_configurable.get("checkpoint_id")
    if not restored_checkpoint_id:
        raise RuntimeError(
            f"Run {run_id} rollback restore did not return checkpoint_id"
        )

    pending_writes = pre_run_snapshot.get("pending_writes", [])
    if not pending_writes:
        return

    writes_by_task: dict[str, list[tuple[str, Any]]] = {}
    for item in pending_writes:
        if not isinstance(item, (tuple, list)) or len(item) != 3:
            raise RuntimeError(
                f"Run {run_id} rollback failed: pending_write is not a 3-tuple: {item!r}"
            )
        task_id, channel, value = item
        if not isinstance(channel, str):
            raise RuntimeError(
                f"Run {run_id} rollback failed: pending_write has non-string channel: task_id={task_id!r}, channel={channel!r}"
            )
        writes_by_task.setdefault(str(task_id), []).append((channel, value))

    for task_id, writes in writes_by_task.items():
        await _call_checkpointer_method(
            checkpointer,
            "aput_writes",
            "put_writes",
            restored_config,
            writes,
            task_id=task_id,
        )


def _lg_mode_to_sse_event(mode: str) -> str:
    """Map LangGraph internal stream_mode name to SSE event name.

    LangGraph's ``astream(stream_mode="messages")`` produces message
    tuples.  The SSE protocol calls this ``messages-tuple`` when the
    client explicitly requests it, but the default SSE event name used
    by LangGraph Platform is simply ``"messages"``.
    """
    # All LG modes map 1:1 to SSE event names — "messages" stays "messages"
    return mode


def _extract_human_message(graph_input: dict) -> HumanMessage | None:
    """Extract or construct a HumanMessage from graph_input for event recording.

    Returns a LangChain HumanMessage so callers can use .model_dump() to get
    the checkpoint-aligned serialization format.
    """
    from langchain_core.messages import HumanMessage

    messages = graph_input.get("messages")
    if not messages:
        return None
    last = messages[-1] if isinstance(messages, list) else messages
    if isinstance(last, HumanMessage):
        return last
    if isinstance(last, str):
        return HumanMessage(content=last) if last else None
    if hasattr(last, "content"):
        content = last.content
        return HumanMessage(content=content)
    if isinstance(last, dict):
        content = last.get("content", "")
        return HumanMessage(content=content) if content else None
    return None


def _unpack_stream_item(
    item: Any,
    lg_modes: list[str],
    stream_subgraphs: bool,
) -> tuple[str | None, Any]:
    """Unpack a multi-mode or subgraph stream item into (mode, chunk).

    Returns ``(None, None)`` if the item cannot be parsed.
    """
    if stream_subgraphs:
        if isinstance(item, tuple) and len(item) == 3:
            _ns, mode, chunk = item
            return str(mode), chunk
        if isinstance(item, tuple) and len(item) == 2:
            mode, chunk = item
            return str(mode), chunk
        return None, None

    if isinstance(item, tuple) and len(item) == 2:
        mode, chunk = item
        return str(mode), chunk

    # Fallback: single-element output from first mode
    return lg_modes[0] if lg_modes else None, item
