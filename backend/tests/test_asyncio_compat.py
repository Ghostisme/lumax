import asyncio

from deerflow.runtime.asyncio_compat import (
    ensure_windows_selector_event_loop_policy,
    patch_uvicorn_windows_loop_factory,
)


def test_non_windows_does_not_change_event_loop_policy(monkeypatch):
    calls = []

    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(asyncio, "set_event_loop_policy", calls.append)

    ensure_windows_selector_event_loop_policy()

    assert calls == []


def test_windows_sets_selector_event_loop_policy_when_needed(monkeypatch):
    class FakeSelectorPolicy:
        pass

    calls = []

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(asyncio, "WindowsSelectorEventLoopPolicy", FakeSelectorPolicy, raising=False)
    monkeypatch.setattr(asyncio, "get_event_loop_policy", object)
    monkeypatch.setattr(asyncio, "set_event_loop_policy", calls.append)

    ensure_windows_selector_event_loop_policy()

    assert len(calls) == 1
    assert isinstance(calls[0], FakeSelectorPolicy)


def test_windows_keeps_existing_selector_event_loop_policy(monkeypatch):
    class FakeSelectorPolicy:
        pass

    calls = []

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(asyncio, "WindowsSelectorEventLoopPolicy", FakeSelectorPolicy, raising=False)
    monkeypatch.setattr(asyncio, "get_event_loop_policy", FakeSelectorPolicy)
    monkeypatch.setattr(asyncio, "set_event_loop_policy", calls.append)

    ensure_windows_selector_event_loop_policy()

    assert calls == []


def test_windows_patches_uvicorn_loop_factory(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")

    patch_uvicorn_windows_loop_factory()

    import uvicorn.loops.asyncio
    import uvicorn.loops.auto

    assert uvicorn.loops.asyncio.asyncio_loop_factory() is asyncio.SelectorEventLoop
    assert uvicorn.loops.auto.auto_loop_factory() is asyncio.SelectorEventLoop
