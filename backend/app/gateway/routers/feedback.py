"""Feedback endpoints — create, list, stats, delete.

Allows users to submit thumbs-up/down feedback on runs,
optionally scoped to a specific message.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.deps import get_current_user, get_feedback_repo, get_store
from deerflow.config.feedback_config import get_feedback_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads", tags=["feedback"])

FEEDBACK_NS_PREFIX: tuple[str, ...] = ("feedback",)
"""Store namespace prefix. Full key is ``("feedback", thread_id)``."""


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class FeedbackCreateRequest(BaseModel):
    message_id: str = Field(..., description="ID of the message being rated")
    run_id: str | None = Field(
        default=None, description="Run ID (used for LangSmith sync)"
    )
    rating: Literal["positive", "negative"] = Field(
        ..., description="Thumbs up or down"
    )
    comment: str | None = Field(default=None, description="Optional text comment")
    tags: list[str] = Field(default_factory=list, description="Optional category tags")


class FeedbackPatchRequest(BaseModel):
    rating: Literal["positive", "negative"] | None = Field(
        default=None, description="Updated rating"
    )
    comment: str | None = Field(default=None, description="Updated comment")
    tags: list[str] | None = Field(default=None, description="Updated tags")


class FeedbackEntry(BaseModel):
    id: str = Field(..., description="Unique feedback identifier")
    thread_id: str = Field(..., description="Thread the feedback belongs to")
    message_id: str = Field(..., description="Message the feedback applies to")
    run_id: str | None = Field(
        default=None, description="Run ID for LangSmith correlation"
    )
    rating: str = Field(..., description="positive or negative")
    comment: str | None = Field(default=None, description="User comment")
    tags: list[str] = Field(default_factory=list, description="Category tags")
    created_at: float = Field(..., description="Unix timestamp")
    updated_at: float = Field(..., description="Unix timestamp")


class FeedbackListResponse(BaseModel):
    feedback: list[FeedbackEntry] = Field(default_factory=list)
    count: int = Field(default=0)


class SqlFeedbackEntry(BaseModel):
    feedback_id: str = Field(..., description="SQL feedback row identifier")
    thread_id: str = Field(..., description="Thread the feedback belongs to")
    run_id: str = Field(..., description="Run the feedback applies to")
    user_id: str | None = Field(default=None, description="Current feedback owner")
    message_id: str | None = Field(
        default=None, description="Optional message or event identifier"
    )
    rating: int = Field(..., description="1 positive, -1 negative, 0 neutral")
    result: Literal["positive", "negative"] | None = Field(
        default=None, description="Current feedback result"
    )
    comment: str | None = Field(default=None, description="Optional user comment")
    feedback_time: str | None = Field(
        default=None, description="Time the user explicitly submitted feedback"
    )
    agent_id: str | None = Field(default=None, description="Agent identifier")
    agent_name: str | None = Field(default=None, description="Agent display name")
    created_at: str = Field(..., description="SQL row creation time")


class SqlFeedbackListResponse(BaseModel):
    feedback: list[SqlFeedbackEntry] = Field(default_factory=list)
    count: int = Field(default=0)


class FeedbackConfigResponse(BaseModel):
    enabled: bool
    langsmith_sync: bool
    require_comment_on_negative: bool


class FeedbackStatsResponse(BaseModel):
    total: int = 0
    positive: int = 0
    negative: int = 0
    with_comments: int = 0


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------


def _thread_ns(thread_id: str) -> tuple[str, ...]:
    return (*FEEDBACK_NS_PREFIX, thread_id)


async def _get_all_feedback(store, thread_id: str) -> list[dict]:
    """Return all feedback entries for a thread from the Store."""
    items = await store.asearch(_thread_ns(thread_id), limit=10_000)
    return [item.value for item in items]


# ---------------------------------------------------------------------------
# LangSmith sync (best-effort, fire-and-forget)
# ---------------------------------------------------------------------------


async def _sync_to_langsmith(run_id: str, rating: str, comment: str | None) -> None:
    """Report feedback to LangSmith. Errors are logged, never raised."""
    try:
        from langsmith import Client as LangSmithClient

        client = LangSmithClient()
        score = 1.0 if rating == "positive" else 0.0
        client.create_feedback(
            run_id=run_id,
            key="user-feedback",
            score=score,
            comment=comment,
        )
        logger.info("Synced feedback to LangSmith: run_id=%s score=%s", run_id, score)
    except ImportError:
        logger.warning("langsmith package not installed — skipping feedback sync")
    except Exception:
        logger.exception("Failed to sync feedback to LangSmith: run_id=%s", run_id)


async def _sync_to_sql_feedback(
    request: Request,
    *,
    thread_id: str,
    run_id: str | None,
    rating: str,
    comment: str | None,
) -> None:
    """Best-effort bridge from legacy message feedback to SQL run feedback."""
    if not run_id:
        return

    feedback_repo = getattr(request.app.state, "feedback_repo", None)
    if feedback_repo is None:
        logger.warning(
            "Skipping SQL feedback sync for thread %s run %s: feedback repo unavailable",
            thread_id,
            run_id,
        )
        return

    try:
        user_id = await get_current_user(request)
        await feedback_repo.upsert_by_run(
            run_id=run_id,
            thread_id=thread_id,
            user_id=user_id,
            result=rating,
            comment=comment,
        )
    except Exception:
        logger.exception(
            "Failed to sync legacy feedback to SQL: thread_id=%s run_id=%s",
            thread_id,
            run_id,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{thread_id}/feedback/config",
    response_model=FeedbackConfigResponse,
    summary="Get Feedback Configuration",
)
async def get_feedback_config_endpoint() -> FeedbackConfigResponse:
    """Return the current feedback configuration."""
    config = get_feedback_config()
    return FeedbackConfigResponse(
        enabled=config.enabled,
        langsmith_sync=config.langsmith_sync,
        require_comment_on_negative=config.require_comment_on_negative,
    )


@router.post(
    "/{thread_id}/feedback",
    response_model=FeedbackEntry,
    summary="Submit Feedback",
    description="Submit user feedback (thumbs up/down) for an AI message.",
)
async def create_feedback(
    thread_id: str, body: FeedbackCreateRequest, request: Request
) -> FeedbackEntry:
    config = get_feedback_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Feedback is disabled")

    if (
        config.require_comment_on_negative
        and body.rating == "negative"
        and not body.comment
    ):
        raise HTTPException(
            status_code=422, detail="A comment is required for negative feedback"
        )

    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    now = time.time()
    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
    record = {
        "id": feedback_id,
        "thread_id": thread_id,
        "message_id": body.message_id,
        "run_id": body.run_id,
        "rating": body.rating,
        "comment": body.comment,
        "tags": body.tags,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await store.aput(_thread_ns(thread_id), feedback_id, record)
    except Exception:
        logger.exception("Failed to store feedback for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    await _sync_to_sql_feedback(
        request,
        thread_id=thread_id,
        run_id=body.run_id,
        rating=body.rating,
        comment=body.comment,
    )

    if config.langsmith_sync and body.run_id:
        await _sync_to_langsmith(body.run_id, body.rating, body.comment)

    return FeedbackEntry(**record)


@router.get(
    "/{thread_id}/feedback",
    response_model=SqlFeedbackListResponse,
    summary="List Feedback",
    description="List SQL run-level feedback current state for a thread.",
)
async def list_feedback(thread_id: str, request: Request) -> SqlFeedbackListResponse:
    config = get_feedback_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Feedback is disabled")

    feedback_repo = get_feedback_repo(request)
    user_id = await get_current_user(request)
    entries = await feedback_repo.list_by_thread(thread_id, user_id=user_id)
    return SqlFeedbackListResponse(
        feedback=[SqlFeedbackEntry(**e) for e in entries],
        count=len(entries),
    )


@router.patch(
    "/{thread_id}/feedback/{feedback_id}",
    response_model=FeedbackEntry,
    summary="Update Feedback",
    description="Partially update an existing feedback entry.",
)
async def update_feedback(
    thread_id: str,
    feedback_id: str,
    body: FeedbackPatchRequest,
    request: Request,
) -> FeedbackEntry:
    config = get_feedback_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Feedback is disabled")

    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    item = await store.aget(_thread_ns(thread_id), feedback_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Feedback {feedback_id} not found")

    record = dict(item.value)
    if body.rating is not None:
        record["rating"] = body.rating
    if body.comment is not None:
        record["comment"] = body.comment
    if body.tags is not None:
        record["tags"] = body.tags
    record["updated_at"] = time.time()

    try:
        await store.aput(_thread_ns(thread_id), feedback_id, record)
    except Exception:
        logger.exception("Failed to update feedback %s", feedback_id)
        raise HTTPException(status_code=500, detail="Failed to update feedback")

    if config.langsmith_sync and record.get("run_id"):
        await _sync_to_langsmith(
            record["run_id"], record["rating"], record.get("comment")
        )

    return FeedbackEntry(**record)


@router.delete(
    "/{thread_id}/feedback/{feedback_id}",
    response_model=FeedbackEntry,
    summary="Delete Feedback",
    description="Delete a feedback entry.",
)
async def delete_feedback(
    thread_id: str,
    feedback_id: str,
    request: Request,
) -> FeedbackEntry:
    config = get_feedback_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Feedback is disabled")

    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    item = await store.aget(_thread_ns(thread_id), feedback_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Feedback {feedback_id} not found")

    record = dict(item.value)
    try:
        await store.adelete(_thread_ns(thread_id), feedback_id)
    except Exception:
        logger.exception("Failed to delete feedback %s", feedback_id)
        raise HTTPException(status_code=500, detail="Failed to delete feedback")

    return FeedbackEntry(**record)


@router.get(
    "/{thread_id}/feedback/stats",
    response_model=FeedbackStatsResponse,
    summary="Feedback Stats",
    description="Get aggregated feedback statistics for a thread.",
)
async def get_feedback_stats(thread_id: str, request: Request) -> FeedbackStatsResponse:
    config = get_feedback_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Feedback is disabled")

    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    entries = await _get_all_feedback(store, thread_id)
    positive = sum(1 for e in entries if e.get("rating") == "positive")
    negative = sum(1 for e in entries if e.get("rating") == "negative")
    with_comments = sum(1 for e in entries if e.get("comment"))

    return FeedbackStatsResponse(
        total=len(entries),
        positive=positive,
        negative=negative,
        with_comments=with_comments,
    )
