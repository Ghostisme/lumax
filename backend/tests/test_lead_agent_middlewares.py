"""Tests for lead agent middleware assembly."""

import pytest

from deerflow.agents.lead_agent import agent as lead_agent_module
from deerflow.agents.middlewares.oceanengine_response_sanitizer_middleware import (
    OceanEngineResponseSanitizerMiddleware,
)
from deerflow.config.app_config import AppConfig
from deerflow.config.sandbox_config import SandboxConfig


def test_lead_agent_includes_oceanengine_response_sanitizer_before_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_config = AppConfig(sandbox=SandboxConfig(use="test"))
    monkeypatch.setattr(lead_agent_module, "_create_summarization_middleware", lambda *args, **kwargs: None)

    middlewares = lead_agent_module._build_middlewares(
        {"configurable": {}},
        model_name=None,
        app_config=app_config,
    )

    mw_types = [type(middleware).__name__ for middleware in middlewares]
    sanitizer_index = next(
        index for index, middleware in enumerate(middlewares) if isinstance(middleware, OceanEngineResponseSanitizerMiddleware)
    )
    clarification_index = mw_types.index("ClarificationMiddleware")

    assert sanitizer_index < clarification_index
