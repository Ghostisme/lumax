from __future__ import annotations

import json
import re
from typing import Any

from . import mcp_client

MAX_RETRIES = 3
API_DATA_MARKER_KEYS = {"projectId", "projectList", "promotionId", "promotionList"}

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

UNIT_DETAIL_SPEC = {
    "title": "获取单元详情",
    "path": "/open_api/v3.0/local/promotion/detail/",
    "operation_type": "read",
    "mcp_tool_name": "localUnitDetail",
}

UNIT_LIST_SPEC = {
    "title": "获取单元列表",
    "path": "/open_api/v3.0/local/promotion/list/",
    "operation_type": "read",
    "mcp_tool_name": "localUnitList",
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


def _same_calendar_day(expected: Any, actual: Any) -> bool:
    if not isinstance(expected, str) or not isinstance(actual, str):
        return False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expected):
        return False
    return actual == expected or actual.startswith(f"{expected} ")


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
        if isinstance(data, dict) and any(key in data for key in API_DATA_MARKER_KEYS):
            return data
        if any(key in candidate for key in API_DATA_MARKER_KEYS):
            return candidate
    return None


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


def _api_failure_message(result: dict[str, Any]) -> str | None:
    if result.get("success") is False:
        message = result.get("message") or "未提供错误说明"
        return f"接口返回失败：{message}"

    raw = result.get("raw", result)
    candidates = [raw]
    for value in _iter_values(raw):
        if isinstance(value, str):
            parsed = _json_from_text(value)
            if parsed is not None:
                candidates.append(parsed)
    for candidate in candidates:
        nonzero = _find_nonzero_code(candidate)
        if nonzero is not None:
            code, message = nonzero
            return f"接口返回 code={code}：{message or '未提供错误说明'}"
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


def _extract_promotion_id(result: dict[str, Any]) -> int | None:
    found = _find_key(result, {"promotion_id", "promotionId"})
    if isinstance(found, int):
        return found
    if isinstance(found, str) and found.isdigit():
        return int(found)
    for value in _iter_values(result):
        if isinstance(value, str):
            parsed = _json_from_text(value)
            if parsed is not None:
                found = _find_key(parsed, {"promotion_id", "promotionId"})
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


def _promotion_ids_from_payload(payload: dict[str, Any], confirmation: dict[str, Any]) -> list[int]:
    if "promotion_id" in payload:
        return [int(payload["promotion_id"])]
    batch_field = confirmation.get("batch_field", "data")
    ids = []
    for item in payload.get(batch_field, []):
        if "promotion_id" in item:
            ids.append(int(item["promotion_id"]))
    return ids


def _confirm_project_details(local_account_id: int, project_ids: list[int]) -> dict[str, Any]:
    details = []
    for project_id in project_ids:
        details.append(mcp_client.invoke_endpoint(PROJECT_DETAIL_SPEC, {"local_account_id": local_account_id, "project_id": project_id}))
    return {"confirmed": True, "mode": "project_detail", "details": details}


def _confirm_unit_details(local_account_id: int, promotion_ids: list[int]) -> dict[str, Any]:
    details = []
    mismatches = []
    for promotion_id in promotion_ids:
        detail = mcp_client.invoke_endpoint(UNIT_DETAIL_SPEC, {"local_account_id": local_account_id, "promotion_id": promotion_id})
        details.append(detail)
        failure_message = _api_failure_message(detail)
        if failure_message:
            mismatches.append(f"promotion_id={promotion_id}: {failure_message}")
            continue

        detail_data = _extract_api_data(detail)
        if not isinstance(detail_data, dict):
            mismatches.append(f"promotion_id={promotion_id}: 未解析到单元详情")
            continue
        confirmed_promotion_id = _extract_promotion_id(detail_data)
        if confirmed_promotion_id != promotion_id:
            mismatches.append(f"promotion_id={promotion_id}: 未确认到目标单元")
    return {"confirmed": not mismatches, "mode": "unit_detail", "details": details, "mismatches": mismatches}


