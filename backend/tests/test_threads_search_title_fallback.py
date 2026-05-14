from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.gateway.routers import threads


@pytest.mark.anyio
async def test_resolve_thread_display_name_backfills_title_from_checkpoint():
    checkpointer = SimpleNamespace(
        aget_tuple=AsyncMock(
            return_value=SimpleNamespace(
                checkpoint={"channel_values": {"title": " Backfilled Title "}},
            )
        )
    )
    thread_store = SimpleNamespace(update_display_name=AsyncMock())

    title = await threads._resolve_thread_display_name(
        {"thread_id": "thread-1", "display_name": None},
        checkpointer=checkpointer,
        thread_store=thread_store,
    )

    assert title == "Backfilled Title"
    checkpointer.aget_tuple.assert_awaited_once_with({"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}})
    thread_store.update_display_name.assert_awaited_once_with("thread-1", "Backfilled Title", touch_updated_at=False)


@pytest.mark.anyio
async def test_resolve_thread_display_name_prefers_existing_summary_title():
    checkpointer = SimpleNamespace(aget_tuple=AsyncMock())
    thread_store = SimpleNamespace(update_display_name=AsyncMock())

    title = await threads._resolve_thread_display_name(
        {"thread_id": "thread-1", "display_name": "Stored Title"},
        checkpointer=checkpointer,
        thread_store=thread_store,
    )

    assert title == "Stored Title"
    checkpointer.aget_tuple.assert_not_awaited()
    thread_store.update_display_name.assert_not_awaited()
