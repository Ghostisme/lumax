import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

from deerflow.runtime.runs import worker as worker_module
from deerflow.runtime.runs.manager import RunManager
from deerflow.runtime.runs.schemas import RunStatus
from deerflow.runtime.runs.worker import RunContext, run_agent


class _FakeBridge:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, object]] = []
        self.ended: list[str] = []

    async def publish(self, run_id: str, event: str, data: object) -> None:
        self.events.append((run_id, event, data))

    async def publish_end(self, run_id: str) -> None:
        self.ended.append(run_id)

    async def cleanup(self, run_id: str, delay: int = 60) -> None:
        return None


class _FakeAgent:
    async def astream(self, graph_input, *, config, stream_mode):
        yield {"messages": graph_input.get("messages", [])}


class _FakeAgentWithAssistantMessage:
    async def astream(self, graph_input, *, config, stream_mode):
        messages = graph_input.setdefault("messages", [])
        messages.append(
            {"role": "assistant", "id": "assistant-msg-1", "content": "answer"}
        )
        yield {"messages": messages}


class _FakeUsageReporter:
    async def check_quota(self, tenant_id: str, user_id: str) -> dict:
        return {"allowed": True}


class _FakeFeedbackRepo:
    def __init__(self) -> None:
        self.neutral_calls: list[dict] = []

    async def ensure_neutral_for_run(self, **kwargs):
        self.neutral_calls.append(kwargs)
        return {"feedback_id": "fb-neutral", **kwargs, "rating": 0, "result": None}


class _FakeCheckpointer:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = messages

    async def aget_tuple(self, config):
        return SimpleNamespace(
            checkpoint={"channel_values": {"messages": self.messages}}
        )


def test_langfuse_run_context_uses_session_id_from_metadata(monkeypatch):
    class _FakeContextManager:
        def __init__(self) -> None:
            self.entered = False
            self.exited = False

        def __enter__(self):
            self.entered = True
            return self

        def __exit__(self, exc_type, exc, tb):
            self.exited = True

    fake_context = _FakeContextManager()
    calls: list[str] = []

    monkeypatch.setattr(
        worker_module,
        "get_tracing_config",
        lambda: SimpleNamespace(
            langfuse=SimpleNamespace(is_configured=True),
        ),
    )
    monkeypatch.setattr(
        worker_module,
        "propagate_attributes",
        lambda *, session_id: calls.append(session_id) or fake_context,
    )

    with worker_module._langfuse_run_context(
        {"metadata": {"langfuse_session_id": "thread-langfuse"}}
    ) as entered:
        assert entered is fake_context

    assert calls == ["thread-langfuse"]
    assert fake_context.entered is True
    assert fake_context.exited is True


@pytest.mark.anyio
async def test_extract_feedback_message_id_uses_last_assistant_from_checkpoint():
    checkpointer = _FakeCheckpointer(
        [
            {"role": "user", "id": "user-msg-1", "content": "hello"},
            {"role": "assistant", "id": "assistant-msg-1", "content": "first"},
            {"role": "assistant", "id": "assistant-msg-2", "content": "final"},
        ]
    )

    message_id = await worker_module._extract_feedback_message_id(
        checkpointer=checkpointer,
        thread_id="thread-feedback",
        fallback_messages=[
            {"role": "assistant", "id": "fallback-msg", "content": "fallback"}
        ],
    )

    assert message_id == "assistant-msg-2"


@pytest.mark.anyio
async def test_extract_feedback_message_id_returns_none_without_assistant():
    message_id = await worker_module._extract_feedback_message_id(
        checkpointer=None,
        thread_id="thread-feedback",
        fallback_messages=[{"role": "user", "id": "user-msg-1", "content": "hello"}],
    )

    assert message_id is None


