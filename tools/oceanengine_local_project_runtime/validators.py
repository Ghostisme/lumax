from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import (
    Field,
    RootModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    TypeAdapter,
    ValidationError,
    model_validator,
)

TYPE_LABELS = {
    "string": "字符串",
    "number": "数字",
    "integer": "整数",
    "array": "数组",
    "object": "对象",
    "boolean": "布尔值",
}

SUPPORTED_CONSTRAINT_TYPES = {
    "at_least_one",
    "conditional_required",
    "forbidden_when",
    "multiple_of",
    "mutually_exclusive",
    "product_max",
    "range",
    "regex",
}

_MISSING = object()
DISPLAY_VALUE_MAX_CHARS = 80
ENUM_CHOICE_DISPLAY_LIMIT = 8


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


def _message_type_ok(value: Any, expected: str) -> bool:
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


def _pydantic_type(expected: str | None) -> Any:
    if expected == "string":
        return StrictStr
    if expected == "number":
        return StrictInt | StrictFloat
    if expected == "integer":
        return StrictInt
    if expected == "array":
        return list[Any]
    if expected == "object":
        return dict[str, Any]
    if expected == "boolean":
        return StrictBool
    return Any


def _pydantic_annotation(rules: Mapping[str, Any]) -> Any:
    allowed = rules.get("enum")
    annotation = Literal.__getitem__(tuple(allowed)) if allowed else _pydantic_type(rules.get("type"))
    field_kwargs: dict[str, Any] = {}
    expected_type = rules.get("type")

    if expected_type == "string":
        if rules.get("min_length") is not None:
            field_kwargs["min_length"] = rules["min_length"]
        if rules.get("max_length") is not None:
            field_kwargs["max_length"] = rules["max_length"]
    elif expected_type in {"number", "integer"}:
        if rules.get("min") is not None:
            field_kwargs["ge"] = rules["min"]
        if rules.get("max") is not None:
            field_kwargs["le"] = rules["max"]
    elif expected_type == "array":
        item_type = rules.get("item_type")
        item_enum = rules.get("item_enum")
        if isinstance(item_type, str):
            item_annotation = (
                Literal.__getitem__(tuple(item_enum))
                if isinstance(item_enum, list) and item_enum
                else _pydantic_type(item_type)
            )
            item_kwargs: dict[str, Any] = {}
            if item_type in {"number", "integer"}:
                if rules.get("item_min") is not None:
                    item_kwargs["ge"] = rules["item_min"]
                if rules.get("item_max") is not None:
                    item_kwargs["le"] = rules["item_max"]
            if item_kwargs:
                item_annotation = Annotated[item_annotation, Field(**item_kwargs)]
            annotation = list[item_annotation]
        if rules.get("min_items") is not None:
            field_kwargs["min_length"] = rules["min_items"]
        if rules.get("max_items") is not None:
            field_kwargs["max_length"] = rules["max_items"]

    if field_kwargs:
        return Annotated[annotation, Field(**field_kwargs)]
    return annotation


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


def _truncate_display_text(value: str, *, max_chars: int = DISPLAY_VALUE_MAX_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max(max_chars - 3, 0)] + "..."


def _display_value(value: Any) -> str:
    return _truncate_display_text(str(value))


def _format_enum_choices(allowed: list[Any], meanings: Mapping[str, Any], *, include_codes: bool) -> str:
    choices: list[str] = []
    for item in allowed:
        if include_codes and item in meanings:
            choice = f"{item}（{meanings[item]}）"
        elif item in meanings:
            choice = str(meanings[item])
        else:
            choice = str(item)
        choices.append(_truncate_display_text(choice))

    shown_choices = choices[:ENUM_CHOICE_DISPLAY_LIMIT]
    text = "、".join(shown_choices)
    omitted_count = max(len(choices) - len(shown_choices), 0)
    if omitted_count:
        text = f"{text}（另有 {omitted_count} 项未展示）" if text else f"另有 {omitted_count} 项未展示"
    return text


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
        choices = _format_enum_choices(list(allowed), meanings, include_codes=False)
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


def _configured_field_paths(spec: Mapping[str, Any]) -> set[str]:
    paths = set(str(field) for field in spec.get("fields", {}) if isinstance(field, str))
    paths.update(str(field) for field in spec.get("required", []) if isinstance(field, str))
    for rule in _constraint_rules(spec, "conditional_required", legacy_key="conditional_required"):
        paths.update(str(field) for field in rule.get("fields", []) if isinstance(field, str))
    batch_field = spec.get("batch_field")
    if isinstance(batch_field, str):
        paths.add(batch_field)
    return paths


def _unknown_field_message(field: str, spec: Mapping[str, Any]) -> str:
    fields = spec.get("fields", {})
    if field == "items" and spec.get("batch_field") == "data":
        return "items 不是官方文档支持的参数字段，请使用官方字段 data。"
    official_filtering_field = f"filtering.{field}"
    if official_filtering_field in fields:
        return f"{field} 不是官方文档支持的顶层参数字段，请使用官方字段 {official_filtering_field}。"
    return f"{field} 不是官方文档支持的参数字段，请改为官方字段路径后重试。"


