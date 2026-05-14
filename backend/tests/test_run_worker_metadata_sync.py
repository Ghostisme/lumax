from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deerflow.runtime.runs.schemas import RunStatus
from deerflow.runtime.runs.worker import _sync_thread_metadata_after_run


class FakeCheckpointer:
    def __init__(self, channel_values: dict | None):
        self.aget_tuple = AsyncMock(
            return_value=SimpleNamespace(
                checkpoint={"channel_values": channel_values or {}},
            )
        )


class FakeThreadStore:
    def __init__(self):
        self.update_display_name = AsyncMock()
        self.update_status = AsyncMock()


@pytest.mark.anyio
async def test_sync_thread_metadata_after_success_persists_title_and_idle_status():
    checkpointer = FakeCheckpointer({"title": "Thread Title"})
    thread_store = FakeThreadStore()

    await _sync_thread_metadata_after_run(
        checkpointer=checkpointer,
        thread_store=thread_store,
        thread_id="thread-1",
        status=RunStatus.success,
    )

    checkpointer.aget_tuple.assert_awaited_once_with({"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}})
    thread_store.update_display_name.assert_awaited_once_with("thread-1", "Thread Title")
    thread_store.update_status.assert_awaited_once_with("thread-1", "idle")


@pytest.mark.anyio
async def test_sync_thread_metadata_skips_blank_title_but_persists_error_status():
    checkpointer = FakeCheckpointer({"title": "  "})
    thread_store = FakeThreadStore()

    await _sync_thread_metadata_after_run(
        checkpointer=checkpointer,
        thread_store=thread_store,
        thread_id="thread-1",
        status=RunStatus.error,
    )

    thread_store.update_display_name.assert_not_awaited()
    thread_store.update_status.assert_awaited_once_with("thread-1", "error")
