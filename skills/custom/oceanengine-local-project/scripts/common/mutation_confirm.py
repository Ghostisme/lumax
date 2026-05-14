from __future__ import annotations

import json
from typing import Any

from common import mcp_client


MAX_RETRIES = 3


PROJECT_DETAIL_SPEC = {
    "title": "获取项目详情",
    "path": "/open_api/v3.0/local/project/detail/",
    "operation_type": "read",
    "mcp_tool_name": "localProjectDetail",
}

PROJECT_LIST_SPEC = {
    "title": "获取项目列表",
    "path": "/open_api/v3.0/local/project/list/",
    "operation_type": "read",
    "mcp_tool_name": "localProjectList",
}


def _iter_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)
    else:
        yield value


def _json_from_text(text: str) -> Any | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _extract_api_data(result: dict[str, Any]) -> Any | None:
    raw = result.get("raw", result)
    parsed = _json_from_text(json.dumps(raw, ensure_ascii=False))
    candidates = [raw, parsed]
    for value in _iter_values(raw):
        if isinstance(value, str):
            candidates.append(_json_from_text(value))
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        data = candidate.get("data")
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if "projectId" in candidate or "projectList" in candidate:
            return candidate
    return None


def _find_key(value: Any, keys: set[str]) -> Any | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                return item
            found = _find_key(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_key(item, keys)
            if found is not None:
                return found
    return None


def _extract_project_id(result: dict[str, Any]) -> int | None:
    found = _find_key(result, {"project_id", "projectId"})
    if isinstance(found, int):
        return found
    if isinstance(found, str) and found.isdigit():
        return int(found)
    for value in _iter_values(result):
        if isinstance(value, str):
            parsed = _json_from_text(value)
            if parsed is not None:
                found = _find_key(parsed, {"project_id", "projectId"})
                if isinstance(found, int):
                    return found
                if isinstance(found, str) and found.isdigit():
                    return int(found)
    return None


def _project_ids_from_payload(payload: dict[str, Any], confirmation: dict[str, Any]) -> list[int]:
    if "project_id" in payload:
        return [int(payload["project_id"])]
    batch_field = confirmation.get("batch_field", "items")
    ids = []
    for item in payload.get(batch_field, []):
        if "project_id" in item:
            ids.append(int(item["project_id"]))
    return ids


def _confirm_project_details(local_account_id: int, project_ids: list[int]) -> dict[str, Any]:
    details = []
    for project_id in project_ids:
        details.append(mcp_client.invoke_endpoint(PROJECT_DETAIL_SPEC, {"local_account_id": local_account_id, "project_id": project_id}))
    return {"confirmed": True, "mode": "project_detail", "details": details}


def _compare_payload_fields(payload: dict[str, Any], detail_data: dict[str, Any], *, fields: set[str] | None = None) -> list[str]:
    ignored = {"local_account_id", "project_id", "items"}
    mismatches = []
    for field, expected in payload.items():
        if field in ignored or (fields is not None and field not in fields):
            continue
        detail_key = _snake_to_camel(field)
        actual = detail_data.get(detail_key)
        if str(actual) != str(expected):
            mismatches.append(f"{field}: 期望 {expected}，实际 {actual}")
    return mismatches


def _confirm_project_detail_payload(local_account_id: int, project_ids: list[int], payload: dict[str, Any], *, fields: set[str] | None = None) -> dict[str, Any]:
    details = []
    mismatches = []
    for project_id in project_ids:
        detail = mcp_client.invoke_endpoint(PROJECT_DETAIL_SPEC, {"local_account_id": local_account_id, "project_id": project_id})
        details.append(detail)
        detail_data = _extract_api_data(detail)
        if not isinstance(detail_data, dict):
            mismatches.append(f"project_id={project_id}: 未解析到项目详情")
            continue
        mismatches.extend(_compare_payload_fields(payload, detail_data, fields=fields))
    return {"confirmed": not mismatches, "mode": "project_detail", "details": details, "mismatches": mismatches}


def _project_list_items(list_result: dict[str, Any]) -> list[dict[str, Any]]:
    data = _extract_api_data(list_result)
    if isinstance(data, dict) and isinstance(data.get("projectList"), list):
        return data["projectList"]
    return []


def _confirm_batch_status(local_account_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    list_result = mcp_client.invoke_endpoint(PROJECT_LIST_SPEC, {"local_account_id": local_account_id})
    projects = _project_list_items(list_result)
    by_id = {int(item["projectId"]): item for item in projects if "projectId" in item}
    mismatches = []
    for item in items:
        project_id = int(item["project_id"])
        expected = "DISABLE" if item.get("opt_status") == "PAUSED" else item.get("opt_status")
        project = by_id.get(project_id)
        if expected == "DELETE":
            if project is not None:
                mismatches.append(f"project_id={project_id}: 期望已删除，列表中仍可见")
            continue
        actual = project.get("projectStatusFirst") if project else None
        if actual != expected:
            mismatches.append(f"project_id={project_id}: 期望状态 {expected}，实际 {actual}")
    return {"confirmed": not mismatches, "mode": "project_list_status", "details": [list_result], "mismatches": mismatches}


def _confirm_created_project(payload: dict[str, Any], mutation_result: dict[str, Any]) -> dict[str, Any]:
    local_account_id = int(payload["local_account_id"])
    project_id = _extract_project_id(mutation_result)
    if project_id is not None:
        return _confirm_project_detail_payload(local_account_id, [project_id], payload)
    list_result = mcp_client.invoke_endpoint(PROJECT_LIST_SPEC, {"local_account_id": local_account_id})
    expected_name = payload.get("name")
    confirmed = expected_name is not None and expected_name in json.dumps(list_result, ensure_ascii=False)
    return {"confirmed": confirmed, "mode": "project_list_by_name", "expected_name": expected_name, "details": [list_result]}


def confirm_mutation(spec: dict[str, Any], payload: dict[str, Any], mutation_result: dict[str, Any]) -> dict[str, Any]:
    confirmation = spec.get("confirmation", {})
    mode = confirmation.get("mode")
    last_error: str | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if mode == "created_project":
                result = _confirm_created_project(payload, mutation_result)
            elif mode == "project_detail":
                project_ids = _project_ids_from_payload(payload, confirmation)
                result = _confirm_project_detail_payload(int(payload["local_account_id"]), project_ids, payload)
            elif mode == "batch_project_detail":
                batch_field = confirmation.get("batch_field", "items")
                items = payload.get(batch_field, [])
                if all("opt_status" in item for item in items):
                    result = _confirm_batch_status(int(payload["local_account_id"]), items)
                elif all("schedule_time" in item for item in items):
                    result = _confirm_project_detail_payload(
                        int(payload["local_account_id"]),
                        _project_ids_from_payload(payload, confirmation),
                        {"schedule_time": items[0]["schedule_time"]} if len(items) == 1 else {},
                        fields={"schedule_time"},
                    )
                else:
                    project_ids = _project_ids_from_payload(payload, confirmation)
                    result = _confirm_project_details(int(payload["local_account_id"]), project_ids)
            else:
                return {"confirmed": True, "retry_count": attempt - 1, "mode": "not_required", "details": []}
            if result.get("confirmed"):
                result["retry_count"] = attempt - 1
                return result
            last_error = "；".join(result.get("mismatches") or []) or "后置查询结果与预期不一致"
        except Exception as exc:  # pragma: no cover - depends on live MCP account state
            last_error = str(exc)
    return {
        "confirmed": False,
        "retry_count": MAX_RETRIES,
        "mode": mode,
        "message": f"{spec['title']} 已执行，但后置查询确认在 {MAX_RETRIES} 次内未通过。",
        "last_error": last_error,
    }
