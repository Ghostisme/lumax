"""Tests for LangGraph stream creation response headers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.gateway.routers import runs, thread_runs


async def _empty_sse_consumer(*_args, **_kwargs):
    if False:
        yield b""


@pytest.mark.asyncio
async def test_thread_stream_run_exposes_metadata_and_reconnect_headers(monkeypatch):
    """Thread run stream creation returns both run metadata and reconnect paths."""
    record = SimpleNamespace(run_id="run-1")

    async def fake_start_run(_body, _thread_id, _request):
        return record

    monkeypatch.setattr(thread_runs, "start_run", fake_start_run)
    monkeypatch.setattr(thread_runs, "sse_consumer", _empty_sse_consumer)
    monkeypatch.setattr(thread_runs, "get_stream_bridge", lambda _request: MagicMock())
    monkeypatch.setattr(thread_runs, "get_run_manager", lambda _request: MagicMock())

    response = await thread_runs.stream_run.__wrapped__(
        "thread-1",
        thread_runs.RunCreateRequest(),
        MagicMock(),
    )

    assert response.headers["content-location"] == "/api/threads/thread-1/runs/run-1"
    assert response.headers["location"] == "/api/threads/thread-1/runs/run-1/stream"


@pytest.mark.asyncio
async def test_stateless_stream_exposes_metadata_and_reconnect_headers(monkeypatch):
    """Stateless stream creation uses the resolved thread id in both headers."""
    record = SimpleNamespace(run_id="run-2")

    async def fake_start_run(_body, _thread_id, _request):
        return record

    monkeypatch.setattr(runs, "start_run", fake_start_run)
    monkeypatch.setattr(runs, "sse_consumer", _empty_sse_consumer)
    monkeypatch.setattr(runs, "get_stream_bridge", lambda _request: MagicMock())
    monkeypatch.setattr(runs, "get_run_manager", lambda _request: MagicMock())

    response = await runs.stateless_stream(
        thread_runs.RunCreateRequest(config={"configurable": {"thread_id": "thread-2"}}),
        MagicMock(),
    )

    assert response.headers["content-location"] == "/api/threads/thread-2/runs/run-2"
    assert response.headers["location"] == "/api/threads/thread-2/runs/run-2/stream"
