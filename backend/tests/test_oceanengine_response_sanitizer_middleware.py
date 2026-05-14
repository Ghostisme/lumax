"""Tests for OceanEngine response sanitizing middleware."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from deerflow.agents.middlewares.oceanengine_response_sanitizer_middleware import (
    OceanEngineResponseSanitizerMiddleware,
)


def _runtime() -> MagicMock:
    runtime = MagicMock()
    runtime.context = {"thread_id": "test-thread"}
    return runtime


def test_sanitizes_oceanengine_enum_and_api_field_tokens() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content='{"success": true}',
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(content="营销目的：线上互动 CONTENT_HEAT\n查询字段 local_delivery_scene：直播"),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    content = result["messages"][0].content
    assert "CONTENT_HEAT" not in content
    assert "local_delivery_scene" not in content
    assert "线上互动" in content
    assert "直播" in content


def test_sanitizes_oceanengine_assignment_style_api_fields() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content='{"success": true}',
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(content="查询条件：page=1, page_size=10，营销目的：线上互动"),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    content = result["messages"][0].content
    assert "page" not in content
    assert "page_size" not in content
    assert "=1" not in content
    assert "=10" not in content
    assert "线上互动" in content


def test_hides_oceanengine_business_tool_call_intro_content() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="我会把 need_enable 设置为 maybe 来校验。",
                tool_calls=[
                    {
                        "name": "oceanengine_local_project",
                        "args": {"capability": "get-poi-ids-by-multi-poi-id", "payload_json": "{}"},
                        "id": "call_1",
                    }
                ],
            )
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    message = result["messages"][0]
    assert message.tool_calls[0]["name"] == "oceanengine_local_project"
    assert message.content == ""


def test_sanitizes_known_rule_enum_values_without_underscores() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content='{"success": true}',
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(content="当前该账户下没有找到任何自定义人群包（`CUSTOM`）。"),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    content = result["messages"][0].content
    assert "CUSTOM" not in content
    assert "`" not in content
    assert "（）" not in content
    assert "自定义人群包" in content


def test_forces_final_reply_after_oceanengine_tool_failure() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content=(
                    '{"success": false, "message": "MCP 工具返回结果与用户请求不一致，不能按成功结果展示。", '
                    '"data": {"user_visible_text": "页码请求值为 1，但接口返回 3，本次结果不满足用户请求的分页条件。\\n'
                    '每页数量请求值为 5，但接口返回 100，本次结果不满足用户请求的分页条件。"}}'
                ),
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(
                content="我再换一个分页参数试试。",
                tool_calls=[
                    {
                        "name": "oceanengine_local_project",
                        "args": {"capability": "list-promotable-products", "payload_json": "{}"},
                        "id": "call_2",
                    }
                ],
                response_metadata={"finish_reason": "tool_calls"},
            ),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    message = result["messages"][0]
    assert message.tool_calls == []
    assert message.response_metadata["finish_reason"] == "stop"
    assert message.content == (
        "页码请求值为 1，但接口返回 3，本次结果不满足用户请求的分页条件。\n"
        "每页数量请求值为 5，但接口返回 100，本次结果不满足用户请求的分页条件。"
    )


def test_forces_final_reply_after_oceanengine_validation_failure() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content=(
                    '{"success": false, "message": "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。", '
                    '"errors": [{"field": "page_size", "message": "每页数量 不能大于 1000。"}]}'
                ),
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(
                content="我把每页数量改成 1000 再试。",
                tool_calls=[
                    {
                        "name": "oceanengine_local_project",
                        "args": {"capability": "list-custom-audiences", "payload_json": "{}"},
                        "id": "call_2",
                    }
                ],
                response_metadata={"finish_reason": "tool_calls"},
            ),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    message = result["messages"][0]
    assert message.tool_calls == []
    assert message.response_metadata["finish_reason"] == "stop"
    assert "参数校验失败" in message.content
    assert "每页数量 不能大于 1000。" in message.content


def test_forces_final_reply_text_after_oceanengine_validation_failure() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(
                content=(
                    '{"success": false, "message": "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。", '
                    '"data": {"user_visible_text": "是否仅查询当前在投门店 类型不正确，应为布尔值。"}, '
                    '"errors": [{"field": "need_enable", "message": "是否仅查询当前在投门店 类型不正确，应为布尔值。"}]}'
                ),
                name="oceanengine_local_project",
                tool_call_id="call_1",
            ),
            AIMessage(content="need_enable参数只接受布尔值，请改成 true 或 false。"),
        ]
    }

    result = middleware.after_model(state, _runtime())

    assert result is not None
    message = result["messages"][0]
    assert message.content == "是否仅查询当前在投门店 类型不正确，应为布尔值。"
    assert "need_enable" not in message.content


def test_ignores_non_oceanengine_conversations() -> None:
    middleware = OceanEngineResponseSanitizerMiddleware()
    state = {
        "messages": [
            ToolMessage(content="{}", name="read_file", tool_call_id="call_1"),
            AIMessage(content="代码常量 CONTENT_HEAT 和字段 local_delivery_scene 保持原样"),
        ]
    }

    assert middleware.after_model(state, _runtime()) is None
