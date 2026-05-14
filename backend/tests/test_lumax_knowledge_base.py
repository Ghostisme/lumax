"""Unit tests for the `lumax_knowledge_base` native tool."""

from __future__ import annotations

import contextvars
import json
from typing import Any

import pytest


# Importing deerflow ensures the repo root sits on sys.path so
# `from tools.lumax_knowledge_base...` resolves.
import deerflow  # noqa: F401  (side-effect import)

from tools.lumax_knowledge_base import lumax_knowledge_base_tool
from tools.lumax_knowledge_base_runtime import client as client_mod
from tools.lumax_knowledge_base_runtime import service as service_mod
from tools.lumax_knowledge_base_runtime.service import (
    LumaxKnowledgeBaseService,
    MAX_TOP_K,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_collection_mapping(monkeypatch):
    """Provide a deterministic tenant→collection mapping without touching config.yaml."""
    mapping = {
        "1": {"collection_name": "kb_platform", "project_name": "default"},
        "12345": {"collection_name": "kb_tenant_12345", "project_name": "tenant_12345"},
    }
    monkeypatch.setattr(service_mod, "_load_tenant_collections", lambda: mapping)


def _set_tenant(tenant_id: str | None) -> None:
    from deerflow.mcp.context import set_request_context

    if tenant_id is None:
        set_request_context(None)
    else:
        set_request_context({"tenant_id": tenant_id})


def _invoke_tool(
    payload: dict[str, Any] | None, capability: str = "search-knowledge"
) -> dict[str, Any]:
    raw = lumax_knowledge_base_tool.invoke(
        {"capability": capability, "payload_json": json.dumps(payload or {})}
    )
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Tool layer
# ---------------------------------------------------------------------------


class _FakeClient:
    def __init__(
        self,
        chunks: list[dict[str, Any]] | None = None,
        raises: Exception | None = None,
    ):
        self.chunks = chunks or []
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    def search_knowledge(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        return self.chunks


def test_tool_happy_path_returns_chunks(monkeypatch):
    fake = _FakeClient(chunks=[{"content": "hello", "doc_name": "a.md", "score": 0.9}])
    monkeypatch.setattr(
        service_mod,
        "VolcengineKnowledgeClient",
        lambda: fake,
    )
    _set_tenant("12345")

    result = _invoke_tool({"query": "hi", "top_k": 3})

    assert result["success"] is True
    assert result["data"]["chunks"] == [
        {"content": "hello", "doc_name": "a.md", "score": 0.9}
    ]
    assert fake.calls[0]["collection_name"] == "kb_tenant_12345"
    assert fake.calls[0]["project_name"] == "tenant_12345"
    assert fake.calls[0]["top_k"] == 3
    _set_tenant(None)


def test_tool_unknown_capability_returns_failure():
    _set_tenant("12345")
    result = _invoke_tool({"query": "hi"}, capability="delete-everything")
    assert result["success"] is False
    assert result["errors"][0]["field"] == "capability"
    _set_tenant(None)


def test_tool_invalid_json_payload_returns_failure():
    _set_tenant("12345")
    raw = lumax_knowledge_base_tool.invoke(
        {"capability": "search-knowledge", "payload_json": "not-json{"}
    )
    result = json.loads(raw)
    assert result["success"] is False
    assert result["errors"][0]["field"] == "payload_json"
    _set_tenant(None)


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def test_missing_tenant_returns_failure(monkeypatch):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant(None)
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "tenant_id"
    assert "租户" in result["data"]["user_visible_text"]


@pytest.mark.parametrize("bad_tenant", ["", "0", "00000", "abc"])
def test_invalid_tenant_normalizes_to_missing(monkeypatch, bad_tenant):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant(bad_tenant)
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "tenant_id"
    _set_tenant(None)


def test_default_tenant_id_one_is_allowed(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("1")
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is True
    assert fake.calls[0]["collection_name"] == "kb_platform"
    _set_tenant(None)


def test_payload_tenant_id_is_ignored(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    # Agent tries to override identity via payload; tool layer must drop it.
    result = _invoke_tool({"query": "hi", "tenant_id": "1"})
    assert result["success"] is True
    assert fake.calls[0]["collection_name"] == "kb_tenant_12345"  # not kb_platform
    _set_tenant(None)


def test_unknown_payload_keys_are_ignored(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    result = _invoke_tool(
        {"query": "hi", "kb_id": "x", "region": "us-west", "ext": {"a": 1}}
    )
    assert result["success"] is True
    _set_tenant(None)


def test_explicit_tenant_overrides_context(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    service = LumaxKnowledgeBaseService()
    result = service.search(tenant_id="1", query="hi")
    assert result["success"] is True
    assert fake.calls[0]["collection_name"] == "kb_platform"
    _set_tenant(None)


def test_cross_thread_propagation(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")

    def worker():
        return _invoke_tool({"query": "hi"})

    captured_ctx = contextvars.copy_context()
    result = captured_ctx.run(worker)
    assert result["success"] is True
    assert fake.calls[0]["collection_name"] == "kb_tenant_12345"
    _set_tenant(None)


# ---------------------------------------------------------------------------
# Collection mapping
# ---------------------------------------------------------------------------


def test_unmapped_tenant_returns_failure(monkeypatch):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant("99999")  # not in fixture mapping
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "tenant_id"
    assert "知识库" in result["data"]["user_visible_text"]
    _set_tenant(None)


# ---------------------------------------------------------------------------
# Query / top_k / tag_filters validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_query", [None, "", "   ", "\n\t"])
def test_empty_query_rejected(monkeypatch, bad_query):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant("12345")
    payload: dict[str, Any] = {} if bad_query is None else {"query": bad_query}
    result = _invoke_tool(payload)
    assert result["success"] is False
    assert result["errors"][0]["field"] == "query"
    _set_tenant(None)


@pytest.mark.parametrize("bad_top_k", [0, -1, MAX_TOP_K + 1, 1.5, "5", True])
def test_top_k_out_of_range(monkeypatch, bad_top_k):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant("12345")
    result = _invoke_tool({"query": "hi", "top_k": bad_top_k})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "top_k"
    _set_tenant(None)


def test_top_k_default_is_five(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    _invoke_tool({"query": "hi"})
    assert fake.calls[0]["top_k"] == 5
    _set_tenant(None)


@pytest.mark.parametrize(
    "bad_filters",
    [
        "not-a-list",
        [{"key": "biz"}],
        [{"key": "biz", "value": "A", "extra": "x"}],
        [{"key": "", "value": "A"}],
        [{"key": "biz", "value": ""}],
        [{"key": "biz", "value": 123}],
    ],
)
def test_invalid_tag_filters_rejected(monkeypatch, bad_filters):
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: _FakeClient())
    _set_tenant("12345")
    result = _invoke_tool({"query": "hi", "tag_filters": bad_filters})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "tag_filters"
    _set_tenant(None)


def test_valid_tag_filters_passed_to_client(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    _invoke_tool(
        {
            "query": "hi",
            "tag_filters": [
                {"key": "biz", "value": "A"},
                {"key": "biz", "value": "B"},
                {"key": "region", "value": "cn"},
            ],
        }
    )
    assert fake.calls[0]["tag_filters"] == [
        {"key": "biz", "value": "A"},
        {"key": "biz", "value": "B"},
        {"key": "region", "value": "cn"},
    ]
    _set_tenant(None)


# ---------------------------------------------------------------------------
# Empty hits & SDK errors
# ---------------------------------------------------------------------------


def test_empty_hits_is_success(monkeypatch):
    fake = _FakeClient(chunks=[])
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    result = _invoke_tool({"query": "no-match"})
    assert result["success"] is True
    assert result["data"]["chunks"] == []
    assert "未检索到相关内容" in result["data"]["user_visible_text"]
    _set_tenant(None)


def test_credentials_missing_returns_credentials_failure(monkeypatch):
    fake = _FakeClient(raises=client_mod.KnowledgeCredentialsMissing("no creds"))
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "credentials"
    assert "凭证" in result["data"]["user_visible_text"]
    _set_tenant(None)


def test_sdk_failure_does_not_leak_trace(monkeypatch):
    fake = _FakeClient(
        raises=client_mod.KnowledgeSearchFailed(
            "ak=ABC123 secret=XYZ789 trace=https://internal/debug"
        )
    )
    monkeypatch.setattr(service_mod, "VolcengineKnowledgeClient", lambda: fake)
    _set_tenant("12345")
    result = _invoke_tool({"query": "hi"})
    assert result["success"] is False
    assert result["errors"][0]["field"] == "sdk"
    rendered = json.dumps(result, ensure_ascii=False)
    assert "ABC123" not in rendered
    assert "XYZ789" not in rendered
    assert "internal/debug" not in rendered
    _set_tenant(None)


# ---------------------------------------------------------------------------
# `tag_filters` → `doc_filter` translation (client helper)
# ---------------------------------------------------------------------------


def test_to_doc_filter_groups_same_key_as_in():
    out = client_mod._to_doc_filter(
        [
            {"key": "biz", "value": "A"},
            {"key": "biz", "value": "B"},
            {"key": "region", "value": "cn"},
        ]
    )
    assert out["op"] == "must"
    conds_by_field = {c["field"]: c for c in out["conds"]}
    assert conds_by_field["biz"]["op"] == "in"
    assert conds_by_field["biz"]["value"] == ["A", "B"]
    assert conds_by_field["region"]["op"] == "=="
    assert conds_by_field["region"]["value"] == "cn"


def test_to_doc_filter_single_value_uses_eq():
    out = client_mod._to_doc_filter([{"key": "biz", "value": "A"}])
    assert out["conds"] == [{"field": "biz", "op": "==", "value": "A"}]
