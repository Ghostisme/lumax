"""Require OceanEngine project skill loading before project business tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

OCEANENGINE_LOCAL_PROJECT_TOOL_NAME = "oceanengine_local_project"
OCEANENGINE_LOCAL_PROJECT_SKILL_PATH = "/mnt/skills/custom/oceanengine-local-project/SKILL.md"


def _read_file_call_ids_for_path(messages: list[object], path: str) -> set[str]:
    call_ids: set[str] = set()
    for message in messages:
        for tool_call in getattr(message, "tool_calls", []) or []:
            if tool_call.get("name") != "read_file":
                continue
            args = tool_call.get("args") or {}
            if isinstance(args, dict) and args.get("path") == path and tool_call.get("id"):
                call_ids.add(str(tool_call["id"]))
    return call_ids


def _has_successful_read_file_result(messages: list[object], call_ids: set[str]) -> bool:
    if not call_ids:
        return False
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        if message.name != "read_file" or str(message.tool_call_id) not in call_ids:
            continue
        if getattr(message, "status", "success") == "error":
            continue
        return True
    return False


def _has_read_project_skill(messages: list[object]) -> bool:
    call_ids = _read_file_call_ids_for_path(messages, OCEANENGINE_LOCAL_PROJECT_SKILL_PATH)
    return _has_successful_read_file_result(messages, call_ids)


class OceanEngineSkillGateMiddleware(AgentMiddleware[AgentState]):
    """Block project business-tool calls until the matching skill was loaded."""

    @staticmethod
    def _build_block_message(request: ToolCallRequest) -> ToolMessage:
        tool_call_id = str(request.tool_call.get("id") or "missing_tool_call_id")
        content = (
            "必须先调用 read_file 读取 "
            f"{OCEANENGINE_LOCAL_PROJECT_SKILL_PATH}，理解其中接口导航和 capability 规则后，"
            "再使用用户原始参数重试本地推项目管理请求；不要直接猜测 capability、底层 MCP tool 或改写用户 ID、分页、筛选值。"
        )
        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=OCEANENGINE_LOCAL_PROJECT_TOOL_NAME,
            status="error",
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if request.tool_call.get("name") != OCEANENGINE_LOCAL_PROJECT_TOOL_NAME:
            return handler(request)
        messages = request.state.get("messages", []) if isinstance(request.state, dict) else []
        if _has_read_project_skill(messages):
            return handler(request)
        return self._build_block_message(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if request.tool_call.get("name") != OCEANENGINE_LOCAL_PROJECT_TOOL_NAME:
            return await handler(request)
        messages = request.state.get("messages", []) if isinstance(request.state, dict) else []
        if _has_read_project_skill(messages):
            return await handler(request)
        return self._build_block_message(request)
