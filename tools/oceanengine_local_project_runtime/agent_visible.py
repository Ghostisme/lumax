from __future__ import annotations

from typing import Any

AGENT_VISIBLE_ERROR_LIMIT = 5
PARAMETER_VALIDATION_VISIBLE_ERROR_LIMIT = 1
AGENT_VISIBLE_PAYLOAD_FIELD_LIMIT = 20
AGENT_VISIBLE_NORMALIZATION_LIMIT = 8


def _agent_payload_summary(payload: Any, normalizations: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "field_count": len(payload) if isinstance(payload, dict) else 0,
    }
    if isinstance(payload, dict):
        fields = sorted(str(field) for field in payload)
        summary["fields"] = fields[:AGENT_VISIBLE_PAYLOAD_FIELD_LIMIT]
        omitted_field_count = max(len(fields) - AGENT_VISIBLE_PAYLOAD_FIELD_LIMIT, 0)
        if omitted_field_count:
            summary["omitted_field_count"] = omitted_field_count

    if isinstance(normalizations, list):
        compact_normalizations: list[dict[str, Any]] = []
        for item in normalizations[:AGENT_VISIBLE_NORMALIZATION_LIMIT]:
            if not isinstance(item, dict):
                continue
            compact_normalizations.append(
                {
                    key: item[key]
                    for key in ("field", "source_field", "source_unit", "api_unit", "normalized_value")
                    if key in item
                }
            )
        summary["normalization_count"] = len(normalizations)
        summary["normalizations"] = compact_normalizations
        omitted_normalization_count = max(len(normalizations) - AGENT_VISIBLE_NORMALIZATION_LIMIT, 0)
        if omitted_normalization_count:
            summary["omitted_normalization_count"] = omitted_normalization_count
    else:
        summary["normalization_count"] = 0

    return summary


def _compact_agent_visible_errors(visible: dict[str, Any], data: dict[str, Any]) -> None:
    errors = visible.get("errors")
    if visible.get("success") is not False or not isinstance(errors, list):
        return

    is_parameter_validation = str(visible.get("message") or "").startswith("参数校验失败")
    visible_error_limit = (
        PARAMETER_VALIDATION_VISIBLE_ERROR_LIMIT
        if is_parameter_validation
        else AGENT_VISIBLE_ERROR_LIMIT
    )
    total = len(errors)
    compact_errors = errors[:visible_error_limit]
    visible["errors"] = compact_errors
    data["error_count"] = total
    data["omitted_error_count"] = max(total - len(compact_errors), 0)

    messages = [
        str(item.get("message"))
        for item in compact_errors
        if isinstance(item, dict) and item.get("message")
    ]
    if data["omitted_error_count"] and not is_parameter_validation:
        messages.append(f"还有 {data['omitted_error_count']} 条校验错误未展示，请先补充以上信息后重试。")
    if messages:
        data["user_visible_text"] = "\n".join(messages)
        data["reply_guidance"] = (
            "面向用户回复时直接展示 user_visible_text 中的中文校验提示，"
            "不要只输出字段名或原始 JSON。"
        )
        if is_parameter_validation:
            data["reply_guidance"] += " 本轮只追问 user_visible_text 中的一个问题，不要追加其它缺失参数。"
        if data.get("mcp_missing") or any(isinstance(item, dict) and item.get("field") == "mcp_tool_name" for item in compact_errors):
            data["reply_guidance"] += (
                " 当前能力因 MCP 工具缺失无法执行时，只说明缺失诊断和禁止绕路；"
                "不要建议或尝试接口地址、HTTP 请求、curl、SDK、浏览器后台、"
                "其它直连方式或替代接口。"
            )
        if any(isinstance(item, dict) and item.get("field") == "mcp" for item in compact_errors):
            failure_text = f"平台返回失败原因：{messages[0]}"
            visible["message"] = failure_text
            data["user_visible_text"] = failure_text
            data["reply_guidance"] += (
                " 这是平台或 MCP 返回的执行结果；不要要求用户提供环境参数，"
                "不要尝试添加 environment、host 等非官方字段，不要再次调用工具，"
                "不要调用 ask_clarification。"
            )


def _omit_confirmation_details(data: dict[str, Any]) -> None:
    confirmation = data.get("confirmation")
    if not isinstance(confirmation, dict) or "details" not in confirmation:
        return

    compact_confirmation = dict(confirmation)
    compact_confirmation.pop("details", None)
    compact_confirmation["details_omitted"] = True
    data["confirmation"] = compact_confirmation


def _omit_diagnostics(data: dict[str, Any]) -> None:
    diagnostics = data.pop("diagnostics", None)
    if diagnostics is None:
        return

    data["diagnostics_omitted"] = True
    if not isinstance(diagnostics, dict):
        return
    unmapped_fields = diagnostics.get("unmapped_response_fields")
    if isinstance(unmapped_fields, list):
        data["unmapped_response_field_count"] = len(unmapped_fields)


def agent_visible_result(result: dict[str, Any]) -> dict[str, Any]:
    visible = dict(result)
    data = dict(visible.get("data") or {})

    if "result" in data:
        data.pop("result")
        data["raw_result_omitted"] = True

    _omit_confirmation_details(data)
    _omit_diagnostics(data)

    display_text = data.get("display_text")
    if isinstance(display_text, str) and display_text.strip():
        data["user_visible_text"] = display_text
        data["reply_guidance"] = (
            "面向用户回复时只使用 user_visible_text 中的中文字段和值；"
            "禁止补充英文 API 字段名、英文枚举值、原始响应，"
            "也不要用括号、说明列或备注列展示英文枚举码；"
            "如果用户明确指定字段或给出示例字段，必须按用户示例字段和顺序展示；"
            "用户未指定字段时，完整保留 user_visible_text 的字段集合和顺序，不要自行摘要、改表头、重排或省略字段。"
        )

    if visible.get("success") is True and data.get("dry-run") is True and "payload" in data:
        payload = data.pop("payload")
        normalizations = data.pop("normalizations", [])
        data["payload_omitted"] = True
        data["payload_summary"] = _agent_payload_summary(payload, normalizations)

    _compact_agent_visible_errors(visible, data)

    visible["data"] = data
    return visible
