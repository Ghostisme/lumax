from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import mcp_client
from .mutation_confirm import confirm_mutation
from .response import failure, print_json, success
from .validators import _conditions_match, _constraint_rules, _is_missing, validate_payload

COMMON_RESPONSE_VALUE_LABELS = {
    "LIVE": "直播",
    "VIDEO_IMAGE": "短视频/图文",
    "CONTENT_HEAT": "线上互动",
    "POI_RECOMMEND": "线下到店",
    "PRODUCT_PAY": "团购成交",
    "EXTERNAL": "获取线索",
    "GENERAL": "通投",
    "SEARCHING": "搜索",
    "POI": "门店",
    "PRODUCT": "商品",
    "FOLLOW_ACTION": "粉丝增长",
    "LIVE_ENGAGEMENT": "直播加热",
    "LIVE_ENTER_ACTION": "直播间观看",
    "LIVE_OTO_CLICK": "直播间商品点击",
    "LIVE_OTO_GROUP_BUYING": "直播间团购购买",
    "LIVE_STAY_TIME": "直播间停留",
    "NATIVE_ACTION": "用户互动",
    "SHOW": "展示量",
    "CLUE_ACQUISITION": "获取线索",
    "PRIVATE_MESSAEG": "私信消息",
    "PRIVATE_MESSAGE": "私信消息",
    "CLUE_CONFIRM": "确认意向",
    "CLUE_HIGH_INTENTION": "预付定金",
    "OTO_PAY": "预付定金",
    "MESSAGE_INTENTION_CLUE": "私信意向线索",
    "MANUAL": "手动出价",
    "SMART": "智能出价",
    "STABILIZE_COSTS": "稳定成本",
    "MAX_CONVERSION": "最大转化",
    "BUDGET_MODE_DAY": "日预算",
    "BUDGET_MODE_TOTAL": "总预算",
    "BUDGET_MODE_7DAY_TOTAL": "七日总预算",
    "DELIVERY_7DAY": "七日总预算",
    "DAILY_DELIVERY_DURATION": "每日投放时长",
    "DAY": "日预算",
    "TOTAL": "总预算",
    "ON": "开启",
    "OFF": "关闭",
    "INTELLIGENT_SELECTION_MODE_ON": "智能优选",
    "INTELLIGENT_SELECTION_MODE_OFF": "自定义",
    "FORM": "表单预约",
    "PHONE_SMART": "电话咨询",
    "CONSULT": "私信咨询",
    "AWEME_PAGE": "推抖音私信页",
    "MARKET_PAGE": "推营销页",
    "PRODUCT_PAGE": "商品投放详情页",
    "SHOP_PAGE": "推门店页",
    "ENABLE": "启用",
    "PAUSED": "暂停",
    "DELETE": "删除",
}


