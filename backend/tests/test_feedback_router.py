"""Tests for the feedback router (CRUD + config)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import feedback
from deerflow.config.feedback_config import FeedbackConfig

# ---------------------------------------------------------------------------
# Minimal in-memory Store stub
# ---------------------------------------------------------------------------


@dataclass
class _StoreItem:
    value: dict


class _InMemoryStore:
    """Minimal Store stub that satisfies the router's async contract."""

    def __init__(self):
        self._data: dict[str, dict[str, dict]] = {}

    async def aput(self, namespace: tuple[str, ...], key: str, value: dict) -> None:
        ns_key = "/".join(namespace)
        self._data.setdefault(ns_key, {})[key] = value

    async def aget(self, namespace: tuple[str, ...], key: str) -> _StoreItem | None:
        ns_key = "/".join(namespace)
        val = self._data.get(ns_key, {}).get(key)
        return _StoreItem(value=val) if val is not None else None

    async def adelete(self, namespace: tuple[str, ...], key: str) -> None:
        ns_key = "/".join(namespace)
        self._data.get(ns_key, {}).pop(key, None)

    async def asearch(
        self, namespace: tuple[str, ...], *, limit: int = 100
    ) -> list[_StoreItem]:
        ns_key = "/".join(namespace)
        return [_StoreItem(value=v) for v in self._data.get(ns_key, {}).values()]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store():
    return _InMemoryStore()


@pytest.fixture()
def app(store):
    """FastAPI test app with the feedback router and a mock Store."""
    _app = FastAPI()
    _app.include_router(feedback.router)
    _app.state.store = store
    feedback_repo = MagicMock()
    feedback_repo.list_by_thread = AsyncMock(return_value=[])
    _app.state.feedback_repo = feedback_repo
    return _app


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _enable_feedback():
    """Ensure feedback is enabled (default) for all tests."""
    with patch.object(
        feedback, "get_feedback_config", return_value=FeedbackConfig(enabled=True)
    ):
        yield


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


