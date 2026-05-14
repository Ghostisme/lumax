from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from common import mcp_client
from common.mutation_confirm import confirm_mutation
from common.response import failure, print_json, success
from common.validators import validate_payload


def _normalize_amount_fields(spec: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = dict(payload)
    normalizations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for rule in spec.get("amount_normalization", []):
        source_field = rule.get("source_field")
        target_field = rule.get("target_field")
        if not source_field or not target_field or source_field not in normalized:
            continue

        source_value = normalized.pop(source_field)
        if target_field in normalized:
            continue
        if not isinstance(source_value, int | float) or isinstance(source_value, bool):
            errors.append({"field": source_field, "message": f"{source_field} 必须是数字，才能按{rule.get('source_unit', '源单位')}转换。"})
            continue

        multiplier = rule.get("multiplier", 1)
        normalized_value = source_value * multiplier
        if isinstance(source_value, int) and isinstance(multiplier, int):
            normalized_value = int(normalized_value)
        normalized[target_field] = normalized_value
        normalizations.append(
            {
                "field": target_field,
                "source_field": source_field,
                "source_unit": rule.get("source_unit"),
                "api_unit": rule.get("api_unit"),
                "source_value": source_value,
                "normalized_value": normalized_value,
            }
        )

    return normalized, normalizations, errors


def _iter_text_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "message", "msg", "error"} and isinstance(item, str):
                yield item
            yield from _iter_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text_values(item)
    elif isinstance(value, str):
        yield value


def _find_nonzero_code(value: Any) -> tuple[Any, str | None] | None:
    if isinstance(value, dict):
        code = value.get("code")
        if code not in (None, 0, "0"):
            return code, value.get("message") or value.get("msg")
        for item in value.values():
            found = _find_nonzero_code(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_nonzero_code(item)
            if found is not None:
                return found
    return None


def _parse_embedded_json(text: str) -> Any | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _mcp_failure_message(raw: Any) -> str | None:
    nonzero = _find_nonzero_code(raw)
    if nonzero is not None:
        code, message = nonzero
        return f"接口返回 code={code}：{message or '未提供错误说明'}"

    markers = ("cannot deserialize", "exception", "bad request", "invalid request", "调用失败", "参数错误")
    for text in _iter_text_values(raw):
        parsed = _parse_embedded_json(text)
        if parsed is not None:
            nonzero = _find_nonzero_code(parsed)
            if nonzero is not None:
                code, message = nonzero
                return f"接口返回 code={code}：{message or '未提供错误说明'}"
        lower = text.lower()
        if re.search(r'\brequest\b"?\s+(?:is|was)\s+null\b', lower) or re.search(r'\brequest\b"?\s*[:=]\s*null\b', lower):
            return f"MCP 请求包装错误：{text[:500]}"
        if "cannot invoke" in lower:
            return f"MCP 请求包装错误：{text[:500]}"
        if any(marker in lower for marker in markers):
            return text[:500]
    return None


def run_endpoint(spec: dict[str, Any], payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    payload, normalizations, normalization_errors = _normalize_amount_fields(spec, payload)
    errors = normalization_errors or validate_payload(payload, spec)
    if errors:
        return failure(
            "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。",
            errors=errors,
            data={"path": spec["path"], "title": spec["title"], "normalizations": normalizations},
        )

    if dry_run:
        return success(
            "参数校验通过（dry-run），未调用 MCP。",
            data={
                "dry-run": True,
                "title": spec["title"],
                "path": spec["path"],
                "operation_type": spec.get("operation_type", "read"),
                "payload": payload,
                "normalizations": normalizations,
                "script_entry": spec.get("script") or spec.get("name"),
                "mcp_server_name": spec.get("mcp_server_name") or spec.get("mcp", {}).get("server"),
                "mcp_tool_name": spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"),
            },
        )

    try:
        result = mcp_client.invoke_endpoint(spec, payload)
    except Exception as exc:
        return failure(
            "MCP 工具调用失败，请根据错误信息检查配置或输入。",
            errors=[{"field": "mcp", "message": str(exc)}],
            data={"path": spec["path"], "title": spec["title"], "normalizations": normalizations},
        )

    mcp_error = _mcp_failure_message(result.get("raw"))
    if mcp_error:
        return failure(
            "MCP 工具返回失败，操作没有通过接口校验或执行。",
            errors=[{"field": "mcp", "message": mcp_error}],
            data={"result": result.get("raw"), "path": spec["path"], "title": spec["title"], "normalizations": normalizations},
            tool_name=result.get("tool_name"),
            request_id=result.get("request_id"),
        )

    confirmation = None
    if spec.get("operation_type") in {"mutation", "batch"}:
        confirmation = confirm_mutation(spec, payload, result)
        if not confirmation.get("confirmed"):
            return failure(
                confirmation.get("message", "操作已执行，但后置查询确认失败。"),
                errors=[{"field": "confirmation", "message": confirmation.get("last_error") or "后置查询未确认到目标数据。"}],
                data={"result": result.get("raw"), "confirmation": confirmation, "path": spec["path"], "title": spec["title"], "normalizations": normalizations},
                tool_name=result.get("tool_name"),
                request_id=result.get("request_id"),
                retry_count=confirmation.get("retry_count", 0),
            )

    return success(
        f"{spec['title']} 调用完成。",
        data={"result": result.get("raw"), "confirmation": confirmation, "path": spec["path"], "title": spec["title"], "normalizations": normalizations},
        tool_name=result.get("tool_name"),
        request_id=result.get("request_id"),
        retry_count=(confirmation or {}).get("retry_count", 0),
    )


def _load_input(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        return json.loads(args.input)
    if args.input_file:
        with open(args.input_file, encoding="utf-8") as handle:
            return json.load(handle)
    raw = sys.stdin.read().strip()
    if raw:
        return json.loads(raw)
    return {}


def main(spec: dict[str, Any]) -> None:
    parser = argparse.ArgumentParser(description=spec["title"])
    parser.add_argument("--input", help="JSON string input.")
    parser.add_argument("--input-file", help="Path to a JSON input file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and build request without calling MCP.")
    args = parser.parse_args()
    payload = _load_input(args)
    print_json(run_endpoint(spec, payload, dry_run=args.dry_run))