@pytest.mark.anyio
async def test_successful_run_stays_success_when_usage_settlement_fails(monkeypatch):
    manager = RunManager()
    record = await manager.create("thread-settlement", "agent")
    bridge = _FakeBridge()

    app_module = types.ModuleType("app")
    gateway_module = types.ModuleType("app.gateway")
    usage_reporter_module = types.ModuleType("app.gateway.usage_reporter")

    class _UsageReporter:
        @staticmethod
        def get_instance():
            return _FakeUsageReporter()

    usage_reporter_module.UsageReporter = _UsageReporter
    gateway_module.usage_reporter = usage_reporter_module
    app_module.gateway = gateway_module
    monkeypatch.setitem(sys.modules, "app", app_module)
    monkeypatch.setitem(sys.modules, "app.gateway", gateway_module)
    monkeypatch.setitem(
        sys.modules, "app.gateway.usage_reporter", usage_reporter_module
    )

    async def _fail_settlement(**kwargs):
        raise TimeoutError("Usage settlement failed after retries")

    monkeypatch.setattr(
        "deerflow.runtime.runs.worker._report_lumax_settlement",
        _fail_settlement,
    )

    await run_agent(
        bridge,
        manager,
        record,
        ctx=RunContext(checkpointer=None),
        agent_factory=lambda **kwargs: _FakeAgent(),
        graph_input={"messages": [{"role": "user", "content": "测试"}]},
        config={"configurable": {"tenant_id": "2052263773707833345", "user_id": 2}},
    )

    await asyncio.sleep(0)

    assert record.status is RunStatus.success
    assert record.error is None
    assert all(event != "error" for _, event, _ in bridge.events)
    assert bridge.ended == [record.run_id]


@pytest.mark.anyio
async def test_run_agent_metering_context_uses_nickname_and_dept_id(monkeypatch):
    manager = RunManager()
    record = await manager.create("thread-settlement", "agent")
    bridge = _FakeBridge()
    captured: dict = {}

    class _UsageReporter:
        @staticmethod
        def get_instance():
            return _FakeUsageReporter()

    async def _capture_settlement(**kwargs):
        captured["metering_context"] = kwargs["metering_context"]

    monkeypatch.setattr(
        "deerflow.runtime.runs.worker._report_lumax_settlement",
        _capture_settlement,
    )
    monkeypatch.setattr(
        "deerflow.runtime.runs.worker._get_usage_reporter_class",
        lambda: _UsageReporter,
    )

    await run_agent(
        bridge,
        manager,
        record,
        ctx=RunContext(checkpointer=None),
        agent_factory=lambda **kwargs: _FakeAgent(),
        graph_input={"messages": [{"role": "user", "content": "hello"}]},
        config={
            "configurable": {
                "tenant_id": "1",
                "user_id": "2",
                "user_context": {
                    "username": "alice",
                    "nickname": "Alice Nick",
                    "dept_id": "dept-1",
                },
            }
        },
    )

    metering_context = captured["metering_context"]
    assert metering_context.username == "Alice Nick"
    assert metering_context.dept_id == "dept-1"


@pytest.mark.anyio
async def test_successful_run_creates_neutral_feedback(monkeypatch):
    manager = RunManager()
    record = await manager.create("thread-feedback", "custom-assistant")
    bridge = _FakeBridge()
    feedback_repo = _FakeFeedbackRepo()

    class _UsageReporter:
        @staticmethod
        def get_instance():
            return _FakeUsageReporter()

    async def _noop_settlement(**kwargs):
        return None

    monkeypatch.setattr(
        "deerflow.runtime.runs.worker._report_lumax_settlement",
        _noop_settlement,
    )

    monkeypatch.setattr(
        "deerflow.runtime.runs.worker._get_usage_reporter_class",
        lambda: _UsageReporter,
    )

    await run_agent(
        bridge,
        manager,
        record,
        ctx=RunContext(checkpointer=None, feedback_repo=feedback_repo),
        agent_factory=lambda **kwargs: _FakeAgentWithAssistantMessage(),
        graph_input={"messages": [{"role": "user", "content": "hello"}]},
        config={
            "context": {"agent_name": "custom-agent"},
            "configurable": {"tenant_id": "1", "user_id": 2},
        },
    )

    assert record.status is RunStatus.success
    assert feedback_repo.neutral_calls == [
        {
            "run_id": record.run_id,
            "thread_id": "thread-feedback",
            "user_id": "2",
            "message_id": "assistant-msg-1",
            "agent_id": "custom-assistant",
            "agent_name": "custom-agent",
        }
    ]
