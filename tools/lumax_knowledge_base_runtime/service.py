"""Reusable Lumax knowledge base search service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from deerflow.config import get_app_config
from deerflow.config.app_config import AppConfig
from deerflow.mcp.context import get_request_context
from deerflow.runtime.tenant import normalize_tenant_id

from .client import KnowledgeCredentialsMissing, KnowledgeSearchFailed, VolcengineKnowledgeClient

logger = logging.getLogger(__name__)

TOOL_NAME = "lumax_knowledge_base"
DEFAULT_TOP_K = 5
MAX_TOP_K = 20

_FAILURE_TENANT_MISSING = "缺少有效租户标识，无法检索知识库。"
_FAILURE_TENANT_UNMAPPED = "当前租户未配置知识库 collection，请联系运维补配。"
_FAILURE_QUERY_EMPTY = "查询文本不能为空。"
_FAILURE_TOP_K_RANGE = f"top_k 必须为 [1, {MAX_TOP_K}] 的整数。"
_FAILURE_TAG_FILTERS_FORMAT = "tag_filters 必须为 [{\"key\": \"...\", \"value\": \"...\"}] 列表。"
_FAILURE_CREDENTIALS = "火山知识库凭证未配置。"
_FAILURE_SEARCH = "火山知识库检索失败。"
_EMPTY_HIT_TEXT = "未检索到相关内容。"


class LumaxKnowledgeBaseService:
    """High-level knowledge base search facade.

    Resolves tenant identity, looks up the tenant→collection mapping declared
    in `config.yaml`, validates the request, and delegates the actual SDK call
    to :class:`VolcengineKnowledgeClient`.
    """

    def __init__(self, client: VolcengineKnowledgeClient | None = None) -> None:
        self._client = client or VolcengineKnowledgeClient()

    def search(
        self,
        tenant_id: str | None = None,
        query: str | None = None,
        top_k: int | None = None,
        tag_filters: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        # Tenant resolution: explicit param overrides ContextVar.
        raw_tenant = tenant_id if tenant_id is not None else _read_tenant_from_context()
        normalized_tenant = normalize_tenant_id(raw_tenant)
        if normalized_tenant is None:
            return _failure(_FAILURE_TENANT_MISSING, "tenant_id")

        if query is None or not str(query).strip():
            return _failure(_FAILURE_QUERY_EMPTY, "query")
        clean_query = str(query).strip()

        effective_top_k = DEFAULT_TOP_K if top_k is None else top_k
        if not isinstance(effective_top_k, int) or isinstance(effective_top_k, bool):
            return _failure(_FAILURE_TOP_K_RANGE, "top_k")
        if effective_top_k < 1 or effective_top_k > MAX_TOP_K:
            return _failure(_FAILURE_TOP_K_RANGE, "top_k")

        validated_filters = _validate_tag_filters(tag_filters)
        if validated_filters is _INVALID:
            return _failure(_FAILURE_TAG_FILTERS_FORMAT, "tag_filters")

        mapping = _resolve_collection(normalized_tenant)
        if mapping is None:
            return _failure(_FAILURE_TENANT_UNMAPPED, "tenant_id")
        collection_name, project_name = mapping

        try:
            chunks = self._client.search_knowledge(
                collection_name=collection_name,
                query=clean_query,
                top_k=effective_top_k,
                tag_filters=validated_filters or None,
                project_name=project_name,
            )
        except KnowledgeCredentialsMissing:
            return _failure(_FAILURE_CREDENTIALS, "credentials")
        except KnowledgeSearchFailed as exc:
            logger.info("Knowledge search failed for tenant=%s: %s", normalized_tenant, exc)
            return _failure(_FAILURE_SEARCH, "sdk")

        return _success(chunks)


# ---------------------------------------------------------------------------
# Tag filter validation
# ---------------------------------------------------------------------------

_INVALID = object()


def _validate_tag_filters(value: Any) -> list[dict[str, str]] | object:
    if value is None:
        return []
    if not isinstance(value, list):
        return _INVALID
    cleaned: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            return _INVALID
        if set(item.keys()) != {"key", "value"}:
            return _INVALID
        if not isinstance(item["key"], str) or not isinstance(item["value"], str):
            return _INVALID
        if not item["key"] or not item["value"]:
            return _INVALID
        cleaned.append({"key": item["key"], "value": item["value"]})
    return cleaned


# ---------------------------------------------------------------------------
# Tenant context + collection mapping
# ---------------------------------------------------------------------------


def _read_tenant_from_context() -> str | None:
    ctx = get_request_context() or {}
    value = ctx.get("tenant_id") if isinstance(ctx, dict) else None
    return None if value is None else str(value)


def _resolve_collection(tenant_id: str) -> tuple[str, str] | None:
    """Return (collection_name, project_name) for the tenant or None if unmapped."""
    raw = _load_tenant_collections()
    entry = raw.get(tenant_id)
    if not entry or not isinstance(entry, dict):
        return None
    collection_name = entry.get("collection_name")
    if not collection_name or not isinstance(collection_name, str):
        return None
    project_name = entry.get("project_name") or "default"
    return collection_name, str(project_name)


def _load_tenant_collections() -> dict[str, Any]:
    """Read `lumax_knowledge_base.tenant_collections` from raw config.yaml.

    Reading raw YAML keeps ``AppConfig`` untouched (per the "minimize edits to
    existing code" constraint of this change). Map keys are coerced to strings
    so YAML integer keys still match string tenant ids.
    """
    try:
        path: Path = AppConfig.resolve_config_path()
    except FileNotFoundError:
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    section = raw.get("lumax_knowledge_base") or {}
    mapping = section.get("tenant_collections") or {}
    if not isinstance(mapping, dict):
        return {}
    # Allow YAML to write integer keys (e.g. `1:`) while consumers always
    # look up by string tenant id.
    return {str(k): v for k, v in mapping.items()}


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------


def _success(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    if chunks:
        message = f"检索到 {len(chunks)} 条相关内容。"
        user_visible = message
    else:
        message = _EMPTY_HIT_TEXT
        user_visible = _EMPTY_HIT_TEXT
    return {
        "success": True,
        "message": message,
        "data": {
            "user_visible_text": user_visible,
            "reply_guidance": "请基于 chunks 内容回答用户问题，引用来源时注明 doc_name。",
            "chunks": chunks,
            "tool_name": TOOL_NAME,
        },
        "errors": [],
        "tool_name": TOOL_NAME,
        "request_id": None,
    }


def _failure(message: str, field: str) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": {
            "user_visible_text": message,
            "reply_guidance": "请向用户说明该问题，并在条件满足后重试。",
            "chunks": [],
            "tool_name": TOOL_NAME,
        },
        "errors": [{"field": field, "message": message}],
        "tool_name": TOOL_NAME,
        "request_id": None,
    }


# Touch get_app_config to ensure the config loader is initialized when the
# service is first imported (matches OceanEngine native tools' behavior).
_ = get_app_config
