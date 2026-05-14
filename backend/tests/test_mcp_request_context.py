"""Tests for deerflow.mcp.context 鈥?MCP outbound request context propagation."""

from __future__ import annotations

import asyncio
import contextvars

import pytest

from deerflow.mcp.context import (
    build_mcp_request_auth,
    build_request_headers,
    clear_request_context,
    get_request_context,
    set_request_context,
)


def setup_function(_func) -> None:
    clear_request_context()


def teardown_function(_func) -> None:
    clear_request_context()


def test_unset_context_yields_empty_headers() -> None:
    assert build_request_headers() == {}


def test_set_then_build_headers_includes_three_fields() -> None:
    set_request_context({"user_id": 42, "tenant_id": 7, "business_code": "talent"})
    headers = build_request_headers()
    assert headers == {
        "X-User-Id": "42",
        "TenantId": "7",
        "BUSINESS_CODE": "talent",
    }


def test_authorization_is_never_emitted() -> None:
    """We never transmit Authorization 鈥?downstream uses HeaderUserAuthenticationFilter."""
    set_request_context({"user_id": 1, "tenant_id": 1, "business_code": "talent"})  # type: ignore[typeddict-unknown-key]
    headers = build_request_headers()
    assert "Authorization" not in headers


def test_tenant_code_is_never_emitted() -> None:
    """TenantCode was intentionally dropped from the context schema."""
    set_request_context({"user_id": 1, "tenant_id": 1, "business_code": "talent"})
    headers = build_request_headers()
    assert "TenantCode" not in headers


def test_partial_context_emits_only_present_fields() -> None:
    set_request_context({"user_id": 99})
    headers = build_request_headers()
    assert headers == {"X-User-Id": "99"}


def test_blank_business_code_skipped() -> None:
    set_request_context({"user_id": 1, "tenant_id": 1, "business_code": "   "})
    headers = build_request_headers()
    assert "BUSINESS_CODE" not in headers


def test_clear_request_context_resets_state() -> None:
    set_request_context({"user_id": 5})
    assert get_request_context() == {"user_id": 5}
    clear_request_context()
    assert get_request_context() is None


def test_contextvar_isolated_across_threads() -> None:
    """Without copy_context(), child threads see no parent state 鈥?confirms ContextVar semantics."""
    import threading

    parent_seen: list = []
    child_seen: list = []

    def child() -> None:
        child_seen.append(get_request_context())

    set_request_context({"user_id": 1})
    parent_seen.append(get_request_context())

    t = threading.Thread(target=child)
    t.start()
    t.join()

    assert parent_seen == [{"user_id": 1}]
    assert child_seen == [None]


def test_copy_context_propagates_into_thread() -> None:
    """contextvars.copy_context().run(fn) carries parent ContextVar into child thread."""
    import threading

    child_seen: list = []

    def child() -> None:
        child_seen.append(get_request_context())

    set_request_context({"user_id": 1, "tenant_id": 2, "business_code": "talent"})
    ctx = contextvars.copy_context()

    t = threading.Thread(target=lambda: ctx.run(child))
    t.start()
    t.join()

    assert child_seen == [{"user_id": 1, "tenant_id": 2, "business_code": "talent"}]


def test_async_context_isolated_across_tasks() -> None:
    """ContextVar is automatically isolated per asyncio Task (asyncio.create_task copies context)."""
    sibling_seen: list = []

    async def sibling() -> None:
        # New task copies parent context at creation; mutations are local to this task.
        set_request_context({"user_id": 999})
        sibling_seen.append(get_request_context())

    async def parent() -> dict | None:
        set_request_context({"user_id": 1})
        await asyncio.create_task(sibling())
        return get_request_context()

    parent_seen = asyncio.run(parent())
    assert parent_seen == {"user_id": 1}
    assert sibling_seen == [{"user_id": 999}]


def test_build_mcp_request_auth_returns_httpx_auth_compatible_object() -> None:
    """The returned object must be accepted by httpx.AsyncClient(auth=...)."""
    import httpx

    auth = build_mcp_request_auth()
    assert isinstance(auth, httpx.Auth)
    assert hasattr(auth, "auth_flow")
    assert hasattr(auth, "requires_request_body")


def test_auth_flow_injects_headers_without_overwrite() -> None:
    """auth_flow merges ContextVar headers but does NOT override pre-set keys."""
    import httpx

    set_request_context({"user_id": 1, "tenant_id": 2, "business_code": "talent"})
    auth = build_mcp_request_auth()

    request = httpx.Request("POST", "http://example.com/mcp", headers={"X-User-Id": "override"})
    flow = auth.auth_flow(request)
    next(flow)

    assert request.headers["X-User-Id"] == "override"  # caller's value preserved
    assert request.headers["TenantId"] == "2"
    assert request.headers["BUSINESS_CODE"] == "talent"


def test_auth_flow_no_context_no_headers() -> None:
    """Without ContextVar values, auth_flow leaves request headers untouched."""
    import httpx

    auth = build_mcp_request_auth()
    request = httpx.Request("POST", "http://example.com/mcp")
    flow = auth.auth_flow(request)
    next(flow)

    assert "X-User-Id" not in request.headers
    assert "TenantId" not in request.headers
    assert "BUSINESS_CODE" not in request.headers
