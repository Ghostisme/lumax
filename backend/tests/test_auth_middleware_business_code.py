"""Tests for AuthMiddleware business_code extraction and ContextVar propagation."""

from __future__ import annotations

import logging

import jwt
import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

# AuthMiddleware imports app-level deerflow.mcp.context; make sure path is set in conftest.
from app.gateway.auth_middleware import (
    AuthMiddleware,
    UserContext,
    _extract_business_code,
    _resolve_business_code_header,
    _user_context_from_claims,
)
from app.gateway.authz import require_permission
from deerflow.mcp.context import (
    build_request_headers,
    clear_request_context,
    get_request_context,
)
from deerflow.runtime.user_context import get_effective_user_id


def setup_function(_func) -> None:
    clear_request_context()


def teardown_function(_func) -> None:
    clear_request_context()


def test_extract_business_code_prefers_camel_case() -> None:
    assert _extract_business_code({"bizCode": "talent"}) == "talent"
    assert _extract_business_code({"businessCode": "talent"}) == "talent"
    assert _extract_business_code({"business_code": "talent"}) == "talent"
    assert _extract_business_code({"BUSINESS_CODE": "talent"}) == "talent"
    assert _extract_business_code({}) is None
    assert _extract_business_code({"bizCode": "  "}) is None


def _make_request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "raw_path": b"/x",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
    }
    return Request(scope)


def test_resolve_business_code_header_variants() -> None:
    assert (
        _resolve_business_code_header(
            _make_request_with_headers({"Business-Code": "talent"})
        )
        == "talent"
    )
    assert (
        _resolve_business_code_header(
            _make_request_with_headers({"BUSINESS_CODE": "xdwx"})
        )
        == "xdwx"
    )
    assert _resolve_business_code_header(_make_request_with_headers({})) is None
    assert (
        _resolve_business_code_header(
            _make_request_with_headers({}), default="fallback"
        )
        == "fallback"
    )


def test_user_context_dataclass_includes_business_code() -> None:
    user = UserContext(
        tenant_id="1", user_id="42", username="u", business_code="talent"
    )
    assert user.business_code == "talent"


def test_user_context_from_claims_extracts_nickname_and_first_dept_id() -> None:
    user = _user_context_from_claims(
        {
            "tenant_id": 1001,
            "user_id": 2002,
            "username": "alice",
            "nickname": "Alice Nick",
            "deptIds": ["dept-1", "dept-2"],
            "business_code": "talent",
        }
    )

    assert user.nickname == "Alice Nick"
    assert user.dept_id == "dept-1"


def test_user_context_from_claims_extracts_nested_user_info() -> None:
    user = _user_context_from_claims(
        {
            "tenantId": 1,
            "user_id": -1,
            "username": "13800138000",
            "user_info": {
                "id": "-1",
                "username": "13800138000",
                "nickname": "超级管理员",
                "deptIds": ["dept-1", "dept-2"],
            },
        }
    )

    assert user.username == "13800138000"
    assert user.nickname == "超级管理员"
    assert user.dept_id == "dept-1"


def test_user_context_from_claims_does_not_scan_past_empty_first_dept_id() -> None:
    user = _user_context_from_claims(
        {
            "tenant_id": 1001,
            "user_id": 2002,
            "username": "alice",
            "nickname": "Alice Nick",
            "deptIds": [" ", "dept-2"],
        }
    )

    assert user.dept_id == ""


@pytest.fixture()
def mock_user_app(monkeypatch):
    """FastAPI app with AuthMiddleware in mock-user mode; captures contextvar at endpoint."""
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "true")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    captured: dict = {}

    @app.get("/probe")
    async def probe(request: Request):
        captured["user"] = request.state.user
        captured["mcp_ctx"] = get_request_context()
        captured["headers"] = build_request_headers()
        return {"ok": True}

    return app, captured


def test_mock_mode_sets_user_and_contextvar(mock_user_app) -> None:
    app, captured = mock_user_app
    client = TestClient(app)

    resp = client.get("/probe", headers={"Business-Code": "xdwx"})
    assert resp.status_code == 200

    user: UserContext = captured["user"]
    assert user.user_id == "1"
    assert user.username == "mock-user"
    assert user.tenant_id == "1"
    assert user.business_code == "xdwx"
    assert captured["mcp_ctx"]["username"] == "mock-user"

    headers = captured["headers"]
    assert headers["X-User-Id"] == "1"
    assert headers["TenantId"] == "1"
    assert headers["BUSINESS_CODE"] == "xdwx"


