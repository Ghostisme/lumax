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
    "async_upload_local_video",
    "list_local_video_upload_tasks",
    "upload_video",
    "get_library_videos",
    "get_aweme_videos",
    "list_carousel_materials",
    "upload_image",
    "list_video_material_attributes",
]

EXPECTED_TOOLS = {
    "async-upload-local-video": "localFileUploadTaskCreate",
    "list-local-video-upload-tasks": "localFileVideoUploadTaskList",
    "upload-video": "localFileVideoUpload",
    "get-library-videos": "localFileVideoGet",
    "get-aweme-videos": "localFileVideoAwemeGet",
    "list-carousel-materials": "localFileCarouselList",
    "upload-image": "localImageUpload",
    "list-video-material-attributes": None,
}

EXPECTED_RESPONSE_PATHS = {
    "async-upload-local-video": [
        "code",
        "message",
        "data",
        "data.task_id",
        "request_id",
    ],
    "list-local-video-upload-tasks": [
        "code",
        "message",
        "data",
        "data.list[]",
        "data.list[].status",
        "data.list[].error_msg",
        "data.list[].create_time",
        "data.list[].task_id",
        "data.list[].video_info",
        "data.list[].video_info.video_id",
        "data.list[].video_info.material_id",
        "data.list[].video_info.size",
        "data.list[].video_info.video_signature",
        "data.list[].video_info.width",
        "data.list[].video_info.height",
        "data.list[].video_info.video_url",
        "data.list[].video_info.duration",
        "request_id",
    ],
    "upload-video": [
        "code",
        "message",
        "data",
        "data.video_id",
        "data.size",
        "data.width",
        "data.height",
        "data.video_url",
        "data.duration",
        "data.material_id",
        "data.video_signature",
        "request_id",
    ],
    "get-library-videos": [
        "code",
        "message",
        "data",
        "data.video_list[]",
        "data.video_list[].video_id",
        "data.video_list[].material_id",
        "data.video_list[].signature",
        "data.video_list[].video_name",
        "data.video_list[].video_url",
        "data.video_list[].poster_url",
        "data.video_list[].material_properties[]",
        "data.video_list[].image_mode",
        "data.video_list[].duration",
        "data.video_list[].source",
        "data.video_list[].create_time",
        "data.page_info",
        "data.page_info.page",
        "data.page_info.page_size",
        "data.page_info.total_page",
        "data.page_info.total_number",
        "request_id",
    ],
    "get-aweme-videos": [
        "code",
        "message",
        "data",
        "data.video_list[]",
        "data.video_list[].item_id",
        "data.video_list[].title",
        "data.video_list[].video_id",
        "data.video_list[].aweme_id",
        "data.video_list[].aweme_name",
        "data.video_list[].image_mode",
        "data.video_list[].duration",
        "data.video_list[].cover_image_url",
        "data.video_list[].aweme_video_url",
        "data.video_list[].not_delivery_reason[]",
        "data.video_list[].can_delivery",
        "data.video_list[].lego_material_id",
        "data.video_list[].video_width",
        "data.video_list[].video_heigh",
        "data.page_info",
        "data.page_info.cursor",
        "data.page_info.has_more",
        "request_id",
    ],
    "list-carousel-materials": [
        "code",
        "message",
        "data",
        "data.carousel_list[]",
        "data.carousel_list[].carousel_id",
        "data.carousel_list[].title",
        "data.carousel_list[].image_list[]",
        "data.carousel_list[].image_list[].uri",
        "data.carousel_list[].image_list[].url",
        "data.carousel_list[].image_list[].height",
        "data.carousel_list[].image_list[].width",
        "data.carousel_list[].music",
        "data.carousel_list[].music.music_id",
        "data.carousel_list[].music.music_vid",
        "data.carousel_list[].music.music_url",
        "data.carousel_list[].create_time",
        "data.page_info",
        "data.page_info.page",
        "data.page_info.page_size",
        "data.page_info.total_number",
        "data.page_info.total_page",
        "request_id",
    ],
    "upload-image": [
        "code",
        "message",
        "data",
        "data.id",
        "data.size",
        "data.width",
        "data.height",
        "data.url",
        "data.format",
        "data.signature",
        "data.material_id",
        "request_id",
    ],
    "list-video-material-attributes": [
        "code",
        "message",
        "data",
        "data.materials[]",
        "data.materials[].material_id",
        "data.materials[].ad_low_quality_suggestions[]",
        "data.materials[].ecp_low_quality_suggestions[]",
        "data.materials[].local_low_quality_suggestions[]",
        "data.materials[].is_ad_high_quality_material",
        "data.materials[].is_ad_low_quality_material",
        "data.materials[].is_ecp_high_quality_material",
        "data.materials[].is_ecp_low_quality_material",
        "data.materials[].is_local_high_quality_material",
        "data.materials[].is_local_low_quality_material",
        "data.materials[].is_first_publish_material",
        "data.materials[].is_inefficient_material",
        "data.materials[].is_carry_material",
        "data.materials[].is_similar_material",
        "data.materials[].is_similar_queue_material",
        "data.materials[].is_similar_expected_queue_material",
        "data.materials[].attributes_modify_time",
        "data.page",
        "data.page.page",
        "data.page.page_size",
        "data.page.total_count",
        "data.page.total_number",
        "request_id",
    ],
}