def _validate_unknown_fields(payload: Mapping[str, Any], spec: Mapping[str, Any], *, item_index: int | None = None) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    paths = _configured_field_paths(spec)
    allowed_top_level = {path.split(".", 1)[0] for path in paths}

    for key, value in payload.items():
        if key not in allowed_top_level:
            errors.append(error(str(key), _unknown_field_message(str(key), spec), item_index=item_index))
            continue

        if key == spec.get("batch_field"):
            continue

        child_prefix = f"{key}."
        child_paths = {path.removeprefix(child_prefix) for path in paths if path.startswith(child_prefix)}
        if child_paths and isinstance(value, Mapping):
            child_spec = {
                "fields": {path: spec.get("fields", {}).get(f"{child_prefix}{path}", {}) for path in child_paths},
                "required": [path for path in child_paths if f"{child_prefix}{path}" in spec.get("required", [])],
                "field_labels": {
                    path: spec.get("field_labels", {}).get(f"{child_prefix}{path}", path)
                    for path in child_paths
                },
            }
            for item in _validate_unknown_fields(value, child_spec, item_index=item_index):
                item["field"] = f"{key}.{item['field']}"
                item["message"] = item["message"].replace(str(item["field"]).removeprefix(f"{key}."), item["field"], 1)
                errors.append(item)

    return errors


def _validate_supported_rule_config(spec: Mapping[str, Any], *, item_index: int | None = None, prefix: str = "") -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field, rules in spec.get("fields", {}).items():
        if not isinstance(field, str) or not isinstance(rules, Mapping):
            continue
        expected_type = rules.get("type")
        if expected_type is not None and expected_type not in TYPE_LABELS:
            field_path = f"{prefix}{field}" if prefix else field
            errors.append(
                error(
                    "__config__",
                    f"规则配置字段 {field_path} 声明了 Pydantic 未覆盖的字段类型：{expected_type}。",
                    item_index=item_index,
                )
            )

    for index, rule in enumerate(spec.get("constraints", [])):
        if not isinstance(rule, Mapping):
            continue
        rule_type = rule.get("type")
        if rule_type not in SUPPORTED_CONSTRAINT_TYPES:
            errors.append(
                error(
                    "__config__",
                    f"规则配置 constraints[{index}] 声明了 Pydantic 未覆盖的约束类型：{rule_type}。",
                    item_index=item_index,
                )
            )

    batch_spec = spec.get("batch_item")
    if isinstance(batch_spec, Mapping):
        errors.extend(_validate_supported_rule_config(batch_spec, item_index=item_index, prefix=f"{prefix}batch_item."))
    return errors


class _PydanticRuleValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("参数校验失败")
        self.rule_errors = errors


def _validate_payload_rules(payload: Mapping[str, Any], spec: Mapping[str, Any], *, item_index: int | None = None) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    errors.extend(_validate_supported_rule_config(spec, item_index=item_index))
    if errors:
        return _dedupe_errors(errors)

    errors.extend(_validate_unknown_fields(payload, spec, item_index=item_index))
    errors.extend(_dependency_prohibition_errors(payload, spec, item_index=item_index))

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
            errors.extend(_validate_value_with_pydantic(field, value, rules, spec, prefix=prefix, item_index=item_index))

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

    for rule in _constraint_rules(spec, "product_max"):
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        fields_to_check = [field for field in rule.get("fields", []) if isinstance(field, str)]
        max_value = rule.get("max")
        if len(fields_to_check) < 2 or not isinstance(max_value, int | float):
            continue
        values: list[int | float] = []
        for field in fields_to_check:
            if _is_missing(payload, field):
                values = []
                break
            value = _first_value(payload, field)
            if not isinstance(value, int | float) or isinstance(value, bool):
                values = []
                break
            values.append(value)
        if not values:
            continue
        product: int | float = 1
        for value in values:
            product *= value
        if product > max_value:
            message = rule.get("message")
            if not message:
                labels = _field_labels(fields_to_check, spec)
                message = f"{labels} 的乘积不能大于 {max_value}。"
            errors.append(error(",".join(fields_to_check), str(message), item_index=item_index))

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
        items_field = spec.get("batch_field", "data")
        items = payload.get(items_field)
        if isinstance(items, list):
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(error(items_field, f"第 {index + 1} 项必须是对象。", item_index=index))
                    continue
                errors.extend(validate_payload(item, batch_spec, item_index=index))

    return _dedupe_errors(errors)


def _dependency_prohibition_errors(payload: Mapping[str, Any], spec: Mapping[str, Any], *, item_index: int | None = None) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
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
    return errors


