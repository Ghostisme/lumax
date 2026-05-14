from __future__ import annotations

import subprocess
import sys
from shutil import which
from pathlib import Path


FRONTEND_PREFIX = "frontend/"


def _frontend_path(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if not normalized.startswith(FRONTEND_PREFIX):
        return None
    relative = normalized[len(FRONTEND_PREFIX) :]
    if not relative:
        return None
    if not (Path("frontend") / relative).exists():
        return None
    return relative


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: precommit_frontend.py <eslint|prettier> [files...]", file=sys.stderr)
        return 2

    tool = sys.argv[1]
    files = [_frontend_path(path) for path in sys.argv[2:]]
    frontend_files = [path for path in files if path is not None]
    if not frontend_files:
        return 0

    pnpm = which("pnpm") or which("pnpm.cmd")
    if pnpm is None:
        print("pnpm not found in PATH", file=sys.stderr)
        return 1

    if tool == "eslint":
        command = [pnpm, "--dir", "frontend", "exec", "eslint", "--fix", *frontend_files]
    elif tool == "prettier":
        command = [pnpm, "--dir", "frontend", "exec", "prettier", "--write", *frontend_files]
    else:
        print(f"unsupported frontend pre-commit tool: {tool}", file=sys.stderr)
        return 2

    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
