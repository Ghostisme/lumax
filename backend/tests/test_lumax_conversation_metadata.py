from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.gateway.lumax_pricing_cache import PricingCacheError
from app.gateway.usage_reporter import UsageSettlement, _settlement_payload


def test_settlement_payload_includes_conversation_title_and_dept_id() -> None:
    settlement = UsageSettlement(
        idempotency_key="k1",
        tenant_id="2052263773707833345",
        user_id="2",
        username="alice",
        dept_id="dept-1",
        thread_id="thread-1",
        run_id="run-1",
        model_name="model-a",
        tokens_in=0,
        tokens_out=0,
        title="First chat",
    )

    assert _settlement_payload(settlement)["title"] == "First chat"
    assert _settlement_payload(settlement)["dept_id"] == "dept-1"


@pytest.mark.anyio
async def test_extract_settlement_title_reads_final_checkpoint_title() -> None:
    from deerflow.runtime.runs.worker import _extract_settlement_title

    class FakeCheckpointer:
        async def aget_tuple(self, config):
            assert config == {
                "configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}
            }
            return SimpleNamespace(
                checkpoint={"channel_values": {"title": "Final Title"}}
            )

    assert (
        await _extract_settlement_title(
            checkpointer=FakeCheckpointer(), thread_id="thread-1"
        )
        == "Final Title"
    )


@pytest.mark.anyio
async def test_persist_settlement_db_writes_conversation_username_agent_and_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gateway.lumax_db_metering as metering

    executed: list[tuple[str, tuple]] = []

    class FakeCursor:
        def __init__(self) -> None:
            self.fetchone_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, sql, params=()):
            executed.append((sql, tuple(params)))

        async def fetchone(self):
            self.fetchone_calls += 1
            if self.fetchone_calls == 1:
                return None
            if self.fetchone_calls == 2:
                return {"id": 101}
            return None

    class FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeConnection:
        def __init__(self) -> None:
            self.cursor_instance = FakeCursor()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def transaction(self):
            return FakeTransaction()

        def cursor(self, row_factory=None):
            return self.cursor_instance

    class FakeAsyncConnection:
        @staticmethod
        async def connect(_dsn):
            return FakeConnection()

    async def fake_calculate_pricing(_settlement):
        raise AssertionError("zero-token settlement should not read model pricing")

    monkeypatch.setattr(metering, "AsyncConnection", FakeAsyncConnection)
    monkeypatch.setattr(metering, "dict_row", object())
    monkeypatch.setattr(metering, "_calculate_pricing", fake_calculate_pricing)

    await metering.persist_settlement_db(
        "postgres://example",
        {
            "tenant_id": "2052263773707833345",
            "user_id": "2",
            "username": "alice",
            "dept_id": "dept-1",
            "thread_id": "thread-1",
            "run_id": "run-1",
            "idempotency_key": "k1",
            "model_name": "model-a",
            "agent_name": "agent-a",
            "skill_name": "",
            "title": "First chat",
            "tokens_total": 0,
            "messages": [],
        },
    )

    insert_sql, insert_params = next(
        item for item in executed if "INSERT INTO lumax_conversation" in item[0]
    )
    assert "username" in insert_sql
    assert "dept_id" in insert_sql
    assert "title" in insert_sql
    assert insert_params[:8] == (
        "2052263773707833345",
        "thread-1",
        "2",
        "alice",
        "dept-1",
        "model-a",
        "agent-a",
        "First chat",
    )

    update_sql, update_params = next(
        item for item in executed if "UPDATE lumax_conversation" in item[0]
    )
    assert "username = %s" in update_sql
    assert "dept_id = %s" in update_sql
    assert "title = %s" in update_sql
    assert update_params[:5] == (
        "alice",
        "dept-1",
        "model-a",
        "agent-a",
        "First chat",
    )


