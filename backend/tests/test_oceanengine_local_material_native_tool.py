import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from deerflow.config.paths import Paths

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIAL_SKILL_ROOT = REPO_ROOT / "skills" / "custom" / "oceanengine-local-material"
MATERIAL_RULES_ROOT = MATERIAL_SKILL_ROOT / "rules"


def _empty_runtime():
    return SimpleNamespace(state={"messages": []})


def test_oceanengine_local_material_native_tool_dry_run_routes_capability():
    from tools.oceanengine_local_material import run_oceanengine_local_material

    result = run_oceanengine_local_material(
        capability="get-library-videos",
        payload={"local_account_id": 1854708763953159, "filtering": {}, "page": 1, "page_size": 20},
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["execution_source"] == "deerflow-native-tool"
    assert result["data"]["business_tool_name"] == "oceanengine_local_material"
    assert result["data"]["mcp_server_name"] == "platform-agent-biz"
    assert result["data"]["mcp_tool_name"] == "localFileVideoGet"
    assert "获取素材库视频" in result["data"]["user_visible_text"]


@pytest.mark.parametrize(
    ("capability", "display_text", "raw_result", "mcp_tool_name", "forbidden_values"),
    [
        (
            "get-library-videos",
            "视频ID：video-1\n素材名称：测试视频\n素材类型：短视频/图文",
            {
                "code": 0,
                "data": {
                    "videoId": "video-1",
                    "marketingGoal": "VIDEO_IMAGE",
                    "localDeliveryScene": "PRODUCT_PAY",
                },
                "requestId": "req-video-get",
            },
            "localFileVideoGet",
            ("videoId", "marketingGoal", "localDeliveryScene", "VIDEO_IMAGE", "PRODUCT_PAY"),
        ),
        (
            "upload-image",
            "图片ID：image-1\n上传状态：成功",
            {
                "code": 0,
                "data": {
                    "imageId": "image-1",
                    "imageMode": "IMAGE_MODE_LARGE",
                    "downloadUrl": "https://example.com/raw-image.png",
                },
                "requestId": "req-image-upload",
            },
            "localImageUpload",
            ("imageId", "imageMode", "downloadUrl", "IMAGE_MODE_LARGE", "https://example.com/raw-image.png"),
        ),
    ],
)
def test_oceanengine_local_material_tool_hides_raw_result_from_agent_visible_output(capability, display_text, raw_result, mcp_tool_name, forbidden_values):
    from tools.oceanengine_local_material import oceanengine_local_material_tool

    with patch(
        "tools.oceanengine_local_material.run_oceanengine_local_material",
        return_value={
            "success": True,
            "message": "素材管理接口 调用完成。",
            "data": {
                "result": raw_result,
                "display_text": display_text,
                "diagnostics": {
                    "unmapped_response_fields": [
                        {"path": "data.rawField", "value": forbidden_values[-1]},
                    ]
                },
                "execution_source": "deerflow-native-tool",
                "business_tool_name": "oceanengine_local_material",
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": mcp_tool_name,
            },
            "errors": [],
            "tool_name": f"nacos-mcp-router_use_tool:{mcp_tool_name}",
            "request_id": raw_result["requestId"],
            "retry_count": 0,
        },
    ):
        output = oceanengine_local_material_tool.func(
            runtime=_empty_runtime(),
            capability=capability,
            payload_json=json.dumps({"local_account_id": 1854708763953159}, ensure_ascii=False),
            dry_run=False,
        )

    result = json.loads(output)
    data = result["data"]
    assert "result" not in data
    assert "diagnostics" not in data
    assert data["raw_result_omitted"] is True
    assert data["diagnostics_omitted"] is True
    assert data["user_visible_text"] == display_text
    for leaked in forbidden_values:
        assert leaked not in output


def test_oceanengine_local_material_native_tool_supports_bound_capabilities_with_guard_context():
    from tools import managed_mcp_guard
    from tools.oceanengine_local_material import run_oceanengine_local_material

    rules_index = json.loads((MATERIAL_RULES_ROOT / "index.json").read_text(encoding="utf-8"))
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
            rule = json.loads((MATERIAL_SKILL_ROOT / item["rule"]).read_text(encoding="utf-8"))
            if rule.get("mcp_missing"):
                result = run_oceanengine_local_material(capability=item["name"], payload={})
                assert result["success"] is False
                assert "当前 MCP 工具缺失" in result["message"]
                continue

            result = run_oceanengine_local_material(capability=item["name"], payload={})
            assert result["success"] is True
            assert result["data"]["business_tool_name"] == "oceanengine_local_material"
            assert result["data"]["mcp_tool_name"] == rule["mcp"]["tool"]

    assert len(observed) == 7
    assert all(allowed for _, _, allowed in observed)


def test_upload_video_resolves_current_thread_attachment_to_host_path(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    video_file = uploads_dir / "demo.mp4"
    video_file.write_bytes(b"video")
    observed_payloads = []

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        observed_payloads.append(payload)
        return {
            "success": True,
            "message": "ok",
            "data": {
                "path": spec["path"],
                "payload": payload,
                "result": {
                    "code": 0,
                    "message": "OK",
                    "data": {
                        "material_id": 1001,
                        "video_id": "video-1001",
                    },
                },
            },
            "errors": [],
            "tool_name": "platform-agent-biz:localFileVideoUpload",
            "request_id": "req-upload-video",
        }

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint),
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_file_path": "/mnt/user-data/uploads/demo.mp4",
                "video_file_size_bytes": 5,
            },
            thread_id="thread-1",
        )

    assert result["success"] is True
    assert observed_payloads
    assert observed_payloads[0]["video_file_path"] == str(video_file)


