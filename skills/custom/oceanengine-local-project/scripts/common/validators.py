from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TYPE_LABELS = {
    "string": "字符串",
    "number": "数字",
    "integer": "整数",
    "array": "数组",
    "object": "对象",
    "boolean": "布尔值",
}

_MISSING = object()


def _field_label(field: str, spec: Mapping[str, Any]) -> str:
    labels = spec.get("field_labels", {})
    return labels.get(field, field)


def error(field: str, message: str, *, item_index: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"field": field, "message": message}
    if item_index is not None:
        payload["item_index"] = item_index
    return payload


def _is_missing(payload: Mapping[str, Any], field: str) -> bool:
    values = _resolve_path(payload, field)
    if not values:
        return True
    return any(value is _MISSING or value is None or value == "" for value in values)


def _resolve_path(payload: Any, field: str) -> list[Any]:
    values: list[Any] = [payload]
    for raw_part in field.split("."):
        next_values: list[Any] = []
        is_array_item = raw_part.endswith("[]")
        part = raw_part[:-2] if is_array_item else raw_part
        for value in values:
            if value is _MISSING:
                next_values.append(_MISSING)
                continue
            if not isinstance(value, Mapping) or part not in value:
                next_values.append(_MISSING)
                continue
            child = value[part]
            if is_array_item:
                if not isinstance(child, list) or not child:
                    next_values.append(_MISSING)
                else:
                    next_values.extend(child)
            else:
                next_values.append(child)
        values = next_values
    return values


def _first_value(payload: Mapping[str, Any], field: str) -> Any:
    values = _resolve_path(payload, field)
    if not values or values[0] is _MISSING:
        return None
    return values[0]


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def _conditions_match(payload: Mapping[str, Any], when: Mapping[str, Any]) -> bool:
    if "field" in when and any(key in when for key in ("equals", "not_equals", "in", "not_in", "exists")):
        field = when.get("field")
        if not isinstance(field, str):
            return False
        actual = _first_value(payload, field)
        exists = not _is_missing(payload, field)
        if "exists" in when:
            return exists is bool(when.get("exists"))
        if "equals" in when:
            return actual == when.get("equals")
        if "not_equals" in when:
            return actual != when.get("not_equals")
        if "in" in when:
            expected = when.get("in")
            return isinstance(expected, list) and actual in expected
        if "not_in" in when:
            expected = when.get("not_in")
            return isinstance(expected, list) and actual not in expected

    for field, expected in when.items():
        actual = _first_value(payload, field)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _constraint_rules(spec: Mapping[str, Any], rule_type: str, *, legacy_key: str | None = None) -> list[Mapping[str, Any]]:
    rules: list[Mapping[str, Any]] = []
    for rule in spec.get("constraints", []):
        if isinstance(rule, Mapping) and rule.get("type") == rule_type:
            rules.append(rule)
    if legacy_key:
        for rule in spec.get(legacy_key, []):
            if isinstance(rule, Mapping):
                rules.append(rule)
    return rules


def _field_labels(fields: list[str], spec: Mapping[str, Any]) -> str:
    return "、".join(_field_label(field, spec) for field in fields)


def _missing_value_message(field: str, spec: Mapping[str, Any], *, item_index: int | None = None, reason: str | None = None) -> str:
    label = _field_label(field, spec)
    subject = f"第 {item_index + 1} 项{label}" if item_index is not None else label
    rules = spec.get("fields", {}).get(field, {})
    options = ""

    if isinstance(rules, Mapping) and rules.get("enum"):
        allowed = rules.get("enum", [])
        meanings = rules.get("enum_labels", {})
        if not meanings or any(item not in meanings for item in allowed):
            return f"{subject} 是必填枚举字段，但规则配置缺少中文枚举标签，请先补全规则配置。"
        choices = "、".join(str(meanings[item]) for item in allowed)
        options = f"可选：{choices}。"
    elif isinstance(rules, Mapping) and rules.get("type") == "boolean":
        options = "可选：是、否。"

    suffix = f"原因：{reason}。" if reason else ""
    return f"{subject}是什么值？{options}{suffix}"


