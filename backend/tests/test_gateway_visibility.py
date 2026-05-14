"""Tests for Gateway user-visible payload sanitizing."""

from __future__ import annotations

import json

import pytest


def test_oceanengine_requests_disable_message_tuple_streaming() -> None:
    from app.gateway.services import constrain_stream_modes_for_user_visible_safety

    modes = constrain_stream_modes_for_user_visible_safety(
        ["values", "messages-tuple", "updates"],
        {"messages": [{"role": "user", "content": "帮我查询本地推账号的营销页"}]},
    )

    assert modes == ["values", "updates"]


def test_oceanengine_requests_disable_message_tuple_streaming_for_content_blocks() -> (
    None
):
    from app.gateway.services import constrain_stream_modes_for_user_visible_safety

    modes = constrain_stream_modes_for_user_visible_safety(
        ["values", "messages-tuple"],
        {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "帮我查询本地推账号的营销页"}],
                }
            ]
        },
    )

    assert modes == ["values"]


def test_non_oceanengine_requests_keep_message_tuple_streaming() -> None:
    from app.gateway.services import constrain_stream_modes_for_user_visible_safety

    modes = constrain_stream_modes_for_user_visible_safety(
        ["values", "messages-tuple"],
        {"messages": [{"role": "user", "content": "帮我写一份汽车分析报告"}]},
    )

    assert modes == ["values", "messages-tuple"]


def test_gateway_visibility_preserves_normal_assistant_reply_with_skill_word() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "ai",
                "content": "你好！我可以帮你进行数据分析、代码开发和技能开发。",
                "additional_kwargs": {},
                "tool_calls": [],
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    assert (
        sanitized["messages"][0]["content"]
        == "你好！我可以帮你进行数据分析、代码开发和技能开发。"
    )
    assert (
        sanitized["messages"][0].get("additional_kwargs", {}).get("hide_from_ui")
        is not True
    )


def test_format_sse_hides_oceanengine_skill_read_chunk() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        [
            {
                "type": "AIMessageChunk",
                "content": "",
                "additional_kwargs": {},
                "tool_calls": [
                    {
                        "name": "read_file",
                        "args": {
                            "path": "/mnt/skills/custom/oceanengine-local-unit/SKILL.md"
                        },
                        "id": "call_1",
                    }
                ],
            },
            {"langgraph_node": "agent"},
        ],
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["additional_kwargs"]["hide_from_ui"] is True


