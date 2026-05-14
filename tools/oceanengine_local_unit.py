"""Native DeerFlow tool for OceanEngine local unit operations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain.tools import tool

from deerflow.config import get_app_config
from tools.managed_mcp_guard import allow_managed_mcp_calls
from tools.oceanengine_local_project_runtime import endpoint_runner, rule_loader
from tools.oceanengine_local_project_runtime.agent_visible import agent_visible_result

BUSINESS_TOOL_NAME = "oceanengine_local_unit"
SKILL_NAME = "oceanengine-local-unit"
logger = logging.getLogger(__name__)


def _skill_root() -> Path:
    return get_app_config().skills.get_skills_path() / "custom" / SKILL_NAME


def _load_capability_rule(skill_root: Path, capability: str) -> dict[str, Any]:
    index_path = skill_root / "rules" / "index.json"
    rules_index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in rules_index.get("capabilities", []):
        if item.get("name") == capability:
            rule_path = skill_root / item["rule"]
            return rule_loader.load_rule_config(rule_path)
    supported = ", ".join(item.get("name", "") for item in rules_index.get("capabilities", []))
    raise ValueError(f"未知的 oceanengine-local-unit 能力：{capability}。可选能力：{supported}")


def _build_user_visible_text(result: dict[str, Any], spec: dict[str, Any]) -> str:
    title = spec.get("title") or "单元管理接口"
    message = result.get("message") or "执行完成"
    if result.get("success"):
        return f"{title}：{message}"
    errors = result.get("errors") or []
    error_text = "；".join(str(item.get("message", "")) for item in errors if isinstance(item, dict) and item.get("message"))
    if error_text:
        return f"{title}未完成：{error_text}"
    return f"{title}未完成：{message}"


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
    data.setdefault("user_visible_text", _build_user_visible_text(enriched, spec))
    enriched["data"] = data
    return enriched


def run_oceanengine_local_unit(capability: str, payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
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


@tool("oceanengine_local_unit", parse_docstring=True)
def oceanengine_local_unit_tool(capability: str, payload_json: str, dry_run: bool = False) -> str:
    """Execute OceanEngine local unit business operations through DeerFlow native logic.

    Args:
        capability: Capability name from oceanengine-local-unit rules index, such as create-unit or list-units.
        payload_json: JSON object string containing user business input fields.
        dry_run: Validate and build payload without calling MCP when true.
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
        if not isinstance(payload, dict):
            raise ValueError("payload_json 必须是 JSON object。")
        result = run_oceanengine_local_unit(capability=capability, payload=payload, dry_run=dry_run)
        result = agent_visible_result(result)
    except Exception as exc:
        result = {
            "success": False,
            "message": "OceanEngine 本地推单元业务工具执行失败。",
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
