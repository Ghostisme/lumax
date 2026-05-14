import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_SKILL_ROOT = REPO_ROOT / "skills" / "custom" / "oceanengine-local-unit"
UNIT_RULES_ROOT = UNIT_SKILL_ROOT / "rules"


def test_oceanengine_local_unit_native_tool_dry_run_routes_capability():
    from tools.oceanengine_local_unit import run_oceanengine_local_unit

    result = run_oceanengine_local_unit(
        capability="get-unit-detail",
        payload={"local_account_id": 1854708763953159, "promotion_id": 1001},
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["execution_source"] == "deerflow-native-tool"
    assert result["data"]["business_tool_name"] == "oceanengine_local_unit"
    assert result["data"]["mcp_server_name"] == "platform-agent-biz"
    assert result["data"]["mcp_tool_name"] == "localUnitDetail"
    assert "获取单元详情" in result["data"]["user_visible_text"]


def test_oceanengine_local_unit_native_tool_uses_official_product_scene_default():
    from tools.oceanengine_local_unit import run_oceanengine_local_unit

    result = run_oceanengine_local_unit(
        capability="list-products-by-poi-ids",
        payload={"local_account_id": 1854708763953159, "poi_ids": [1712695600134144]},
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["business_tool_name"] == "oceanengine_local_unit"
    assert result["data"]["mcp_tool_name"] == "localProductGetByPoiIds"
    assert "local_delivery_scene" not in result["data"]["payload"]


def test_oceanengine_local_unit_native_tool_returns_chinese_validation_error_from_root_rules():
    from tools.oceanengine_local_unit import run_oceanengine_local_unit

    result = run_oceanengine_local_unit(
        capability="batch-get-unit-reject-reasons",
        payload={"local_account_id": 1854708763953159, "promotion_ids": list(range(11))},
        dry_run=True,
    )

    assert result["success"] is False
    assert result["data"]["business_tool_name"] == "oceanengine_local_unit"
    assert result["data"]["mcp_tool_name"] == "localPromotionRejectReasonBatchGet"
    assert "最多支持 10 项" in result["data"]["user_visible_text"]


def test_oceanengine_local_unit_native_tool_uses_response_fields_for_display_and_diagnostics():
    from tools.oceanengine_local_unit import run_oceanengine_local_unit

    raw_response = {
        "code": 0,
        "message": "ok",
        "data": {
            "promotionId": 1001,
            "enableGraphicDelivery": False,
            "unexpectedNewField": "needs-diagnostic",
        },
        "requestId": "req-detail",
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"raw": raw_response, "tool_name": "localUnitDetail", "request_id": "req-detail"},
    ):
        result = run_oceanengine_local_unit(
            capability="get-unit-detail",
            payload={"local_account_id": 1854708763953159, "promotion_id": 1001},
        )

    assert result["success"] is True
    assert "单元ID：1001" in result["data"]["display_text"]
    assert "是否开启团购卡：否" in result["data"]["display_text"]
    unmapped = result["data"]["diagnostics"]["unmapped_response_fields"]
    assert {"path": "data.unexpected_new_field", "value": "needs-diagnostic", "reason": "官方应答字段未记录或未配置为默认展示。"} in unmapped


def test_oceanengine_local_unit_create_confirmation_fails_on_detail_error():
    from tools.oceanengine_local_project_runtime import endpoint_runner, rule_loader

    spec = rule_loader.load_rule_config(UNIT_RULES_ROOT / "create-unit.json")
    payload = {
        "local_account_id": 1854708763953159,
        "project_id": 1001,
        "name": "测试单元",
    }

    def fake_invoke_endpoint(call_spec, call_payload):
        mcp_tool_name = call_spec.get("mcp_tool_name") or call_spec.get("mcp", {}).get("tool")
        if mcp_tool_name == "localUnitCreate":
            return {
                "raw": {"code": 0, "message": "ok", "data": {"promotionId": 2001}, "requestId": "req-create"},
                "tool_name": "localUnitCreate",
                "request_id": "req-create",
            }
        assert mcp_tool_name == "localUnitDetail"
        assert call_payload == {"local_account_id": 1854708763953159, "promotion_id": 2001}
        return {
            "raw": {"code": 40000, "message": "promotion not found", "data": None, "requestId": "req-detail"},
            "tool_name": "localUnitDetail",
            "request_id": "req-detail",
        }

    with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint", side_effect=fake_invoke_endpoint):
        result = endpoint_runner.run_endpoint(spec, payload)

    assert result["success"] is False
    assert result["errors"][0]["field"] == "confirmation"
    assert "code=40000" in result["errors"][0]["message"]


def test_oceanengine_local_unit_tool_hides_raw_result_from_agent_visible_output():
    from tools.oceanengine_local_unit import oceanengine_local_unit_tool

    with patch(
        "tools.oceanengine_local_unit.run_oceanengine_local_unit",
        return_value={
            "success": True,
            "message": "获取单元详情 调用完成。",
            "data": {
                "result": {
                    "code": 0,
                    "data": {
                        "promotionId": 1001,
                        "marketingGoal": "VIDEO_IMAGE",
                        "localDeliveryScene": "PRODUCT_PAY",
                    },
                    "requestId": "req-unit-detail",
                },
                "display_text": "单元ID：1001\n营销场景：短视频/图文\n转化目标：团购成交",
                "diagnostics": {
                    "unmapped_response_fields": [
                        {"path": "data.marketingGoal", "value": "VIDEO_IMAGE"},
                        {"path": "data.localDeliveryScene", "value": "PRODUCT_PAY"},
                    ]
                },
                "execution_source": "deerflow-native-tool",
                "business_tool_name": "oceanengine_local_unit",
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localUnitDetail",
            },
            "errors": [],
            "tool_name": "nacos-mcp-router_use_tool:localUnitDetail",
            "request_id": "req-unit-detail",
            "retry_count": 0,
        },
    ):
        output = oceanengine_local_unit_tool.func(
            capability="get-unit-detail",
            payload_json=json.dumps({"local_account_id": 1854708763953159, "promotion_id": 1001}, ensure_ascii=False),
            dry_run=False,
        )

    result = json.loads(output)
    data = result["data"]
    assert "result" not in data
    assert "diagnostics" not in data
    assert data["raw_result_omitted"] is True
    assert data["diagnostics_omitted"] is True
    assert data["user_visible_text"] == data["display_text"]
    for leaked in ("promotionId", "marketingGoal", "localDeliveryScene", "VIDEO_IMAGE", "PRODUCT_PAY"):
        assert leaked not in output


def test_oceanengine_local_unit_native_tool_supports_every_rules_index_capability_with_guard_context():
    from tools import managed_mcp_guard
    from tools.oceanengine_local_unit import run_oceanengine_local_unit

    rules_index = json.loads((UNIT_RULES_ROOT / "index.json").read_text(encoding="utf-8"))
    observed: list[tuple[str, str, bool]] = []

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        observed.append((spec["name"], spec["mcp"]["tool"], managed_mcp_guard.is_managed_mcp_call_allowed()))
        return {
            "success": True,
            "message": "ok",
            "data": {"path": spec["path"]},
            "errors": [],
            "tool_name": f"nacos-mcp-router_use_tool:{spec['mcp']['tool']}",
            "request_id": f"req-{spec['name']}",
        }

    with patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint):
        for item in rules_index["capabilities"]:
            result = run_oceanengine_local_unit(capability=item["name"], payload={})
            rule = json.loads((UNIT_SKILL_ROOT / item["rule"]).read_text(encoding="utf-8"))
            assert result["success"] is True
            assert result["data"]["business_tool_name"] == "oceanengine_local_unit"
            assert result["data"]["mcp_tool_name"] == rule["mcp"]["tool"]

    assert len(observed) == 7
    assert all(allowed for _, _, allowed in observed)