def _compare_payload_fields(payload: dict[str, Any], detail_data: dict[str, Any], *, fields: set[str] | None = None) -> list[str]:
    ignored = {"local_account_id", "project_id", "promotion_id", "items", "data"}
    mismatches = []
    for field, expected in payload.items():
        if field in ignored or (fields is not None and field not in fields):
            continue
        detail_key = _snake_to_camel(field)
        actual = detail_data.get(detail_key)
        if _same_calendar_day(expected, actual):
            continue
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


def _confirm_deferred_project_details(local_account_id: int, project_ids: list[int]) -> dict[str, Any]:
    details = []
    mismatches = []
    for project_id in project_ids:
        detail = mcp_client.invoke_endpoint(PROJECT_DETAIL_SPEC, {"local_account_id": local_account_id, "project_id": project_id})
        details.append(detail)
        failure_message = _api_failure_message(detail)
        if failure_message:
            mismatches.append(f"project_id={project_id}: {failure_message}")
            continue

        detail_data = _extract_api_data(detail)
        if not isinstance(detail_data, dict):
            mismatches.append(f"project_id={project_id}: 未解析到项目详情")
            continue
        confirmed_project_id = _extract_project_id(detail_data)
        if confirmed_project_id != project_id:
            mismatches.append(f"project_id={project_id}: 未确认到目标项目")
    return {
        "confirmed": not mismatches,
        "mode": "project_detail_deferred",
        "details": details,
        "mismatches": mismatches,
        "deferred_effect": True,
        "deferred_fields": ["schedule_time"],
    }


def _confirm_unit_detail_payload(local_account_id: int, promotion_ids: list[int], payload: dict[str, Any], *, fields: set[str] | None = None) -> dict[str, Any]:
    details = []
    mismatches = []
    for promotion_id in promotion_ids:
        detail = mcp_client.invoke_endpoint(UNIT_DETAIL_SPEC, {"local_account_id": local_account_id, "promotion_id": promotion_id})
        details.append(detail)
        detail_data = _extract_api_data(detail)
        if not isinstance(detail_data, dict):
            mismatches.append(f"promotion_id={promotion_id}: 未解析到单元详情")
            continue
        mismatches.extend(_compare_payload_fields(payload, detail_data, fields=fields))
    return {"confirmed": not mismatches, "mode": "unit_detail", "details": details, "mismatches": mismatches}


def _project_list_items(list_result: dict[str, Any]) -> list[dict[str, Any]]:
    data = _extract_api_data(list_result)
    if isinstance(data, dict) and isinstance(data.get("projectList"), list):
        return data["projectList"]
    return []


def _unit_list_items(list_result: dict[str, Any]) -> list[dict[str, Any]]:
    data = _extract_api_data(list_result)
    if isinstance(data, dict) and isinstance(data.get("promotionList"), list):
        return data["promotionList"]
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


