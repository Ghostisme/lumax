"""Gateway authentication middleware for platform-issued access tokens."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.gateway.authz import _ALL_PERMISSIONS, AuthContext
from app.gateway.internal_auth import (
    INTERNAL_AUTH_HEADER_NAME,
    get_internal_user,
    is_valid_internal_auth_token,
)
from app.gateway.redis_client import GatewayRedis, is_redis_connection_error
from app.gateway.tenant import DEFAULT_TENANT_ID, normalize_tenant_id
from deerflow.mcp.context import clear_request_context, set_request_context
from deerflow.runtime.user_context import reset_current_user, set_current_user

try:  # pyjwt is present in app deployments; keep tests/imports resilient.
    import jwt
except Exception:  # pragma: no cover - depends on optional deployment package
    jwt = None


DEFAULT_BUSINESS_CODE = "talent"

_TOKEN_KEY_TEMPLATE = "{tenant_id}:{business_code}:token::access_token::{token}"
_PLATFORM_TOKEN_KEY_TEMPLATE = "token::access_token::{token}"
_TOKEN_SCAN_TEMPLATE = "*token::access_token::{token}"
_TOKEN_KEY_MARKER = "token::access_token::"
_ACCESS_TOKEN_CLASS = "org.springframework.security.oauth2.core.OAuth2AccessToken"
_CLAIMS_METADATA_KEY = "metadata.token.claims"
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UserContext:
    """Minimal authenticated user shape used by Gateway and persistence."""

    tenant_id: str = DEFAULT_TENANT_ID
    user_id: str = "1"
    username: str = "mock-user"
    nickname: str = ""
    dept_id: str = ""
    business_code: str = DEFAULT_BUSINESS_CODE
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=lambda: list(_ALL_PERMISSIONS))
    claims: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(self.user_id)


_PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/models",
    "/api/auth",
)


def _is_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _is_mock_enabled() -> bool:
    return os.getenv("AUTH_MOCK", "false").strip().lower() in {"1", "true", "yes", "on"}


def _is_public(path: str) -> bool:
    return any(path.rstrip("/").startswith(prefix) for prefix in _PUBLIC_PATH_PREFIXES)


def _is_local_memory_read(request: Request) -> bool:
    if request.method != "GET":
        return False

    if request.url.path.rstrip("/") != "/api/memory":
        return False

    host = request.url.hostname
    return host in {"localhost", "127.0.0.1", "::1"}


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _user_attr(user: Any, *names: str) -> str | None:
    for name in names:
        text = _clean_string(getattr(user, name, None))
        if text is not None:
            return text
    return None


def _pick_first(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if _clean_string(value) is not None:
            return value
    return None


def _extract_business_code(claims: Mapping[str, Any]) -> str | None:
    value = _pick_first(
        claims, ("bizCode", "businessCode", "business_code", "BUSINESS_CODE")
    )
    return _clean_string(value)


def _extract_first_dept_id(claims: Mapping[str, Any]) -> str:
    dept_ids = claims.get("deptIds")
    if dept_ids is None:
        dept_ids = claims.get("dept_ids")
    if isinstance(dept_ids, list | tuple):
        if not dept_ids:
            return ""
        return _clean_string(dept_ids[0]) or ""
    return (
        _clean_string(claims.get("dept_id"))
        or _clean_string(claims.get("deptId"))
        or ""
    )


def _nested_user_info(claims: Mapping[str, Any]) -> Mapping[str, Any]:
    user_info = claims.get("user_info")
    return user_info if isinstance(user_info, Mapping) else {}


def _resolve_business_code_header(
    request: Request, default: str | None = None
) -> str | None:
    return (
        _clean_string(request.headers.get("BusinessCode"))
        or _clean_string(request.headers.get("Business-Code"))
        or _clean_string(request.headers.get("BUSINESS_CODE"))
        or _clean_string(request.headers.get("BUSINESS-CODE"))
        or _clean_string(request.headers.get("business-code"))
        or default
    )


def _resolve_tenant_header(request: Request) -> str | None:
    return (
        _clean_string(request.headers.get("TenantId"))
        or _clean_string(request.headers.get("TENANT-ID"))
        or _clean_string(request.headers.get("X-Tenant-Id"))
    )


def _resolve_bearer_token(request: Request) -> str | None:
    value = request.headers.get("Authorization")
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _make_token_key(tenant_id: str | int, business_code: str, token: str) -> str:
    return _TOKEN_KEY_TEMPLATE.format(
        tenant_id=tenant_id, business_code=business_code, token=token
    )


def _make_platform_token_key(token: str) -> str:
    return _PLATFORM_TOKEN_KEY_TEMPLATE.format(token=token)


def _loads_json(value: Any) -> Any:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    for _ in range(3):
        if not isinstance(value, str):
            break
        text = value.strip()
        if not text:
            return value
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def _looks_like_claims(value: Mapping[str, Any]) -> bool:
    return (
        _pick_first(
            value,
            (
                "user_id",
                "userId",
                "tenant_id",
                "tenantId",
                "username",
                "user_name",
                "account",
                "sub",
                "mobile",
            ),
        )
        is not None
    )


def _extract_platform_claims(value: Mapping[str, Any]) -> dict[str, Any] | None:
    tokens = value.get("tokens")
    if not isinstance(tokens, Mapping):
        return None
    access_token = tokens.get(_ACCESS_TOKEN_CLASS)
    if not isinstance(access_token, Mapping):
        return None
    metadata = access_token.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    claims = metadata.get(_CLAIMS_METADATA_KEY)
    if isinstance(claims, Mapping) and _looks_like_claims(claims):
        return dict(claims)
    return None


def _find_claims(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None

    platform_claims = _extract_platform_claims(value)
    if platform_claims is not None:
        return platform_claims

    for key in ("metadata.token.claims", "token.claims", "claims", "metadata"):
        nested = value.get(key)
        if isinstance(nested, Mapping) and _looks_like_claims(nested):
            return dict(nested)

    if _looks_like_claims(value):
        return dict(value)

    for nested in value.values():
        found = _find_claims(nested)
        if found is not None:
            return found
    return None


def _decode_jwt_claims_unverified(token: str) -> dict[str, Any] | None:
    """Read JWT claims after the Redis token key has already confirmed validity."""
    if jwt is None:
        return None
    try:
        decoded = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except Exception:
        return None
    return _find_claims(decoded)


def _parse_context_from_token_key(key: str) -> tuple[str | None, str | None]:
    if _TOKEN_KEY_MARKER not in key:
        return None, None
    prefix = key.split(_TOKEN_KEY_MARKER, 1)[0].rstrip(":")
    if not prefix:
        return None, None
    parts = prefix.split(":")
    if len(parts) != 2:
        return None, None
    return _clean_string(parts[0]), _clean_string(parts[1])


def _user_context_from_claims(
    claims: Mapping[str, Any],
    *,
    tenant_override: str | None = None,
    business_override: str | None = None,
    tenant_from_key: str | None = None,
    business_from_key: str | None = None,
) -> UserContext:
    tenant_id = (
        normalize_tenant_id(tenant_override)
        or normalize_tenant_id(
            _pick_first(claims, ("tenant_id", "tenantId", "tenantID"))
        )
        or normalize_tenant_id(tenant_from_key)
        or DEFAULT_TENANT_ID
    )
    user_id = (
        _clean_string(_pick_first(claims, ("user_id", "userId", "id", "sub"))) or "1"
    )
    username = (
        _clean_string(
            _pick_first(claims, ("username", "user_name", "account", "name", "mobile"))
        )
        or "platform-user"
    )
    user_info = _nested_user_info(claims)
    nickname = (
        _clean_string(claims.get("nickname"))
        or _clean_string(user_info.get("nickname"))
        or ""
    )
    dept_id = _extract_first_dept_id(claims) or _extract_first_dept_id(user_info)
    business_code = (
        business_override
        or _extract_business_code(claims)
        or business_from_key
        or DEFAULT_BUSINESS_CODE
    )

    roles = _string_list(_pick_first(claims, ("roles", "roleCodes", "authorities")))
    permissions = _string_list(
        _pick_first(claims, ("permissions", "permissionCodes", "perms"))
    ) or list(_ALL_PERMISSIONS)
    return UserContext(
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        nickname=nickname,
        dept_id=dept_id,
        business_code=business_code,
        roles=roles,
        permissions=permissions,
        claims=dict(claims),
    )


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [
            entry
            for entry in (part.strip() for part in value.replace(",", " ").split())
            if entry
        ]
    if isinstance(value, list | tuple | set):
        result: list[str] = []
        for entry in value:
            if isinstance(entry, Mapping):
                text = _clean_string(
                    _pick_first(
                        entry, ("code", "roleCode", "name", "value", "authority")
                    )
                )
            else:
                text = _clean_string(entry)
            if text:
                result.append(text)
        return list(dict.fromkeys(result))
    return []


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


async def _scan_token_keys(redis_client: Any, token: str) -> AsyncIterator[str]:
    scan_iter = getattr(redis_client, "scan_iter", None)
    if scan_iter is None:
        return
    iterator = scan_iter(match=_TOKEN_SCAN_TEMPLATE.format(token=token), count=100)
    if hasattr(iterator, "__aiter__"):
        async for key in iterator:
            yield key.decode("utf-8") if isinstance(key, bytes) else str(key)
    else:
        for key in await _maybe_await(iterator):
            yield key.decode("utf-8") if isinstance(key, bytes) else str(key)


async def _lookup_token_payload(
    redis_client: Any,
    token: str,
    *,
    tenant_id: str | None,
    business_code: str | None,
) -> tuple[dict[str, Any], str | None, str | None] | None:
    if redis_client is None:
        return None

    candidate_keys: list[tuple[str, str | None, str | None]] = []
    if tenant_id and business_code:
        candidate_keys.append(
            (_make_token_key(tenant_id, business_code, token), tenant_id, business_code)
        )

    for key, key_tenant, key_business in candidate_keys:
        raw = await _maybe_await(redis_client.get(key))
        if raw is not None:
            claims = _find_claims(_loads_json(raw))
            if claims is None:
                claims = _decode_jwt_claims_unverified(token)
            if claims is not None:
                return claims, key_tenant, key_business

    async for key in _scan_token_keys(redis_client, token):
        raw = await _maybe_await(redis_client.get(key))
        if raw is None:
            continue
        claims = _find_claims(_loads_json(raw))
        if claims is None:
            claims = _decode_jwt_claims_unverified(token)
        if claims is None:
            continue
        key_tenant, key_business = _parse_context_from_token_key(key)
        return claims, key_tenant, key_business
    return None


async def resolve_platform_user(
    request: Request, redis_client: Any | None = None
) -> UserContext:
    if _is_mock_enabled():
        business_code = (
            _resolve_business_code_header(request, DEFAULT_BUSINESS_CODE)
            or DEFAULT_BUSINESS_CODE
        )
        tenant_id = (
            normalize_tenant_id(_resolve_tenant_header(request)) or DEFAULT_TENANT_ID
        )
        return UserContext(
            tenant_id=tenant_id,
            user_id="1",
            username="mock-user",
            business_code=business_code,
        )

    token = _resolve_bearer_token(request)
    if token is None:
        logger.warning(
            "auth_rejected path=%s reason=no_bearer_token",
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="请先登录：请求未携带 Authorization 令牌")

    tenant_header = _resolve_tenant_header(request)
    business_header = _resolve_business_code_header(request)
    redis = redis_client if redis_client is not None else GatewayRedis.get_client()
    if redis is None:
        logger.error(
            "auth_rejected path=%s reason=redis_not_configured token=%s...%s",
            request.url.path,
            token[:8] if len(token) > 16 else "***",
            token[-4:] if len(token) > 16 else "***",
        )
        raise HTTPException(status_code=401, detail="请先登录：Redis 未配置")

    lookup = await _lookup_token_payload(
        redis,
        token,
        tenant_id=tenant_header,
        business_code=business_header,
    )
    if lookup is None:
        logger.warning(
            "auth_rejected path=%s reason=token_not_found_in_redis "
            "tenant_header=%s business_header=%s token=%s...%s",
            request.url.path,
            tenant_header,
            business_header,
            token[:8] if len(token) > 16 else "***",
            token[-4:] if len(token) > 16 else "***",
        )
        raise HTTPException(
            status_code=401,
            detail=f"请先登录：令牌在 Redis 中未找到 (tenant={tenant_header}, biz={business_header})",
        )

    claims, tenant_from_key, business_from_key = lookup
    return _user_context_from_claims(
        claims,
        tenant_override=tenant_header,
        business_override=business_header,
        tenant_from_key=tenant_from_key,
        business_from_key=business_from_key,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Fail-closed auth gate backed by the platform token store."""

    def __init__(self, app: ASGIApp, redis_client: Any | None = None) -> None:
        super().__init__(app)
        # Only store an externally-injected client (used in tests).
        # At runtime, always obtain the shared client via GatewayRedis.get_client()
        # so that health-check and retry logic are handled centrally.
        self._redis_client_override = redis_client

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if (
            not _is_enabled()
            or _is_public(path)
            or _is_local_memory_read(request)
        ):
            return await call_next(request)

        logger.debug("auth_dispatch path=%s method=%s", path, request.method)

        internal_user = None
        if is_valid_internal_auth_token(request.headers.get(INTERNAL_AUTH_HEADER_NAME)):
            internal_user = get_internal_user()

        user = internal_user
        if user is None:
            user, resp = await self._resolve_with_retry(request, path)
            if resp is not None:
                return resp

        logger.info(
            "auth_user_context path=%s user_id=%s tenant_id=%s business_code=%s internal_auth=%s",
            path,
            _user_attr(user, "user_id", "id"),
            _user_attr(user, "tenant_id"),
            _user_attr(user, "business_code"),
            internal_user is not None,
        )

        request.state.user = user
        request.state.auth = AuthContext(
            user=user, permissions=list(getattr(user, "permissions", _ALL_PERMISSIONS))
        )

        runtime_token = set_current_user(user)
        if isinstance(user, UserContext):
            set_request_context(
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "nickname": user.nickname,
                    "dept_id": user.dept_id,
                    "tenant_id": user.tenant_id,
                    "business_code": user.business_code,
                }
            )
        try:
            return await call_next(request)
        finally:
            clear_request_context()
            reset_current_user(runtime_token)

    async def _resolve_with_retry(
        self, request: Request, path: str
    ) -> tuple[Any, Response | None]:
        """Resolve the platform user, retrying once on Redis connection failure.

        Returns ``(user, None)`` on success or ``(None, error_response)`` on
        definitive failure.
        """
        redis_client = self._redis_client_override or GatewayRedis.get_client()

        try:
            user = await resolve_platform_user(request, redis_client)
            return user, None
        except HTTPException as exc:
            logger.warning(
                "auth_rejected path=%s status=%s detail=%s",
                path, exc.status_code, exc.detail,
            )
            resp = JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )
            resp.headers["X-Auth-Reject"] = "HTTPException"
            return None, resp
        except Exception as first_exc:
            if not is_redis_connection_error(first_exc):
                logger.exception("auth_unexpected_error path=%s", path)
                resp = JSONResponse(
                    status_code=401,
                    content={"detail": f"请先登录：鉴权异常 ({type(first_exc).__name__}: {first_exc})"},
                )
                resp.headers["X-Auth-Reject"] = f"Exception:{type(first_exc).__name__}"
                return None, resp

            # Retry path must stay inside this ``except`` suite: CPython clears the
            # ``as first_exc`` binding when the suite ends, so ``first_exc`` must
            # not be referenced after the block exits.
            logger.warning(
                "auth_redis_connection_lost path=%s exc=%s, reconnecting and retrying",
                path,
                first_exc,
            )
            redis_client = GatewayRedis.reconnect()

            try:
                user = await resolve_platform_user(request, redis_client)
                logger.info("auth_retry_success path=%s", path)
                return user, None
            except HTTPException as exc:
                logger.warning(
                    "auth_rejected_after_retry path=%s status=%s detail=%s",
                    path, exc.status_code, exc.detail,
                )
                resp = JSONResponse(
                    status_code=exc.status_code, content={"detail": exc.detail}
                )
                resp.headers["X-Auth-Reject"] = "HTTPException-retry"
                return None, resp
            except Exception as retry_exc:
                logger.exception(
                    "auth_retry_failed path=%s first_exc=%s retry_exc=%s",
                    path, first_exc, retry_exc,
                )
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": f"请先登录：Redis 连接失败，重试后仍然异常 ({type(retry_exc).__name__}: {retry_exc})"
                    },
                )
                resp.headers["X-Auth-Reject"] = f"RetryFailed:{type(retry_exc).__name__}"
                return None, resp
