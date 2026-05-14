"""MCP 出站请求上下文。

仅承载身份/租户/业务线三件套，不透传 Bearer token —— MCP 服务端通过统一的
HeaderUserAuthenticationFilter 用 X-User-Id 还原真实 PigUser，无需 Authorization。

通过 ContextVar 在单次请求内传播：AuthMiddleware 写入 → MCP 出站 httpx.Auth
读取 → 合并到 HTTP headers。
"""

from __future__ import annotations

from collections.abc import Generator
from contextvars import ContextVar
from typing import TypedDict

import httpx


class McpRequestContext(TypedDict, total=False):
    """每次请求绑定到 contextvar 的 MCP 出站身份上下文。"""

    user_id: int | str
    username: str
    tenant_id: str
    business_code: str


_REQUEST_CTX: ContextVar[McpRequestContext | None] = ContextVar(
    "deerflow_mcp_request_ctx", default=None
)


def set_request_context(ctx: McpRequestContext | None) -> None:
    """设置当前协程/线程的 MCP 出站上下文。"""
    _REQUEST_CTX.set(ctx)


def get_request_context() -> McpRequestContext | None:
    """获取当前 MCP 出站上下文，若未设置返回 None。"""
    return _REQUEST_CTX.get()


def clear_request_context() -> None:
    """清空当前 MCP 出站上下文。"""
    _REQUEST_CTX.set(None)


def build_request_headers() -> dict[str, str]:
    """根据当前 contextvar 构建 MCP 出站 HTTP 头。

    返回的 header 仅包含三件套：X-User-Id / TenantId / BUSINESS_CODE。
    不包含 Authorization——下游通过 X-User-Id 自行还原 PigUser。
    """
    ctx = _REQUEST_CTX.get() or {}
    headers: dict[str, str] = {}

    user_id = ctx.get("user_id")
    if user_id is not None and str(user_id).strip():
        headers["X-User-Id"] = str(user_id)

    tenant_id = ctx.get("tenant_id")
    if tenant_id is not None and str(tenant_id).strip():
        headers["TenantId"] = str(tenant_id)

    business_code = ctx.get("business_code")
    if business_code and business_code.strip():
        headers["BUSINESS_CODE"] = business_code.strip()

    return headers


def build_mcp_request_auth() -> McpRequestContextAuth:
    """工厂方法：返回一个 httpx.Auth 实例，每次请求时从 ContextVar 注入身份头。

    用于 SSE / streamable_http transport 的 ``auth`` 参数；session 长期持有，
    每次出站请求都会触发 ``auth_flow`` 读取最新 ContextVar 值。
    """
    return McpRequestContextAuth()


class McpRequestContextAuth(httpx.Auth):
    """httpx.Auth 实现：从 ContextVar 读取身份并合并到出站请求头。

    优先级：调用方显式设置的 header > ContextVar 注入的 header（不覆盖已存在键）。
    Authorization 不在此类负责注入范围内（OAuth interceptor 走启动期注入）。
    """

    requires_request_body = False
    requires_response_body = False

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        for key, value in build_request_headers().items():
            if key not in request.headers:
                request.headers[key] = value
        yield request

    # httpx.Auth 接口的同步/异步入口都默认调用 auth_flow，无需额外重写。
