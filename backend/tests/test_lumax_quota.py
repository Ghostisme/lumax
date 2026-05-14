from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_run_agent_checks_quota_before_agent_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from deerflow.runtime.runs.manager import RunManager
    from deerflow.runtime.runs.schemas import DisconnectMode, RunStatus
    from deerflow.runtime.runs.worker import RunContext, run_agent

    class FakeBridge:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, dict]] = []
            self.ended: list[str] = []

        async def publish(self, run_id, event, data):
            self.events.append((run_id, event, data))

        async def publish_end(self, run_id):
            self.ended.append(run_id)

        async def cleanup(self, run_id, *, delay=0):
            pass

    class FakeReporter:
        def __init__(self) -> None:
            self.checks: list[tuple[str, str]] = []
            self.settlements = 0

        async def check_quota(self, tenant_id: str, user_id: str) -> dict:
            self.checks.append((tenant_id, user_id))
            return {"allowed": False, "remaining": 0, "message": "Token 总配额不足"}

        async def report_settlement(self, settlement) -> None:
            self.settlements += 1

    reporter = FakeReporter()

    import app.gateway.usage_reporter as usage_reporter

    monkeypatch.setattr(usage_reporter.UsageReporter, "get_instance", lambda: reporter)

    run_manager = RunManager()
    record = await run_manager.create(
        thread_id="thread-1",
        assistant_id="assistant-1",
        on_disconnect=DisconnectMode.cancel,
    )

    agent_factory_called = False

    def agent_factory(**kwargs):
        nonlocal agent_factory_called
        agent_factory_called = True
        raise AssertionError(
            "agent_factory must not be called when quota precheck denies"
        )

    bridge = FakeBridge()
    await run_agent(
        bridge=bridge,
        run_manager=run_manager,
        record=record,
        ctx=RunContext(checkpointer=None),
        agent_factory=agent_factory,
        graph_input={"messages": []},
        config={"configurable": {"tenant_id": "2052263773707833345", "user_id": 2}},
    )

    assert reporter.checks == [("2052263773707833345", "2")]
    assert reporter.settlements == 0
    assert agent_factory_called is False
    assert record.status is RunStatus.error
    assert record.error == "429: Token 总配额不足"
    assert bridge.events == [
        (
            record.run_id,
            "error",
            {"message": "429: Token 总配额不足", "name": "HTTPException"},
        )
    ]
    assert bridge.ended == [record.run_id]


@pytest.mark.anyio
async def test_check_quota_db_denies_when_user_quota_missing(
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
            return None

    class FakeConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def cursor(self, row_factory=None):
            return FakeCursor()

    class FakeAsyncConnection:
        @staticmethod
        async def connect(_dsn):
            return FakeConnection()

    monkeypatch.setattr(metering, "AsyncConnection", FakeAsyncConnection)
    monkeypatch.setattr(metering, "dict_row", object())

    result = await metering.check_quota_db(
        "postgres://example", tenant_id="2052263773707833345", user_id=2
    )

    assert result == {"allowed": False, "remaining": 0, "message": "Token 总配额不足"}
    query_sql, query_params = executed[0]
    assert "WHERE tenant_id = %s AND user_id = %s" in query_sql
    assert query_params == ("2052263773707833345", "2")


@pytest.mark.anyio
@pytest.mark.parametrize("total_quota", [None, "", "not-a-number"])
async def test_check_quota_db_denies_when_total_quota_invalid(
    monkeypatch: pytest.MonkeyPatch,
    total_quota,
) -> None:
    import app.gateway.lumax_db_metering as metering

    class FakeCursor:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, sql, params=()):
            pass

        async def fetchone(self):
            return {"total_quota": total_quota, "used_quota": 0}

    class FakeConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def cursor(self, row_factory=None):
            return FakeCursor()

    class FakeAsyncConnection:
        @staticmethod
        async def connect(_dsn):
            return FakeConnection()

    monkeypatch.setattr(metering, "AsyncConnection", FakeAsyncConnection)
    monkeypatch.setattr(metering, "dict_row", object())

    result = await metering.check_quota_db(
        "postgres://example", tenant_id="2052263773707833345", user_id=2
    )

    assert result == {"allowed": False, "remaining": 0, "message": "Token 总配额不足"}


@pytest.mark.anyio
async def test_consume_user_quota_denies_when_user_quota_missing() -> None:
    import app.gateway.lumax_db_metering as metering

    executed: list[str] = []

    class FakeCursor:
        async def execute(self, sql, params=()):
            executed.append(sql)

        async def fetchone(self):
            return None

    with pytest.raises(RuntimeError, match="Token 总配额不足"):
        await metering._consume_user_quota(
            FakeCursor(),
            tenant_id="2052263773707833345",
            user_id=2,
            username="alice",
            total_tokens=100,
        )

    assert not any("INSERT INTO lumax_user_quota" in sql for sql in executed)


@pytest.mark.anyio
async def test_consume_user_quota_normalizes_user_id_to_string() -> None:
    import app.gateway.lumax_db_metering as metering

    executed: list[tuple[str, tuple]] = []

    class FakeCursor:
        async def execute(self, sql, params=()):
            executed.append((sql, tuple(params)))

        async def fetchone(self):
            return {"total_quota": 100, "used_quota": 10}

    await metering._consume_user_quota(
        FakeCursor(),
        tenant_id="2052263773707833345",
        user_id=2,
        username="alice",
        total_tokens=25,
    )

    assert executed[0][1] == ("2052263773707833345", "2")
    assert executed[-1][1] == (25, "2052263773707833345", "2")


@pytest.mark.anyio
async def test_consume_user_quota_records_actual_usage_when_remaining_insufficient() -> (
    None
):
    import app.gateway.lumax_db_metering as metering

    executed: list[tuple[str, tuple]] = []

    class FakeCursor:
        async def execute(self, sql, params=()):
            executed.append((sql, tuple(params)))

        async def fetchone(self):
            return {"total_quota": 100, "used_quota": 90}

    await metering._consume_user_quota(
        FakeCursor(),
        tenant_id="2052263773707833345",
        user_id=2,
        username="alice",
        total_tokens=25,
    )

    update_sql, update_params = executed[-1]
    assert "UPDATE lumax_user_quota" in update_sql
    assert "SET used_quota = used_quota + %s" in update_sql
    assert update_params == (25, "2052263773707833345", "2")
