"""Tenant identifier helpers shared by runtime and gateway flows."""

from __future__ import annotations

import re
from typing import Any

DEFAULT_TENANT_ID = "1"
GLOBAL_TENANT_ID = "0"

_DIGITS_RE = re.compile(r"^\d+$")


def normalize_tenant_id(value: Any) -> str | None:
    """Return a non-zero digit string tenant id, preserving long values exactly."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or not _DIGITS_RE.fullmatch(text):
        return None
    if all(ch == "0" for ch in text):
        return None
    return text