@pytest.mark.anyio
async def test_persist_settlement_db_preserves_existing_dept_id_when_new_value_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gateway.lumax_db_metering as metering

    executed: list[tuple[str, tuple]] = []

    class FakeCursor:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, sql, params=()):
            executed.append((sql, tuple(params)))

        async def fetchone(self):
            return {
                "id": 101,
                "username": "alice-old",
                "dept_id": "dept-old",
                "title": "Old title",
                "model_name": "model-old",
                "agent_name": "agent-old",
                "skill_name": "skill-old",
            }

    class FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeConnection:
        def __init__(self) -> None:
            self.cursor_instance = FakeCursor()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def transaction(self):
            return FakeTransaction()

        def cursor(self, row_factory=None):
            return self.cursor_instance

    class FakeAsyncConnection:
        @staticmethod
        async def connect(_dsn):
            return FakeConnection()

    async def fake_calculate_pricing(_settlement):
        raise AssertionError("zero-token settlement should not read model pricing")

    monkeypatch.setattr(metering, "AsyncConnection", FakeAsyncConnection)
    monkeypatch.setattr(metering, "dict_row", object())
    monkeypatch.setattr(metering, "_calculate_pricing", fake_calculate_pricing)

    await metering.persist_settlement_db(
        "postgres://example",
        {
            "tenant_id": "2052263773707833345",
            "user_id": "2",
            "username": "alice",
            "dept_id": "",
            "thread_id": "thread-1",
            "run_id": "run-1",
            "idempotency_key": "k1",
            "model_name": "model-a",
            "agent_name": "agent-a",
            "skill_name": "",
            "title": "",
            "tokens_total": 0,
            "messages": [],
        },
    )

    update_sql, update_params = next(
        item for item in executed if "UPDATE lumax_conversation" in item[0]
    )
    assert "dept_id = %s" in update_sql
    assert update_params[:5] == (
        "alice",
        "dept-old",
        "model-a",
        "agent-a",
        "Old title",
    )


@pytest.mark.anyio
async def test_calculate_pricing_falls_back_to_db_when_redis_pricing_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import psycopg

    import app.gateway.lumax_db_metering as metering

    executed: list[tuple[str, tuple]] = []

    class FakeCursor:
        def __init__(self) -> None:
            self.fetchone_calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=()):
            executed.append((sql, tuple(params)))

        def fetchone(self):
            self.fetchone_calls += 1
            return {
                "id": 10,
                "tenant_id": "2052263773707833345",
                "model_code": "doubao-seed-2.0-pro",
                "price_unit": "per_1m_tokens",
                "currency": "CNY",
                "has_tiered_pricing": True,
                "supported_inference_modes": "online,batch",
                "input_price": "3.2",
                "output_price": "16",
                "cache_write_price": "0",
                "cache_read_price": "0.64",
                "cache_storage_price": "0",
                "updated_at": "2026-05-06T00:00:00",
            }

        def fetchall(self):
            return [
                {
                    "id": 101,
                    "inference_mode": "online",
                    "input_length_min": 0,
                    "input_length_max": 32,
                    "output_length_min": 0,
                    "output_length_max": -1,
                    "input_price": "3.2",
                    "output_price": "16",
                    "cache_storage_price": "0.017",
                    "cache_read_price": "0.64",
                    "sort_order": 1,
                }
            ]

    class FakeConnection:
        def __init__(self) -> None:
            self.cursor_instance = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return self.cursor_instance

    async def fake_get_model_pricing(*, tenant_id: str, model_name: str):
        raise PricingCacheError(
            f"模型计费信息未配置：租户ID={tenant_id}，模型={model_name}"
        )

    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: FakeConnection())
    monkeypatch.setattr(metering, "get_model_pricing", fake_get_model_pricing)

    result = await metering._calculate_pricing(
        "postgres://example",
        {
            "tenant_id": "2052263773707833345",
            "model_name": "doubao-seed-2.0-pro",
            "tokens_in": 1000,
            "tokens_out": 500,
            "tokens_total": 1500,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "reasoning_tokens": 0,
            "inference_mode": "online",
        },
    )

    assert result["price_tier_id"] == 101
    assert str(result["total_cost"]) == "0.011200"
    assert result["price_snapshot"]["modelCode"] == "doubao-seed-2.0-pro"
    assert result["price_snapshot"]["pricingUpdatedAt"] == "2026-05-06T00:00:00"
    pricing_sql, pricing_params = next(
        item for item in executed if "FROM lumax_llm_model" in item[0]
    )
    assert "tenant_id IN (%s, %s)" in pricing_sql
    assert pricing_params == (
        "doubao-seed-2.0-pro",
        "2052263773707833345",
        "0",
        "2052263773707833345",
    )
