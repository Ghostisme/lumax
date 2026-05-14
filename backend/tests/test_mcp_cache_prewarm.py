import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

from langchain_core.tools import StructuredTool


def _reset_cache_module(cache_module):
    cache_module._mcp_tools_cache = None
    cache_module._cache_initialized = False
    cache_module._state_token = None
    cache_module._prewarm_active = False
    cache_module._prewarm_event.set()


def test_prime_mcp_tools_cache_starts_one_background_prewarm(monkeypatch):
    from deerflow.mcp import cache

    _reset_cache_module(cache)
    started_threads = []

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self):
            started_threads.append(self)

    monkeypatch.setattr(cache.threading, "Thread", FakeThread)

    first_event = cache.prime_mcp_tools_cache()
    second_event = cache.prime_mcp_tools_cache()

    assert first_event is second_event
    assert len(started_threads) == 1
    assert started_threads[0].name == "mcp-tools-prewarm"
    assert started_threads[0].daemon is True


def test_mcp_prewarm_failure_does_not_break_lazy_loading(monkeypatch):
    from deerflow.mcp import cache

    _reset_cache_module(cache)

    async def fail_initialize():
        raise RuntimeError("prewarm failed")

    monkeypatch.setattr(cache, "_get_enabled_mcp_server_count", lambda: 1)
    monkeypatch.setattr(cache, "initialize_mcp_tools", fail_initialize)

    prewarm_event = cache.prime_mcp_tools_cache()
    assert prewarm_event.wait(timeout=2)
    assert cache._cache_initialized is False

    tool = StructuredTool.from_function(lambda: "ok", name="prewarmed_tool", description="test tool")

    async def successful_initialize():
        cache._mcp_tools_cache = [tool]
        cache._cache_initialized = True
        cache._state_token = (1.0, 0)
        return [tool]

    monkeypatch.setattr(cache, "initialize_mcp_tools", successful_initialize)
    monkeypatch.setattr(cache, "_is_cache_stale", lambda: False)

    assert cache.get_cached_mcp_tools() == [tool]


def test_get_available_tools_uses_prewarmed_mcp_cache_without_reinitializing(monkeypatch):
    import deerflow.mcp.cache as cache
    import deerflow.tools.tools as tools_module

    _reset_cache_module(cache)
    tool = StructuredTool.from_function(lambda: "ok", name="prewarmed_tool", description="test tool")
    cache._mcp_tools_cache = [tool]
    cache._cache_initialized = True
    cache._state_token = (1.0, 0)

    async_mock = AsyncMock(side_effect=AssertionError("should not initialize MCP tools again"))
    monkeypatch.setattr(cache, "initialize_mcp_tools", async_mock)
    monkeypatch.setattr(cache, "_is_cache_stale", lambda: False)
    monkeypatch.setattr(tools_module, "get_app_config", lambda: SimpleNamespace(tools=[], models=[], tool_search=SimpleNamespace(enabled=False), get_model_config=lambda _name: None))
    monkeypatch.setattr(tools_module, "is_host_bash_allowed", lambda _config: True)
    monkeypatch.setattr("deerflow.mcp.runtime.get_merged_mcp_servers", lambda: {"server": SimpleNamespace(enabled=True)})

    tools = tools_module.get_available_tools(include_mcp=True, subagent_enabled=False)

    assert tool in tools
    async_mock.assert_not_called()


def test_agents_import_primes_mcp_tools_cache(monkeypatch):
    import deerflow.agents as agents_module
    import deerflow.agents.lead_agent.prompt as prompt_module
    import deerflow.mcp.cache as cache

    calls = []
    monkeypatch.setattr(prompt_module, "prime_enabled_skills_cache", lambda: None)
    monkeypatch.setattr(cache, "prime_mcp_tools_cache", lambda: calls.append("mcp"))

    importlib.reload(agents_module)

    assert calls == ["mcp"]