def test_mock_mode_default_business_code_when_header_missing(mock_user_app) -> None:
    app, captured = mock_user_app
    client = TestClient(app)

    resp = client.get("/probe")
    assert resp.status_code == 200

    user: UserContext = captured["user"]
    assert user.business_code == "talent"  # mock default
    assert captured["headers"]["BUSINESS_CODE"] == "talent"


def test_contextvar_cleared_after_request(mock_user_app) -> None:
    app, _captured = mock_user_app
    client = TestClient(app)

    client.get("/probe")
    # After response returns, the parent thread's ContextVar should be cleared.
    assert get_request_context() is None


def test_public_path_does_not_set_contextvar(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    captured: dict = {}

    @app.get("/health")
    async def health(request: Request):
        captured["mcp_ctx"] = get_request_context()
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert captured["mcp_ctx"] is None


def test_models_list_path_is_public_even_with_invalid_bearer(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/models")
    async def list_models(_request: Request):
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/models", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_models_detail_path_is_public_even_with_invalid_bearer(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/models/{model_name}")
    async def get_model(model_name: str, _request: Request):
        return {"model": model_name}

    client = TestClient(app)
    resp = client.get(
        "/api/models/doubao", headers={"Authorization": "Bearer invalid-token"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"model": "doubao"}


def test_protected_path_invalid_bearer_returns_401_response(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/private")
    async def private_endpoint(_request: Request):
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/private", headers={"Authorization": "Bearer invalid-token"})

    assert resp.status_code == 401
    assert resp.json()["detail"]


def test_protected_path_missing_bearer_returns_401_response(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/private")
    async def private_endpoint(_request: Request):
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/private")

    assert resp.status_code == 401
    assert resp.json() == {"detail": "请先登录"}


def test_header_tenant_and_business_override_redis_claims(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")
    long_tenant_id = "2052263773707833345"

    class FakeRedis:
        async def get(self, key):
            if key != f"{long_tenant_id}:xdwx:token::access_token::good-token":
                return None
            return '{"tokens":{"org.springframework.security.oauth2.core.OAuth2AccessToken":{"metadata":{"metadata.token.claims":{"tenant_id":1001,"user_id":2002,"username":"alice","business_code":"talent"}}}}}'

        async def zrevrange(self, key, start, end):
            return []

    app = FastAPI()
    app.add_middleware(AuthMiddleware, redis_client=FakeRedis())

    captured: dict = {}

    @app.get("/api/private")
    async def private_endpoint(request: Request):
        captured["user"] = request.state.user
        captured["mcp_ctx"] = get_request_context()
        captured["headers"] = build_request_headers()
        return {"ok": True}

    client = TestClient(app)
    resp = client.get(
        "/api/private",
        headers={
            "Authorization": "Bearer good-token",
            "TenantId": long_tenant_id,
            "BUSINESS_CODE": "xdwx",
        },
    )

    assert resp.status_code == 200
    user: UserContext = captured["user"]
    assert user.tenant_id == long_tenant_id
    assert user.username == "alice"
    assert user.business_code == "xdwx"
    assert captured["mcp_ctx"]["username"] == "alice"
    assert captured["headers"]["TenantId"] == long_tenant_id
    assert captured["headers"]["BUSINESS_CODE"] == "xdwx"


def test_auth_success_logs_safe_user_context(monkeypatch, caplog) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    class FakeRedis:
        async def get(self, key):
            if key == "1001:talent:token::access_token::good-token":
                return '{"tokens":{"org.springframework.security.oauth2.core.OAuth2AccessToken":{"metadata":{"metadata.token.claims":{"tenant_id":1001,"user_id":2002,"username":"alice","business_code":"talent"}}}}}'
            return None

    app = FastAPI()
    app.add_middleware(AuthMiddleware, redis_client=FakeRedis())

    @app.get("/api/private")
    async def private_endpoint(_request: Request):
        return {"ok": True}

    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="app.gateway.auth_middleware"):
        resp = client.get(
            "/api/private",
            headers={
                "Authorization": "Bearer good-token",
                "TENANT-ID": "1001",
                "Business-Code": "talent",
            },
        )

    assert resp.status_code == 200
    log_output = "\n".join(record.getMessage() for record in caplog.records)
    assert "auth_user_context" in log_output
    assert "user_id=2002" in log_output
    assert "tenant_id=1001" in log_output
    assert "business_code=talent" in log_output
    assert "good-token" not in log_output
    assert "Bearer" not in log_output


def test_protected_path_decodes_user_id_from_jwt_token_when_redis_payload_has_no_claims(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    token = jwt.encode(
        {
            "tenant_id": 1001,
            "user_id": 2002,
            "username": "alice",
            "business_code": "talent",
        },
        "test-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )

    class FakeRedis:
        async def get(self, key):
            if key == f"1001:talent:token::access_token::{token}":
                return "{}"
            return None

    app = FastAPI()
    app.add_middleware(AuthMiddleware, redis_client=FakeRedis())

    captured: dict = {}

    @app.get("/api/private")
    async def private_endpoint(request: Request):
        captured["user"] = request.state.user
        captured["effective_user_id"] = get_effective_user_id()
        captured["headers"] = build_request_headers()
        return {"ok": True}

    client = TestClient(app)
    resp = client.get(
        "/api/private",
        headers={
            "Authorization": f"Bearer {token}",
            "TENANT-ID": "1001",
            "Business-Code": "talent",
        },
    )

    assert resp.status_code == 200
    user: UserContext = captured["user"]
    assert user.user_id == "2002"
    assert captured["effective_user_id"] == "2002"
    assert captured["headers"]["X-User-Id"] == "2002"


def test_permission_decorator_sets_effective_user_context_without_auth_middleware(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    class FakeRedis:
        async def get(self, key):
            if key == "1001:talent:token::access_token::good-token":
                return '{"tokens":{"org.springframework.security.oauth2.core.OAuth2AccessToken":{"metadata":{"metadata.token.claims":{"tenant_id":1001,"user_id":2002,"username":"alice","business_code":"talent"}}}}}'
            return None

    class AllowThreadStore:
        async def check_access(self, thread_id, user_id, *, require_existing=False):
            return (
                thread_id == "thread-1"
                and user_id == "2002"
                and require_existing is False
            )

    app = FastAPI()
    app.state.auth_redis_client = FakeRedis()
    app.state.thread_store = AllowThreadStore()

    @app.get("/api/threads/{thread_id}/uploads/list")
    @require_permission("threads", "read", owner_check=True)
    async def private_endpoint(thread_id: str, request: Request):
        return {"effective_user_id": get_effective_user_id()}

    client = TestClient(app)
    resp = client.get(
        "/api/threads/thread-1/uploads/list",
        headers={
            "Authorization": "Bearer good-token",
            "TENANT-ID": "1001",
            "Business-Code": "talent",
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"effective_user_id": "2002"}


def test_protected_path_requires_tenant_and_business_headers_for_redis_lookup(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    class FakeRedis:
        async def get(self, key):
            return '{"tokens":{"org.springframework.security.oauth2.core.OAuth2AccessToken":{"metadata":{"metadata.token.claims":{"tenant_id":1001,"user_id":2002,"username":"alice","business_code":"talent"}}}}}'

        async def zrevrange(self, key, start, end):
            return []

    app = FastAPI()
    app.add_middleware(AuthMiddleware, redis_client=FakeRedis())

    @app.get("/api/private")
    async def private_endpoint(_request: Request):
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/private", headers={"Authorization": "Bearer good-token"})

    assert resp.status_code == 401


def test_protected_path_can_fallback_by_token_suffix_scan_without_tenant_business_headers(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_MOCK", "false")

    class FakeRedis:
        async def get(self, key):
            if key == "1:ai:token::access_token::good-token":
                return '{"tokens":{"org.springframework.security.oauth2.core.OAuth2AccessToken":{"metadata":{"metadata.token.claims":{"tenantId":1,"user_id":2002,"username":"alice"}}}}}'
            return None

        async def zrevrange(self, key, start, end):
            return []

        async def scan_iter(self, match=None, count=None):
            if match == "*token::access_token::good-token":
                yield "1:ai:token::access_token::good-token"

    app = FastAPI()
    app.add_middleware(AuthMiddleware, redis_client=FakeRedis())

    @app.get("/api/private")
    async def private_endpoint(_request: Request):
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/private", headers={"Authorization": "Bearer good-token"})

    assert resp.status_code == 200