def test_format_sse_temporarily_preserves_oceanengine_internal_stream_text() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        [
            {
                "type": "AIMessageChunk",
                "content": "读取营销页列表查询的参考文档\n/mnt/skills/custom/oceanengine-local-project/references/list-market-pages.md",
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ],
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"]
    assert payload[0].get("additional_kwargs", {}).get("hide_from_ui") is not True


def test_format_sse_hides_read_file_chunk_before_path_arrives() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        [
            {
                "content": "",
                "additional_kwargs": {},
                "tool_call_chunks": [{"name": "read_file", "args": "", "id": "call_1"}],
            },
            {"langgraph_node": "agent"},
        ],
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["additional_kwargs"]["hide_from_ui"] is True


def test_format_sse_temporarily_preserves_internal_stream_text_without_message_type() -> (
    None
):
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        [
            {
                "content": "现在我将调用 oceanengine_local_project，由业务工具参数校验器返回具体的中文追问。",
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ],
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"]
    assert payload[0].get("additional_kwargs", {}).get("hide_from_ui") is not True


def test_format_sse_sanitizes_messages_tuple_payloads() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        (
            {
                "content": "读取oceanengine-local-project技能文件，了解如何查询本地推账号的可用营销页",
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ),
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"]
    assert payload[0].get("additional_kwargs", {}).get("hide_from_ui") is not True


def test_format_sse_temporarily_preserves_internal_content_blocks() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        (
            {
                "content": [
                    {"type": "text", "text": "现在我需要调用"},
                    {"type": "code", "text": "oceanengine_local_project"},
                    {"type": "text", "text": "工具来查询营销页。"},
                ],
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ),
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"]
    assert payload[0].get("additional_kwargs", {}).get("hide_from_ui") is not True


def test_format_sse_temporarily_preserves_internal_reading_preamble_before_path_arrives() -> (
    None
):
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        (
            {
                "content": "我来帮您查询本地推账号的可用营销页。首先让我读取",
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ),
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"]
    assert payload[0].get("additional_kwargs", {}).get("hide_from_ui") is not True


def test_format_sse_hides_summary_named_messages() -> None:
    from app.gateway.services import format_sse

    frame = format_sse(
        "messages",
        [
            {
                "type": "human",
                "name": "summary",
                "content": "Here is a summary of the conversation to date:\n\nSUMMARY",
                "additional_kwargs": {},
            },
            {"langgraph_node": "agent"},
        ],
    )

    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload[0]["content"] == ""
    assert payload[0]["additional_kwargs"]["hide_from_ui"] is True
    assert "SUMMARY" not in json.dumps(payload, ensure_ascii=False)


def test_gateway_visibility_removes_internal_reasoning_content() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "ai",
                "content": "",
                "additional_kwargs": {
                    "reasoning_content": "SESSION INTENT\nUse /mnt/skills/custom/oceanengine-local-unit/SKILL.md."
                },
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    text = json.dumps(sanitized, ensure_ascii=False)
    assert "reasoning_content" not in text
    assert "SESSION INTENT" not in text
    assert "/mnt/skills/" not in text


def test_gateway_visibility_hides_summary_named_messages() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "human",
                "name": "summary",
                "content": "Here is a summary of the conversation to date:\n\nSESSION INTENT",
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True
    assert sanitized["messages"][0]["content"] == ""
    text = json.dumps(sanitized, ensure_ascii=False)
    assert "SESSION INTENT" not in text
    assert "Here is a summary" not in text


def test_gateway_visibility_hides_summary_langchain_messages() -> None:
    from langchain_core.messages import HumanMessage

    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            HumanMessage(
                content="Here is a summary of the conversation to date:\n\nSESSION INTENT",
                name="summary",
            )
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True
    assert sanitized["messages"][0]["content"] == ""
    text = json.dumps(sanitized, default=str, ensure_ascii=False)
    assert "SESSION INTENT" not in text
    assert "Here is a summary" not in text


def test_gateway_visibility_exposes_oceanengine_choice_cards_as_structured_clarification() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": "oceanengine_local_project",
                "content": json.dumps(
                    {
                        "success": False,
                        "message": "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。",
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": "marketing_goal",
                                "field_label": "营销场景",
                                "question": "营销场景是什么值？可选：直播、短视频/图文。",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "options": [
                                        {"value": "LIVE", "label": "直播"},
                                        {"value": "VIDEO_IMAGE", "label": "短视频/图文"},
                                    ],
                                },
                            },
                            "user_visible_text": "营销场景是什么值？可选：直播、短视频/图文。",
                            "business_tool_name": "oceanengine_local_project",
                            "mcp_server_name": "platform-agent-biz",
                            "mcp_tool_name": "localProjectCreate",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    structured = sanitized["structured_clarifications"][0]
    assert structured == {
        "version": "v1",
        "reason": "missing_required_parameter",
        "field": "marketing_goal",
        "field_label": "营销场景",
        "question": "营销场景是什么值？可选：直播、短视频/图文。",
        "input_control": {
            "type": "choice_cards",
            "selection_mode": "single",
            "options": [
                {"value": "LIVE", "label": "直播"},
                {"value": "VIDEO_IMAGE", "label": "短视频/图文"},
            ],
        },
        "user_visible_text": "营销场景是什么值？可选：直播、短视频/图文。",
    }
    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True
    assert sanitized["messages"][0]["additional_kwargs"]["structured_clarifications"] == [
        structured
    ]
    text = json.dumps(sanitized, ensure_ascii=False)
    assert "business_tool_name" not in text
    assert "mcp_server_name" not in text
    assert "mcp_tool_name" not in text
    assert "oceanengine_local_project" not in text
    assert "localProjectCreate" not in text


def test_gateway_visibility_preserves_dynamic_choice_metadata_in_structured_clarification() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": "oceanengine_local_project",
                "content": json.dumps(
                    {
                        "success": False,
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": "product_id",
                                "field_label": "商品投放ID",
                                "question": "商品投放ID是什么值？",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "page_info": {"page": 1, "page_size": 20},
                                    "options": [
                                        {
                                            "value": 882001,
                                            "label": "测试团购套餐A",
                                            "description": "价格：9900；适用门店数：12；绑定营销页ID：772001",
                                            "metadata": {
                                                "product_id": 882001,
                                                "product_name": "测试团购套餐A",
                                                "price": 9900,
                                                "product_pics": ["https://example.com/a.jpg"],
                                                "applicable_poi_num": 12,
                                                "bind_market_page_infos": [{"market_page_id": 772001}],
                                            },
                                        }
                                    ],
                                },
                            },
                            "user_visible_text": "商品投放ID是什么值？\n1. 测试团购套餐A（ID：882001）",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    option = sanitized["structured_clarifications"][0]["input_control"]["options"][0]
    assert option["value"] == "882001"
    assert option["label"] == "测试团购套餐A"
    assert option["description"] == "价格：9900；适用门店数：12；绑定营销页ID：772001"
    assert option["metadata"] == {
        "product_id": 882001,
        "product_name": "测试团购套餐A",
        "price": 9900,
        "product_pics": ["https://example.com/a.jpg"],
        "applicable_poi_num": 12,
        "bind_market_page_infos": [{"market_page_id": 772001}],
    }
    assert sanitized["structured_clarifications"][0]["input_control"]["page_info"] == {"page": 1, "page_size": 20}


def test_gateway_visibility_preserves_multiple_dynamic_choice_cards() -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": "oceanengine_local_project",
                "content": json.dumps(
                    {
                        "success": False,
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": "poi_ids",
                                "field_label": "门店",
                                "question": "请选择可投门店。",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "multiple",
                                    "page_info": {"page": 1, "page_size": 20},
                                    "options": [
                                        {
                                            "value": 901,
                                            "label": "人民广场店",
                                            "description": "上海市黄浦区",
                                            "metadata": {"poi_id": 901, "city": "上海"},
                                        },
                                        {
                                            "value": 902,
                                            "label": "徐家汇店",
                                            "description": "上海市徐汇区",
                                            "metadata": {"poi_id": 902, "city": "上海"},
                                        },
                                    ],
                                },
                            },
                            "user_visible_text": "请选择可投门店。\n请回复多个候选 ID 或名称。",
                            "business_tool_name": "oceanengine_local_project",
                            "mcp_server_name": "platform-agent-biz",
                            "mcp_tool_name": "localPoiGet",
                            "payload_json": "{}",
                            "trace": {"request_id": "internal"},
                            "request_id": "req-poi-list",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    input_control = sanitized["structured_clarifications"][0]["input_control"]
    assert input_control["type"] == "choice_cards"
    assert input_control["selection_mode"] == "multiple"
    assert input_control["page_info"] == {"page": 1, "page_size": 20}
    assert input_control["options"] == [
        {
            "value": "901",
            "label": "人民广场店",
            "description": "上海市黄浦区",
            "metadata": {"poi_id": 901, "city": "上海"},
        },
        {
            "value": "902",
            "label": "徐家汇店",
            "description": "上海市徐汇区",
            "metadata": {"poi_id": 902, "city": "上海"},
        },
    ]
    text = json.dumps(sanitized, ensure_ascii=False)
    assert "business_tool_name" not in text
    assert "mcp_server_name" not in text
    assert "mcp_tool_name" not in text
    assert "payload_json" not in text
    assert "trace" not in text
    assert "localPoiGet" not in text


@pytest.mark.parametrize(
    ("tool_name", "field", "field_label", "options"),
    [
        (
            "oceanengine_local_unit",
            "opt_status",
            "单元操作状态",
            [{"value": "ENABLE", "label": "启用单元"}, {"value": "PAUSED", "label": "暂停单元"}],
        ),
        (
            "oceanengine_local_material",
            "upload_type",
            "上传方式",
            [{"value": "UPLOAD_BY_FILE", "label": "本地文件上传"}],
        ),
    ],
)
def test_gateway_visibility_exposes_structured_clarification_for_all_oceanengine_native_tools(
    tool_name: str,
    field: str,
    field_label: str,
    options: list[dict[str, str]],
) -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": tool_name,
                "content": json.dumps(
                    {
                        "success": False,
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": field,
                                "field_label": field_label,
                                "question": f"{field_label}是什么值？",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "options": options,
                                },
                            },
                            "user_visible_text": f"{field_label}是什么值？",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    assert sanitized["structured_clarifications"][0]["field"] == field
    assert sanitized["structured_clarifications"][0]["field_label"] == field_label
    assert sanitized["structured_clarifications"][0]["input_control"]["options"] == options
    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True


def test_gateway_visibility_exposes_oceanengine_choice_cards_as_structured_clarification() -> (
    None
):
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": "oceanengine_local_project",
                "content": json.dumps(
                    {
                        "success": False,
                        "message": "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。",
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": "marketing_goal",
                                "field_label": "营销场景",
                                "question": "营销场景是什么值？可选：直播、短视频/图文。",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "options": [
                                        {"value": "LIVE", "label": "直播"},
                                        {
                                            "value": "VIDEO_IMAGE",
                                            "label": "短视频/图文",
                                        },
                                    ],
                                },
                            },
                            "user_visible_text": "营销场景是什么值？可选：直播、短视频/图文。",
                            "business_tool_name": "oceanengine_local_project",
                            "mcp_server_name": "platform-agent-biz",
                            "mcp_tool_name": "localProjectCreate",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    structured = sanitized["structured_clarifications"][0]
    assert structured == {
        "version": "v1",
        "reason": "missing_required_parameter",
        "field": "marketing_goal",
        "field_label": "营销场景",
        "question": "营销场景是什么值？可选：直播、短视频/图文。",
        "input_control": {
            "type": "choice_cards",
            "selection_mode": "single",
            "options": [
                {"value": "LIVE", "label": "直播"},
                {"value": "VIDEO_IMAGE", "label": "短视频/图文"},
            ],
        },
        "user_visible_text": "营销场景是什么值？可选：直播、短视频/图文。",
    }
    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True
    assert sanitized["messages"][0]["additional_kwargs"]["structured_clarifications"] == [
        structured
    ]
    text = json.dumps(sanitized, ensure_ascii=False)
    assert "business_tool_name" not in text
    assert "mcp_server_name" not in text
    assert "mcp_tool_name" not in text
    assert "oceanengine_local_project" not in text
    assert "localProjectCreate" not in text


def test_gateway_visibility_preserves_dynamic_choice_metadata_in_structured_clarification() -> (
    None
):
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": "oceanengine_local_project",
                "content": json.dumps(
                    {
                        "success": False,
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": "product_id",
                                "field_label": "商品投放ID",
                                "question": "商品投放ID是什么值？",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "page_info": {"page": 1, "page_size": 20},
                                    "options": [
                                        {
                                            "value": 882001,
                                            "label": "测试团购套餐A",
                                            "description": "价格：9900；适用门店数：12；绑定营销页ID：772001",
                                            "metadata": {
                                                "product_id": 882001,
                                                "product_name": "测试团购套餐A",
                                                "price": 9900,
                                                "product_pics": [
                                                    "https://example.com/a.jpg"
                                                ],
                                                "applicable_poi_num": 12,
                                                "bind_market_page_infos": [
                                                    {"market_page_id": 772001}
                                                ],
                                            },
                                        }
                                    ],
                                },
                            },
                            "user_visible_text": "商品投放ID是什么值？\n1. 测试团购套餐A（ID：882001）",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    option = sanitized["structured_clarifications"][0]["input_control"]["options"][0]
    assert option["value"] == "882001"
    assert option["label"] == "测试团购套餐A"
    assert option["description"] == "价格：9900；适用门店数：12；绑定营销页ID：772001"
    assert option["metadata"] == {
        "product_id": 882001,
        "product_name": "测试团购套餐A",
        "price": 9900,
        "product_pics": ["https://example.com/a.jpg"],
        "applicable_poi_num": 12,
        "bind_market_page_infos": [{"market_page_id": 772001}],
    }
    assert sanitized["structured_clarifications"][0]["input_control"]["page_info"] == {
        "page": 1,
        "page_size": 20,
    }


@pytest.mark.parametrize(
    ("tool_name", "field", "field_label", "options"),
    [
        (
            "oceanengine_local_unit",
            "opt_status",
            "单元操作状态",
            [
                {"value": "ENABLE", "label": "启用单元"},
                {"value": "PAUSED", "label": "暂停单元"},
            ],
        ),
        (
            "oceanengine_local_material",
            "upload_type",
            "上传方式",
            [{"value": "UPLOAD_BY_FILE", "label": "本地文件上传"}],
        ),
    ],
)
def test_gateway_visibility_exposes_structured_clarification_for_all_oceanengine_native_tools(
    tool_name: str,
    field: str,
    field_label: str,
    options: list[dict[str, str]],
) -> None:
    from app.gateway.visibility import sanitize_user_visible_payload

    payload = {
        "messages": [
            {
                "type": "tool",
                "name": tool_name,
                "content": json.dumps(
                    {
                        "success": False,
                        "data": {
                            "clarification": {
                                "version": "v1",
                                "reason": "missing_required_parameter",
                                "field": field,
                                "field_label": field_label,
                                "question": f"{field_label}是什么值？",
                                "input_control": {
                                    "type": "choice_cards",
                                    "selection_mode": "single",
                                    "options": options,
                                },
                            },
                            "user_visible_text": f"{field_label}是什么值？",
                        },
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {},
            }
        ]
    }

    sanitized = sanitize_user_visible_payload(payload)

    assert sanitized["structured_clarifications"][0]["field"] == field
    assert sanitized["structured_clarifications"][0]["field_label"] == field_label
    assert (
        sanitized["structured_clarifications"][0]["input_control"]["options"] == options
    )
    assert sanitized["messages"][0]["additional_kwargs"]["hide_from_ui"] is True
