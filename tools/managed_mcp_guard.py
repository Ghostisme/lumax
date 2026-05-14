"""Guardrails for MCP tools owned by native business tools."""

from __future__ import annotations

import contextvars
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_allowed_business_tool: contextvars.ContextVar[str | None] = contextvars.ContextVar("managed_mcp_allowed_business_tool", default=None)

_MANAGED_MCP_TOOLS: dict[tuple[str, str], str] = {
    ("platform-agent-biz", "localProjectCreate"): "oceanengine_local_project",
    ("platform-agent-biz", "localProjectUpdate"): "oceanengine_local_project",
    ("platform-agent-biz", "localProjectList"): "oceanengine_local_project",
    ("platform-agent-biz", "localProjectDetail"): "oceanengine_local_project",
    ("platform-agent-biz", "localProjectStatusBatchUpdate"): "oceanengine_local_project",
    ("platform-agent-biz", "localPoiGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localProductGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localAwemeAuthorizedGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localCustomAudienceGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localMultiPoiIdPoiIdsGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localToolPackListGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localToolPackDetailGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localMarketPageListGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localMarketPageGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localImAccountGet"): "oceanengine_local_project",
    ("platform-agent-biz", "localProjectWeekScheduleBatchUpdate"): "oceanengine_local_project",
    ("platform-agent-biz", "localUnitCreate"): "oceanengine_local_unit",
    ("platform-agent-biz", "localUnitUpdate"): "oceanengine_local_unit",
    ("platform-agent-biz", "localUnitList"): "oceanengine_local_unit",
    ("platform-agent-biz", "localUnitDetail"): "oceanengine_local_unit",
    ("platform-agent-biz", "localUnitStatusBatchUpdate"): "oceanengine_local_unit",
    ("platform-agent-biz", "localProductGetByPoiIds"): "oceanengine_local_unit",
    ("platform-agent-biz", "localPromotionRejectReasonBatchGet"): "oceanengine_local_unit",
    ("platform-agent-biz", "localFileUploadTaskCreate"): "oceanengine_local_material",
    ("platform-agent-biz", "localFileVideoUploadTaskList"): "oceanengine_local_material",
    ("platform-agent-biz", "localFileVideoUpload"): "oceanengine_local_material",
    ("platform-agent-biz", "localFileVideoGet"): "oceanengine_local_material",
    ("platform-agent-biz", "localFileVideoAwemeGet"): "oceanengine_local_material",
    ("platform-agent-biz", "localFileCarouselList"): "oceanengine_local_material",
    ("platform-agent-biz", "localImageUpload"): "oceanengine_local_material",
}

_PROJECT_MCP_RECOVERY_MAP: dict[str, tuple[str, dict[str, str]]] = {
    "localAwemeAuthorizedGet": (
        "list-authorized-awemes",
        {
            "localAccountId": "local_account_id",
            "marketingGoal": "marketing_goal",
            "searchKeyWord": "filtering.search_key_word",
            "page": "page",
            "pageSize": "page_size",
        },
    ),
    "localCustomAudienceGet": (
        "list-custom-audiences",
        {
            "localAccountId": "local_account_id",
            "tagsType": "tags_type",
            "page": "page",
            "pageSize": "page_size",
        },
    ),
    "localMultiPoiIdPoiIdsGet": (
        "get-poi-ids-by-multi-poi-id",
        {
            "localAccountId": "local_account_id",
            "local_account_id": "local_account_id",
            "multiPoiIds": "multi_poi_ids",
            "multi_poi_ids": "multi_poi_ids",
            "needEnable": "need_enable",
            "need_enable": "need_enable",
        },
    ),
    "localToolPackListGet": (
        "list-tool-packs",
        {
            "localAccountId": "local_account_id",
            "local_account_id": "local_account_id",
            "deliveryGoal": "delivery_goal",
            "delivery_goal": "delivery_goal",
            "poiIds": "poi_ids",
            "poi_ids": "poi_ids",
            "productIds": "product_ids",
            "product_ids": "product_ids",
            "intelligentSelectionMode": "intelligent_selection_mode",
            "intelligent_selection_mode": "intelligent_selection_mode",
            "page": "page",
            "pageSize": "page_size",
            "page_size": "page_size",
        },
    ),
    "localMarketPageListGet": (
        "list-market-pages",
        {
            "localAccountId": "local_account_id",
            "local_account_id": "local_account_id",
            "deliveryGoal": "delivery_goal",
            "delivery_goal": "delivery_goal",
            "poiIds": "poi_ids",
            "poi_ids": "poi_ids",
            "productIds": "product_ids",
            "product_ids": "product_ids",
            "page": "page",
            "pageSize": "page_size",
            "page_size": "page_size",
        },
    ),
    "localMarketPageGet": (
        "get-market-page-detail",
        {
            "localAccountId": "local_account_id",
            "local_account_id": "local_account_id",
            "marketPageIds": "market_page_ids",
            "market_page_ids": "market_page_ids",
        },
    ),
}

