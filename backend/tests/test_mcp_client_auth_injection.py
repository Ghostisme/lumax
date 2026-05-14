"""Tests for MCP client param building — confirm httpx.Auth injection on HTTP/SSE transports."""

from __future__ import annotations

from deerflow.config.extensions_config import McpServerConfig
from deerflow.mcp.client import build_server_params
from deerflow.mcp.context import McpRequestContextAuth


def test_stdio_transport_has_no_auth() -> None:
    cfg = McpServerConfig(enabled=True, type="stdio", command="echo", args=["hi"])
    params = build_server_params("s", cfg)
    assert params["transport"] == "stdio"
    assert "auth" not in params


def test_sse_transport_injects_auth() -> None:
    cfg = McpServerConfig(enabled=True, type="sse", url="http://localhost:9000/sse", headers={"X-Test": "v"})
    params = build_server_params("s", cfg)
    assert params["transport"] == "sse"
    assert params["url"] == "http://localhost:9000/sse"
    assert params["headers"] == {"X-Test": "v"}
    assert isinstance(params["auth"], McpRequestContextAuth)


def test_http_transport_injects_auth() -> None:
    cfg = McpServerConfig(enabled=True, type="http", url="http://localhost:9000/mcp")
    params = build_server_params("s", cfg)
    assert params["transport"] == "http"
    assert isinstance(params["auth"], McpRequestContextAuth)


def test_http_transport_without_static_headers_still_has_auth() -> None:
    cfg = McpServerConfig(enabled=True, type="http", url="http://localhost:9000/mcp")
    params = build_server_params("s", cfg)
    # No static headers field present, but auth must still be injected
    assert isinstance(params["auth"], McpRequestContextAuth)
