"""Tests for Gateway run creation failure cleanup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.gateway import services
from app.gateway.routers.thread_runs import RunCreateRequest
from deerflow.runtime import RunContext, RunManager, RunStatus
from deerflow.runtime.stream_bridge.memory import MemoryStreamBridge


class _ThreadStore:
    async def get(self, _thread_id: str):
        return None

    async def create(self, *_args, **_kwargs):
        return None


@pytest.mark.anyio
async def test_start_run_marks_record_error_when_pre_task_setup_fails(monkeypatch):
    """A setup-time 500 must not leave a pending run that causes later 409s."""
    run_manager = RunManager()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    run_context = RunContext(
        checkpointer=None,
        thread_store=_ThreadStore(),
    )

    monkeypatch.setattr(services, "get_stream_bridge", lambda _request: MemoryStreamBridge())
    monkeypatch.setattr(services, "get_run_manager", lambda _request: run_manager)
    monkeypatch.setattr(services, "get_run_context", lambda _request: run_context)
    monkeypatch.setattr(
        services,
        "resolve_agent_factory",
        MagicMock(side_effect=RuntimeError("setup failed")),
    )

    with pytest.raises(RuntimeError, match="setup failed"):
        await services.start_run(RunCreateRequest(), "thread-1", request)

    runs = await run_manager.list_by_thread("thread-1")
    assert len(runs) == 1
    assert runs[0].status == RunStatus.error
    assert runs[0].error == "setup failed"
    assert await run_manager.has_inflight("thread-1") is False