_PROJECT_SKILL_PATH = "/mnt/skills/custom/oceanengine-local-project/SKILL.md"


@contextmanager
def allow_managed_mcp_calls(business_tool_name: str) -> Iterator[None]:
    token = _allowed_business_tool.set(business_tool_name)
    try:
        yield
    finally:
        _allowed_business_tool.reset(token)


def is_managed_mcp_call_allowed() -> bool:
    return _allowed_business_tool.get() is not None


def _parse_router_params(params: Any) -> dict[str, Any]:
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        try:
            parsed = json.loads(params)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _set_dotted(payload: dict[str, Any], dotted_path: str, value: Any) -> None:
    current = payload
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        nested = current.get(part)
        if not isinstance(nested, dict):
            nested = {}
            current[part] = nested
        current = nested
    current[parts[-1]] = value


def _build_project_recovery_guidance(mcp_tool_name: str, arguments: dict[str, Any]) -> str:
    recovery = _PROJECT_MCP_RECOVERY_MAP.get(mcp_tool_name)
    if recovery is None:
        return ""

    capability, field_map = recovery
    mcp_params = _parse_router_params(arguments.get("params"))
    payload: dict[str, Any] = {}
    for source_field, target_field in field_map.items():
        if source_field in mcp_params:
            _set_dotted(payload, target_field, mcp_params[source_field])

    skill_first_guidance = (
        f" 请先调用 read_file 读取 {_PROJECT_SKILL_PATH}，"
        "理解项目管理接口导航和 capability 规则后，再改用原生业务工具调用。"
        " 真实查询或浏览器验收必须使用 dry_run=false，不要改成本地预检。"
    )
    if not payload:
        return f"{skill_first_guidance} capability={capability}。"

    payload_json = json.dumps(payload, ensure_ascii=False)
    return (
        skill_first_guidance
        + " 调用参数："
        f"tool=oceanengine_local_project，capability={capability}，payload_json={payload_json}。"
        " 必须保留 payload_json 中的原始用户参数，不要重新推断或改写数字、ID、分页或筛选值。"
    )


def guard_managed_mcp_tool_call(tool_name: str, arguments: dict[str, Any] | None) -> None:
    if tool_name != "nacos-mcp-router_use_tool":
        return

    arguments = arguments or {}
    server_name = arguments.get("mcp_server_name")
    mcp_tool_name = arguments.get("mcp_tool_name")
    owner = _MANAGED_MCP_TOOLS.get((str(server_name), str(mcp_tool_name)))
    if owner is None:
        return

    if _allowed_business_tool.get() == owner:
        return

    guidance = _build_project_recovery_guidance(str(mcp_tool_name), arguments) if owner == "oceanengine_local_project" else ""
    raise PermissionError(
        f"MCP 工具 {server_name}/{mcp_tool_name} 由 DeerFlow 原生业务工具 {owner} 管理，"
        f"请调用 {owner}，不要直接调用 nacos-mcp-router_use_tool。{guidance}"
    )