def _build_pydantic_payload_model(spec: Mapping[str, Any], *, item_index: int | None = None) -> type[RootModel[dict[str, Any]]]:
    class PydanticPayloadModel(RootModel[dict[str, Any]]):
        @model_validator(mode="after")
        def validate_rule_config(self) -> PydanticPayloadModel:
            errors = _validate_payload_rules(self.root, spec, item_index=item_index)
            if errors:
                raise _PydanticRuleValidationError(errors)
            return self

    return PydanticPayloadModel


def _rule_errors_from_validation_error(exc: ValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for item in exc.errors():
        original_error = item.get("ctx", {}).get("error")
        if isinstance(original_error, _PydanticRuleValidationError):
            errors.extend(original_error.rule_errors)
    return _dedupe_errors(errors)


def validate_payload(payload: Mapping[str, Any], spec: Mapping[str, Any], *, item_index: int | None = None) -> list[dict[str, Any]]:
    model = _build_pydantic_payload_model(spec, item_index=item_index)
    try:
        model.model_validate(payload)
    except ValidationError as exc:
        rule_errors = _rule_errors_from_validation_error(exc)
        if rule_errors:
            return rule_errors
        return [error("__root__", "参数格式不正确，请按对象传入。", item_index=item_index)]
    return []


def _format_pydantic_value_errors(
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
    label = _field_label(field, spec)
    subject = f"{prefix}{label}" if prefix else label

    if expected_type and not _message_type_ok(value, expected_type):
        errors.append(error(field, f"{subject} 类型不正确，应为{TYPE_LABELS.get(expected_type, expected_type)}。", item_index=item_index))
        return errors

    allowed = rules.get("enum")
    if allowed and value not in allowed:
        meanings = rules.get("enum_labels", {})
        choices = _format_enum_choices(list(allowed), meanings, include_codes=True)
        display_value = _display_value(value)
        errors.append(error(field, f"{subject}（{field}）的值 {display_value} 不在允许范围内；允许值：{choices}。", item_index=item_index))

    if isinstance(value, str):
        min_len = rules.get("min_length")
        max_len = rules.get("max_length")
        if min_len is not None and len(value) < min_len:
            errors.append(error(field, f"{label} 长度不能少于 {min_len} 个字符。", item_index=item_index))
        if max_len is not None and len(value) > max_len:
            errors.append(error(field, f"{label} 长度不能超过 {max_len} 个字符。", item_index=item_index))

    if isinstance(value, int | float) and not isinstance(value, bool):
        min_value = rules.get("min")
        max_value = rules.get("max")
        if min_value is not None and value < min_value:
            errors.append(error(field, f"{label} 不能小于 {min_value}。", item_index=item_index))
        if max_value is not None and value > max_value:
            errors.append(error(field, f"{label} 不能大于 {max_value}。", item_index=item_index))

    if isinstance(value, list):
        min_items = rules.get("min_items")
        max_items = rules.get("max_items")
        if min_items is not None and len(value) < min_items:
            errors.append(error(field, f"{label} 至少需要 {min_items} 项。", item_index=item_index))
        if max_items is not None and len(value) > max_items:
            errors.append(error(field, f"{label} 最多支持 {max_items} 项。", item_index=item_index))
        item_type = rules.get("item_type")
        if isinstance(item_type, str):
            for index, item in enumerate(value):
                if not _message_type_ok(item, item_type):
                    errors.append(error(field, f"{label}第 {index + 1} 项 类型不正确，应为{TYPE_LABELS.get(item_type, item_type)}。", item_index=index))
                    continue
                item_enum = rules.get("item_enum")
                if isinstance(item_enum, list) and item_enum and item not in item_enum:
                    meanings = rules.get("enum_labels", {})
                    choices = _format_enum_choices(list(item_enum), meanings, include_codes=True)
                    display_value = _display_value(item)
                    errors.append(
                        error(
                            field,
                            f"{label}第 {index + 1} 项（{field}）的值 {display_value} 不在允许范围内；允许值：{choices}。",
                            item_index=index,
                        )
                    )
                    continue
                if isinstance(item, int | float) and not isinstance(item, bool):
                    item_min = rules.get("item_min")
                    item_max = rules.get("item_max")
                    if item_min is not None and item < item_min:
                        errors.append(error(field, f"{label}第 {index + 1} 项 不能小于 {item_min}。", item_index=index))
                    if item_max is not None and item > item_max:
                        errors.append(error(field, f"{label}第 {index + 1} 项 不能大于 {item_max}。", item_index=index))
    return errors


def _validate_value_with_pydantic(
    field: str,
    value: Any,
    rules: Mapping[str, Any],
    spec: Mapping[str, Any],
    *,
    prefix: str,
    item_index: int | None,
) -> list[dict[str, Any]]:
    try:
        TypeAdapter(_pydantic_annotation(rules)).validate_python(value)
    except ValidationError:
        return _format_pydantic_value_errors(field, value, rules, spec, prefix=prefix, item_index=item_index)
    return []
