from __future__ import annotations

import contextlib
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_async_make_store_uses_unified_database_when_legacy_checkpointer_absent(
    monkeypatch,
):
    from deerflow.runtime.store import async_provider

    calls = []
    database_config = SimpleNamespace(
        backend="postgres", postgres_url="postgresql://localhost/db"
    )
    app_config = SimpleNamespace(checkpointer=None, database=database_config)

    @contextlib.asynccontextmanager
    async def fake_database_store(config):
        calls.append(config)
        yield "database-store"

    monkeypatch.setattr(
        async_provider, "_async_store_from_database", fake_database_store
    )

    async with async_provider.make_store(app_config) as store:
        assert store == "database-store"

    assert calls == [database_config]


@pytest.mark.asyncio
async def test_async_make_store_prefers_legacy_checkpointer_over_unified_database(
    monkeypatch,
):
    from deerflow.runtime.store import async_provider

    calls = []
    legacy_config = SimpleNamespace(type="sqlite", connection_string="legacy.db")
    database_config = SimpleNamespace(
        backend="postgres", postgres_url="postgresql://localhost/db"
    )
    app_config = SimpleNamespace(checkpointer=legacy_config, database=database_config)

    @contextlib.asynccontextmanager
    async def fake_legacy_store(config):
        calls.append(("legacy", config))
        yield "legacy-store"

    @contextlib.asynccontextmanager
    async def fake_database_store(config):
        calls.append(("database", config))
        yield "database-store"

    monkeypatch.setattr(async_provider, "_async_store", fake_legacy_store)
    monkeypatch.setattr(
        async_provider, "_async_store_from_database", fake_database_store
    )

    async with async_provider.make_store(app_config) as store:
        assert store == "legacy-store"

    assert calls == [("legacy", legacy_config)]


def test_sync_store_context_uses_unified_database_when_legacy_checkpointer_absent(
    monkeypatch,
):
    from deerflow.runtime.store import provider

    calls = []
    database_config = SimpleNamespace(
        backend="postgres", postgres_url="postgresql://localhost/db"
    )
    app_config = SimpleNamespace(checkpointer=None, database=database_config)

    @contextlib.contextmanager
    def fake_database_store(config):
        calls.append(config)
        yield "database-store"

    monkeypatch.setattr(provider, "get_app_config", lambda: app_config)
    monkeypatch.setattr(provider, "_sync_store_cm_from_database", fake_database_store)

    with provider.store_context() as store:
        assert store == "database-store"

    assert calls == [database_config]
