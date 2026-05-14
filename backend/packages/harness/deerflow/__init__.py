"""DeerFlow harness package."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    if not (repo_root / "tools").is_dir():
        return

    value = str(repo_root)
    if value not in sys.path:
        sys.path.insert(0, value)


_ensure_repo_root_on_path()
