from __future__ import annotations

from types import SimpleNamespace

LONG_TENANT_ID = "2052263773707833345"


def test_merge_gateway_context_preserves_long_numeric_tenant_id() -> None:
    from app.gateway.services import merge_gateway_context

    request = SimpleNamespace(
        state=SimpleNamespace(
            user=SimpleNamespace(
                tenant_id=LONG_TENANT_ID,
                user_id="2",
                username="alice",
                nickname="Alice Nick",
                dept_id="dept-1",
                business_code="talent",
            )
        )
    )
    config: dict = {}

    merge_gateway_context(config, request, context=None)

    assert config["configurable"]["tenant_id"] == LONG_TENANT_ID
    assert config["configurable"]["user_id"] == "2"
    assert config["configurable"]["user_context"]["tenant_id"] == LONG_TENANT_ID
    assert config["configurable"]["user_context"]["user_id"] == "2"
    assert config["configurable"]["user_context"]["username"] == "alice"
    assert config["configurable"]["user_context"]["nickname"] == "Alice Nick"
    assert config["configurable"]["user_context"]["dept_id"] == "dept-1"


def test_merge_gateway_context_rejects_non_digit_tenant_id() -> None:
    from app.gateway.services import merge_gateway_context

    request = SimpleNamespace(state=SimpleNamespace(user=None))
    config: dict = {}

    merge_gateway_context(
        config,
        request,
        context={"user_context": {"tenant_id": "tenant-a", "user_id": 2}},
    )

    assert "tenant_id" not in config["configurable"]


def test_ensure_langfuse_session_id_defaults_to_thread_id() -> None:
    from app.gateway.services import ensure_langfuse_session_id

    config: dict = {}

    result = ensure_langfuse_session_id(config, thread_id="thread-123")

    assert result["metadata"]["langfuse_session_id"] == "thread-123"


def test_ensure_langfuse_session_id_preserves_explicit_value() -> None:
    from app.gateway.services import ensure_langfuse_session_id

    config = {"metadata": {"langfuse_session_id": "session-explicit"}}

    result = ensure_langfuse_session_id(config, thread_id="thread-123")

    assert result["metadata"]["langfuse_session_id"] == "session-explicit"
