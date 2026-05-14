"""LangGraph Server auth handler using platform Bearer tokens."""

from __future__ import annotations

from langgraph_sdk import Auth

from app.gateway.auth_middleware import resolve_platform_user

auth = Auth()


@auth.authenticate
async def authenticate(request):
    """Validate the platform access token and return the user identity."""
    try:
        user = await resolve_platform_user(request)
    except Exception as exc:
        status_code = getattr(exc, "status_code", 401)
        detail = getattr(exc, "detail", "Not authenticated")
        raise Auth.exceptions.HTTPException(status_code=status_code, detail=detail) from exc
    return user.id


@auth.on
async def add_owner_filter(ctx: Auth.types.AuthContext, value: dict):
    """Inject user_id metadata on writes; filter by user_id on reads."""
    metadata = value.setdefault("metadata", {})
    metadata["user_id"] = ctx.user.identity
    return {"user_id": ctx.user.identity}