def test_upload_video_confirms_java_text_mcp_result(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    video_file = uploads_dir / "java-text.mp4"
    video_file.write_bytes(b"video")

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        return {
            "success": True,
            "message": "上传视频 调用完成。",
            "data": {
                "result": [
                    {
                        "type": "text",
                        "text": "\n".join(
                            [
                                "OceanengineResult(code=0, msg=请求成功, data=class LocalFileVideoUploadV30Response {",
                                "    materialId: 7638899784782987274",
                                "    videoId: v02033g10000d81d5saljht3dkuks82g",
                                "})",
                            ]
                        ),
                    }
                ],
                "path": spec["path"],
                "title": spec["title"],
            },
            "errors": [],
            "tool_name": "platform-agent-biz:localFileVideoUpload",
            "request_id": None,
        }

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint),
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "java-text.mp4",
                "video_file_path": "/mnt/user-data/uploads/java-text.mp4",
                "video_file_size_bytes": 5,
            },
            thread_id="thread-1",
        )

    assert result["success"] is True
    assert result["data"]["upload_result_status"] == "uploaded"
    assert "7638899784782987274" in result["data"]["user_visible_text"]
    assert "v02033g10000d81d5saljht3dkuks82g" in result["data"]["user_visible_text"]
    assert "未返回可确认的素材结果" not in result["data"]["user_visible_text"]


def test_upload_video_platform_failure_does_not_leak_host_path(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    video_file = uploads_dir / "demo.mp4"
    video_file.write_bytes(b"video")

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        host_path = payload["video_file_path"]
        return {
            "success": False,
            "message": f"平台返回失败原因：videoFilePath 对应文件不存在: {host_path}",
            "data": {"path": spec["path"]},
            "errors": [{"field": "mcp", "message": f"videoFilePath 对应文件不存在: {host_path}"}],
            "tool_name": "platform-agent-biz:localFileVideoUpload",
            "request_id": None,
        }

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint),
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_file_path": "/mnt/user-data/uploads/demo.mp4",
            },
            thread_id="thread-1",
        )

    serialized = json.dumps(result, ensure_ascii=False)
    assert str(video_file) not in serialized
    assert str(uploads_dir) not in serialized
    assert "当前对话附件文件" in result["data"]["user_visible_text"]


def test_upload_video_duplicate_mcp_result_says_material_already_uploaded(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    video_file = uploads_dir / "same-content.mp4"
    video_file.write_bytes(b"video")

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        return {
            "success": True,
            "message": "上传视频 调用完成。",
            "data": {
                "result": {
                    "code": 0,
                    "message": "素材已上传，返回已有素材。",
                    "data": {
                        "material_id": 7638854171928641579,
                        "video_id": "v03033g10000d81airaljht0lv31ge5g",
                    },
                },
                "display_text": "视频ID：v03033g10000d81airaljht0lv31ge5g\n素材id：7638854171928641579",
                "path": spec["path"],
                "title": spec["title"],
            },
            "errors": [],
            "tool_name": "platform-agent-biz:localFileVideoUpload",
            "request_id": "req-duplicate-upload",
        }

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint),
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "same-content.mp4",
                "video_file_path": "/mnt/user-data/uploads/same-content.mp4",
            },
            thread_id="thread-1",
        )

    assert result["success"] is True
    assert result["data"]["user_visible_text"].startswith("素材已上传")
    assert "7638854171928641579" in result["data"]["user_visible_text"]
    assert "v03033g10000d81airaljht0lv31ge5g" in result["data"]["user_visible_text"]
    assert "新增成功" not in result["data"]["user_visible_text"]


