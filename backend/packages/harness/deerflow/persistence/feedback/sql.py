"""SQLAlchemy-backed feedback storage.

Each method acquires its own short-lived session.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deerflow.persistence.feedback.model import FeedbackRow
from deerflow.runtime.user_context import AUTO, _AutoSentinel, resolve_user_id


class FeedbackRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    @staticmethod
    def _result_for_rating(rating: int) -> str | None:
        if rating == 1:
            return "positive"
        if rating == -1:
            return "negative"
        if rating == 0:
            return None
        raise ValueError(f"rating must be +1, 0, or -1, got {rating}")

    @staticmethod
    def _rating_for_result(result: str) -> int:
        if result == "positive":
            return 1
        if result == "negative":
            return -1
        raise ValueError(f"result must be 'positive' or 'negative', got {result!r}")

    @staticmethod
    def _row_to_dict(row: FeedbackRow) -> dict:
        d = row.to_dict()
        for key in ("created_at", "feedback_time"):
            val = d.get(key)
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d

    async def create(
        self,
        *,
        run_id: str,
        thread_id: str,
        rating: int,
        user_id: str | None | _AutoSentinel = AUTO,
        message_id: str | None = None,
        comment: str | None = None,
        agent_id: str = "lead_agent",
        agent_name: str = "",
    ) -> dict:
        """Create a feedback record. rating must be +1, 0, or -1."""
        result = self._result_for_rating(rating)
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.create"
        )
        now = datetime.now(UTC)
        row = FeedbackRow(
            feedback_id=str(uuid.uuid4()),
            run_id=run_id,
            thread_id=thread_id,
            user_id=resolved_user_id,
            message_id=message_id,
            rating=rating,
            result=result,
            comment=comment if rating in (1, -1) else None,
            feedback_time=now if rating in (1, -1) else None,
            agent_id=agent_id or "lead_agent",
            agent_name=agent_name or "",
            created_at=now,
        )
        async with self._sf() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._row_to_dict(row)

    async def get(
        self,
        feedback_id: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict | None:
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.get"
        )
        async with self._sf() as session:
            row = await session.get(FeedbackRow, feedback_id)
            if row is None:
                return None
            if resolved_user_id is not None and row.user_id != resolved_user_id:
                return None
            return self._row_to_dict(row)

    async def list_by_run(
        self,
        thread_id: str,
        run_id: str,
        *,
        limit: int = 100,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> list[dict]:
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.list_by_run"
        )
        stmt = select(FeedbackRow).where(
            FeedbackRow.thread_id == thread_id, FeedbackRow.run_id == run_id
        )
        if resolved_user_id is not None:
            stmt = stmt.where(FeedbackRow.user_id == resolved_user_id)
        stmt = stmt.order_by(FeedbackRow.created_at.asc()).limit(limit)
        async with self._sf() as session:
            result = await session.execute(stmt)
            return [self._row_to_dict(r) for r in result.scalars()]

    async def list_by_thread(
        self,
        thread_id: str,
        *,
        limit: int = 100,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> list[dict]:
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.list_by_thread"
        )
        stmt = select(FeedbackRow).where(FeedbackRow.thread_id == thread_id)
        if resolved_user_id is not None:
            stmt = stmt.where(FeedbackRow.user_id == resolved_user_id)
        stmt = stmt.order_by(FeedbackRow.created_at.asc()).limit(limit)
        async with self._sf() as session:
            result = await session.execute(stmt)
            return [self._row_to_dict(r) for r in result.scalars()]

    async def delete(
        self,
        feedback_id: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> bool:
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.delete"
        )
        async with self._sf() as session:
            row = await session.get(FeedbackRow, feedback_id)
            if row is None:
                return False
            if resolved_user_id is not None and row.user_id != resolved_user_id:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def upsert(
        self,
        *,
        run_id: str,
        thread_id: str,
        rating: int,
        user_id: str | None | _AutoSentinel = AUTO,
        comment: str | None = None,
    ) -> dict:
        """Create or update feedback for (thread_id, run_id, user_id). rating must be +1, 0, or -1."""
        result_value = self._result_for_rating(rating)
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.upsert"
        )
        async with self._sf() as session:
            stmt = select(FeedbackRow).where(
                FeedbackRow.thread_id == thread_id,
                FeedbackRow.run_id == run_id,
                FeedbackRow.user_id == resolved_user_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            now = datetime.now(UTC)
            if row is not None:
                row.rating = rating
                row.result = result_value
                row.comment = comment if rating in (1, -1) else None
                row.feedback_time = now if rating in (1, -1) else None
                if rating in (1, -1):
                    row.created_at = now
            else:
                row = FeedbackRow(
                    feedback_id=str(uuid.uuid4()),
                    run_id=run_id,
                    thread_id=thread_id,
                    user_id=resolved_user_id,
                    rating=rating,
                    result=result_value,
                    comment=comment if rating in (1, -1) else None,
                    feedback_time=now if rating in (1, -1) else None,
                    agent_id="lead_agent",
                    agent_name="",
                    created_at=now,
                )
                session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._row_to_dict(row)

    async def ensure_neutral_for_run(
        self,
        *,
        run_id: str,
        thread_id: str,
        user_id: str | None | _AutoSentinel = AUTO,
        message_id: str | None = None,
        agent_id: str = "lead_agent",
        agent_name: str = "",
    ) -> dict:
        """Ensure a neutral feedback row exists for (thread_id, run_id, user_id)."""
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.ensure_neutral_for_run"
        )
        async with self._sf() as session:
            stmt = select(FeedbackRow).where(
                FeedbackRow.thread_id == thread_id,
                FeedbackRow.run_id == run_id,
                FeedbackRow.user_id == resolved_user_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                row = FeedbackRow(
                    feedback_id=str(uuid.uuid4()),
                    run_id=run_id,
                    thread_id=thread_id,
                    user_id=resolved_user_id,
                    message_id=message_id,
                    rating=0,
                    result=None,
                    comment=None,
                    feedback_time=None,
                    agent_id=agent_id or "lead_agent",
                    agent_name=agent_name or "",
                    created_at=datetime.now(UTC),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
            return self._row_to_dict(row)

    async def upsert_by_run(
        self,
        *,
        run_id: str,
        thread_id: str,
        result: str,
        user_id: str | None | _AutoSentinel = AUTO,
        comment: str | None = None,
        agent_id: str = "lead_agent",
        agent_name: str = "",
    ) -> dict:
        """Create or update explicit user feedback for a run."""
        rating = self._rating_for_result(result)
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.upsert_by_run"
        )
        async with self._sf() as session:
            stmt = select(FeedbackRow).where(
                FeedbackRow.thread_id == thread_id,
                FeedbackRow.run_id == run_id,
                FeedbackRow.user_id == resolved_user_id,
            )
            query_result = await session.execute(stmt)
            row = query_result.scalar_one_or_none()
            now = datetime.now(UTC)
            if row is not None:
                row.rating = rating
                row.result = result
                row.comment = comment
                row.feedback_time = now
                row.agent_id = row.agent_id or agent_id or "lead_agent"
                row.agent_name = row.agent_name or agent_name or ""
            else:
                row = FeedbackRow(
                    feedback_id=str(uuid.uuid4()),
                    run_id=run_id,
                    thread_id=thread_id,
                    user_id=resolved_user_id,
                    rating=rating,
                    result=result,
                    comment=comment,
                    feedback_time=now,
                    agent_id=agent_id or "lead_agent",
                    agent_name=agent_name or "",
                    created_at=now,
                )
                session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._row_to_dict(row)

    async def reset_by_run(
        self,
        *,
        thread_id: str,
        run_id: str,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict | None:
        """Reset current user's feedback for a run to the neutral state."""
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.reset_by_run"
        )
        async with self._sf() as session:
            stmt = select(FeedbackRow).where(
                FeedbackRow.thread_id == thread_id,
                FeedbackRow.run_id == run_id,
                FeedbackRow.user_id == resolved_user_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            row.rating = 0
            row.result = None
            row.comment = None
            row.feedback_time = None
            await session.commit()
            await session.refresh(row)
            return self._row_to_dict(row)

    async def delete_by_run(
        self,
        *,
        thread_id: str,
        run_id: str,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> bool:
        """Delete the current user's feedback for a run. Returns True if a record was deleted."""
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.delete_by_run"
        )
        async with self._sf() as session:
            stmt = select(FeedbackRow).where(
                FeedbackRow.thread_id == thread_id,
                FeedbackRow.run_id == run_id,
                FeedbackRow.user_id == resolved_user_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def list_by_thread_grouped(
        self,
        thread_id: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, dict]:
        """Return feedback grouped by run_id for a thread: {run_id: feedback_dict}."""
        resolved_user_id = resolve_user_id(
            user_id, method_name="FeedbackRepository.list_by_thread_grouped"
        )
        stmt = select(FeedbackRow).where(FeedbackRow.thread_id == thread_id)
        if resolved_user_id is not None:
            stmt = stmt.where(FeedbackRow.user_id == resolved_user_id)
        async with self._sf() as session:
            result = await session.execute(stmt)
            return {row.run_id: self._row_to_dict(row) for row in result.scalars()}

    async def aggregate_by_run(self, thread_id: str, run_id: str) -> dict:
        """Aggregate feedback stats for a run using database-side counting."""
        stmt = select(
            func.coalesce(
                func.sum(case((FeedbackRow.rating.in_((1, -1)), 1), else_=0)), 0
            ).label("total"),
            func.coalesce(
                func.sum(case((FeedbackRow.rating == 1, 1), else_=0)), 0
            ).label("positive"),
            func.coalesce(
                func.sum(case((FeedbackRow.rating == -1, 1), else_=0)), 0
            ).label("negative"),
        ).where(FeedbackRow.thread_id == thread_id, FeedbackRow.run_id == run_id)
        async with self._sf() as session:
            row = (await session.execute(stmt)).one()
            return {
                "run_id": run_id,
                "total": row.total,
                "positive": row.positive,
                "negative": row.negative,
            }