def _normalize_amount_fields(spec: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """按规则配置归一金额字段。

    入参:
        spec: 当前 capability 的规则配置，读取其中的 `amount_normalization`。
        payload: 用户侧输入参数，通常使用 snake_case 字段名。

    出参:
        返回三元组 `(normalized_payload, normalizations, errors)`：
        - `normalized_payload`: 已把源金额字段转换为接口字段后的 payload。
        - `normalizations`: 每个成功转换字段的来源、单位和转换后数值。
        - `errors`: 金额源字段类型不合法时的中文校验错误。
    """
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


def _field_spec_for_error(spec: dict[str, Any], error_item: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    field = str(error_item.get("field") or "")
    if error_item.get("item_index") is not None and isinstance(spec.get("batch_item"), dict):
        batch_spec = spec["batch_item"]
        batch_fields = batch_spec.get("fields", {})
        if isinstance(batch_fields, dict) and isinstance(batch_fields.get(field), dict):
            return field, batch_fields[field], batch_spec

    fields = spec.get("fields", {})
    if isinstance(fields, dict) and isinstance(fields.get(field), dict):
        return field, fields[field], spec

    if "." in field:
        leaf_field = field.split(".")[-1].replace("[]", "")
        if error_item.get("item_index") is not None and isinstance(spec.get("batch_item"), dict):
            batch_spec = spec["batch_item"]
            batch_fields = batch_spec.get("fields", {})
            if isinstance(batch_fields, dict) and isinstance(batch_fields.get(leaf_field), dict):
                return field, batch_fields[leaf_field], batch_spec
        if isinstance(fields, dict) and isinstance(fields.get(leaf_field), dict):
            return field, fields[leaf_field], spec

    return field, {}, spec


def _clarification_field_label(field: str, field_rules: dict[str, Any], owning_spec: dict[str, Any]) -> str:
    label = field_rules.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    labels = owning_spec.get("field_labels", {})
    if isinstance(labels, dict):
        configured_label = labels.get(field) or labels.get(field.split(".")[-1].replace("[]", ""))
        if isinstance(configured_label, str) and configured_label.strip():
            return configured_label.strip()
    return field


def _clarification_options(field_rules: dict[str, Any]) -> tuple[list[Any], str] | None:
    enum_values = field_rules.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values, "single"
    item_enum_values = field_rules.get("item_enum")
    if isinstance(item_enum_values, list) and item_enum_values:
        return item_enum_values, "multiple"
    if field_rules.get("type") == "boolean":
        return ["true", "false"], "single"
    return None


def _build_parameter_clarification(spec: dict[str, Any], errors: list[dict[str, Any]], payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not errors:
        return None
    first_error = errors[0]
    if not isinstance(first_error, dict):
        return None
    question = str(first_error.get("message") or "").strip()
    if "是什么值？" not in question:
        return None

    field, field_rules, owning_spec = _field_spec_for_error(spec, first_error)
    if not field or not field_rules:
        return None

    field_label = _clarification_field_label(field, field_rules, owning_spec)
    clarification: dict[str, Any] = {
        "version": "v1",
        "reason": "missing_required_parameter",
        "field": field,
        "field_label": field_label,
        "question": question,
    }

    options = _clarification_options(field_rules)
    if options is not None:
        values, selection_mode = options
        if payload is not None:
            values = _filter_static_clarification_values(spec, owning_spec, payload, first_error, field, values)
        enum_labels = field_rules.get("enum_labels", {})
        if not isinstance(enum_labels, dict):
            enum_labels = {}
        if field_rules.get("type") == "boolean":
            enum_labels = {**enum_labels, "true": "是", "false": "否"}
        question = _sync_choice_question(question, values, enum_labels)
        first_error["message"] = question
        clarification["question"] = question
        clarification["input_control"] = {
            "type": "choice_cards",
            "selection_mode": selection_mode,
            "options": [
                {
                    "value": value,
                    "label": str(enum_labels.get(value) or value),
                }
                for value in values
            ],
        }
    else:
        value_type = field_rules.get("type") or "string"
        clarification["input_control"] = {
            "type": "text_input",
            "value_type": str(value_type),
            "placeholder": f"请填写{field_label}",
        }
    return clarification


def _sync_choice_question(question: str, values: list[Any], enum_labels: dict[Any, Any]) -> str:
    if "可选：" not in question:
        return question
    head, tail = question.split("可选：", 1)
    suffix = ""
    reason_index = tail.find("原因：")
    if reason_index != -1:
        suffix = tail[reason_index:].strip()
    choices = "、".join(str(enum_labels.get(value) or value) for value in values)
    synced = f"{head}可选：{choices}。"
    if suffix:
        synced += suffix
    return synced


def _filter_static_clarification_values(
    root_spec: dict[str, Any],
    owning_spec: dict[str, Any],
    payload: dict[str, Any],
    error_item: dict[str, Any],
    field: str,
    values: list[Any],
) -> list[Any]:
    candidate_base = _clarification_filter_payload(root_spec, owning_spec, payload, error_item)
    filtered = []
    for value in values:
        candidate_payload = deepcopy(candidate_base)
        _assign_candidate_value(candidate_payload, field, value)
        if _candidate_violates_dependency_rules(owning_spec, candidate_payload, field):
            continue
        filtered.append(value)
    return filtered


def _clarification_filter_payload(
    root_spec: dict[str, Any],
    owning_spec: dict[str, Any],
    payload: dict[str, Any],
    error_item: dict[str, Any],
) -> dict[str, Any]:
    if owning_spec is root_spec:
        return deepcopy(payload)

    item_index = error_item.get("item_index")
    if item_index is None:
        return deepcopy(payload)

    items_field = root_spec.get("batch_field", "data")
    items = payload.get(items_field)
    if isinstance(items, list) and isinstance(item_index, int) and 0 <= item_index < len(items) and isinstance(items[item_index], dict):
        return deepcopy(items[item_index])
    return {}


def _assign_candidate_value(payload: dict[str, Any], field: str, value: Any) -> None:
    current = payload
    parts = field.split(".")
    for raw_part in parts[:-1]:
        is_array_item = raw_part.endswith("[]")
        part = raw_part[:-2] if is_array_item else raw_part
        if is_array_item:
            items = current.get(part)
            if not isinstance(items, list) or not items or not isinstance(items[0], dict):
                items = [{}]
                current[part] = items
            current = items[0]
            continue
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child

    raw_leaf = parts[-1]
    if raw_leaf.endswith("[]"):
        current[raw_leaf[:-2]] = [value]
    else:
        current[raw_leaf] = value


def _candidate_violates_dependency_rules(spec: dict[str, Any], payload: dict[str, Any], field: str) -> bool:
    for rule in _constraint_rules(spec, "forbidden_when", legacy_key="forbidden_when"):
        fields = [item for item in rule.get("fields", []) if isinstance(item, str)]
        if not any(_same_rule_field(item, field) for item in fields):
            continue
        if _conditions_match(payload, rule.get("when", {})):
            return True

    for rule in _constraint_rules(spec, "mutually_exclusive"):
        fields = [item for item in rule.get("fields", []) if isinstance(item, str)]
        if not any(_same_rule_field(item, field) for item in fields):
            continue
        when = rule.get("when", {})
        if when and not _conditions_match(payload, when):
            continue
        present = [item for item in fields if not _is_missing(payload, item)]
        if len(present) > 1:
            return True
    return False


def _same_rule_field(rule_field: str, target_field: str) -> bool:
    if rule_field == target_field:
        return True
    return rule_field.split(".")[-1].replace("[]", "") == target_field.split(".")[-1].replace("[]", "")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_project_rule(name: str) -> dict[str, Any]:
    path = _repo_root() / "skills" / "custom" / "oceanengine-local-project" / "rules" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _dynamic_product_choice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("delivery_goal") != "PRODUCT":
        return None
    local_account_id = payload.get("local_account_id")
    local_delivery_scene = payload.get("local_delivery_scene")
    if local_account_id is None or local_delivery_scene is None:
        return None

    choice_payload = {
        "local_account_id": local_account_id,
        "local_delivery_scene": local_delivery_scene,
        "page": payload.get("page", 1),
        "page_size": payload.get("page_size", 20),
    }
    keyword = payload.get("product_name") or payload.get("search_key_word")
    if isinstance(keyword, str) and keyword.strip():
        choice_payload["filtering"] = {"search_key_word": keyword.strip()}
    return choice_payload


def _product_option_description(product: dict[str, Any]) -> str | None:
    parts: list[str] = []
    price = _dict_get_with_official_key(product, "price")
    if price is not None:
        parts.append(f"价格：{price}")
    applicable_poi_num = _dict_get_with_official_key(product, "applicable_poi_num")
    if applicable_poi_num is not None:
        parts.append(f"适用门店数：{applicable_poi_num}")
    market_page_infos = _dict_get_with_official_key(product, "bind_market_page_infos")
    if isinstance(market_page_infos, list):
        market_page_ids = [
            _dict_get_with_official_key(item, "market_page_id")
            for item in market_page_infos
            if isinstance(item, dict) and _dict_get_with_official_key(item, "market_page_id") is not None
        ]
        if market_page_ids:
            parts.append("绑定营销页ID：" + "、".join(str(item) for item in market_page_ids))
    return "；".join(parts) if parts else None


def _product_option_metadata(product: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    field_map = {
        "product_id": "product_id",
        "product_name": "product_name",
        "price": "price",
        "product_pics": "product_pics",
        "applicable_poi_num": "applicable_poi_num",
    }
    for source, target in field_map.items():
        value = _dict_get_with_official_key(product, source)
        if value is not None:
            metadata[target] = value

    market_page_infos = _dict_get_with_official_key(product, "bind_market_page_infos")
    if isinstance(market_page_infos, list):
        normalized_infos = []
        for item in market_page_infos:
            if not isinstance(item, dict):
                continue
            market_page_id = _dict_get_with_official_key(item, "market_page_id")
            if market_page_id is not None:
                normalized_infos.append({"market_page_id": market_page_id})
        if normalized_infos:
            metadata["bind_market_page_infos"] = normalized_infos
    return metadata


def _product_choice_options(raw: Any) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    source = _response_display_source(raw)
    if not isinstance(source, dict):
        return [], None
    products = _dict_get_with_official_key(_dict_get_with_official_key(source, "data") or {}, "products")
    if not isinstance(products, list):
        products = _dict_get_with_official_key(source, "products")
    if not isinstance(products, list):
        return [], None

    options: list[dict[str, Any]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        product_id = _dict_get_with_official_key(product, "product_id")
        if product_id is None:
            continue
        product_name = _dict_get_with_official_key(product, "product_name")
        option = {
            "value": product_id,
            "label": str(product_name or product_id),
            "metadata": _product_option_metadata(product),
        }
        description = _product_option_description(product)
        if description:
            option["description"] = description
        options.append(option)

    data = _dict_get_with_official_key(source, "data") if isinstance(source, dict) else None
    page_info = _dict_get_with_official_key(data or {}, "page_info") if isinstance(data, dict) else None
    if not isinstance(page_info, dict):
        page_info = _dict_get_with_official_key(source, "page_info") if isinstance(source, dict) else None
    return options, page_info if isinstance(page_info, dict) else None


def _augment_dynamic_product_choices(spec: dict[str, Any], payload: dict[str, Any], errors: list[dict[str, Any]], clarification: dict[str, Any] | None) -> None:
    if clarification is None or not errors:
        return
    first_error = errors[0]
    if first_error.get("field") != "product_id" or spec.get("name") not in {"create-project", "update-project"}:
        return

    choice_payload = _dynamic_product_choice_payload(payload)
    if choice_payload is None:
        return

    product_spec = _load_project_rule("list-promotable-products.json")
    try:
        result = mcp_client.invoke_endpoint(product_spec, _apply_default_pagination(product_spec, choice_payload))
    except Exception as exc:
        clarification["candidate_error"] = f"商品候选查询失败：{_mcp_exception_message(exc)}"
        return

    mcp_error = _mcp_failure_message(result.get("raw"))
    if mcp_error:
        clarification["candidate_error"] = f"商品候选查询失败：{mcp_error}"
        return

    options, page_info = _product_choice_options(result.get("raw"))
    if not options:
        clarification["candidate_error"] = "当前账户和营销目的下暂无可投商品候选。"
        return

    input_control = {
        "type": "choice_cards",
        "selection_mode": "single",
        "options": options,
    }
    if page_info:
        input_control["page_info"] = page_info
    clarification["input_control"] = input_control


def _iter_text_values(value: Any):
    """递归遍历响应结构中的文本内容。

    入参:
        value: MCP 原始响应或其中任意嵌套节点。

    出参:
        逐个 yield 可用于错误识别的字符串。
    """
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
    """递归查找接口响应中的非零业务 code。

    入参:
        value: MCP 原始响应、解析后的 JSON 或任意嵌套节点。

    出参:
        找到失败 code 时返回 `(code, message)`；未找到时返回 `None`。
    """
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
    """从文本中提取并解析嵌入的 JSON 对象。

    入参:
        text: 可能包含 JSON 片段的 MCP 文本响应。

    出参:
        解析成功时返回 JSON 对象；无法解析时返回 `None`。
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _extract_textcontent_texts(text: str) -> list[str]:
    texts: list[str] = []
    pattern = r"text=(?P<literal>'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")"
    for match in re.finditer(pattern, text):
        try:
            value = ast.literal_eval(match.group("literal"))
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, str):
            texts.append(value)
    return texts


def _platform_partial_errors_message(value: Any) -> str | None:
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, dict):
            nested_message = _platform_partial_errors_message(data)
            if nested_message:
                return nested_message

        errors = value.get("errors")
        if errors is None:
            errors = value.get("error")
        if isinstance(errors, list) and errors:
            messages: list[str] = []
            project_ids = value.get("projectIds")
            if isinstance(project_ids, list):
                messages.extend(f"项目ID {project_id}：平台已受理" for project_id in project_ids)

            for item in errors:
                if not isinstance(item, dict):
                    continue
                message = item.get("errorMessage") or item.get("message") or item.get("msg") or "未提供错误说明"
                if item.get("projectId") is not None:
                    messages.append(f"项目ID {item['projectId']}：{message}")
                elif item.get("promotionId") is not None:
                    messages.append(f"单元ID {item['promotionId']}：{message}")
                else:
                    messages.append(str(message))
            if messages:
                return "；".join(messages)

        for item in value.values():
            nested_message = _platform_partial_errors_message(item)
            if nested_message:
                return nested_message
    elif isinstance(value, list):
        for item in value:
            nested_message = _platform_partial_errors_message(item)
            if nested_message:
                return nested_message
    return None


def _mcp_failure_message(raw: Any) -> str | None:
    """把 MCP 原始失败形态归类为用户可理解的中文错误。

    入参:
        raw: `mcp_client.invoke_endpoint()` 返回结果中的 `raw` 字段。

    出参:
        识别到失败时返回中文错误摘要；未识别为失败时返回 `None`。
    """
    runtime_exception_markers = ("nonetype", "has no attribute", "traceback", "nullpointerexception")
    nonzero = _find_nonzero_code(raw)
    if nonzero is not None:
        code, message = nonzero
        if isinstance(message, str) and any(marker in message.lower() for marker in runtime_exception_markers):
            return "MCP 工具返回内部异常，请检查输入是否属于当前账户且资源有效。"
        return f"接口返回 code={code}：{message or '未提供错误说明'}"

    partial_message = _platform_partial_errors_message(raw)
    if partial_message:
        return partial_message

    markers = ("cannot deserialize", "exception", "bad request", "invalid request", "调用失败", "参数错误", "非法")
    business_failure_markers = ("未找到", "不存在", "无权访问")
    for text in _iter_text_values(raw):
        candidates = _extract_textcontent_texts(text) or [text]
        for candidate in candidates:
            parsed = _parse_embedded_json(candidate)
            if parsed is not None:
                nonzero = _find_nonzero_code(parsed)
                if nonzero is not None:
                    code, message = nonzero
                    if isinstance(message, str) and any(marker in message.lower() for marker in runtime_exception_markers):
                        return "MCP 工具返回内部异常，请检查输入是否属于当前账户且资源有效。"
                    return f"接口返回 code={code}：{message or '未提供错误说明'}"
                partial_message = _platform_partial_errors_message(parsed)
                if partial_message:
                    return partial_message
            lower = candidate.lower()
            if re.search(r'\brequest\b"?\s+(?:is|was)\s+null\b', lower) or re.search(r'\brequest\b"?\s*[:=]\s*null\b', lower):
                return f"MCP 请求包装错误：{candidate[:500]}"
            if "cannot invoke" in lower:
                return f"MCP 请求包装错误：{candidate[:500]}"
            if any(marker in lower for marker in runtime_exception_markers):
                return "MCP 工具返回内部异常，请检查输入是否属于当前账户且资源有效。"
            if "doesn't exist or the role is wrong" in lower or ("account" in lower and "role is wrong" in lower):
                return "账户不存在或当前角色无权访问，请检查账户是否正确并确认当前操作权限。"
            if any(marker in candidate for marker in business_failure_markers):
                return candidate[:500]
            if any(marker in lower for marker in markers):
                return candidate[:500]
    return None


def _response_fields(spec: dict[str, Any]) -> list[dict[str, Any]]:
    output = spec.get("output")
    if not isinstance(output, dict):
        return []
    response_fields = output.get("response_fields")
    return response_fields if isinstance(response_fields, list) else []


def _display_value(field: dict[str, Any], value: Any) -> Any:
    value_labels = field.get("value_labels") or field.get("enum_labels") or {}
    if isinstance(value_labels, dict) and value in value_labels:
        return value_labels[value]
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, str) and re.match(r"^https?://", value):
        return "已隐藏原始链接"
    if isinstance(value, str) and value in COMMON_RESPONSE_VALUE_LABELS:
        return COMMON_RESPONSE_VALUE_LABELS[value]
    return value


def _camelize(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def _dict_get_with_official_key(value: dict[str, Any], key: str) -> Any:
    if key in value:
        return value[key]
    camel_key = _camelize(key)
    if camel_key in value:
        return value[camel_key]
    return None


def _collect_path_values(value: Any, segments: list[str], *, prefix: str = "") -> list[tuple[str, Any]]:
    if not segments:
        return [(prefix, value)]

    segment = segments[0]
    is_array = segment.endswith("[]")
    key = segment[:-2] if is_array else segment
    next_value = _dict_get_with_official_key(value, key) if isinstance(value, dict) else None
    if next_value is None:
        return []

    current_path = f"{prefix}.{segment}" if prefix else segment
    if is_array:
        if not isinstance(next_value, list):
            return []
        collected: list[tuple[str, Any]] = []
        for item in next_value:
            collected.extend(_collect_path_values(item, segments[1:], prefix=current_path))
        return collected
    return _collect_path_values(next_value, segments[1:], prefix=current_path)


def _flatten_leaf_values(value: Any, *, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        flattened: list[tuple[str, Any]] = []
        for key, item in value.items():
            official_key = _snake_case(key)
            item_path = f"{prefix}.{official_key}" if prefix else official_key
            flattened.extend(_flatten_leaf_values(item, prefix=item_path))
        return flattened
    if isinstance(value, list):
        flattened = []
        array_path = f"{prefix}[]" if prefix else "[]"
        for item in value:
            flattened.extend(_flatten_leaf_values(item, prefix=array_path))
        return flattened
    return [(prefix, value)]


def _configured_response_paths(fields: list[dict[str, Any]]) -> set[str]:
    return {field["path"] for field in fields if isinstance(field, dict) and isinstance(field.get("path"), str)}


def _fallback_response_display(source: Any, fields: list[dict[str, Any]]) -> list[str]:
    if not isinstance(source, dict):
        return []

    field_labels = {
        field.get("path"): field.get("label")
        for field in fields
        if isinstance(field, dict) and isinstance(field.get("path"), str) and isinstance(field.get("label"), str)
    }
    fallback_parts: list[str] = []
    message = _dict_get_with_official_key(source, "message") or _dict_get_with_official_key(source, "msg")
    if message:
        fallback_parts.append(f"返回信息：{message}")

    data = _dict_get_with_official_key(source, "data")
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and not value:
                label = field_labels.get(f"data.{_snake_case(key)}[]") or field_labels.get(f"data.{key}[]")
                if label:
                    fallback_parts.append(f"{label}：空")

    return fallback_parts


def _response_display_source(raw: Any) -> Any:
    if isinstance(raw, dict):
        for key in ("text", "message", "msg"):
            text = raw.get(key)
            if isinstance(text, str):
                parsed = _parse_embedded_json(text)
                if parsed is not None:
                    return _response_display_source(parsed)
        nested = raw.get("data")
        if isinstance(nested, dict) and "data" in nested and ("code" in nested or "message" in nested or "requestId" in nested):
            return nested
        return raw
    if isinstance(raw, list):
        for item in raw:
            source = _response_display_source(item)
            if source is not item:
                return source
        return raw
    if isinstance(raw, str):
        parsed = _parse_embedded_json(raw)
        if parsed is not None:
            return _response_display_source(parsed)
    return raw


def _augment_response_display(spec: dict[str, Any], raw: Any, data: dict[str, Any]) -> None:
    fields = _response_fields(spec)
    if not fields:
        return

    source = _response_display_source(raw)
    display_parts: list[str] = []
    configured_paths = _configured_response_paths(fields)
    for field in fields:
        if not isinstance(field, dict) or field.get("display") == "diagnostic":
            continue
        path = field.get("path")
        label = field.get("label")
        if not isinstance(path, str) or not isinstance(label, str):
            continue
        for _, value in _collect_path_values(source, path.split(".")):
            if isinstance(value, dict | list):
                continue
            display_parts.append(f"{label}：{_display_value(field, value)}")

    unmapped_fields = []
    for path, value in _flatten_leaf_values(source):
        if path in configured_paths or path in {"code", "message", "msg", "request_id", "requestId"}:
            continue
        if isinstance(value, dict | list):
            continue
        unmapped_fields.append(
            {
                "path": path,
                "value": value,
                "reason": "官方应答字段未记录或未配置为默认展示。",
            }
        )

    if not display_parts:
        display_parts = _fallback_response_display(source, fields)
    if display_parts:
        data["display_text"] = "\n".join(display_parts)
    diagnostics = dict(data.get("diagnostics") or {})
    diagnostics["unmapped_response_fields"] = unmapped_fields
    data["diagnostics"] = diagnostics


def _response_page_postcondition_errors(payload: dict[str, Any], raw: Any) -> list[dict[str, Any]]:
    source = _response_display_source(raw)
    checks = [
        ("page", "data.page_info.page", "页码"),
        ("page_size", "data.page_info.page_size", "每页数量"),
    ]
    errors: list[dict[str, Any]] = []
    for field, response_path, label in checks:
        if field not in payload:
            continue
        values = _collect_path_values(source, response_path.split("."))
        if not values:
            continue
        actual = values[0][1]
        expected = payload[field]
        if actual != expected:
            errors.append(
                {
                    "field": field,
                    "message": f"{label}请求值为 {expected}，但接口返回 {actual}，本次结果不满足用户请求的分页条件。",
                }
            )
    return errors


def _mcp_exception_message(exc: BaseException) -> str:
    messages: list[str] = []
    if isinstance(exc, BaseExceptionGroup):
        for item in exc.exceptions:
            child_message = _mcp_exception_message(item)
            if child_message:
                messages.append(child_message)
    else:
        message = str(exc).strip()
        if message:
            messages.append(message)

    for message in messages:
        if "Server disconnected without sending a response" in message:
            return f"MCP 连接中断：{message}"
    for message in messages:
        if message and "TaskGroup" not in message:
            return message
    return str(exc)


def _apply_default_pagination(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    fields = spec.get("fields")
    if spec.get("operation_type") != "read" or not isinstance(fields, dict):
        return payload
    if "page" not in fields or "page_size" not in fields:
        return payload
    normalized = dict(payload)
    normalized.setdefault("page", 1)
    normalized.setdefault("page_size", 20)
    return normalized


def _apply_filtering_aliases(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    fields = spec.get("fields")
    if not isinstance(fields, dict):
        return payload

    filtering = fields.get("filtering")
    filtering_fields = filtering.get("fields") if isinstance(filtering, dict) else None
    if not isinstance(filtering_fields, dict) or "search_key_word" not in filtering_fields:
        return payload
    if "search_key_word" not in payload:
        return payload

    normalized = dict(payload)
    keyword = normalized.pop("search_key_word")
    existing_filtering = normalized.get("filtering")
    if existing_filtering is None:
        normalized["filtering"] = {"search_key_word": keyword}
    elif isinstance(existing_filtering, dict) and "search_key_word" not in existing_filtering:
        nested_filtering = dict(existing_filtering)
        nested_filtering["search_key_word"] = keyword
        normalized["filtering"] = nested_filtering
    else:
        normalized["search_key_word"] = keyword
    return normalized


def _apply_field_aliases(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    fields = spec.get("fields")
    if not isinstance(fields, dict):
        return payload

    aliases = {}
    if "local_account_id" in fields:
        aliases["account_id"] = "local_account_id"
    configured_aliases = spec.get("field_aliases")
    if isinstance(configured_aliases, dict):
        aliases.update(configured_aliases)

    normalized = dict(payload)
    for source_field, target_field in aliases.items():
        if source_field not in normalized or target_field in normalized:
            continue
        value = normalized.pop(source_field)
        target_config = fields.get(target_field, {})
        if isinstance(target_config, dict):
            value = _normalize_field_value(value, target_config)
        normalized[target_field] = value

    for field, config in fields.items():
        if "." in field or field not in normalized or not isinstance(config, dict):
            continue
        normalized[field] = _normalize_field_value(normalized[field], config)
    return normalized


def _normalize_field_value(value: Any, config: dict[str, Any]) -> Any:
    field_type = config.get("type")
    if field_type == "string" and config.get("format") == "date":
        return _normalize_date_string(value)
    if field_type == "array":
        values = value if isinstance(value, list) else [value]
        item_type = config.get("item_type")
        if item_type in {"number", "integer"}:
            return [_coerce_numeric_string(item, item_type) for item in values]
        return values
    if field_type in {"number", "integer"}:
        return _coerce_numeric_string(value, field_type)
    return value


def _normalize_date_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}:\d{2})?", text)
    if match:
        return match.group(1)
    return value


def _coerce_numeric_string(value: Any, expected_type: str) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if expected_type == "integer":
        return int(text) if re.fullmatch(r"[+-]?\d+", text) else value
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d+\.\d+", text):
        return float(text)
    return value


def run_endpoint(spec: dict[str, Any], payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    """执行单个 OceanEngine 本地推接口能力的通用流水线。

    入参:
        spec: 当前 capability 的完整规则配置，包含字段规则、MCP 目标和确认策略。
        payload: 用户侧结构化输入，使用 rule 中定义的字段名。
        dry_run: 为 `True` 时只做本地预检和 payload 构造摘要，不调用 MCP。

    出参:
        返回统一结构化结果字典，包含 `success`、`message`、`data`、`errors`、
        `tool_name`、`request_id` 和 `retry_count`。校验失败时不会调用 MCP；
        增改类接口会在 MCP 成功后执行后置确认。
    """
    payload, normalizations, normalization_errors = _normalize_amount_fields(spec, payload)
    payload = _apply_field_aliases(spec, payload)
    payload = _apply_filtering_aliases(spec, payload)
    payload = _apply_default_pagination(spec, payload)
    errors = normalization_errors or validate_payload(payload, spec)
    if errors:
        data = {"path": spec["path"], "title": spec["title"], "normalizations": normalizations}
        clarification = _build_parameter_clarification(spec, errors, payload)
        if not dry_run:
            _augment_dynamic_product_choices(spec, payload, errors, clarification)
        if clarification is not None:
            data["clarification"] = clarification
        return failure(
            "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。",
            errors=errors,
            data=data,
        )

    if spec.get("mcp_missing"):
        return failure(
            "当前 MCP 工具缺失，无法执行该官方接口。",
            errors=[
                {
                    "field": "mcp_tool_name",
                    "message": f"{spec['title']} 当前未在 platform-agent-biz 暴露对应 MCP 工具，请补齐 MCP server 后再执行。",
                }
            ],
            data={
                "path": spec["path"],
                "title": spec["title"],
                "mcp_server_name": spec.get("mcp_server_name") or spec.get("mcp", {}).get("server"),
                "mcp_tool_name": spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool"),
                "mcp_missing": True,
            },
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
        message = _mcp_exception_message(exc)
        return failure(
            "MCP 工具调用失败，请根据错误信息检查配置或输入。",
            errors=[{"field": "mcp", "message": message}],
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

    postcondition_errors = _response_page_postcondition_errors(payload, result.get("raw"))
    if postcondition_errors:
        return failure(
            "MCP 工具返回结果与用户请求不一致，不能按成功结果展示。",
            errors=postcondition_errors,
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

    data = {"result": result.get("raw"), "confirmation": confirmation, "path": spec["path"], "title": spec["title"], "normalizations": normalizations}
    _augment_response_display(spec, result.get("raw"), data)
    return success(
        f"{spec['title']} 调用完成。",
        data=data,
        tool_name=result.get("tool_name"),
        request_id=result.get("request_id"),
        retry_count=(confirmation or {}).get("retry_count", 0),
    )


def _load_input(args: argparse.Namespace) -> dict[str, Any]:
    """从 CLI 参数或标准输入读取 JSON payload。

    入参:
        args: argparse 解析后的命令行参数，支持 `--input` 和 `--input-file`。

    出参:
        返回解析后的 dict；没有输入时返回空 dict。
    """
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
    """endpoint 脚本的命令行入口。

    入参:
        spec: 当前 endpoint 预加载的规则配置。

    出参:
        无返回值；把 `run_endpoint()` 的结构化结果以 JSON 打印到 stdout。
    """
    parser = argparse.ArgumentParser(description=spec["title"])
    parser.add_argument("--input", help="JSON string input.")
    parser.add_argument("--input-file", help="Path to a JSON input file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and build request without calling MCP.")
    args = parser.parse_args()
    payload = _load_input(args)
    print_json(run_endpoint(spec, payload, dry_run=args.dry_run))
