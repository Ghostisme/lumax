import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
ENDPOINTS_ROOT = SCRIPTS_ROOT / "endpoints"
RULES_ROOT = SKILL_ROOT / "rules"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


EXPECTED_ENDPOINTS = [
    "create_unit",
    "update_unit",
    "list_units",
    "get_unit_detail",
    "batch_update_unit_status",
    "list_products_by_poi_ids",
    "batch_get_unit_reject_reasons",
]

EXPECTED_TOOLS = {
    "create-unit": "localUnitCreate",
    "update-unit": "localUnitUpdate",
    "list-units": "localUnitList",
    "get-unit-detail": "localUnitDetail",
    "batch-update-unit-status": "localUnitStatusBatchUpdate",
    "list-products-by-poi-ids": "localProductGetByPoiIds",
    "batch-get-unit-reject-reasons": "localPromotionRejectReasonBatchGet",
}

EXPECTED_RESPONSE_PATHS = {
    "create-unit": [
        "code",
        "message",
        "data",
        "data.promotion_id",
        "request_id",
    ],
    "update-unit": [
        "code",
        "message",
        "data",
        "request_id",
    ],
    "list-units": [
        "code",
        "message",
        "data",
        "data.promotion_list[]",
        "data.promotion_list[].project_id",
        "data.promotion_list[].local_account_id",
        "data.promotion_list[].ad_type",
        "data.promotion_list[].promotion_id",
        "data.promotion_list[].promotion_name",
        "data.promotion_list[].promotion_create_time",
        "data.promotion_list[].promotion_modify_time",
        "data.promotion_list[].promotion_status_first",
        "data.promotion_list[].promotion_status_second[]",
        "data.promotion_list[].learning_phase",
        "data.promotion_list[].aweme_id",
        "data.promotion_list[].aweme_name",
        "data.page_info",
        "data.page_info.page",
        "data.page_info.page_size",
        "data.page_info.total_number",
        "data.page_info.total_page",
        "request_id",
    ],
    "get-unit-detail": [
        "code",
        "message",
        "data",
        "data.promotion_id",
        "data.enable_graphic_delivery",
        "data.aweme_id",
        "data.video_hp_visibility",
        "data.live_material_type",
        "data.customer_material_list[]",
        "data.customer_material_list[].image_mode",
        "data.customer_material_list[].title_material",
        "data.customer_material_list[].title_material.title",
        "data.customer_material_list[].title_material.lego_material_id",
        "data.customer_material_list[].title_material.material_id",
        "data.customer_material_list[].video_material",
        "data.customer_material_list[].video_material.video_id",
        "data.customer_material_list[].video_material.lego_material_id",
        "data.customer_material_list[].video_material.material_id",
        "data.customer_material_list[].video_material.aweme_item_id",
        "data.customer_material_list[].video_material.image_mode",
        "data.customer_material_list[].video_material.video_duration",
        "data.customer_material_list[].video_material.video_height",
        "data.customer_material_list[].video_material.video_width",
        "data.customer_material_list[].video_material.video_play_url",
        "data.customer_material_list[].video_material.cover_image_height",
        "data.customer_material_list[].video_material.cover_image_width",
        "data.customer_material_list[].video_material.cover_web_uri",
        "data.customer_material_list[].video_material.cover_web_url",
        "data.procedural_material",
        "data.procedural_material.title_material_list[]",
        "data.procedural_material.title_material_list[].title",
        "data.procedural_material.title_material_list[].lego_material_id",
        "data.procedural_material.title_material_list[].material_id",
        "data.procedural_material.video_material_list[]",
        "data.procedural_material.video_material_list[].image_mode",
        "data.procedural_material.video_material_list[].video_id",
        "data.procedural_material.video_material_list[].lego_material_id",
        "data.procedural_material.video_material_list[].material_id",
        "data.procedural_material.video_material_list[].video_duration",
        "data.procedural_material.video_material_list[].video_height",
        "data.procedural_material.video_material_list[].video_width",
        "data.procedural_material.video_material_list[].video_play_url",
        "data.procedural_material.video_material_list[].cover_image_height",
        "data.procedural_material.video_material_list[].cover_image_width",
        "data.procedural_material.video_material_list[].cover_web_uri",
        "data.procedural_material.video_material_list[].cover_web_url",
        "data.procedural_material.video_material_list[].is_ff_see_setting",
        "data.procedural_material.carousel_material_list[]",
        "data.procedural_material.carousel_material_list[].carousel_id",
        "data.procedural_material.carousel_material_list[].image_list[]",
        "data.procedural_material.carousel_material_list[].image_list[].uri",
        "data.procedural_material.carousel_material_list[].image_list[].url",
        "data.procedural_material.carousel_material_list[].image_list[].height",
        "data.procedural_material.carousel_material_list[].image_list[].width",
        "data.procedural_material.carousel_material_list[].music",
        "data.procedural_material.carousel_material_list[].music.music_id",
        "data.procedural_material.carousel_material_list[].music.music_vid",
        "data.procedural_material.carousel_material_list[].music.music_url",
        "data.promotion_card_info",
        "data.promotion_card_info.product_name",
        "data.promotion_card_info.product_images[]",
        "data.promotion_card_info.product_images[].image_uri",
        "data.promotion_card_info.product_images[].image_url",
        "data.promotion_card_info.product_images[].height",
        "data.promotion_card_info.product_images[].width",
        "data.promotion_card_info.product_selling_points[]",
        "data.promotion_card_info.product_selling_points[].selling_point",
        "data.promotion_card_info.call_to_actions[]",
        "data.promotion_card_info.call_to_actions[].action",
        "data.promotion_card_info.enable_personal_call_to_action",
        "request_id",
    ],
    "batch-update-unit-status": [
        "code",
        "message",
        "data",
        "data.promotion_ids[]",
        "data.errors[]",
        "data.errors[].promotion_id",
        "data.errors[].error_message",
        "request_id",
    ],
    "list-products-by-poi-ids": [
        "code",
        "message",
        "data",
        "data.product_ids[]",
        "request_id",
    ],
    "batch-get-unit-reject-reasons": [
        "code",
        "message",
        "data",
        "data.list[]",
        "data.list[].promotion_id",
        "data.list[].material_reject[]",
        "data.list[].material_reject[].audit_platform",
        "data.list[].material_reject[].type",
        "data.list[].material_reject[].content",
        "data.list[].material_reject[].video_material",
        "data.list[].material_reject[].video_material.video_id",
        "data.list[].material_reject[].video_material.video_url",
        "data.list[].material_reject[].image_material[]",
        "data.list[].material_reject[].image_material[].web_url",
        "data.list[].material_reject[].image_material[].web_uri",
        "data.list[].material_reject[].image_material[].height",
        "data.list[].material_reject[].image_material[].width",
        "data.list[].material_reject[].reject_reason[]",
        "data.list[].material_reject[].suggestion[]",
        "request_id",
    ],
}

