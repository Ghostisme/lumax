# ruff: noqa: E402, I001

"""依赖参数澄清选项的边界测试。

边界约定：
- 静态枚举选项只来自 rules/*.json，本地规则负责过滤依赖后不合法的选项。
- 用户已经选择的参数组合如果违反依赖规则，应优先返回非法组合错误，而不是继续追问后续参数。
- 平台动态候选只用 mocked MCP 响应验证候选来源，不要求固定枚举值。
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.oceanengine_local_material import oceanengine_local_material_tool, run_oceanengine_local_material
from tools.oceanengine_local_project import _agent_visible_result, oceanengine_local_project_tool, run_oceanengine_local_project
from tools.oceanengine_local_project_runtime import endpoint_runner, rule_loader
from tools.oceanengine_local_project_runtime.validators import validate_payload
from tools.oceanengine_local_unit import oceanengine_local_unit_tool


def _empty_runtime():
    return SimpleNamespace(state={"messages": []})


RULE_ROOTS = {
    "project": REPO_ROOT / "skills" / "custom" / "oceanengine-local-project" / "rules",
    "unit": REPO_ROOT / "skills" / "custom" / "oceanengine-local-unit" / "rules",
    "material": REPO_ROOT / "skills" / "custom" / "oceanengine-local-material" / "rules",
}


def _load_rule(domain: str, filename: str) -> dict:
    return rule_loader.load_rule_config(RULE_ROOTS[domain] / filename)


def _iter_rule_files():
    for domain, root in RULE_ROOTS.items():
        for path in sorted(root.glob("*.json")):
            if path.name == "index.json":
                continue
            spec = rule_loader.load_rule_config(path)
            if isinstance(spec.get("fields"), dict):
                yield domain, path.name, spec


def _clarification_field_label(field: str, field_rules: dict, owning_spec: dict) -> str:
    label = field_rules.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    labels = owning_spec.get("field_labels", {})
    if isinstance(labels, dict):
        configured_label = labels.get(field) or labels.get(field.split(".")[-1].replace("[]", ""))
        if isinstance(configured_label, str) and configured_label.strip():
            return configured_label.strip()
    return field


def _static_enum_cases():
    cases = []
    for domain, filename, spec in _iter_rule_files():
        for field, rules in spec.get("fields", {}).items():
            if not isinstance(rules, dict):
                continue
            if rules.get("enum") or rules.get("item_enum"):
                cases.append((domain, filename, "fields", field, rules))

        batch_spec = spec.get("batch_item")
        if not isinstance(batch_spec, dict):
            continue
        for field, rules in batch_spec.get("fields", {}).items():
            if not isinstance(rules, dict):
                continue
            if rules.get("enum") or rules.get("item_enum"):
                cases.append((domain, filename, "batch_item", field, rules))
    return cases


STATIC_ENUM_CASES = _static_enum_cases()
STATIC_ENUM_CASE_IDS = [
    f"{domain}/{filename}:{location}.{field}"
    for domain, filename, location, field, _ in STATIC_ENUM_CASES
]


def _expected_choice_options(rules: dict) -> tuple[str, list[dict[str, str]]]:
    values = rules.get("enum")
    selection_mode = "single"
    if not values:
        values = rules.get("item_enum")
        selection_mode = "multiple"
    labels = rules.get("enum_labels") if isinstance(rules.get("enum_labels"), dict) else {}
    return selection_mode, [{"value": value, "label": str(labels.get(value) or value)} for value in values]


def _tool_result(output: str) -> dict:
    return json.loads(output)


def _project_tool_result(payload: dict, *, capability: str = "create-project", dry_run: bool = True) -> dict:
    return _tool_result(
        oceanengine_local_project_tool.func(
            capability=capability,
            payload_json=json.dumps(payload, ensure_ascii=False),
            dry_run=dry_run,
        )
    )


def _choice_control(result: dict) -> dict:
    return result["data"]["clarification"]["input_control"]


def _choice_values(result: dict) -> list:
    return [option["value"] for option in _choice_control(result)["options"]]


def _assert_choice_values(result: dict, *, field: str, values: list) -> None:
    assert result["success"] is False
    assert result["data"]["clarification"]["field"] == field
    assert _choice_control(result)["type"] == "choice_cards"
    assert _choice_values(result) == values


def _assert_first_error(result: dict, *, field: str, message_fragment: str) -> None:
    assert result["success"] is False
    assert result["errors"][0]["field"] == field
    assert message_fragment in result["errors"][0]["message"]
    assert message_fragment in result["data"]["user_visible_text"]


def _messages_for(errors: list[dict], field: str) -> list[str]:
    return [item["message"] for item in errors if item["field"] == field]


def _base_create_project_payload(**overrides) -> dict:
    payload = {
        "local_account_id": 1854708763953159,
        "name": "依赖选项过滤测试",
        "marketing_goal": "VIDEO_IMAGE",
        "local_delivery_scene": "PRODUCT_PAY",
        "ad_type": "GENERAL",
        "schedule_type": "START_TO_END",
        "start_time": "2026-05-10",
        "end_time": "2026-05-13",
        "bid_type": "SMART",
        "budget_mode": "BUDGET_MODE_DAY",
        "budget": 18000,
        "audience": {"district": "ALL"},
        "is_set_peak_budget": False,
    }
    payload.update(overrides)
    return payload


def test_static_enum_case_inventory_covers_project_unit_and_material_rules():
    covered_domains = {domain for domain, *_ in STATIC_ENUM_CASES}

    assert covered_domains == {"project", "unit", "material"}
    assert any(location == "batch_item" for _, _, location, _, _ in STATIC_ENUM_CASES)
    assert len(STATIC_ENUM_CASES) >= 40


@pytest.mark.parametrize(
    ("domain", "filename", "location", "field", "rules"),
    STATIC_ENUM_CASES,
    ids=STATIC_ENUM_CASE_IDS,
)
def test_static_enum_clarification_options_are_derived_from_rules_only(domain, filename, location, field, rules):
    spec = _load_rule(domain, filename)
    owning_spec = spec["batch_item"] if location == "batch_item" else spec
    label = _clarification_field_label(field, rules, owning_spec)
    error_item = {
        "field": field,
        "message": f"{label}是什么值？",
    }
    if location == "batch_item":
        error_item["item_index"] = 0
        error_item["message"] = f"第 1 项{label}是什么值？"

    first = endpoint_runner._build_parameter_clarification(spec, [error_item])
    second = endpoint_runner._build_parameter_clarification(spec, [error_item])

    assert first == second
    assert first["field"] == field
    assert first["field_label"] == label
    assert first["input_control"]["type"] == "choice_cards"
    expected_mode, expected_options = _expected_choice_options(rules)
    assert first["input_control"]["selection_mode"] == expected_mode
    assert first["input_control"]["options"] == expected_options


@pytest.mark.parametrize(
    ("scene", "forbidden_value"),
    [
        pytest.param("CONTENT_HEAT", "SEARCHING", id="content-heat-forbids-searching-ad-type"),
        pytest.param("EXTERNAL", "SEARCHING", id="external-clue-forbids-searching-ad-type"),
    ],
)
def test_create_project_filters_search_ad_type_when_selected_scene_forbids_it(scene, forbidden_value):
    payload = {
        "local_account_id": 1854708763953159,
        "name": "单元类型依赖过滤测试",
        "marketing_goal": "VIDEO_IMAGE",
        "local_delivery_scene": scene,
    }

    result = _project_tool_result(payload)

    _assert_choice_values(result, field="ad_type", values=["GENERAL"])
    assert forbidden_value not in _choice_values(result)
    assert "搜索" not in result["data"]["user_visible_text"]


def test_create_project_filters_product_delivery_goal_when_scene_is_poi_recommend():
    payload = _base_create_project_payload(
        local_delivery_scene="POI_RECOMMEND",
    )
    payload.pop("delivery_goal", None)

    result = _project_tool_result(payload)

    _assert_choice_values(result, field="delivery_goal", values=["POI"])
    assert "商品" not in result["data"]["user_visible_text"]


def test_create_project_missing_boolean_parameter_uses_yes_no_choice_cards():
    payload = _base_create_project_payload(
        delivery_goal="PRODUCT",
        product_id=123,
    )
    payload.pop("is_set_peak_budget", None)

    result = _project_tool_result(payload)

    _assert_choice_values(result, field="is_set_peak_budget", values=["true", "false"])
    assert result["data"]["clarification"]["input_control"]["options"] == [
        {"value": "true", "label": "是"},
        {"value": "false", "label": "否"},
    ]
    assert "可选：是、否" in result["data"]["user_visible_text"]


@pytest.mark.parametrize(
    ("payload", "field", "message_fragment"),
    [
        pytest.param(
            {
                "local_account_id": 1854708763953159,
                "name": "非法搜索单元组合",
                "marketing_goal": "VIDEO_IMAGE",
                "local_delivery_scene": "CONTENT_HEAT",
                "ad_type": "SEARCHING",
            },
            "ad_type",
            "不支持搜索单元",
            id="content-heat-selected-searching-ad-type",
        ),
        pytest.param(
            {
                "local_account_id": 1854708763953159,
                "name": "非法线索搜索组合",
                "marketing_goal": "VIDEO_IMAGE",
                "local_delivery_scene": "EXTERNAL",
                "ad_type": "SEARCHING",
            },
            "ad_type",
            "不支持搜索单元",
            id="external-clue-selected-searching-ad-type",
        ),
        pytest.param(
            _base_create_project_payload(
                local_delivery_scene="POI_RECOMMEND",
                delivery_goal="PRODUCT",
            ),
            "delivery_goal",
            "线下到店仅支持投放门店",
            id="poi-recommend-selected-product-delivery-goal",
        ),
    ],
)
def test_selected_invalid_dependency_combination_is_reported_before_followup_missing_fields(payload, field, message_fragment):
    result = _project_tool_result(payload)

    _assert_first_error(result, field=field, message_fragment=message_fragment)
    assert "投放日期类型是什么值" not in result["data"]["user_visible_text"]
    assert "商品投放ID是什么值" not in result["data"]["user_visible_text"]
    assert "clarification" not in result["data"]


def test_unit_conditional_required_and_forbidden_boundaries_for_status_second():
    spec = _load_rule("unit", "list-units.json")

    inactive_missing_second = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {"promotion_status_first": "PROMOTION_STATUS_DISABLE"},
        },
        spec,
    )
    enabled_missing_second = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {"promotion_status_first": "PROMOTION_STATUS_ENABLE"},
        },
        spec,
    )
    enabled_with_second = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {
                "promotion_status_first": "PROMOTION_STATUS_ENABLE",
                "promotion_status_second": "PROMOTION_STATUS_AUDIT",
            },
        },
        spec,
    )

    assert any("有效且必填" in message for message in _messages_for(inactive_missing_second, "filtering.promotion_status_second"))
    assert _messages_for(enabled_missing_second, "filtering.promotion_status_second") == []
    assert any("才支持传入" in message for message in _messages_for(enabled_with_second, "filtering.promotion_status_second"))


def test_material_anchor_type_conditional_required_boundaries():
    spec = _load_rule("material", "get-aweme-videos.json")

    poi_anchor_missing_pois = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "cursor": 1,
            "filtering": {"anchor_info": {"anchor_types": ["POI_ANCHOR"]}},
        },
        spec,
    )
    product_anchor_missing_products = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "cursor": 1,
            "filtering": {"anchor_info": {"anchor_types": ["PRODUCT_ANCHOR"]}},
        },
        spec,
    )
    all_anchor_missing_awemes = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "cursor": 1,
            "filtering": {"anchor_info": {"anchor_types": ["ALL_ANCHOR"]}},
        },
        spec,
    )

    assert _messages_for(poi_anchor_missing_pois, "filtering.anchor_info.poi_ids")
    assert _messages_for(product_anchor_missing_products, "filtering.anchor_info.product_ids")
    assert _messages_for(all_anchor_missing_awemes, "filtering.aweme_ids")


def test_project_at_least_one_rules_trigger_only_when_condition_matches():
    spec = _load_rule("project", "create-project.json")
    base_payload = _base_create_project_payload(
        local_delivery_scene="EXTERNAL",
        external_action="CLUE_ACQUISITION",
        delivery_package="DELIVERY_PACKAGE_NORMAL",
        intelligent_selection_mode="INTELLIGENT_SELECTION_MODE_ON",
        audience={"district": "ALL"},
    )

    no_custom_interest = validate_payload(base_payload, spec)
    custom_interest_without_interest_or_action = validate_payload(
        {
            **base_payload,
            "audience": {
                "district": "ALL",
                "customized_interest_action": "INTERESTACTION_CUSTOM",
            },
        },
        spec,
    )

    assert all("行为和兴趣至少需要传入一个" not in item["message"] for item in no_custom_interest)
    assert any("行为和兴趣至少需要传入一个" in item["message"] for item in custom_interest_without_interest_or_action)


def test_rule_matrix_has_no_uncovered_mutually_exclusive_rules():
    rules_with_mutually_exclusive = []
    for domain, filename, spec in _iter_rule_files():
        for rule in spec.get("constraints", []):
            if isinstance(rule, dict) and rule.get("type") == "mutually_exclusive":
                rules_with_mutually_exclusive.append(f"{domain}/{filename}")

    assert rules_with_mutually_exclusive == []


def test_batch_item_missing_enum_still_returns_single_choice_cards_question():
    result = _tool_result(
        oceanengine_local_unit_tool.func(
            capability="batch-update-unit-status",
            payload_json=json.dumps(
                {
                    "local_account_id": 1854708763953159,
                    "data": [{"promotion_id": 7636841423678226451}],
                },
                ensure_ascii=False,
            ),
            dry_run=True,
        )
    )

    assert result["success"] is False
    assert result["errors"] == [
        {
            "field": "opt_status",
            "item_index": 0,
            "message": "第 1 项目标操作是什么值？可选：启用单元、暂停单元。",
        }
    ]
    _assert_choice_values(result, field="opt_status", values=["ENABLE", "PAUSED"])
    assert result["data"]["clarification"]["input_control"]["options"] == [
        {"value": "ENABLE", "label": "启用单元"},
        {"value": "PAUSED", "label": "暂停单元"},
    ]
    assert result["data"]["user_visible_text"] == "第 1 项目标操作是什么值？可选：启用单元、暂停单元。"


def test_material_missing_static_enum_uses_choice_cards_without_platform_data():
    result = _tool_result(
        oceanengine_local_material_tool.func(
            runtime=_empty_runtime(),
            capability="upload-image",
            payload_json=json.dumps(
                {
                    "local_account_id": 1854708763953159,
                    "image_file_path": "/tmp/oceanengine-test.png",
                    "image_signature": "1234567890abcdef1234567890abcdef",
                    "is_aigc": False,
                },
                ensure_ascii=False,
            ),
            dry_run=True,
        )
    )

    _assert_choice_values(result, field="upload_type", values=["UPLOAD_BY_FILE"])
    assert result["data"]["clarification"]["input_control"] == {
        "type": "choice_cards",
        "selection_mode": "single",
        "options": [{"value": "UPLOAD_BY_FILE", "label": "本地文件上传"}],
    }
    assert result["data"]["user_visible_text"] == "上传方式是什么值？可选：本地文件上传。"


def test_dynamic_product_candidate_options_remain_platform_driven_not_static_enum():
    raw_products = {
        "code": 0,
        "message": "OK",
        "data": {
            "products": [
                {"productId": 882101, "productName": "平台实时候选A"},
                {"productId": 882102, "productName": "平台实时候选B"},
            ],
            "pageInfo": {"page": 1, "pageSize": 20, "totalNumber": 2, "totalPage": 1},
        },
        "requestId": "req-dynamic-products",
    }
    payload = _base_create_project_payload(delivery_goal="PRODUCT")
    payload.pop("product_id", None)

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={
            "tool_name": "nacos-mcp-router_use_tool:localProductGet",
            "raw": raw_products,
            "request_id": "req-dynamic-products",
        },
    ):
        result = run_oceanengine_local_project("create-project", payload, dry_run=False)

    _assert_choice_values(result, field="product_id", values=[882101, 882102])
    assert result["data"]["clarification"]["input_control"]["options"] == [
        {"value": 882101, "label": "平台实时候选A", "metadata": {"product_id": 882101, "product_name": "平台实时候选A"}},
        {"value": 882102, "label": "平台实时候选B", "metadata": {"product_id": 882102, "product_name": "平台实时候选B"}},
    ]
    visible_text = result["data"]["user_visible_text"]
    assert "商品投放ID是什么值？" in visible_text
    assert "平台实时候选A" in visible_text
    assert "882101" in visible_text
    assert "平台实时候选B" in visible_text
    assert "882102" in visible_text
    assert "请回复一个候选 ID 或名称" in visible_text
    product_field_rules = _load_rule("project", "create-project.json")["fields"]["product_id"]
    assert "enum" not in product_field_rules
    assert "item_enum" not in product_field_rules


def test_multiple_dynamic_choice_cards_user_visible_text_allows_multiple_answers():
    visible = _agent_visible_result(
        {
            "success": False,
            "message": "参数校验失败，请根据中文提示补充或修改后重试。本次不会调用 MCP。",
            "data": {
                "clarification": {
                    "version": "v1",
                    "reason": "missing_required_parameter",
                    "field": "poi_ids",
                    "field_label": "门店",
                    "question": "请选择可投门店。",
                    "input_control": {
                        "type": "choice_cards",
                        "selection_mode": "multiple",
                        "options": [
                            {
                                "value": 901,
                                "label": "人民广场店",
                                "description": "上海市黄浦区",
                                "metadata": {"poi_id": 901},
                            },
                            {
                                "value": 902,
                                "label": "徐家汇店",
                                "metadata": {"poi_id": 902},
                            },
                        ],
                    },
                }
            },
            "errors": [{"field": "poi_ids", "message": "请选择可投门店。"}],
        }
    )

    visible_text = visible["data"]["user_visible_text"]
    assert "请选择可投门店。" in visible_text
    assert "人民广场店" in visible_text
    assert "901" in visible_text
    assert "上海市黄浦区" in visible_text
    assert "徐家汇店" in visible_text
    assert "902" in visible_text
    assert "请回复多个候选 ID 或名称" in visible_text


def test_dynamic_candidate_query_is_not_attempted_for_static_material_enum():
    with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint") as invoke_endpoint:
        result = run_oceanengine_local_material(
            "upload-image",
            {
                "local_account_id": 1854708763953159,
                "image_file_path": "/tmp/oceanengine-test.png",
                "image_signature": "1234567890abcdef1234567890abcdef",
                "is_aigc": False,
            },
            dry_run=True,
        )

    invoke_endpoint.assert_not_called()
    _assert_choice_values(result, field="upload_type", values=["UPLOAD_BY_FILE"])
