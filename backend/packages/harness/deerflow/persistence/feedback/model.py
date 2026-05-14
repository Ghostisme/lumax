"""ORM model for user feedback on runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class FeedbackRow(Base):
    __tablename__ = "feedback"

    __table_args__ = (
        UniqueConstraint(
            "thread_id", "run_id", "user_id", name="uq_feedback_thread_run_user"
        ),
    )

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    message_id: Mapped[str | None] = mapped_column(String(64))
    # message_id is an optional RunEventStore event identifier —
    # allows feedback to target a specific message or the entire run

    rating: Mapped[int] = mapped_column(nullable=False)
    # +1 (thumbs-up), -1 (thumbs-down), 0 (not rated yet)

    result: Mapped[str | None] = mapped_column(String(16))
    # "positive", "negative", or NULL for not rated yet

    comment: Mapped[str | None] = mapped_column(Text)
    # Optional text feedback from the user

    feedback_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Time when the user explicitly submitted feedback; NULL for neutral rows

    agent_id: Mapped[str] = mapped_column(String(128), default="lead_agent")
    agent_name: Mapped[str] = mapped_column(String(128), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
