"""Guardrails for MCP tools owned by native business tools."""

from __future__ import annotations

import contextvars
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
}


@contextmanager
def allow_managed_mcp_calls(business_tool_name: str) -> Iterator[None]:
    token = _allowed_business_tool.set(business_tool_name)
    try:
        yield
    finally:
        _allowed_business_tool.reset(token)


def is_managed_mcp_call_allowed() -> bool:
    return _allowed_business_tool.get() is not None


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

    raise PermissionError(f"MCP 工具 {server_name}/{mcp_tool_name} 由 DeerFlow 原生业务工具 {owner} 管理，请调用 {owner}，不要直接调用 nacos-mcp-router_use_tool。")