def test_oceanengine_local_unit_native_tool_does_not_add_skill_scripts_path_to_sys_path():
    from tools.oceanengine_local_unit import _skill_root, run_oceanengine_local_unit

    unit_scripts_path = str(_skill_root() / "scripts")
    project_scripts_path = str(_skill_root().parent / "oceanengine-local-project" / "scripts")
    original_sys_path = list(sys.path)
    sys.path[:] = [path for path in sys.path if path not in {unit_scripts_path, project_scripts_path}]

    try:
        with patch(
            "tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint",
            return_value={
                "success": True,
                "message": "ok",
                "data": {"path": "/open_api/v3.0/local/promotion/get/"},
                "errors": [],
                "tool_name": "nacos-mcp-router_use_tool:localUnitDetail",
                "request_id": "req-unit-no-skill-scripts",
            },
        ):
            result = run_oceanengine_local_unit(
                capability="get-unit-detail",
                payload={"local_account_id": 1854708763953159, "promotion_id": 1001},
                dry_run=True,
            )
    finally:
        sys.path[:] = original_sys_path

    assert result["success"] is True
    assert unit_scripts_path not in sys.path
    assert project_scripts_path not in sys.path


def test_managed_mcp_guard_blocks_direct_unit_router_call():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    with pytest.raises(PermissionError, match="oceanengine_local_unit"):
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localUnitCreate",
                "params": "{}",
            },
        )


def test_managed_mcp_guard_covers_all_oceanengine_local_unit_tools():
    from tools.managed_mcp_guard import allow_managed_mcp_calls, guard_managed_mcp_tool_call

    rules_index = json.loads((UNIT_RULES_ROOT / "index.json").read_text(encoding="utf-8"))

    for item in rules_index["capabilities"]:
        rule = json.loads((UNIT_SKILL_ROOT / item["rule"]).read_text(encoding="utf-8"))
        arguments = {
            "mcp_server_name": rule["mcp"]["server"],
            "mcp_tool_name": rule["mcp"]["tool"],
            "params": "{}",
        }

        with pytest.raises(PermissionError, match="oceanengine_local_unit"):
            guard_managed_mcp_tool_call(tool_name="nacos-mcp-router_use_tool", arguments=arguments)

        with allow_managed_mcp_calls("oceanengine_local_unit"):
            guard_managed_mcp_tool_call(tool_name="nacos-mcp-router_use_tool", arguments=arguments)


def test_config_example_registers_oceanengine_local_unit_business_tool():
    config = REPO_ROOT / "config.example.yaml"

    content = config.read_text(encoding="utf-8")

    assert "name: oceanengine_local_unit" in content
    assert "use: tools.oceanengine_local_unit:oceanengine_local_unit_tool" in content


def test_configured_oceanengine_local_unit_tool_path_resolves_from_backend_cwd():
    from deerflow.reflection.resolvers import resolve_variable

    resolved_tool = resolve_variable("tools.oceanengine_local_unit:oceanengine_local_unit_tool")

    assert resolved_tool.name == "oceanengine_local_unit"


def test_old_deerflow_unit_tool_path_is_not_available():
    module_name = ".".join(("deerflow", "tools", "oceanengine_local_unit"))
    sys.modules.pop(module_name, None)

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
