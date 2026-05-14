"""Gateway filtering for normal end-user visible payloads."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import BaseMessage

_INTERNAL_REASONING_RE = re.compile(
    r"(^|\n)\s*(SESSION INTENT|SUMMARY)\s*(\n|$)|"
    r"nacos-mcp-router_|oceanengine_local_|/mnt/skills/|skills/custom/oceanengine-local-|"
    r"local[A-Z][A-Za-z0-9]*(Get|Create|Update|List)"
)
_INTERNAL_ASSISTANT_CONTENT_RE = re.compile(
    r"nacos-mcp-router_|oceanengine_local_|/mnt/skills/|skills/custom/oceanengine-local-|"
    r"local[A-Z][A-Za-z0-9]*(Get|Create|Update|List)|"
    r"(读取|调用|执行).{0,60}(技能文件|参考文件|参考文档|规则文件|业务工具)|"
    r"读取|调用|技能|技能文件|参考文件|参考文档|规则文件|业务工具|"
    r"接口文档|详细文档|规则配置|根据文档|根据技能|参数要求|references/|rules/|"
    r"local_account_id|delivery_goal|poi_ids|payload_json|dry_run"
)
_OCEANENGINE_NATIVE_TOOL_PREFIX = "oceanengine_local_"
_ASSISTANT_MESSAGE_TYPES = {"ai", "AIMessage", "AIMessageChunk"}
_STRUCTURED_CLARIFICATION_MESSAGE_TYPES = {"tool", "ToolMessage"}
_CLARIFICATION_KEYS = ("version", "reason", "field", "field_label", "question")
_INPUT_CONTROL_KEYS = ("type", "selection_mode", "value_type", "placeholder", "page_info")
_OPTION_KEYS = ("value", "label", "description", "metadata")


def _is_internal_oceanengine_tool_call(tool_call: dict[str, Any]) -> bool:
    name = tool_call.get("name")
    if isinstance(name, str) and name.startswith(_OCEANENGINE_NATIVE_TOOL_PREFIX):
        return True
    if name == "read_file":
        return True
    return False


def _is_assistant_message(data: dict[str, Any]) -> bool:
    message_type = data.get("type")
    if message_type == "human":
        return False
    if isinstance(message_type, str) and message_type in _ASSISTANT_MESSAGE_TYPES:
        return True
    return data.get("content") is not None


def _safe_choice_options(options: Any) -> list[dict[str, Any]]:
    if not isinstance(options, list):
        return []
    safe_options: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        safe_option = {key: option[key] for key in _OPTION_KEYS if key in option}
        if "value" in safe_option and not isinstance(safe_option["value"], str):
            safe_option["value"] = str(safe_option["value"])
        if safe_option:
            safe_options.append(safe_option)
    return safe_options


def _safe_input_control(input_control: Any) -> dict[str, Any] | None:
    if not isinstance(input_control, dict):
        return None
    safe = {key: input_control[key] for key in _INPUT_CONTROL_KEYS if key in input_control}
    if "options" in input_control:
        options = _safe_choice_options(input_control.get("options"))
        if options:
            safe["options"] = options
    return safe if safe.get("type") else None


def _load_tool_content_json(content: Any) -> dict[str, Any] | None:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return content if isinstance(content, dict) else None


def _extract_structured_clarification(data: dict[str, Any]) -> dict[str, Any] | None:
    message_type = data.get("type")
    if isinstance(message_type, str) and message_type not in _STRUCTURED_CLARIFICATION_MESSAGE_TYPES:
        return None
    name = data.get("name")
    if not (isinstance(name, str) and name.startswith(_OCEANENGINE_NATIVE_TOOL_PREFIX)):
        return None

    parsed = _load_tool_content_json(data.get("content"))
    if not isinstance(parsed, dict):
        return None
    payload_data = parsed.get("data")
    if not isinstance(payload_data, dict):
        return None
    clarification = payload_data.get("clarification")
    if not isinstance(clarification, dict):
        return None

    input_control = _safe_input_control(clarification.get("input_control"))
    if input_control is None:
        return None

    safe = {key: clarification[key] for key in _CLARIFICATION_KEYS if key in clarification}
    safe["input_control"] = input_control
    user_visible_text = payload_data.get("user_visible_text") or clarification.get("question")
    if isinstance(user_visible_text, str) and user_visible_text.strip():
        safe["user_visible_text"] = user_visible_text
    return safe


def _payload_structured_clarifications(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []
    clarifications: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        clarification = _extract_structured_clarification(message)
        if clarification is not None:
            clarifications.append(clarification)
    return clarifications


def _safe_choice_options(options: Any) -> list[dict[str, Any]]:
    if not isinstance(options, list):
        return []
    safe_options: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        safe_option = {key: option[key] for key in _OPTION_KEYS if key in option}
        if "value" in safe_option and not isinstance(safe_option["value"], str):
            safe_option["value"] = str(safe_option["value"])
        if safe_option:
            safe_options.append(safe_option)
    return safe_options


def _safe_input_control(input_control: Any) -> dict[str, Any] | None:
    if not isinstance(input_control, dict):
        return None
    safe = {
        key: input_control[key] for key in _INPUT_CONTROL_KEYS if key in input_control
    }
    if "options" in input_control:
        options = _safe_choice_options(input_control.get("options"))
        if options:
            safe["options"] = options
    return safe if safe.get("type") else None


def _load_tool_content_json(content: Any) -> dict[str, Any] | None:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return content if isinstance(content, dict) else None


def _extract_structured_clarification(data: dict[str, Any]) -> dict[str, Any] | None:
    message_type = data.get("type")
    if (
        isinstance(message_type, str)
        and message_type not in _STRUCTURED_CLARIFICATION_MESSAGE_TYPES
    ):
        return None
    name = data.get("name")
    if not (isinstance(name, str) and name.startswith(_OCEANENGINE_NATIVE_TOOL_PREFIX)):
        return None

    parsed = _load_tool_content_json(data.get("content"))
    if not isinstance(parsed, dict):
        return None
    payload_data = parsed.get("data")
    if not isinstance(payload_data, dict):
        return None
    clarification = payload_data.get("clarification")
    if not isinstance(clarification, dict):
        return None

    input_control = _safe_input_control(clarification.get("input_control"))
    if input_control is None:
        return None

    safe = {
        key: clarification[key] for key in _CLARIFICATION_KEYS if key in clarification
    }
    safe["input_control"] = input_control
    user_visible_text = payload_data.get("user_visible_text") or clarification.get(
        "question"
    )
    if isinstance(user_visible_text, str) and user_visible_text.strip():
        safe["user_visible_text"] = user_visible_text
    return safe


def _payload_structured_clarifications(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []
    clarifications: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        clarification = _extract_structured_clarification(message)
        if clarification is not None:
            clarifications.append(clarification)
    return clarifications


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                for key in ("text", "content"):
                    value = item.get(key)
                    if isinstance(value, str):
                        parts.append(value)
        return "\n".join(parts)
    return ""


def _sanitize_message_dict(data: dict[str, Any]) -> dict[str, Any]:
    additional_kwargs = data.get("additional_kwargs")
    if not isinstance(additional_kwargs, dict):
        additional_kwargs = {}
    changed = False
    structured_clarification = _extract_structured_clarification(data)

    reasoning_content = additional_kwargs.get("reasoning_content")
    if isinstance(reasoning_content, str) and _INTERNAL_REASONING_RE.search(
        reasoning_content
    ):
        additional_kwargs = dict(additional_kwargs)
        additional_kwargs.pop("reasoning_content", None)
        changed = True

    is_summary_message = data.get("name") == "summary"
    if is_summary_message:
        additional_kwargs = dict(additional_kwargs)
        additional_kwargs["hide_from_ui"] = True
        changed = True

    calls: list[dict[str, Any]] = []
    for key in ("tool_calls", "tool_call_chunks"):
        value = data.get(key)
        if isinstance(value, list):
            calls.extend(item for item in value if isinstance(item, dict))
    if any(_is_internal_oceanengine_tool_call(call) for call in calls):
        additional_kwargs = dict(additional_kwargs)
        additional_kwargs["hide_from_ui"] = True
        changed = True

    if structured_clarification is not None:
        additional_kwargs = dict(additional_kwargs)
        additional_kwargs["hide_from_ui"] = True
        additional_kwargs["structured_clarifications"] = [structured_clarification]
        changed = True

    # Temporary recovery path: the broad internal-content regex hides normal
    # assistant replies containing words like "技能". Keep the rest of the
    # visibility guardrails active while this rule is made more precise.
    has_internal_content = False
    if has_internal_content:
        additional_kwargs = dict(additional_kwargs)
        additional_kwargs["hide_from_ui"] = True
        changed = True

    if not changed:
        return data
    sanitized = dict(data)
    sanitized["additional_kwargs"] = additional_kwargs
    if structured_clarification is not None:
        sanitized["name"] = "structured_clarification"
        sanitized["content"] = structured_clarification.get("user_visible_text", "")
    if is_summary_message:
        sanitized["content"] = ""
    if has_internal_content:
        sanitized["content"] = ""
    return sanitized


def sanitize_user_visible_payload(payload: Any) -> Any:
    """Remove or hide internal diagnostics from normal user-visible payloads."""
    if isinstance(payload, BaseMessage):
        return _sanitize_message_dict(payload.model_dump(mode="json"))
    if isinstance(payload, dict):
        structured_clarifications = _payload_structured_clarifications(payload)
        sanitized = {
            key: sanitize_user_visible_payload(value) for key, value in payload.items()
        }
        if structured_clarifications and "structured_clarifications" not in sanitized:
            sanitized["structured_clarifications"] = structured_clarifications
        return _sanitize_message_dict(sanitized)
    if isinstance(payload, tuple):
        return [sanitize_user_visible_payload(item) for item in payload]
    if isinstance(payload, list):
        return [sanitize_user_visible_payload(item) for item in payload]
    return payload