def _confirm_batch_unit_status(local_account_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    list_result = mcp_client.invoke_endpoint(UNIT_LIST_SPEC, {"local_account_id": local_account_id})
    units = _unit_list_items(list_result)
    by_id = {int(item["promotionId"]): item for item in units if "promotionId" in item}
    mismatches = []
    for item in items:
        promotion_id = int(item["promotion_id"])
        expected = "DISABLE" if item.get("opt_status") == "PAUSED" else item.get("opt_status")
        unit = by_id.get(promotion_id)
        actual = unit.get("promotionStatusFirst") if unit else None
        if actual != expected:
            mismatches.append(f"promotion_id={promotion_id}: 期望状态 {expected}，实际 {actual}")
    return {"confirmed": not mismatches, "mode": "unit_list_status", "details": [list_result], "mismatches": mismatches}


def _configured_confirmation_fields(confirmation: dict[str, Any]) -> set[str] | None:
    fields = confirmation.get("fields")
    if not isinstance(fields, list):
        return None
    return {field for field in fields if isinstance(field, str)}


def _is_next_day_week_schedule(items: list[dict[str, Any]]) -> bool:
    return bool(items) and all(item.get("schedule_scene") == "NEXT_DAY" and "schedule_time" in item for item in items)


def _confirm_created_project(payload: dict[str, Any], mutation_result: dict[str, Any], confirmation: dict[str, Any]) -> dict[str, Any]:
    local_account_id = int(payload["local_account_id"])
    project_id = _extract_project_id(mutation_result)
    if project_id is not None:
        return _confirm_project_detail_payload(
            local_account_id,
            [project_id],
            payload,
            fields=_configured_confirmation_fields(confirmation),
        )
    list_result = mcp_client.invoke_endpoint(PROJECT_LIST_SPEC, {"local_account_id": local_account_id})
    expected_name = payload.get("name")
    confirmed = expected_name is not None and expected_name in json.dumps(list_result, ensure_ascii=False)
    return {"confirmed": confirmed, "mode": "project_list_by_name", "expected_name": expected_name, "details": [list_result]}


def _confirm_created_unit(payload: dict[str, Any], mutation_result: dict[str, Any]) -> dict[str, Any]:
    local_account_id = int(payload["local_account_id"])
    promotion_id = _extract_promotion_id(mutation_result)
    if promotion_id is not None:
        return _confirm_unit_details(local_account_id, [promotion_id])
    list_result = mcp_client.invoke_endpoint(UNIT_LIST_SPEC, {"local_account_id": local_account_id})
    expected_name = payload.get("name")
    confirmed = expected_name is not None and expected_name in json.dumps(list_result, ensure_ascii=False)
    return {"confirmed": confirmed, "mode": "unit_list_by_name", "expected_name": expected_name, "details": [list_result]}


def confirm_mutation(spec: dict[str, Any], payload: dict[str, Any], mutation_result: dict[str, Any]) -> dict[str, Any]:
    confirmation = spec.get("confirmation", {})
    mode = confirmation.get("mode")
    last_error: str | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if mode == "created_project":
                result = _confirm_created_project(payload, mutation_result, confirmation)
            elif mode == "created_unit":
                result = _confirm_created_unit(payload, mutation_result)
            elif mode == "project_detail":
                project_ids = _project_ids_from_payload(payload, confirmation)
                result = _confirm_project_detail_payload(
                    int(payload["local_account_id"]),
                    project_ids,
                    payload,
                    fields=_configured_confirmation_fields(confirmation),
                )
            elif mode == "unit_detail":
                promotion_ids = _promotion_ids_from_payload(payload, confirmation)
                result = _confirm_unit_detail_payload(int(payload["local_account_id"]), promotion_ids, payload)
            elif mode == "batch_project_detail":
                batch_field = confirmation.get("batch_field", "items")
                items = payload.get(batch_field, [])
                if all("opt_status" in item for item in items):
                    result = _confirm_batch_status(int(payload["local_account_id"]), items)
                elif _is_next_day_week_schedule(items):
                    result = _confirm_deferred_project_details(
                        int(payload["local_account_id"]),
                        _project_ids_from_payload(payload, confirmation),
                    )
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
            elif mode == "batch_unit_status":
                batch_field = confirmation.get("batch_field", "data")
                items = payload.get(batch_field, [])
                if all("opt_status" in item for item in items):
                    result = _confirm_batch_unit_status(int(payload["local_account_id"]), items)
                else:
                    promotion_ids = _promotion_ids_from_payload(payload, confirmation)
                    result = _confirm_unit_details(int(payload["local_account_id"]), promotion_ids)
            else:
                return {"confirmed": True, "retry_count": attempt - 1, "mode": "not_required", "details": []}
            if result.get("confirmed"):
                result["retry_count"] = attempt - 1
                return result
            last_error = "；".join(result.get("mismatches") or []) or "后置查询结果与预期不一致"
        except Exception as exc:  # pragma: no cover
            last_error = str(exc)
    return {
        "confirmed": False,
        "retry_count": MAX_RETRIES,
        "mode": mode,
        "message": f"{spec['title']} 已执行，但后置查询确认在 {MAX_RETRIES} 次内未通过。",
        "last_error": last_error,
    }
