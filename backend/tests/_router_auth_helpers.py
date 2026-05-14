from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI

from app.gateway.authz import AuthContext, Permissions


class _AllowAllThreadStore:
    async def check_access(
        self, thread_id: str, user_id: str, *, require_existing: bool = False
    ) -> bool:
        return True


def make_authed_test_app() -> FastAPI:
    app = FastAPI()
    app.state.thread_store = _AllowAllThreadStore()

    @app.middleware("http")
    async def _auth_middleware(request, call_next):
        user = SimpleNamespace(id="test-user")
        request.state.user = user
        request.state.auth = AuthContext(
            user=user,
            permissions=[
                Permissions.THREADS_READ,
                Permissions.THREADS_WRITE,
                Permissions.THREADS_DELETE,
                Permissions.RUNS_CREATE,
                Permissions.RUNS_READ,
                Permissions.RUNS_CANCEL,
            ],
        )
        return await call_next(request)

    return app


async def call_unwrapped(func, *args: Any, **kwargs: Any) -> Any:
    target = func
    while hasattr(target, "__wrapped__"):
        target = target.__wrapped__
    return await target(*args, **kwargs)
