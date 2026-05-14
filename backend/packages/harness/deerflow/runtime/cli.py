"""Runtime command wrappers used by local development scripts."""

from __future__ import annotations

import sys

from deerflow.runtime.asyncio_compat import (
    ensure_windows_selector_event_loop_policy,
    patch_uvicorn_windows_loop_factory,
)


def _run_langgraph(args: list[str]) -> None:
    ensure_windows_selector_event_loop_policy()
    patch_uvicorn_windows_loop_factory()
    from langgraph_cli.cli import cli

    sys.argv = ["langgraph", *args]
    cli()


def _run_uvicorn(args: list[str]) -> None:
    ensure_windows_selector_event_loop_policy()
    patch_uvicorn_windows_loop_factory()
    from uvicorn.main import main

    sys.argv = ["uvicorn", *args]
    main()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m deerflow.runtime.cli <langgraph|uvicorn> [args...]")

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "langgraph":
        _run_langgraph(args)
        return

    if command == "uvicorn":
        _run_uvicorn(args)
        return

    raise SystemExit(f"Unknown runtime command: {command}")


if __name__ == "__main__":
    main()