def test_upload_video_weak_mcp_result_does_not_fabricate_success(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    video_file = uploads_dir / "uncertain.mp4"
    video_file.write_bytes(b"video")

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        return {
            "success": True,
            "message": "上传视频 调用完成。",
            "data": {
                "result": {"code": 0, "message": "OK", "data": {}},
                "path": spec["path"],
                "title": spec["title"],
            },
            "errors": [],
            "tool_name": "platform-agent-biz:localFileVideoUpload",
            "request_id": "req-weak-upload",
        }

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint", side_effect=fake_run_endpoint),
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "uncertain.mp4",
                "video_file_path": "/mnt/user-data/uploads/uncertain.mp4",
            },
            thread_id="thread-1",
        )

    assert result["success"] is False
    assert "未返回可确认的素材结果" in result["data"]["user_visible_text"]
    assert "素材已上传" not in result["data"]["user_visible_text"]
    assert "上传成功" not in result["data"]["user_visible_text"]
    assert "materialId" not in json.dumps(result, ensure_ascii=False)
    assert "videoId" not in json.dumps(result, ensure_ascii=False)


def test_upload_video_virtual_attachment_requires_thread_id():
    from tools.oceanengine_local_material import run_oceanengine_local_material

    with patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint") as run_endpoint:
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_file_path": "/mnt/user-data/uploads/demo.mp4",
            },
        )

    assert result["success"] is False
    assert "当前对话" in result["data"]["user_visible_text"]
    run_endpoint.assert_not_called()


def test_upload_video_rejects_non_current_attachment_path():
    from tools.oceanengine_local_material import run_oceanengine_local_material

    with patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint") as run_endpoint:
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_file_path": "/mnt/user-data/uploads/../demo.mp4",
            },
            thread_id="thread-1",
        )

    assert result["success"] is False
    assert "当前对话附件" in result["data"]["user_visible_text"]
    run_endpoint.assert_not_called()


def test_upload_video_rejects_attachment_size_mismatch(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "demo.mp4").write_bytes(b"video")

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint") as run_endpoint,
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "demo.mp4",
                "video_file_path": "/mnt/user-data/uploads/demo.mp4",
                "video_file_size_bytes": 999,
            },
            thread_id="thread-1",
        )

    assert result["success"] is False
    assert result["errors"][0]["field"] == "video_file_size_bytes"
    assert "大小" in result["data"]["user_visible_text"]
    assert str(uploads_dir) not in result["data"]["user_visible_text"]
    run_endpoint.assert_not_called()


def test_upload_video_rejects_attachment_filename_mismatch(tmp_path):
    from tools.oceanengine_local_material import run_oceanengine_local_material

    paths = Paths(tmp_path)
    uploads_dir = paths.sandbox_uploads_dir("thread-1", user_id="user-1")
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "demo.mp4").write_bytes(b"video")

    with (
        patch("tools.oceanengine_local_material.get_paths", return_value=paths),
        patch("tools.oceanengine_local_material.get_effective_user_id", return_value="user-1"),
        patch("tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint") as run_endpoint,
    ):
        result = run_oceanengine_local_material(
            capability="upload-video",
            payload={
                "local_account_id": 1854708763953159,
                "filename": "other.mp4",
                "video_file_path": "/mnt/user-data/uploads/demo.mp4",
            },
            thread_id="thread-1",
        )

    assert result["success"] is False
    assert "文件名" in result["data"]["user_visible_text"]
    assert str(uploads_dir) not in result["data"]["user_visible_text"]
    run_endpoint.assert_not_called()


def test_oceanengine_local_material_native_tool_does_not_add_skill_scripts_path_to_sys_path():
    from tools.oceanengine_local_material import _skill_root, run_oceanengine_local_material

    material_scripts_path = str(_skill_root() / "scripts")
    project_scripts_path = str(_skill_root().parent / "oceanengine-local-project" / "scripts")
    original_sys_path = list(sys.path)
    sys.path[:] = [path for path in sys.path if path not in {material_scripts_path, project_scripts_path}]

    try:
        with patch(
            "tools.oceanengine_local_project_runtime.endpoint_runner.run_endpoint",
            return_value={
                "success": True,
                "message": "ok",
                "data": {"path": "/open_api/v3.0/local/file/video/get/"},
                "errors": [],
                "tool_name": "nacos-mcp-router_use_tool:localFileVideoGet",
                "request_id": "req-material-no-skill-scripts",
            },
        ):
            result = run_oceanengine_local_material(
                capability="get-library-videos",
                payload={"local_account_id": 1854708763953159, "filtering": {}, "page": 1, "page_size": 20},
                dry_run=True,
            )
    finally:
        sys.path[:] = original_sys_path

    assert result["success"] is True
    assert material_scripts_path not in sys.path
    assert project_scripts_path not in sys.path


