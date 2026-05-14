"""Native DeerFlow tool: Lumax knowledge base search."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.tools import tool

from tools.lumax_knowledge_base_runtime.service import LumaxKnowledgeBaseService

TOOL_NAME = "lumax_knowledge_base"
SUPPORTED_CAPABILITIES = ("search-knowledge",)

logger = logging.getLogger(__name__)


@tool("lumax_knowledge_base", parse_docstring=True)
def lumax_knowledge_base_tool(capability: str, payload_json: str) -> str:
    """Search the Lumax (Volcengine VikingDB) knowledge base for the current tenant.

    Args:
        capability: Capability name. Currently only `search-knowledge` is supported.
        payload_json: JSON object string containing `query`, optional `top_k`, optional `tag_filters`.
    """
    try:
        if capability not in SUPPORTED_CAPABILITIES:
            return _dump(
                _capability_error(capability),
            )

        try:
            payload = json.loads(payload_json) if payload_json else {}
        except json.JSONDecodeError as exc:
            return _dump(_failure(f"payload_json 不是合法 JSON：{exc.msg}", "payload_json"))

        if not isinstance(payload, dict):
            return _dump(_failure("payload_json 必须是 JSON object。", "payload_json"))

        # Identity must come from the request context. Any tenant_id sent by
        # the model in the payload is silently dropped, along with any other
        # unknown keys (kb_id / region / etc.) so the agent cannot break the
        # tool by sending superfluous fields.
        query = payload.get("query")
        top_k = payload.get("top_k")
        tag_filters = payload.get("tag_filters")

        service = LumaxKnowledgeBaseService()
        result = service.search(
            tenant_id=None,
            query=query if isinstance(query, str) or query is None else str(query),
            top_k=top_k,
            tag_filters=tag_filters,
        )
    except Exception as exc:  # defensive: never leak raw stack into Agent
        logger.exception("lumax_knowledge_base_tool unexpected failure")
        result = _failure("Lumax 知识库检索工具执行异常。", "tool")
        result["errors"].append({"field": "exception", "message": str(exc)})

    return _dump(result)


def _capability_error(capability: str) -> dict[str, Any]:
    return _failure(
        f"未知的 capability：{capability}。可选能力：{', '.join(SUPPORTED_CAPABILITIES)}",
        "capability",
    )


def _failure(message: str, field: str) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": {
            "user_visible_text": message,
            "reply_guidance": "请按提示修正请求后重试。",
            "chunks": [],
            "tool_name": TOOL_NAME,
        },
        "errors": [{"field": field, "message": message}],
        "tool_name": TOOL_NAME,
        "request_id": None,
    }


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False)