def test_get_feedback_config(client):
    with patch.object(
        feedback,
        "get_feedback_config",
        return_value=FeedbackConfig(
            enabled=True, langsmith_sync=False, require_comment_on_negative=True
        ),
    ):
        resp = client.get("/api/threads/t1/feedback/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["langsmith_sync"] is False
    assert data["require_comment_on_negative"] is True


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_feedback(client):
    resp = client.post(
        "/api/threads/t1/feedback",
        json={"message_id": "msg_1", "rating": "positive"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["thread_id"] == "t1"
    assert data["message_id"] == "msg_1"
    assert data["rating"] == "positive"
    assert data["id"].startswith("fb_")


def test_create_feedback_with_comment(client):
    resp = client.post(
        "/api/threads/t1/feedback",
        json={
            "message_id": "msg_1",
            "rating": "negative",
            "comment": "Not helpful",
            "tags": ["wrong-answer"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["comment"] == "Not helpful"
    assert data["tags"] == ["wrong-answer"]


def test_create_feedback_syncs_sql_feedback_when_run_id_present(store, monkeypatch):
    feedback_repo = MagicMock()
    feedback_repo.upsert_by_run = AsyncMock(return_value={})
    app = FastAPI()
    app.include_router(feedback.router)
    app.state.store = store
    app.state.feedback_repo = feedback_repo

    async def mock_current_user(request):
        return "user-1"

    monkeypatch.setattr(feedback, "get_current_user", mock_current_user)

    with TestClient(app) as c:
        resp = c.post(
            "/api/threads/t1/feedback",
            json={
                "message_id": "msg_1",
                "run_id": "run_1",
                "rating": "positive",
                "comment": "Nice",
            },
        )

    assert resp.status_code == 200
    feedback_repo.upsert_by_run.assert_awaited_once_with(
        run_id="run_1",
        thread_id="t1",
        user_id="user-1",
        result="positive",
        comment="Nice",
    )


def test_create_feedback_sql_sync_failure_keeps_store_feedback(store, monkeypatch):
    feedback_repo = MagicMock()
    feedback_repo.upsert_by_run = AsyncMock(side_effect=RuntimeError("db down"))
    app = FastAPI()
    app.include_router(feedback.router)
    app.state.store = store
    app.state.feedback_repo = feedback_repo

    async def mock_current_user(request):
        return "user-1"

    monkeypatch.setattr(feedback, "get_current_user", mock_current_user)

    with TestClient(app) as c:
        resp = c.post(
            "/api/threads/t1/feedback",
            json={
                "message_id": "msg_1",
                "run_id": "run_1",
                "rating": "negative",
                "comment": "Bad",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["rating"] == "negative"
    assert len(store._data["feedback/t1"]) == 1
    feedback_repo.upsert_by_run.assert_awaited_once()


def test_create_feedback_disabled():
    app = FastAPI()
    app.include_router(feedback.router)
    app.state.store = _InMemoryStore()

    with patch.object(
        feedback, "get_feedback_config", return_value=FeedbackConfig(enabled=False)
    ):
        with TestClient(app) as c:
            resp = c.post(
                "/api/threads/t1/feedback",
                json={"message_id": "m1", "rating": "positive"},
            )
    assert resp.status_code == 403


def test_create_negative_requires_comment_when_configured(client):
    with patch.object(
        feedback,
        "get_feedback_config",
        return_value=FeedbackConfig(enabled=True, require_comment_on_negative=True),
    ):
        resp = client.post(
            "/api/threads/t1/feedback", json={"message_id": "m1", "rating": "negative"}
        )
    assert resp.status_code == 422
    assert "comment is required" in resp.json()["detail"].lower()


def test_create_negative_with_comment_when_required(client):
    with patch.object(
        feedback,
        "get_feedback_config",
        return_value=FeedbackConfig(enabled=True, require_comment_on_negative=True),
    ):
        resp = client.post(
            "/api/threads/t1/feedback",
            json={"message_id": "m1", "rating": "negative", "comment": "Bad"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_feedback_empty(client):
    resp = client.get("/api/threads/t1/feedback")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback"] == []
    assert data["count"] == 0


def test_list_feedback_returns_sql_current_state(app, monkeypatch):
    app.state.feedback_repo.list_by_thread = AsyncMock(
        return_value=[
            {
                "feedback_id": "fb-sql-1",
                "thread_id": "t1",
                "run_id": "run-1",
                "user_id": "user-1",
                "message_id": None,
                "rating": 1,
                "result": "positive",
                "comment": "Good",
                "feedback_time": "2026-05-11T03:00:00+00:00",
                "agent_id": "lead_agent",
                "agent_name": "",
                "created_at": "2026-05-11T02:59:00+00:00",
            },
            {
                "feedback_id": "fb-sql-2",
                "thread_id": "t1",
                "run_id": "run-2",
                "user_id": "user-1",
                "message_id": "msg-2",
                "rating": 0,
                "result": None,
                "comment": None,
                "feedback_time": None,
                "agent_id": "research_agent",
                "agent_name": "Research",
                "created_at": "2026-05-11T03:01:00+00:00",
            },
        ]
    )

    async def mock_current_user(request):
        return "user-1"

    monkeypatch.setattr(feedback, "get_current_user", mock_current_user)

    with TestClient(app) as client:
        resp = client.get("/api/threads/t1/feedback")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["feedback"] == [
        {
            "feedback_id": "fb-sql-1",
            "thread_id": "t1",
            "run_id": "run-1",
            "user_id": "user-1",
            "message_id": None,
            "rating": 1,
            "result": "positive",
            "comment": "Good",
            "feedback_time": "2026-05-11T03:00:00+00:00",
            "agent_id": "lead_agent",
            "agent_name": "",
            "created_at": "2026-05-11T02:59:00+00:00",
        },
        {
            "feedback_id": "fb-sql-2",
            "thread_id": "t1",
            "run_id": "run-2",
            "user_id": "user-1",
            "message_id": "msg-2",
            "rating": 0,
            "result": None,
            "comment": None,
            "feedback_time": None,
            "agent_id": "research_agent",
            "agent_name": "Research",
            "created_at": "2026-05-11T03:01:00+00:00",
        },
    ]
    app.state.feedback_repo.list_by_thread.assert_awaited_once_with(
        "t1", user_id="user-1"
    )


def test_list_feedback_ignores_store_history(app, store, monkeypatch):
    store._data["feedback/t1"] = {
        "fb-store-1": {
            "id": "fb-store-1",
            "thread_id": "t1",
            "message_id": "msg-store-1",
            "run_id": "run-1",
            "rating": "negative",
            "comment": "",
            "tags": [],
            "created_at": 1.0,
            "updated_at": 1.0,
        },
        "fb-store-2": {
            "id": "fb-store-2",
            "thread_id": "t1",
            "message_id": "msg-store-2",
            "run_id": "run-1",
            "rating": "positive",
            "comment": "",
            "tags": [],
            "created_at": 2.0,
            "updated_at": 2.0,
        },
    }
    app.state.feedback_repo.list_by_thread = AsyncMock(
        return_value=[
            {
                "feedback_id": "fb-sql-current",
                "thread_id": "t1",
                "run_id": "run-1",
                "user_id": "user-1",
                "message_id": None,
                "rating": -1,
                "result": "negative",
                "comment": "",
                "feedback_time": "2026-05-11T03:28:08+00:00",
                "agent_id": "lead_agent",
                "agent_name": "",
                "created_at": "2026-05-11T02:55:12+00:00",
            }
        ]
    )

    async def mock_current_user(request):
        return "user-1"

    monkeypatch.setattr(feedback, "get_current_user", mock_current_user)

    with TestClient(app) as client:
        resp = client.get("/api/threads/t1/feedback")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["feedback"][0]["feedback_id"] == "fb-sql-current"
    assert data["feedback"][0]["rating"] == -1


def test_list_feedback_without_sql_repo_returns_503(store):
    app = FastAPI()
    app.include_router(feedback.router)
    app.state.store = store

    with TestClient(app) as client:
        resp = client.get("/api/threads/t1/feedback")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Feedback not available"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_feedback(client):
    create_resp = client.post(
        "/api/threads/t1/feedback", json={"message_id": "m1", "rating": "positive"}
    )
    fb_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/threads/t1/feedback/{fb_id}",
        json={"rating": "negative", "comment": "Changed my mind"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["rating"] == "negative"
    assert data["comment"] == "Changed my mind"


def test_update_feedback_not_found(client):
    resp = client.patch(
        "/api/threads/t1/feedback/nonexistent", json={"rating": "positive"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_feedback(client, store):
    create_resp = client.post(
        "/api/threads/t1/feedback", json={"message_id": "m1", "rating": "positive"}
    )
    fb_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/threads/t1/feedback/{fb_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["id"] == fb_id

    assert fb_id not in store._data.get("feedback/t1", {})


def test_delete_feedback_not_found(client):
    resp = client.delete("/api/threads/t1/feedback/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_feedback_stats(client):
    client.post(
        "/api/threads/t1/feedback", json={"message_id": "m1", "rating": "positive"}
    )
    client.post(
        "/api/threads/t1/feedback",
        json={"message_id": "m2", "rating": "negative", "comment": "Bad"},
    )
    client.post(
        "/api/threads/t1/feedback",
        json={"message_id": "m3", "rating": "positive", "comment": "Great"},
    )

    resp = client.get("/api/threads/t1/feedback/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["positive"] == 2
    assert data["negative"] == 1
    assert data["with_comments"] == 2


# ---------------------------------------------------------------------------
# Store unavailable
# ---------------------------------------------------------------------------


def test_create_feedback_no_store():
    app = FastAPI()
    app.include_router(feedback.router)

    with patch.object(
        feedback, "get_feedback_config", return_value=FeedbackConfig(enabled=True)
    ):
        with TestClient(app) as c:
            resp = c.post(
                "/api/threads/t1/feedback",
                json={"message_id": "m1", "rating": "positive"},
            )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# LangSmith sync
# ---------------------------------------------------------------------------


def test_langsmith_sync_called_when_enabled(client, monkeypatch):
    sync_calls: list[tuple] = []

    async def mock_sync(run_id, rating, comment):
        sync_calls.append((run_id, rating, comment))

    monkeypatch.setattr(feedback, "_sync_to_langsmith", mock_sync)

    with patch.object(
        feedback,
        "get_feedback_config",
        return_value=FeedbackConfig(enabled=True, langsmith_sync=True),
    ):
        resp = client.post(
            "/api/threads/t1/feedback",
            json={
                "message_id": "m1",
                "run_id": "run_abc",
                "rating": "positive",
                "comment": "Nice",
            },
        )

    assert resp.status_code == 200
    assert len(sync_calls) == 1
    assert sync_calls[0] == ("run_abc", "positive", "Nice")


def test_langsmith_sync_skipped_without_run_id(client, monkeypatch):
    sync_calls: list = []

    async def mock_sync(run_id, rating, comment):
        sync_calls.append(1)

    monkeypatch.setattr(feedback, "_sync_to_langsmith", mock_sync)

    with patch.object(
        feedback,
        "get_feedback_config",
        return_value=FeedbackConfig(enabled=True, langsmith_sync=True),
    ):
        resp = client.post(
            "/api/threads/t1/feedback",
            json={"message_id": "m1", "rating": "positive"},
        )

    assert resp.status_code == 200
    assert len(sync_calls) == 0