def test_managed_mcp_guard_blocks_direct_material_router_call():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    with pytest.raises(PermissionError, match="oceanengine_local_material"):
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localFileVideoGet",
                "params": "{}",
            },
        )


def test_managed_mcp_guard_covers_all_bound_oceanengine_local_material_tools():
    from tools.managed_mcp_guard import allow_managed_mcp_calls, guard_managed_mcp_tool_call

    rules_index = json.loads((MATERIAL_RULES_ROOT / "index.json").read_text(encoding="utf-8"))

    for item in rules_index["capabilities"]:
        rule = json.loads((MATERIAL_SKILL_ROOT / item["rule"]).read_text(encoding="utf-8"))
        if rule.get("mcp_missing"):
            continue
        arguments = {
            "mcp_server_name": rule["mcp"]["server"],
            "mcp_tool_name": rule["mcp"]["tool"],
            "params": "{}",
        }

        with pytest.raises(PermissionError, match="oceanengine_local_material"):
            guard_managed_mcp_tool_call(tool_name="nacos-mcp-router_use_tool", arguments=arguments)

        with allow_managed_mcp_calls("oceanengine_local_material"):
            guard_managed_mcp_tool_call(tool_name="nacos-mcp-router_use_tool", arguments=arguments)


def test_config_example_registers_oceanengine_local_material_business_tool():
    config = REPO_ROOT / "config.example.yaml"

    content = config.read_text(encoding="utf-8")

    assert "name: oceanengine_local_material" in content
    assert "use: tools.oceanengine_local_material:oceanengine_local_material_tool" in content


def test_oceanengine_local_material_tool_description_defers_project_create_flow():
    from tools.oceanengine_local_material import oceanengine_local_material_tool

    description = oceanengine_local_material_tool.description

    assert "创建本地推项目" in description
    assert "oceanengine_local_project_create_flow" in description
    assert "不要先用本素材工具" in description


def test_oceanengine_local_material_tool_blocks_create_flow_context_before_mcp():
    from tools.oceanengine_local_material import oceanengine_local_material_tool

    runtime = SimpleNamespace(
        state={
            "messages": [
                HumanMessage(
                    content="创建本地推投流项目：投手张三，本地推账户1854708763953159，营销场景短视频/图文，投放目标线下到店，单元类型通投，视频从素材库选择。"
                )
            ]
        }
    )

    with patch("tools.oceanengine_local_material.run_oceanengine_local_material") as material_runner:
        output = oceanengine_local_material_tool.func(
            capability="get-library-videos",
            payload_json=json.dumps({"local_account_id": 1854708763953159}, ensure_ascii=False),
            dry_run=False,
            runtime=runtime,
        )

    material_runner.assert_not_called()
    result = json.loads(output)
    assert result["success"] is False
    assert result["data"]["route_tool_preference"] == "oceanengine_local_project_create_flow"
    assert "创建项目流程应使用 oceanengine_local_project_create_flow" in result["data"]["agent_guidance"]


def test_oceanengine_local_material_tool_blocks_create_flow_context_from_object_state():
    from tools.oceanengine_local_material import oceanengine_local_material_tool

    runtime = SimpleNamespace(
        state=SimpleNamespace(
            messages=[
                HumanMessage(
                    content="创建本地推投流项目：投手张三，本地推账户1854708763953159，营销场景短视频/图文，投放目标线下到店，单元类型通投，视频从素材库选择。"
                )
            ]
        )
    )

    with patch("tools.oceanengine_local_material.run_oceanengine_local_material") as material_runner:
        output = oceanengine_local_material_tool.func(
            capability="get-library-videos",
            payload_json=json.dumps({"local_account_id": 1854708763953159}, ensure_ascii=False),
            dry_run=False,
            runtime=runtime,
        )

    material_runner.assert_not_called()
    result = json.loads(output)
    assert result["success"] is False
    assert result["data"]["route_tool_preference"] == "oceanengine_local_project_create_flow"


def test_configured_oceanengine_local_material_tool_path_resolves_from_backend_cwd():
    from deerflow.reflection.resolvers import resolve_variable

    resolved_tool = resolve_variable("tools.oceanengine_local_material:oceanengine_local_material_tool")

    assert resolved_tool.name == "oceanengine_local_material"


def test_old_deerflow_material_tool_path_is_not_available():
    module_name = ".".join(("deerflow", "tools", "oceanengine_local_material"))
    sys.modules.pop(module_name, None)

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
