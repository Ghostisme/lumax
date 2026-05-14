from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from deerflow.agents.middlewares.oceanengine_skill_gate_middleware import (
    OCEANENGINE_LOCAL_PROJECT_SKILL_PATH,
    OceanEngineSkillGateMiddleware,
)


def _request(tool_name: str, messages: list[object]) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={"name": tool_name, "id": "call_1", "args": {}},
        tool=SimpleNamespace(name=tool_name),
        state={"messages": messages},
        runtime=MagicMock(),
    )


def test_oceanengine_project_tool_requires_skill_read_first():
    middleware = OceanEngineSkillGateMiddleware()
    handler = MagicMock(return_value=ToolMessage(content="ok", name="oceanengine_local_project", tool_call_id="call_1"))

    result = middleware.wrap_tool_call(_request("oceanengine_local_project", []), handler)

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert OCEANENGINE_LOCAL_PROJECT_SKILL_PATH in result.content
    handler.assert_not_called()


def test_oceanengine_project_tool_allows_after_successful_skill_read():
    middleware = OceanEngineSkillGateMiddleware()
    handler_result = ToolMessage(content="ok", name="oceanengine_local_project", tool_call_id="call_1")
    handler = MagicMock(return_value=handler_result)
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "id": "read_skill",
                    "args": {"path": OCEANENGINE_LOCAL_PROJECT_SKILL_PATH},
                }
            ],
        ),
        ToolMessage(content="# skill", name="read_file", tool_call_id="read_skill"),
    ]

    result = middleware.wrap_tool_call(_request("oceanengine_local_project", messages), handler)

    assert result is handler_result
    handler.assert_called_once()
