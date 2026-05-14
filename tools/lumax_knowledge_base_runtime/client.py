"""Volcengine VikingDB knowledge base SDK adapter.

Only this module talks to the official `vikingdb-python-sdk`. The signature is
intentionally narrow — `tenant_id` lives one layer up in the service class, so
this adapter only knows about a `collection_name` plus query parameters.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeCredentialsMissing(RuntimeError):
    """Raised when AK/SK or region is not present in the environment."""


class KnowledgeSearchFailed(RuntimeError):
    """Raised when the SDK call fails for any other reason."""


class VolcengineKnowledgeClient:
    """Thin wrapper around `vikingdb-python-sdk` knowledge search."""

    def __init__(self) -> None:
        self._service: Any | None = None

    def _build_service(self) -> Any:
        ak = os.getenv("VOLC_ACCESSKEY") or os.getenv("VOLC_AK")
        sk = os.getenv("VOLC_SECRETKEY") or os.getenv("VOLC_SK")
        region = os.getenv("VIKINGDB_REGION")
        if not ak or not sk or not region:
            raise KnowledgeCredentialsMissing("火山知识库凭证未配置")

        host = os.getenv("VIKINGDB_HOST") or f"api-knowledgebase.mlp.{region}.volces.com"

        try:
            from vikingdb import IAM
            from vikingdb.knowledge import VikingKnowledge
        except ImportError as exc:  # pragma: no cover - import-time guard
            raise KnowledgeCredentialsMissing(
                "未安装 vikingdb-python-sdk，请执行 `uv add vikingdb-python-sdk`"
            ) from exc

        auth = IAM(ak=ak, sk=sk)
        return VikingKnowledge(auth=auth, host=host, region=region, scheme="https")

    def _ensure_service(self) -> Any:
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def search_knowledge(
        self,
        collection_name: str,
        query: str,
        top_k: int,
        tag_filters: list[dict[str, str]] | None = None,
        *,
        project_name: str = "default",
    ) -> list[dict[str, Any]]:
        """Execute a knowledge base search and return a normalized chunk list.

        The adapter never raises Agent-visible Chinese text; mapping to user
        messages is the service layer's job.
        """
        service = self._ensure_service()
        try:
            from vikingdb.knowledge import SearchKnowledgeRequest
        except ImportError as exc:  # pragma: no cover - import-time guard
            raise KnowledgeCredentialsMissing(
                "未安装 vikingdb-python-sdk，请执行 `uv add vikingdb-python-sdk`"
            ) from exc

        try:
            collection = service.collection(
                collection_name=collection_name,
                project_name=project_name,
            )
            request_kwargs: dict[str, Any] = {"query": query, "limit": top_k}
            if tag_filters:
                request_kwargs["doc_filter"] = _to_doc_filter(tag_filters)
            response = collection.search_knowledge(SearchKnowledgeRequest(**request_kwargs))
        except KnowledgeCredentialsMissing:
            raise
        except Exception as exc:
            logger.warning("VikingDB knowledge search failed: %s", exc)
            raise KnowledgeSearchFailed(str(exc)) from exc

        return _normalize_chunks(response)


def _to_doc_filter(tag_filters: list[dict[str, str]]) -> dict[str, Any]:
    """Translate Agent-friendly `tag_filters` into VikingDB `doc_filter`.

    Same key → OR; different keys → AND. Adjust here if SDK semantics differ.
    """
    grouped: dict[str, list[str]] = {}
    for item in tag_filters:
        key = item["key"]
        grouped.setdefault(key, []).append(item["value"])

    must: list[dict[str, Any]] = []
    for key, values in grouped.items():
        if len(values) == 1:
            must.append({"field": key, "op": "==", "value": values[0]})
        else:
            must.append({"field": key, "op": "in", "value": values})
    return {"op": "must", "conds": must}


def _normalize_chunks(response: Any) -> list[dict[str, Any]]:
    result_list = _safe_attr(_safe_attr(response, "result"), "result_list") or []
    chunks: list[dict[str, Any]] = []
    for item in result_list:
        chunks.append(
            {
                "content": _safe_attr(item, "content") or _safe_attr(item, "text"),
                "doc_name": _safe_attr(item, "doc_name") or _safe_attr(item, "source"),
                "source": _safe_attr(item, "source"),
                "score": _safe_attr(item, "score") or _safe_attr(item, "rerank_score"),
            }
        )
    return chunks


def _safe_attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
