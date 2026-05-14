from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ALLOWED_OPERATION_TYPES = {"read", "mutation", "batch"}
ALLOWED_FIELD_TYPES = {"string", "number", "integer", "array", "object", "boolean"}
CONSTRAINT_TYPES = {"conditional_required", "forbidden_when", "mutually_exclusive", "range", "at_least_one"}


def _error(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _parameter_names(parameters: Sequence[Any]) -> set[str]:
    return {item["name"] for item in parameters if isinstance(item, Mapping) and isinstance(item.get("name"), str)}


def _validate_parameters(parameters: Any, *, prefix: str = "parameters") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(parameters, list):
        return [_error(prefix, f"{prefix} 必须是数组。")]

    seen: set[str] = set()
    for index, parameter in enumerate(parameters):
        field_prefix = f"{prefix}[{index}]"
        if not isinstance(parameter, Mapping):
            errors.append(_error(field_prefix, "参数定义必须是对象。"))
            continue

        for key in ("name", "label", "type"):
            if _is_missing(parameter.get(key)):
                errors.append(_error(f"{field_prefix}.{key}", f"{field_prefix}.{key} 为必填字段。"))

        name = parameter.get("name")
        if isinstance(name, str):
            if name in seen:
                errors.append(_error(f"{field_prefix}.name", f"参数名重复：{name}。"))
            seen.add(name)

        field_type = parameter.get("type")
        if isinstance(field_type, str) and field_type not in ALLOWED_FIELD_TYPES:
            errors.append(_error(f"{field_prefix}.type", f"字段 {name or index} 的 type 不支持：{field_type}。"))

        enum = parameter.get("enum")
        if enum is not None:
            if not isinstance(enum, list):
                errors.append(_error(f"{field_prefix}.enum", f"字段 {name or index} 的 enum 必须是数组。"))
            else:
                duplicates = sorted(value for value, count in Counter(enum).items() if count > 1)
                if duplicates:
                    errors.append(_error(f"{field_prefix}.enum", f"字段 {name or index} 的 enum 存在重复值：{', '.join(map(str, duplicates))}。"))

                enum_labels = parameter.get("enum_labels", {})
                if isinstance(enum_labels, Mapping):
                    enum_values = set(enum)
                    for label_key in enum_labels.keys():
                        if label_key not in enum_values:
                            errors.append(_error(f"{field_prefix}.enum_labels.{label_key}", f"字段 {name or index} 的 enum_labels 引用了未定义枚举值：{label_key}。"))

    return errors


def _validate_constraints(constraints: Any, defined_fields: set[str]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if constraints is None:
        return errors
    if not isinstance(constraints, list):
        return [_error("constraints", "constraints 必须是数组。")]

    for index, constraint in enumerate(constraints):
        prefix = f"constraints[{index}]"
        if not isinstance(constraint, Mapping):
            errors.append(_error(prefix, "约束定义必须是对象。"))
            continue

        constraint_type = constraint.get("type")
        if constraint_type not in CONSTRAINT_TYPES:
            errors.append(_error(f"{prefix}.type", f"不支持的约束类型：{constraint_type}。"))

        when = constraint.get("when")
        if isinstance(when, Mapping):
            if "field" in when and any(key in when for key in ("equals", "not_equals", "in", "not_in")):
                when_field = when.get("field")
                if isinstance(when_field, str) and when_field not in defined_fields:
                    errors.append(_error(f"{prefix}.when.field", f"约束引用了未定义字段：{when_field}。"))
            else:
                for when_field in when:
                    if isinstance(when_field, str) and when_field not in defined_fields:
                        errors.append(_error(f"{prefix}.when.{when_field}", f"约束引用了未定义字段：{when_field}。"))

        fields = constraint.get("fields", [])
        if isinstance(fields, list):
            for field_index, field_name in enumerate(fields):
                if isinstance(field_name, str) and field_name not in defined_fields:
                    errors.append(_error(f"{prefix}.fields[{field_index}]", f"约束引用了未定义字段：{field_name}。"))
        elif fields:
            errors.append(_error(f"{prefix}.fields", "约束 fields 必须是数组。"))

        field_name = constraint.get("field")
        if isinstance(field_name, str) and field_name not in defined_fields:
            errors.append(_error(f"{prefix}.field", f"约束引用了未定义字段：{field_name}。"))

    return errors


def _validate_batch(config: Mapping[str, Any], defined_fields: set[str]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if config.get("operation_type") != "batch":
        return errors

    batch = config.get("batch")
    if not isinstance(batch, Mapping):
        return [_error("batch", "operation_type=batch 时必须配置 batch 对象。")]

    batch_field = batch.get("field")
    if not isinstance(batch_field, str) or not batch_field:
        errors.append(_error("batch.field", "batch.field 为必填字段。"))
    elif batch_field not in defined_fields:
        errors.append(_error("batch.field", f"批量字段 {batch_field} 必须在顶层 parameters 中定义。"))

    item_schema = batch.get("item_schema")
    if not isinstance(item_schema, Mapping):
        errors.append(_error("batch.item_schema", "batch.item_schema 为必填对象。"))
        return errors

    item_parameters = item_schema.get("parameters")
    errors.extend(_validate_parameters(item_parameters, prefix="batch.item_schema.parameters"))
    item_fields = _parameter_names(item_parameters if isinstance(item_parameters, list) else [])

    item_identifier = batch.get("item_identifier")
    if not isinstance(item_identifier, str) or not item_identifier:
        errors.append(_error("batch.item_identifier", "batch.item_identifier 为必填字段。"))
    elif item_identifier not in item_fields:
        errors.append(_error("batch.item_identifier", f"批量项定位字段 {item_identifier} 必须在 batch.item_schema.parameters 中定义。"))

    errors.extend(_validate_constraints(item_schema.get("constraints"), item_fields))
    return errors


def _validate_confirmation(config: Mapping[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    confirmation = config.get("confirmation")
    if confirmation is None:
        return errors
    if not isinstance(confirmation, Mapping):
        return [_error("confirmation", "confirmation 必须是对象。")]

    if confirmation.get("enabled") is True:
        if _is_missing(confirmation.get("query_capability")):
            errors.append(_error("confirmation.query_capability", "启用后置确认时 query_capability 为必填字段。"))
        max_retries = confirmation.get("max_retries")
        if not isinstance(max_retries, int) or max_retries < 1:
            errors.append(_error("confirmation.max_retries", "启用后置确认时 max_retries 必须是大于等于 1 的整数。"))
    return errors


def validate_rule_index(config: Mapping[str, Any], base_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for key in ("schema_version", "skill", "capabilities"):
        if _is_missing(config.get(key)):
            errors.append(_error(key, f"{key} 为必填字段。"))

    capabilities = config.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append(_error("capabilities", "capabilities 必须是数组。"))
        return errors

    seen: set[str] = set()
    for index, capability in enumerate(capabilities):
        prefix = f"capabilities[{index}]"
        if not isinstance(capability, Mapping):
            errors.append(_error(prefix, "能力定义必须是对象。"))
            continue

        for key in ("name", "operation_type", "reference", "rule", "script"):
            if _is_missing(capability.get(key)):
                errors.append(_error(f"{prefix}.{key}", f"{prefix}.{key} 为必填字段。"))

        name = capability.get("name")
        if isinstance(name, str):
            if name in seen:
                errors.append(_error(f"{prefix}.name", f"能力名称重复：{name}。"))
            seen.add(name)

        operation_type = capability.get("operation_type")
        if isinstance(operation_type, str) and operation_type not in ALLOWED_OPERATION_TYPES:
            errors.append(_error(f"{prefix}.operation_type", f"operation_type 不支持：{operation_type}。"))

        for key in ("reference", "rule", "script"):
            value = capability.get(key)
            if isinstance(value, str) and not (base_dir / value).exists():
                errors.append(_error(f"{prefix}.{key}", f"{key} 指向的文件不存在：{value}。"))

    return errors


def validate_rule_config(config: Mapping[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    for key in ("schema_version", "name", "title", "operation_type", "path", "mcp", "parameters", "output"):
        if _is_missing(config.get(key)):
            errors.append(_error(key, f"{key} 为必填字段。"))

    operation_type = config.get("operation_type")
    if isinstance(operation_type, str) and operation_type not in ALLOWED_OPERATION_TYPES:
        errors.append(_error("operation_type", f"operation_type 必须是 read、mutation 或 batch，当前为：{operation_type}。"))

    mcp = config.get("mcp")
    if isinstance(mcp, Mapping):
        if _is_missing(mcp.get("server")):
            errors.append(_error("mcp.server", "mcp.server 为必填字段。"))
        if _is_missing(mcp.get("tool")) and _is_missing(mcp.get("match_tokens")):
            errors.append(_error("mcp.tool", "mcp.tool 或 mcp.match_tokens 至少需要配置一个。"))
    elif mcp is not None:
        errors.append(_error("mcp", "mcp 必须是对象。"))

    parameters = config.get("parameters")
    errors.extend(_validate_parameters(parameters))
    defined_fields = _parameter_names(parameters if isinstance(parameters, list) else [])
    errors.extend(_validate_constraints(config.get("constraints"), defined_fields))
    errors.extend(_validate_batch(config, defined_fields))
    errors.extend(_validate_confirmation(config))

    return errors


def load_rule_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate standard DeerFlow skill rule configuration JSON files.")
    parser.add_argument("files", nargs="+", help="Rule config JSON files to validate.")
    args = parser.parse_args()

    failed = False
    for raw_path in args.files:
        path = Path(raw_path)
        try:
            config = load_rule_config(path)
            if path.name == "index.json" and "capabilities" in config:
                errors = validate_rule_index(config, path.parent.parent)
            else:
                errors = validate_rule_config(config)
        except Exception as exc:
            errors = [_error(str(path), f"无法读取或解析规则配置：{exc}")]

        if errors:
            failed = True
            print(json.dumps({"file": str(path), "success": False, "errors": errors}, ensure_ascii=False))
        else:
            print(json.dumps({"file": str(path), "success": True, "errors": []}, ensure_ascii=False))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
