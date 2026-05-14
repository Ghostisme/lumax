"""Centralized accessors for singleton objects stored on ``app.state``.

**Getters** (used by routers): raise 503 when a required dependency is
missing, except ``get_store`` which returns ``None``.

Initialization is handled directly in ``app.py`` via :class:`AsyncExitStack`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, TypeVar, cast

from fastapi import FastAPI, HTTPException, Request
from langgraph.types import Checkpointer

from deerflow.config.app_config import AppConfig
from deerflow.persistence.feedback import FeedbackRepository
from deerflow.runtime import RunContext, RunManager, StreamBridge
from deerflow.runtime.events.store.base import RunEventStore
from deerflow.runtime.runs.store.base import RunStore

if TYPE_CHECKING:
    from deerflow.persistence.thread_meta.base import ThreadMetaStore


T = TypeVar("T")


def get_config(request: Request) -> AppConfig:
    """Return the app-scoped ``AppConfig`` stored on ``app.state``."""
    config = getattr(request.app.state, "config", None)
    if config is None:
        raise HTTPException(status_code=503, detail="Configuration not available")
    return config


@asynccontextmanager
async def langgraph_runtime(app: FastAPI) -> AsyncGenerator[None, None]:
    """Bootstrap and tear down all LangGraph runtime singletons.

    Usage in ``app.py``::

        async with langgraph_runtime(app):
            yield
    """
    from deerflow.persistence.engine import (
        close_engine,
        get_session_factory,
        init_engine_from_config,
    )
    from deerflow.runtime import make_store, make_stream_bridge
    from deerflow.runtime.checkpointer.async_provider import make_checkpointer
    from deerflow.runtime.events.store import make_run_event_store

    async with AsyncExitStack() as stack:
        config = getattr(app.state, "config", None)
        if config is None:
            raise RuntimeError(
                "langgraph_runtime() requires app.state.config to be initialized"
            )

        app.state.stream_bridge = await stack.enter_async_context(
            make_stream_bridge(config)
        )

        # Initialize persistence engine BEFORE checkpointer so that
        # auto-create-database logic runs first (postgres backend).
        await init_engine_from_config(config.database)

        app.state.checkpointer = await stack.enter_async_context(
            make_checkpointer(config)
        )
        app.state.store = await stack.enter_async_context(make_store(config))

        # Initialize repositories 鈥?one get_session_factory() call for all.
        sf = get_session_factory()
        if sf is not None:
            from deerflow.persistence.feedback import FeedbackRepository
            from deerflow.persistence.run import RunRepository

            app.state.run_store = RunRepository(sf)
            app.state.feedback_repo = FeedbackRepository(sf)
        else:
            from deerflow.runtime.runs.store.memory import MemoryRunStore

            app.state.run_store = MemoryRunStore()
            app.state.feedback_repo = None

        from deerflow.persistence.thread_meta import make_thread_store

        app.state.thread_store = make_thread_store(sf, app.state.store)

        # Run event store (has its own factory with config-driven backend selection)
        run_events_config = getattr(config, "run_events", None)
        app.state.run_event_store = make_run_event_store(run_events_config)

        # RunManager with store backing for persistence
        app.state.run_manager = RunManager(store=app.state.run_store)

        try:
            yield
        finally:
            await close_engine()


# ---------------------------------------------------------------------------
# Getters 鈥?called by routers per-request
# ---------------------------------------------------------------------------


def _require(attr: str, label: str) -> Callable[[Request], T]:
    """Create a FastAPI dependency that returns ``app.state.<attr>`` or 503."""

    def dep(request: Request) -> T:
        val = getattr(request.app.state, attr, None)
        if val is None:
            raise HTTPException(status_code=503, detail=f"{label} not available")
        return cast(T, val)

    dep.__name__ = dep.__qualname__ = f"get_{attr}"
    return dep


get_stream_bridge: Callable[[Request], StreamBridge] = _require(
    "stream_bridge", "Stream bridge"
)
get_run_manager: Callable[[Request], RunManager] = _require(
    "run_manager", "Run manager"
)
get_checkpointer: Callable[[Request], Checkpointer] = _require(
    "checkpointer", "Checkpointer"
)
get_run_event_store: Callable[[Request], RunEventStore] = _require(
    "run_event_store", "Run event store"
)
get_feedback_repo: Callable[[Request], FeedbackRepository] = _require(
    "feedback_repo", "Feedback"
)
get_run_store: Callable[[Request], RunStore] = _require("run_store", "Run store")


def get_store(request: Request):
    """Return the global store (may be ``None`` if not configured)."""
    return getattr(request.app.state, "store", None)


def get_thread_store(request: Request) -> ThreadMetaStore:
    """Return the thread metadata store (SQL or memory-backed)."""
    val = getattr(request.app.state, "thread_store", None)
    if val is None:
        raise HTTPException(
            status_code=503, detail="Thread metadata store not available"
        )
    return val


def get_run_context(request: Request) -> RunContext:
    """Build a :class:`RunContext` from ``app.state`` singletons.

    Returns a *base* context with infrastructure dependencies.
    """
    config = get_config(request)
    return RunContext(
        checkpointer=get_checkpointer(request),
        store=get_store(request),
        event_store=get_run_event_store(request),
        run_events_config=getattr(config, "run_events", None),
        thread_store=get_thread_store(request),
        app_config=config,
        feedback_repo=getattr(request.app.state, "feedback_repo", None),
    )


# ---------------------------------------------------------------------------
# Auth helpers (used by authz.py and auth middleware)
# ---------------------------------------------------------------------------


async def get_current_user_from_request(request: Request):
    """Return the platform-authenticated user for the current request."""
    user = getattr(getattr(request, "state", None), "user", None)
    if user is not None:
        return user

    from app.gateway.auth_middleware import resolve_platform_user
    from app.gateway.redis_client import GatewayRedis

    state = getattr(getattr(request, "app", None), "state", None)
    redis_client = getattr(state, "auth_redis_client", None) or GatewayRedis.get_client()
    return await resolve_platform_user(request, redis_client)


async def get_optional_user_from_request(request: Request):
    """Return the authenticated platform user, or ``None``."""
    try:
        return await get_current_user_from_request(request)
    except HTTPException:
        return None


async def get_current_user(request: Request) -> str | None:
    """Extract user_id from request state/token, or None if unauthenticated.

    Thin adapter that returns the string id for callers that only need
    identification (e.g., ``feedback.py``). Full-user callers should use
    ``get_current_user_from_request`` or ``get_optional_user_from_request``.
    """
    user = await get_optional_user_from_request(request)
    return str(user.id) if user else None