MINIMAL_PAYLOADS = {
    "async_upload_local_video": {
        "local_account_id": 1854708763953159,
        "filename": "demo.mp4",
        "video_url": "https://example.tos-cn-beijing.volces.com/demo.mp4",
    },
    "list_local_video_upload_tasks": {
        "local_account_id": 1854708763953159,
        "task_ids": [123456789],
    },
    "upload_video": {
        "local_account_id": 1854708763953159,
        "filename": "demo.mp4",
        "video_file_path": "/tmp/demo.mp4",
    },
    "get_library_videos": {
        "local_account_id": 1854708763953159,
        "filtering": {},
        "page": 1,
        "page_size": 20,
    },
    "get_aweme_videos": {
        "local_account_id": 1854708763953159,
        "cursor": "0",
        "filtering": {"anchor_info": {"anchor_types": ["ALL_ANCHOR"]}, "aweme_ids": [123456789]},
        "page_size": 20,
    },
    "list_carousel_materials": {
        "local_account_id": 1854708763953159,
        "page": 1,
        "page_size": 20,
    },
    "upload_image": {
        "local_account_id": 1854708763953159,
        "image_file_path": "/tmp/demo.jpg",
        "image_signature": "0123456789abcdef0123456789abcdef",
        "is_aigc": False,
        "upload_type": "UPLOAD_BY_FILE",
    },
}


