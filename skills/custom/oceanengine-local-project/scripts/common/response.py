from __future__ import annotations

import json
from typing import Any


def success(message: str, *, data: dict[str, Any] | None = None, tool_name: str | None = None, request_id: str | None = None, retry_count: int = 0) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data or {},
        "errors": [],
        "tool_name": tool_name,
        "request_id": request_id,
        "retry_count": retry_count,
    }


def failure(message: str, *, errors: list[dict[str, Any]] | None = None, data: dict[str, Any] | None = None, tool_name: str | None = None, request_id: str | None = None, retry_count: int = 0) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "tool_name": tool_name,
        "request_id": request_id,
        "retry_count": retry_count,
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