CREATE_UNIT_PAYLOAD = {
    "local_account_id": 1854708763953159,
    "project_id": 100,
    "name": "测试单元",
    "aweme_id": "12345",
    "enable_graphic_delivery": False,
    "live_material_type": "VIDEO",
    "customer_material_list": [
        {
            "image_mode": "IMAGE_MODE_VIDEO",
            "title_material": {"title": "测试标题标题"},
            "video_material": {"video_id": "v1", "cover_web_uri": "cover", "aweme_item_id": 123},
        }
    ],
    "procedural_material": {
        "title_material_list": [{"title": "测试标题标题"}],
        "video_material_list": [
            {
                "image_mode": "IMAGE_MODE_VIDEO",
                "video_id": "v1",
                "cover_web_uri": "cover",
                "is_ff_see_setting": "HIDE_VIDEO_ON_HP",
            }
        ],
    },
    "promotion_card_info": {
        "product_name": "测试卡片",
        "product_images": [{"image_uri": "image"}],
        "product_selling_points": [{"selling_point": "测试卖点"}],
        "call_to_actions": [{"action": "咨询"}],
        "enable_personal_call_to_action": False,
    },
    "video_hp_visibility": "HIDE_VIDEO_ON_HP",
}

MINIMAL_PAYLOADS = {
    "create_unit": CREATE_UNIT_PAYLOAD,
    "update_unit": {"local_account_id": 1854708763953159, "promotion_id": 1001},
    "list_units": {"local_account_id": 1854708763953159},
    "get_unit_detail": {"local_account_id": 1854708763953159, "promotion_id": 1001},
    "batch_update_unit_status": {
        "local_account_id": 1854708763953159,
        "data": [{"promotion_id": 1001, "opt_status": "ENABLE"}],
    },
    "list_products_by_poi_ids": {
        "local_account_id": 1854708763953159,
        "poi_ids": [1, 2],
    },
    "batch_get_unit_reject_reasons": {
        "local_account_id": 1854708763953159,
        "promotion_ids": [1001, 1002],
    },
}