class OceanEngineLocalMaterialScriptsTest(unittest.TestCase):
    def test_each_official_endpoint_has_its_own_script(self):
        missing = [name for name in EXPECTED_ENDPOINTS if not (ENDPOINTS_ROOT / f"{name}.py").exists()]
        self.assertEqual([], missing)

    def test_rules_index_declares_each_official_material_capability(self):
        index_path = RULES_ROOT / "index.json"
        self.assertTrue(index_path.exists(), "rules/index.json must exist")
        rules_index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual("oceanengine-local-material", rules_index["skill"])
        capabilities = {item["name"]: item for item in rules_index["capabilities"]}
        self.assertEqual(set(EXPECTED_TOOLS), set(capabilities))

        for capability, expected_tool in EXPECTED_TOOLS.items():
            with self.subTest(capability=capability):
                entry = capabilities[capability]
                rule = json.loads((SKILL_ROOT / entry["rule"]).read_text(encoding="utf-8"))
                self.assertEqual("platform-agent-biz", rule["mcp"]["server"])
                if expected_tool is None:
                    self.assertTrue(rule.get("mcp_missing"))
                    self.assertIsNone(rule["mcp"].get("tool"))
                else:
                    self.assertEqual(expected_tool, rule["mcp"]["tool"])
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

    def test_each_bound_endpoint_accepts_minimal_valid_payload_in_dry_run(self):
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

    def test_upload_video_uses_request_wrapped_file_path_payload(self):
        module = importlib.import_module("endpoints.upload_video")
        result = module.run(MINIMAL_PAYLOADS["upload_video"], dry_run=True)

        self.assertTrue(result["success"], result)
        self.assertEqual("localFileVideoUpload", result["data"]["mcp_tool_name"])
        self.assertEqual("/tmp/demo.mp4", result["data"]["payload"]["video_file_path"])

    def test_async_upload_rejects_non_tos_video_url_in_chinese(self):
        module = importlib.import_module("endpoints.async_upload_local_video")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_url": "https://example.com/demo.mp4",
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("连山云", joined_errors)
        self.assertIn("tos", joined_errors.lower())

    def test_upload_image_requires_signature_for_current_mcp_schema(self):
        module = importlib.import_module("endpoints.upload_image")
        payload = dict(MINIMAL_PAYLOADS["upload_image"])
        payload.pop("image_signature")

        result = module.run(payload, dry_run=True)

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("图片签名", joined_errors)

    def test_upload_video_rejects_unsupported_file_extension(self):
        module = importlib.import_module("endpoints.upload_video")
        payload = dict(MINIMAL_PAYLOADS["upload_video"])
        payload["video_file_path"] = "/tmp/demo.mov"

        result = module.run(payload, dry_run=True)

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("视频文件路径", joined_errors)
        self.assertIn("mp4", joined_errors)

    def test_upload_task_list_rejects_more_than_100_task_ids(self):
        module = importlib.import_module("endpoints.list_local_video_upload_tasks")
        result = module.run(
            {"local_account_id": 1854708763953159, "task_ids": list(range(101))},
            dry_run=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("上传任务ID列表 最多支持 100 项", "\n".join(error["message"] for error in result["errors"]))

    def test_aweme_videos_requires_poi_ids_for_poi_anchor(self):
        module = importlib.import_module("endpoints.get_aweme_videos")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "cursor": "0",
                "filtering": {"anchor_info": {"anchor_types": ["POI_ANCHOR"]}},
                "page_size": 20,
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("门店ID列表", joined_errors)
        self.assertIn("POI_ANCHOR", joined_errors)

    def test_aweme_videos_accepts_official_nested_poi_ids_for_poi_anchor(self):
        module = importlib.import_module("endpoints.get_aweme_videos")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "cursor": "0",
                "filtering": {
                    "anchor_info": {
                        "anchor_types": ["POI_ANCHOR"],
                        "poi_ids": [17909122334455],
                    }
                },
                "page_size": 20,
            },
            dry_run=True,
        )

        self.assertTrue(result["success"], result)

    def test_aweme_videos_requires_aweme_ids_for_all_anchor(self):
        module = importlib.import_module("endpoints.get_aweme_videos")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "cursor": "0",
                "filtering": {"anchor_info": {"anchor_types": ["ALL_ANCHOR"]}},
                "page_size": 20,
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("抖音号ID列表", joined_errors)
        self.assertIn("ALL_ANCHOR", joined_errors)

    def test_library_videos_rejects_unknown_material_source(self):
        module = importlib.import_module("endpoints.get_library_videos")
        result = module.run(
            {
                "local_account_id": 1854708763953159,
                "filtering": {"material_source": ["NOT_OFFICIAL"]},
                "page": 1,
                "page_size": 20,
            },
            dry_run=True,
        )

        self.assertFalse(result["success"])
        self.assertIn("素材来源", "\n".join(error["message"] for error in result["errors"]))

    def test_upload_video_rejects_filename_longer_than_official_limit(self):
        module = importlib.import_module("endpoints.upload_video")
        payload = dict(MINIMAL_PAYLOADS["upload_video"])
        payload["filename"] = f"{'a' * 256}.mp4"

        result = module.run(payload, dry_run=True)

        self.assertFalse(result["success"])
        self.assertIn("视频文件名 长度不能超过 255", "\n".join(error["message"] for error in result["errors"]))

    def test_carousel_rejects_page_product_over_10000_through_pydantic_constraint(self):
        module = importlib.import_module("endpoints.list_carousel_materials")
        result = module.run({"local_account_id": 1854708763953159, "page": 101, "page_size": 100}, dry_run=True)

        self.assertFalse(result["success"])
        joined_errors = "\n".join(error["message"] for error in result["errors"])
        self.assertIn("页码和每页数量的乘积不能大于 10000", joined_errors)

    def test_material_endpoint_uses_shared_pydantic_payload_model(self):
        validators = importlib.import_module("tools.oceanengine_local_project_runtime.validators")
        module = importlib.import_module("endpoints.get_library_videos")

        with patch.object(
            validators,
            "_build_pydantic_payload_model",
            wraps=validators._build_pydantic_payload_model,
        ) as build_model:
            result = module.run({"local_account_id": "bad", "filtering": {}}, dry_run=True)

        self.assertFalse(result["success"])
        build_model.assert_called()
        self.assertIn("Pydantic", Path(validators.__file__).read_text(encoding="utf-8"))
        self.assertNotIn("except ImportError", Path(validators.__file__).read_text(encoding="utf-8"))

    def test_missing_material_attributes_mcp_tool_returns_diagnostic_without_calling_mcp(self):
        module = importlib.import_module("endpoints.list_video_material_attributes")

        with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint") as invoke_endpoint:
            result = module.run(
                {
                    "account_id": 1854708763953159,
                    "account_type": "LOCAL",
                    "page": 1,
                    "page_size": 20,
                },
                dry_run=False,
            )

        self.assertFalse(result["success"])
        invoke_endpoint.assert_not_called()
        self.assertIn("当前 MCP 工具缺失", result["message"])


if __name__ == "__main__":
    unittest.main()
