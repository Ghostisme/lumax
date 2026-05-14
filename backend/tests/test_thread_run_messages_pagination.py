"""Tests for paginated GET /api/threads/{thread_id}/runs/{run_id}/messages endpoint."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from _router_auth_helpers import make_authed_test_app
from fastapi.testclient import TestClient

from app.gateway.routers import thread_runs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(event_store=None, run_manager=None, feedback_repo=None):
    """Build a test FastAPI app with stub auth and mocked state."""
    app = make_authed_test_app()
    app.include_router(thread_runs.router)

    if event_store is not None:
        app.state.run_event_store = event_store
    if run_manager is not None:
        app.state.run_manager = run_manager
    if feedback_repo is not None:
        app.state.feedback_repo = feedback_repo

    return app


def _make_event_store(rows: list[dict]):
    """Return an AsyncMock event store whose list_messages_by_run() returns rows."""
    store = MagicMock()
    store.list_messages_by_run = AsyncMock(return_value=rows)
    return store


def _make_thread_event_store(rows: list[dict]):
    """Return an AsyncMock event store whose list_messages() returns rows."""
    store = MagicMock()
    store.list_messages = AsyncMock(return_value=rows)
    return store


def _make_message(seq: int) -> dict:
    return {
        "seq": seq,
        "event_type": "ai_message",
        "category": "message",
        "content": f"msg-{seq}",
    }


async def _make_run_manager(thread_id: str, run_id_holder: dict[str, str]):
    from deerflow.runtime.runs.manager import RunManager

    manager = RunManager()
    record = await manager.create(thread_id=thread_id, assistant_id="assistant-1")
    run_id_holder["run_id"] = record.run_id
    return manager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_paginated_envelope():
    """GET /api/threads/{tid}/runs/{rid}/messages returns {data: [...], has_more: bool}."""
    rows = [_make_message(i) for i in range(1, 4)]
    app = _make_app(event_store=_make_event_store(rows))
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-1/runs/run-1/messages")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "has_more" in body
    assert body["has_more"] is False
    assert len(body["data"]) == 3


def test_has_more_true_when_extra_row_returned():
    """has_more=True when event store returns limit+1 rows."""
    # Default limit is 50; provide 51 rows
    rows = [_make_message(i) for i in range(1, 52)]  # 51 rows
    app = _make_app(event_store=_make_event_store(rows))
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-2/runs/run-2/messages")
    assert response.status_code == 200
    body = response.json()
    assert body["has_more"] is True
    assert len(body["data"]) == 50  # trimmed to limit


def test_after_seq_forwarded_to_event_store():
    """after_seq query param is forwarded to event_store.list_messages_by_run."""
    rows = [_make_message(10)]
    event_store = _make_event_store(rows)
    app = _make_app(event_store=event_store)
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-3/runs/run-3/messages?after_seq=5")
    assert response.status_code == 200
    event_store.list_messages_by_run.assert_awaited_once_with(
        "thread-3",
        "run-3",
        limit=51,  # default limit(50) + 1
        before_seq=None,
        after_seq=5,
    )


def test_before_seq_forwarded_to_event_store():
    """before_seq query param is forwarded to event_store.list_messages_by_run."""
    rows = [_make_message(3)]
    event_store = _make_event_store(rows)
    app = _make_app(event_store=event_store)
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-4/runs/run-4/messages?before_seq=10")
    assert response.status_code == 200
    event_store.list_messages_by_run.assert_awaited_once_with(
        "thread-4",
        "run-4",
        limit=51,
        before_seq=10,
        after_seq=None,
    )


def test_custom_limit_forwarded_to_event_store():
    """Custom limit is forwarded as limit+1 to the event store."""
    rows = [_make_message(i) for i in range(1, 6)]
    event_store = _make_event_store(rows)
    app = _make_app(event_store=event_store)
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-5/runs/run-5/messages?limit=10")
    assert response.status_code == 200
    event_store.list_messages_by_run.assert_awaited_once_with(
        "thread-5",
        "run-5",
        limit=11,  # 10 + 1
        before_seq=None,
        after_seq=None,
    )


def test_empty_data_when_no_messages():
    """Returns empty data list with has_more=False when no messages exist."""
    app = _make_app(event_store=_make_event_store([]))
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-6/runs/run-6/messages")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["has_more"] is False


def test_thread_messages_include_feedback_display_fields():
    rows = [
        {
            "run_id": "run-1",
            "seq": 1,
            "event_type": "user_message",
            "category": "message",
            "content": "hello",
        },
        {
            "run_id": "run-1",
            "seq": 2,
            "event_type": "ai_message",
            "category": "message",
            "content": "hi",
        },
    ]
    feedback_repo = MagicMock()
    feedback_repo.list_by_thread_grouped = AsyncMock(
        return_value={
            "run-1": {
                "feedback_id": "fb-1",
                "rating": 0,
                "result": None,
                "comment": None,
                "feedback_time": None,
                "agent_id": "assistant-1",
                "agent_name": "custom-agent",
            }
        }
    )
    app = _make_app(
        event_store=_make_thread_event_store(rows), feedback_repo=feedback_repo
    )
    with TestClient(app) as client:
        response = client.get("/api/threads/thread-fb/messages")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["feedback"] is None
    assert body[1]["feedback"] == {
        "feedback_id": "fb-1",
        "rating": 0,
        "result": None,
        "comment": None,
        "feedback_time": None,
        "agent_id": "assistant-1",
        "agent_name": "custom-agent",
    }


def test_put_run_feedback_by_result():
    run_holder: dict[str, str] = {}

    run_manager = asyncio.run(_make_run_manager("thread-fb", run_holder))
    feedback_repo = MagicMock()
    feedback_repo.upsert_by_run = AsyncMock(
        return_value={
            "feedback_id": "fb-1",
            "thread_id": "thread-fb",
            "run_id": run_holder["run_id"],
            "rating": 1,
            "result": "positive",
            "comment": "good",
            "feedback_time": "2026-05-08T12:00:00+00:00",
            "agent_id": "assistant-1",
            "agent_name": "",
        }
    )
    app = _make_app(run_manager=run_manager, feedback_repo=feedback_repo)
    with TestClient(app) as client:
        response = client.put(
            f"/api/threads/thread-fb/runs/{run_holder['run_id']}/feedback",
            json={"result": "positive", "comment": "good"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == 1
    assert body["result"] == "positive"
    feedback_repo.upsert_by_run.assert_awaited_once()


def test_delete_run_feedback_resets_record():
    run_holder: dict[str, str] = {}

    run_manager = asyncio.run(_make_run_manager("thread-fb", run_holder))
    feedback_repo = MagicMock()
    feedback_repo.reset_by_run = AsyncMock(
        return_value={
            "feedback_id": "fb-1",
            "thread_id": "thread-fb",
            "run_id": run_holder["run_id"],
            "rating": 0,
            "result": None,
            "comment": None,
            "feedback_time": None,
            "agent_id": "assistant-1",
            "agent_name": "",
        }
    )
    app = _make_app(run_manager=run_manager, feedback_repo=feedback_repo)
    with TestClient(app) as client:
        response = client.delete(
            f"/api/threads/thread-fb/runs/{run_holder['run_id']}/feedback"
        )
    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == 0
    assert body["result"] is None
    feedback_repo.reset_by_run.assert_awaited_once()
