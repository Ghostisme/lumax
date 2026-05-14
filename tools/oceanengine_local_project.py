"""Native DeerFlow tool for OceanEngine local project operations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain.tools import tool

from deerflow.config import get_app_config
from tools.managed_mcp_guard import allow_managed_mcp_calls
from tools.oceanengine_local_project_runtime import endpoint_runner, rule_loader

BUSINESS_TOOL_NAME = "oceanengine_local_project"
SKILL_NAME = "oceanengine-local-project"
AGENT_VISIBLE_ERROR_LIMIT = 5
PARAMETER_VALIDATION_VISIBLE_ERROR_LIMIT = 1
AGENT_VISIBLE_PAYLOAD_FIELD_LIMIT = 20
AGENT_VISIBLE_NORMALIZATION_LIMIT = 8
logger = logging.getLogger(__name__)

_CAPABILITY_ALIASES: dict[str, str] = {
    "local-poi-get": "list-promotable-pois",
    "localPoiGet": "list-promotable-pois",
    "local-product-get": "list-promotable-products",
    "localProductGet": "list-promotable-products",
    "local-aweme-authorized-get": "list-authorized-awemes",
    "localAwemeAuthorizedGet": "list-authorized-awemes",
    "local-custom-audience-get": "list-custom-audiences",
    "localCustomAudienceGet": "list-custom-audiences",
    "local-multi-poi-id-poi-ids-get": "get-poi-ids-by-multi-poi-id",
    "localMultiPoiIdPoiIdsGet": "get-poi-ids-by-multi-poi-id",
    "local-tool-pack-list-get": "list-tool-packs",
    "localToolPackListGet": "list-tool-packs",
    "local-tool-pack-detail-get": "get-tool-pack-detail",
    "localToolPackDetailGet": "get-tool-pack-detail",
    "local-market-page-list-get": "list-market-pages",
    "localMarketPageListGet": "list-market-pages",
    "local-market-page-get": "get-market-page-detail",
    "localMarketPageGet": "get-market-page-detail",
    "local-im-account-get": "list-consult-awemes",
    "localImAccountGet": "list-consult-awemes",
    "local-project-week-schedule-batch-update": "batch-update-project-week-schedule",
    "localProjectWeekScheduleBatchUpdate": "batch-update-project-week-schedule",
}


def _skill_root() -> Path:
    return get_app_config().skills.get_skills_path() / "custom" / SKILL_NAME


def _normalize_capability(capability: str) -> str:
    return _CAPABILITY_ALIASES.get(capability, capability)


def _load_capability_rule(skill_root: Path, capability: str) -> dict[str, Any]:
    capability = _normalize_capability(capability)
    index_path = skill_root / "rules" / "index.json"
    rules_index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in rules_index.get("capabilities", []):
        if item.get("name") == capability:
            rule_path = skill_root / item["rule"]
            return rule_loader.load_rule_config(rule_path)
    supported = ", ".join(item.get("name", "") for item in rules_index.get("capabilities", []))
    raise ValueError(f"未知的 oceanengine-local-project 能力：{capability}。可选能力：{supported}")


def _enrich_result(result: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    data = dict(enriched.get("data") or {})
    data.setdefault("execution_source", "deerflow-native-tool")
    data.setdefault("business_tool_name", BUSINESS_TOOL_NAME)
    data.setdefault(
        "mcp_server_name",
        spec.get("mcp_server_name") or spec.get("mcp", {}).get("server") or "platform-agent-biz",
    )
    data.setdefault("mcp_tool_name", spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"))
    clarification_text = _clarification_user_visible_text(data.get("clarification"))
    if clarification_text:
        data.setdefault("user_visible_text", clarification_text)
    enriched["data"] = data
    return enriched


def _choice_card_lines(input_control: dict[str, Any]) -> list[str]:
    options = input_control.get("options")
    if not isinstance(options, list):
        return []

    lines: list[str] = []
    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            continue
        value = option.get("value")
        label = option.get("label")
        if value is None or not label:
            continue
        line = f"{index}. {label}（ID：{value}）"
        description = option.get("description")
        if isinstance(description, str) and description.strip():
            line = f"{line}：{description.strip()}"
        lines.append(line)
    return lines


def _clarification_user_visible_text(clarification: Any) -> str | None:
    if not isinstance(clarification, dict):
        return None
    input_control = clarification.get("input_control")
    if not isinstance(input_control, dict) or input_control.get("type") != "choice_cards":
        return None

    lines = _choice_card_lines(input_control)
    if not lines:
        return None

    question = clarification.get("question")
    head = str(question).strip() if question else "请选择一个候选项。"
    selection_mode = input_control.get("selection_mode")
    if selection_mode == "multiple":
        guidance = "请回复多个候选 ID 或名称。"
    else:
        guidance = "请回复一个候选 ID 或名称。"
    return "\n".join([head, *lines, guidance])


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
        clarification_text = _clarification_user_visible_text(data.get("clarification"))
        if clarification_text:
            data["user_visible_text"] = clarification_text
        data["reply_guidance"] = (
            "面向用户回复时直接展示 user_visible_text 中的中文校验提示，"
            "不要只输出字段名或原始 JSON。"
        )
        if is_parameter_validation:
            data["reply_guidance"] += " 本轮只追问 user_visible_text 中的一个问题，不要追加其它缺失参数。"


def _agent_visible_result(result: dict[str, Any]) -> dict[str, Any]:
    visible = dict(result)
    data = dict(visible.get("data") or {})

    if "result" in data:
        data.pop("result")
        data["raw_result_omitted"] = True

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


def run_oceanengine_local_project(capability: str, payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    capability = _normalize_capability(capability)
    skill_root = _skill_root()
    spec = _load_capability_rule(skill_root, capability)
    logger.info(
        "OceanEngine native business tool invoked: business_tool=%s capability=%s dry_run=%s mcp_server=%s mcp_tool=%s",
        BUSINESS_TOOL_NAME,
        capability,
        dry_run,
        spec.get("mcp_server_name") or spec.get("mcp", {}).get("server") or "platform-agent-biz",
        spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"),
    )

    with allow_managed_mcp_calls(BUSINESS_TOOL_NAME):
        result = endpoint_runner.run_endpoint(spec, payload, dry_run=dry_run)
    return _enrich_result(result, spec)


@tool("oceanengine_local_project", parse_docstring=True)
def oceanengine_local_project_tool(capability: str, payload_json: str, dry_run: bool = False) -> str:
    """Execute OceanEngine local project business operations through DeerFlow native logic.

    Covers local project create/update/list/detail/status/schedule operations, promotable POI/product/aweme/audience/tool-pack/market-page queries, and get-poi-ids-by-multi-poi-id. For end-to-end natural-language create-flow requests that mention 投手, 营销场景, 投放目标, 单元类型, 用户定向, 排期预算, 出价, or 视频素材, use oceanengine_local_project_create_flow instead of this lower-level project tool. When a matching request only lacks the local project account ID, ask only for that account ID. For an empty list boundary that the user explicitly provides, call this tool with the empty list so native validation returns the boundary error. For tool-pack lead collection mode, do not guess custom or intelligent selection from other user wording; pass explicit invalid wording through for native validation or ask for clarification.

    Args:
        capability: Capability name from oceanengine-local-project rules index, such as create-project or list-projects.
        payload_json: JSON object string containing user business input fields.
        dry_run: Only set true when the user explicitly asks for local validation without real MCP/API calls; normal queries and acceptance tests must keep false.
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
        if not isinstance(payload, dict):
            raise ValueError("payload_json 必须是 JSON object。")
        result = run_oceanengine_local_project(capability=capability, payload=payload, dry_run=dry_run)
        result = _agent_visible_result(result)
    except Exception as exc:
        result = {
            "success": False,
            "message": "OceanEngine 本地推业务工具执行失败。",
            "data": {
                "execution_source": "deerflow-native-tool",
                "business_tool_name": BUSINESS_TOOL_NAME,
                "capability": capability,
            },
            "errors": [{"field": "tool", "message": str(exc)}],
            "tool_name": BUSINESS_TOOL_NAME,
            "request_id": None,
        }
    return json.dumps(result, ensure_ascii=False)