def _dedupe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int | None]] = set()
    deduped: list[dict[str, Any]] = []
    for item in errors:
        key = (str(item.get("field", "")), str(item.get("message", "")), item.get("item_index"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def validate_payload(payload: Mapping[str, Any], spec: Mapping[str, Any], *, item_index: int | None = None) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    for field in spec.get("required", []):
        if _is_missing(payload, field):
            errors.append(error(field, _missing_value_message(field, spec, item_index=item_index), item_index=item_index))

    for rule in _constraint_rules(spec, "conditional_required", legacy_key="conditional_required"):
        when = rule.get("when", {})
        if not _conditions_match(payload, when):
            continue
        for field in rule.get("fields", []):
            if _is_missing(payload, field):
                reason = rule.get("message") or "当前字段组合下该字段必填"
                errors.append(error(field, _missing_value_message(field, spec, item_index=item_index, reason=reason), item_index=item_index))

    prefix = f"第 {item_index + 1} 项" if item_index is not None else ""
    fields = spec.get("fields", {})
    for field, rules in fields.items():
        if _is_missing(payload, field):
            continue
        values = _resolve_path(payload, field)
        if "[]" not in field:
            values = values[:1]
        for value in values:
            if value is _MISSING or value is None or value == "":
                continue
            errors.extend(_validate_value(field, value, rules, spec, prefix=prefix, item_index=item_index))

    for rule in _constraint_rules(spec, "multiple_of"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        fields_to_check = list(rule.get("fields") or [])
        if isinstance(rule.get("field"), str):
            fields_to_check.append(rule["field"])
        divisor = rule.get("value")
        if not isinstance(divisor, int | float) or divisor == 0:
            continue
        for field in fields_to_check:
            if _is_missing(payload, field):
                continue
            for value in _resolve_path(payload, field):
                if not isinstance(value, int | float) or isinstance(value, bool):
                    continue
                if value % divisor != 0:
                    label = _field_label(field, spec)
                    errors.append(error(field, f"{label} 必须是 {divisor} 的整数倍。", item_index=item_index))

    for rule in _constraint_rules(spec, "regex"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        pattern = rule.get("pattern")
        if not isinstance(pattern, str):
            continue
        fields_to_check = list(rule.get("fields") or [])
        if isinstance(rule.get("field"), str):
            fields_to_check.append(rule["field"])
        for field in fields_to_check:
            if _is_missing(payload, field):
                continue
            for value in _resolve_path(payload, field):
                if isinstance(value, str) and re.fullmatch(pattern, value) is None:
                    label = _field_label(field, spec)
                    reason = rule.get("message") or f"必须匹配格式 {pattern}"
                    errors.append(error(field, f"{label} 格式不正确，原因：{reason}。", item_index=item_index))

    for rule in _constraint_rules(spec, "range"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        fields_to_check = list(rule.get("fields") or [])
        if isinstance(rule.get("field"), str):
            fields_to_check.append(rule["field"])
        for field in fields_to_check:
            if _is_missing(payload, field):
                continue
            for value in _resolve_path(payload, field):
                if not isinstance(value, int | float) or isinstance(value, bool):
                    continue
                min_value = rule.get("min")
                max_value = rule.get("max")
                label = _field_label(field, spec)
                if min_value is not None and value < min_value:
                    errors.append(error(field, f"{label} 不能小于 {min_value}。", item_index=item_index))
                if max_value is not None and value > max_value:
                    errors.append(error(field, f"{label} 不能大于 {max_value}。", item_index=item_index))

    for rule in _constraint_rules(spec, "forbidden_when", legacy_key="forbidden_when"):
        when = rule.get("when", {})
        if not _conditions_match(payload, when):
            continue
        for field in rule.get("fields", []):
            if not _is_missing(payload, field):
                label = _field_label(field, spec)
                reason = rule.get("message") or "当前字段组合下不支持传入"
                errors.append(error(field, f"{label} 不应传入，原因：{reason}。", item_index=item_index))

    for rule in _constraint_rules(spec, "mutually_exclusive"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        fields_to_check = [field for field in rule.get("fields", []) if isinstance(field, str)]
        present = [field for field in fields_to_check if not _is_missing(payload, field)]
        if len(present) > 1:
            labels = _field_labels(fields_to_check, spec)
            reason = rule.get("message") or "这些字段互斥，不能同时传入"
            errors.append(error(",".join(present), f"{labels} 只能传入一个，原因：{reason}。", item_index=item_index))

    for rule in _constraint_rules(spec, "at_least_one"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        fields_to_check = [field for field in rule.get("fields", []) if isinstance(field, str)]
        if fields_to_check and all(_is_missing(payload, field) for field in fields_to_check):
            labels = _field_labels(fields_to_check, spec)
            reason = rule.get("message") or "这些字段至少需要提供一个"
            errors.append(error(",".join(fields_to_check), f"{labels} 至少需要提供一个，原因：{reason}。", item_index=item_index))

    batch_spec = spec.get("batch_item")
    if batch_spec is not None:
        items_field = spec.get("batch_field", "items")
        items = payload.get(items_field)
        if isinstance(items, list):
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(error(items_field, f"第 {index + 1} 项必须是对象。", item_index=index))
                    continue
                errors.extend(validate_payload(item, batch_spec, item_index=index))

    return _dedupe_errors(errors)


def _validate_value(
    field: str,
    value: Any,
    rules: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    prefix: str,
    item_index: int | None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    expected_type = rules.get("type")
    if expected_type and not _type_ok(value, expected_type):
        label = _field_label(field, spec)
        subject = f"{prefix}{label}" if prefix else label
        errors.append(error(field, f"{subject} 类型不正确，应为{TYPE_LABELS.get(expected_type, expected_type)}。", item_index=item_index))
        return errors

    allowed = rules.get("enum")
    if allowed and value not in allowed:
        label = _field_label(field, spec)
        meanings = rules.get("enum_labels", {})
        choices = "、".join(f"{item}（{meanings[item]}）" if item in meanings else str(item) for item in allowed)
        subject = f"{prefix}{label}" if prefix else label
        errors.append(error(field, f"{subject}（{field}）的值 {value} 不在允许范围内；允许值：{choices}。", item_index=item_index))

    if isinstance(value, str):
        min_len = rules.get("min_length")
        max_len = rules.get("max_length")
        if min_len is not None and len(value) < min_len:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 长度不能少于 {min_len} 个字符。", item_index=item_index))
        if max_len is not None and len(value) > max_len:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 长度不能超过 {max_len} 个字符。", item_index=item_index))

    if isinstance(value, int | float) and not isinstance(value, bool):
        min_value = rules.get("min")
        max_value = rules.get("max")
        if min_value is not None and value < min_value:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 不能小于 {min_value}。", item_index=item_index))
        if max_value is not None and value > max_value:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 不能大于 {max_value}。", item_index=item_index))

    if isinstance(value, list):
        min_items = rules.get("min_items")
        max_items = rules.get("max_items")
        if min_items is not None and len(value) < min_items:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 至少需要 {min_items} 项。", item_index=item_index))
        if max_items is not None and len(value) > max_items:
            label = _field_label(field, spec)
            errors.append(error(field, f"{label} 最多支持 {max_items} 项。", item_index=item_index))
    return errors