class OceanEngineLocalUnitScriptsTest(unittest.TestCase):
    def test_each_official_endpoint_has_its_own_script(self):
        missing = [name for name in EXPECTED_ENDPOINTS if not (ENDPOINTS_ROOT / f"{name}.py").exists()]
        self.assertEqual([], missing)

    def test_rules_index_declares_each_official_unit_capability(self):
        index_path = RULES_ROOT / "index.json"
        self.assertTrue(index_path.exists(), "rules/index.json must exist")
        rules_index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual("oceanengine-local-unit", rules_index["skill"])
        capabilities = {item["name"]: item for item in rules_index["capabilities"]}
        self.assertEqual(set(EXPECTED_TOOLS), set(capabilities))

        for capability, expected_tool in EXPECTED_TOOLS.items():
            with self.subTest(capability=capability):
                entry = capabilities[capability]
                rule = json.loads((SKILL_ROOT / entry["rule"]).read_text(encoding="utf-8"))
                self.assertEqual(expected_tool, rule["mcp"]["tool"])
                self.assertEqual("platform-agent-biz", rule["mcp"]["server"])
                self.assertTrue((SKILL_ROOT / entry["reference"]).exists())
                self.assertTrue((SKILL_ROOT / entry["script"]).exists())

    def test_each_endpoint_loads_rule_file_declared_in_rules_index(self):
        rules_index = json.loads((RULES_ROOT / "index.json").read_text(encoding="utf-8"))
        capabilities = {item["script"]: item for item in rules_index["capabilities"]}

        for endpoint in EXPECTED_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                script = f"scripts/endpoints/{endpoint}.py"
                self.assertIn(script, capabilities)
                entry = capabilities[script]
                module = importlib.import_module(f"endpoints.{endpoint}")
                rule_file = getattr(module, "RULE_FILE", None)
                self.assertEqual(SKILL_ROOT / entry["rule"], Path(rule_file))
                rule_config = json.loads(Path(rule_file).read_text(encoding="utf-8"))
                self.assertEqual(entry["name"], rule_config["name"])
                self.assertEqual(entry["operation_type"], rule_config["operation_type"])

    def test_each_endpoint_accepts_minimal_valid_payload_in_dry_run(self):
        for endpoint, payload in MINIMAL_PAYLOADS.items():
            with self.subTest(endpoint=endpoint):
                module = importlib.import_module(f"endpoints.{endpoint}")
                result = module.run(payload, dry_run=True)
                self.assertTrue(result["success"], result)
                rule = json.loads(Path(module.RULE_FILE).read_text(encoding="utf-8"))
                self.assertEqual(rule["mcp"]["tool"], result["data"]["mcp_tool_name"])

    def test_rules_record_official_response_fields(self):
        rules_index = json.loads((RULES_ROOT / "index.json").read_text(encoding="utf-8"))
        capabilities = {item["name"]: item for item in rules_index["capabilities"]}

        for capability, expected_paths in EXPECTED_RESPONSE_PATHS.items():
            with self.subTest(capability=capability):
                rule = json.loads((SKILL_ROOT / capabilities[capability]["rule"]).read_text(encoding="utf-8"))
                response_fields = rule["output"].get("response_fields", [])
                actual_paths = [field.get("path") for field in response_fields]
                self.assertEqual(expected_paths, actual_paths)

    def test_references_include_official_response_field_sections(self):
        rules_index = json.loads((RULES_ROOT / "index.json").read_text(encoding="utf-8"))
        capabilities = {item["name"]: item for item in rules_index["capabilities"]}

        for capability, expected_paths in EXPECTED_RESPONSE_PATHS.items():
            with self.subTest(capability=capability):
                reference = (SKILL_ROOT / capabilities[capability]["reference"]).read_text(encoding="utf-8")
                self.assertIn("## 响应字段", reference)
                for path in expected_paths:
                    self.assertIn(f"`{path}`", reference)

    def test_create_unit_accepts_only_official_common_required_fields(self):
        module = importlib.import_module("endpoints.create_unit")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "project_id": 100,
                "name": "测试单元",
            },
            dry_run=True,
        )

        self.assertTrue(result["success"], result)

    def test_list_units_dry_run_builds_flat_mcp_payload(self):
        module = importlib.import_module("endpoints.list_units")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "filtering": {
                    "promotion_ids": [123],
                    "promotion_status_first": "PROMOTION_STATUS_DISABLE",
                    "promotion_status_second": "AUDIT",
                    "promotion_create_time_start": "2026-05-01 00:00:00",
                    "promotion_create_time_end": "2026-05-01 23:59:59",
                },
                "page": 1,
                "page_size": 20,
            },
            dry_run=True,
        )

        self.assertTrue(result["success"], result)
        self.assertEqual("localUnitList", result["data"]["mcp_tool_name"])
        self.assertEqual(1854708763953159, result["data"]["payload"]["local_account_id"])
        self.assertEqual([123], result["data"]["payload"]["filtering"]["promotion_ids"])
        self.assertEqual("PROMOTION_STATUS_DISABLE", result["data"]["payload"]["filtering"]["promotion_status_first"])

    def test_list_units_requires_second_status_when_first_status_is_disabled(self):
        module = importlib.import_module("endpoints.list_units")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "filtering": {"promotion_status_first": "PROMOTION_STATUS_DISABLE"},
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("单元二级状态", joined_errors)
        self.assertIn("仅当 promotion_status_first=PROMOTION_STATUS_DISABLE", joined_errors)

    def test_batch_update_status_reports_missing_batch_item_in_chinese(self):
        module = importlib.import_module("endpoints.batch_update_unit_status")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "data": [{"promotion_id": 1001}],
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("第 1 项目标操作", joined_errors)
        self.assertIn("可选：启用单元、暂停单元", joined_errors)

    def test_create_unit_uses_request_wrapped_mcp_payload(self):
        module = importlib.import_module("endpoints.create_unit")

        observed = {}

        def fake_invoke(spec, payload):
            tool_name = spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool")
            if tool_name == "localUnitCreate":
                observed["spec"] = spec
                observed["payload"] = payload
                return {"raw": {"code": 0, "message": "ok", "data": {"promotionId": 1001}}, "tool_name": tool_name, "request_id": "req-unit"}
            if tool_name == "localUnitDetail":
                return {"raw": {"code": 0, "message": "ok", "data": {"data": {"promotionId": 1001}}}, "tool_name": tool_name, "request_id": "req-detail"}
            self.fail(f"unexpected tool: {tool_name}")

        with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint", side_effect=fake_invoke):
            result = module.run(
                CREATE_UNIT_PAYLOAD,
                dry_run=False,
            )

        self.assertTrue(result["success"], result)
        self.assertEqual("localUnitCreate", observed["spec"]["mcp"]["tool"])
        self.assertEqual("测试单元", observed["payload"]["name"])

    def test_create_unit_confirms_created_unit_by_detail_query(self):
        module = importlib.import_module("endpoints.create_unit")
        calls = []

        def fake_invoke(spec, payload):
            tool_name = spec.get("mcp_tool_name") or spec.get("mcp", {}).get("tool")
            calls.append((tool_name, payload))
            if tool_name == "localUnitCreate":
                return {
                    "raw": {"code": 0, "message": "ok", "data": {"promotionId": 1001}},
                    "tool_name": tool_name,
                    "request_id": "req-create",
                }
            if tool_name == "localUnitDetail":
                return {
                    "raw": {"code": 0, "message": "ok", "data": {"data": {"promotionId": 1001}}},
                    "tool_name": tool_name,
                    "request_id": "req-detail",
                }
            self.fail(f"unexpected tool: {tool_name}")

        with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint", side_effect=fake_invoke):
            result = module.run(CREATE_UNIT_PAYLOAD, dry_run=False)

        self.assertTrue(result["success"], result)
        self.assertEqual("localUnitCreate", calls[0][0])
        self.assertIn(("localUnitDetail", {"local_account_id": 1854708763953159, "promotion_id": 1001}), calls)

    def test_product_by_poi_allows_omitting_scene_because_official_doc_has_default(self):
        module = importlib.import_module("endpoints.list_products_by_poi_ids")
        result = module.run({"local_account_id": 1854708763953159, "poi_ids": [1, 2]}, dry_run=True)

        self.assertTrue(result["success"], result)
        self.assertNotIn("local_delivery_scene", result["data"]["payload"])

    def test_detail_rejects_invalid_type_in_chinese(self):
        module = importlib.import_module("endpoints.get_unit_detail")
        result = module.run({"local_account_id": 1854708763953159, "promotion_id": "bad"}, dry_run=True)

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("单元ID 类型不正确，应为数字", joined_errors)

    def test_batch_update_status_rejects_invalid_enum_and_empty_batch(self):
        module = importlib.import_module("endpoints.batch_update_unit_status")
        invalid_enum = module.run(
            {"local_account_id": 1854708763953159, "data": [{"promotion_id": 1001, "opt_status": "DELETE"}]},
            dry_run=True,
        )
        empty_batch = module.run({"local_account_id": 1854708763953159, "data": []}, dry_run=True)

        self.assertFalse(invalid_enum["success"])
        self.assertIn("ENABLE（启用单元）", "\n".join(error["message"] for error in invalid_enum["errors"]))
        self.assertFalse(empty_batch["success"])
        self.assertIn("批量单元状态列表 至少需要 1 项", "\n".join(error["message"] for error in empty_batch["errors"]))

    def test_batch_update_status_rejects_more_than_50_items(self):
        module = importlib.import_module("endpoints.batch_update_unit_status")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "data": [{"promotion_id": index, "opt_status": "ENABLE"} for index in range(51)],
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("最多支持 50 项", "\n".join(error["message"] for error in result["errors"]))

    def test_reject_reason_rejects_more_than_10_promotion_ids(self):
        module = importlib.import_module("endpoints.batch_get_unit_reject_reasons")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "promotion_ids": list(range(11)),
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("最多支持 10 项", "\n".join(error["message"] for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
