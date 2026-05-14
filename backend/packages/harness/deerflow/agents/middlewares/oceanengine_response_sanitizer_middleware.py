"""Sanitize OceanEngine business-tool replies before they reach users."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.runtime import Runtime

_BUSINESS_TOOL_NAME = "oceanengine_local_project"
_API_ASSIGNMENT_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]*\s*=\s*[^,，、)）\s]+")
_UPPER_ENUM_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+(?![A-Za-z0-9_])")
_SNAKE_API_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])[a-z]+(?:_[a-z0-9]+)+(?![A-Za-z0-9_])")
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")


def _collect_codes(value: object, codes: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"enum_labels", "value_labels"} and isinstance(item, dict):
                for code in item:
                    if isinstance(code, str) and _ASCII_ALPHA_RE.search(code):
                        codes.add(code)
            elif key == "enum" and isinstance(item, list):
                for code in item:
                    if isinstance(code, str) and _ASCII_ALPHA_RE.search(code):
                        codes.add(code)
            _collect_codes(item, codes)
    elif isinstance(value, list):
        for item in value:
            _collect_codes(item, codes)


@lru_cache(maxsize=1)
def _known_rule_enum_pattern() -> re.Pattern[str] | None:
    rules_dir = Path(__file__).resolve().parents[6] / "skills/custom/oceanengine-local-project/rules"
    if not rules_dir.exists():
        return None

    codes: set[str] = set()
    for rule_path in rules_dir.glob("*.json"):
        try:
            _collect_codes(json.loads(rule_path.read_text(encoding="utf-8")), codes)
        except (OSError, json.JSONDecodeError):
            continue

    if not codes:
        return None

    alternatives = "|".join(re.escape(code) for code in sorted(codes, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternatives})(?![A-Za-z0-9_])")


def _uses_oceanengine_tool(messages: list[object]) -> bool:
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == _BUSINESS_TOOL_NAME:
            return True
        for tool_call in getattr(message, "tool_calls", []) or []:
            if tool_call.get("name") == _BUSINESS_TOOL_NAME:
                return True
    return False


def _has_oceanengine_tool_call(message: object) -> bool:
    for tool_call in getattr(message, "tool_calls", []) or []:
        if tool_call.get("name") == _BUSINESS_TOOL_NAME:
            return True
    return False


def _strip_code_tokens(content: str) -> str:
    token_patterns = tuple(
        pattern
        for pattern in (
            _UPPER_ENUM_TOKEN_RE,
            _SNAKE_API_TOKEN_RE,
            _known_rule_enum_pattern(),
        )
        if pattern is not None
    )
    sanitized = _API_ASSIGNMENT_RE.sub("", content)
    for pattern in token_patterns:
        sanitized = re.sub(rf"\s*[（(]\s*`+\s*{pattern.pattern}\s*`+\s*[）)]", "", sanitized)
        sanitized = re.sub(rf"\s*[（(]\s*{pattern.pattern}\s*[）)]", "", sanitized)
        sanitized = re.sub(rf"`+\s*{pattern.pattern}\s*`+", "", sanitized)
        sanitized = re.sub(rf"(?<=\S)\s+{pattern.pattern}", "", sanitized)
        sanitized = pattern.sub("", sanitized)
    sanitized = re.sub(r"\s*[（(]\s*`*\s*[）)]", "", sanitized)
    sanitized = re.sub(r"([：:])\s*[,，、]\s*", r"\1", sanitized)
    sanitized = re.sub(r"[,，、]\s*[,，、]+", "，", sanitized)
    sanitized = re.sub(r"[ \t]{2,}", " ", sanitized)
    sanitized = re.sub(r"\n[ \t]+", "\n", sanitized)
    return sanitized


def _business_failure_text(message: ToolMessage) -> str | None:
    if message.name != _BUSINESS_TOOL_NAME or not isinstance(message.content, str):
        return None

    try:
        payload = json.loads(message.content)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict) or payload.get("success") is not False:
        return None

    data = payload.get("data")
    if isinstance(data, dict):
        user_visible_text = data.get("user_visible_text")
        if isinstance(user_visible_text, str) and user_visible_text.strip():
            return user_visible_text.strip()

    errors = payload.get("errors")
    if isinstance(errors, list):
        messages: list[str] = []
        for item in errors:
            if isinstance(item, dict) and isinstance(item.get("message"), str) and item["message"].strip():
                messages.append(item["message"].strip())
        if messages:
            message_text = payload.get("message")
            prefix = f"{message_text.strip()}\n" if isinstance(message_text, str) and message_text.strip() else ""
            return prefix + "\n".join(messages)

    message_text = payload.get("message")
    if isinstance(message_text, str) and message_text.strip():
        return message_text.strip()
    return None


def _latest_blocking_business_failure(messages: list[object]) -> str | None:
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            return None
        if isinstance(message, ToolMessage):
            if message.name == _BUSINESS_TOOL_NAME:
                return _business_failure_text(message)
            failure_text = _business_failure_text(message)
            if failure_text:
                return failure_text
    return None


class OceanEngineResponseSanitizerMiddleware(AgentMiddleware[AgentState]):
    """Remove API code tokens from final replies for OceanEngine conversations."""

    @staticmethod
    def _build_forced_final_update(last_message: AIMessage, content: str) -> dict:
        additional_kwargs = dict(getattr(last_message, "additional_kwargs", {}) or {})
        for key in ("tool_calls", "function_call"):
            additional_kwargs.pop(key, None)

        response_metadata = dict(getattr(last_message, "response_metadata", {}) or {})
        if response_metadata.get("finish_reason") == "tool_calls":
            response_metadata["finish_reason"] = "stop"

        return {
            "content": content,
            "tool_calls": [],
            "additional_kwargs": additional_kwargs,
            "response_metadata": response_metadata,
        }

    def _apply(self, state: AgentState) -> dict | None:
        messages = state.get("messages", [])
        if not messages or not _uses_oceanengine_tool(messages):
            return None

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return None
        failure_text = _latest_blocking_business_failure(messages[:-1])
        if failure_text:
            forced_message = last_message.model_copy(
                update=self._build_forced_final_update(last_message, failure_text)
            )
            return {"messages": [forced_message]}
        if _has_oceanengine_tool_call(last_message) and last_message.content:
            return {"messages": [last_message.model_copy(update={"content": ""})]}
        if not isinstance(last_message.content, str):
            return None

        sanitized = _strip_code_tokens(last_message.content)
        if sanitized == last_message.content:
            return None

        return {"messages": [last_message.model_copy(update={"content": sanitized})]}

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state)
