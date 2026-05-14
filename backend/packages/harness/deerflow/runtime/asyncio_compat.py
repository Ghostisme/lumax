"""Asyncio compatibility helpers for runtime integrations."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable


def ensure_windows_selector_event_loop_policy() -> None:
    """Use a psycopg-compatible event loop policy on Windows.

    psycopg async connections do not support the default ProactorEventLoop.
    Setting the policy before an event loop is created makes asyncio.run() and
    server startup create SelectorEventLoop instances instead.
    """
    if sys.platform != "win32":
        return

    policy_cls = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy_cls is None:
        return

    current_policy = asyncio.get_event_loop_policy()
    if isinstance(current_policy, policy_cls):
        return

    asyncio.set_event_loop_policy(policy_cls())


def selector_event_loop_factory(use_subprocess: bool = False) -> Callable[[], asyncio.AbstractEventLoop]:
    """Return a psycopg-compatible asyncio loop factory for Uvicorn."""
    return asyncio.SelectorEventLoop


def patch_uvicorn_windows_loop_factory() -> None:
    """Force Uvicorn to use SelectorEventLoop on Windows.

    Uvicorn 0.36 explicitly selects ProactorEventLoop on Windows when not using
    subprocess mode, which is incompatible with psycopg async connections.
    """
    if sys.platform != "win32":
        return

    try:
        import uvicorn.loops.asyncio
        import uvicorn.loops.auto
    except ImportError:
        return

    uvicorn.loops.asyncio.asyncio_loop_factory = selector_event_loop_factory
    uvicorn.loops.auto.auto_loop_factory = selector_event_loop_factory
