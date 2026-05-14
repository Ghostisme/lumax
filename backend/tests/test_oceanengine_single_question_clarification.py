import json
from pathlib import Path
from types import SimpleNamespace

from tools.oceanengine_local_material import oceanengine_local_material_tool
from tools.oceanengine_local_project import oceanengine_local_project_tool
from tools.oceanengine_local_unit import oceanengine_local_unit_tool

REPO_ROOT = Path(__file__).resolve().parents[2]


def _tool_result(output: str) -> dict:
    return json.loads(output)


def _empty_runtime():
    return SimpleNamespace(state={"messages": []})


def test_project_validation_failure_exposes_only_first_question():
    result = _tool_result(
        oceanengine_local_project_tool.func(
            capability="create-project",
            payload_json="{}",
            dry_run=True,
        )
    )

    assert result["success"] is False
    assert result["data"]["error_count"] > 1
    assert result["data"]["omitted_error_count"] == result["data"]["error_count"] - 1
    assert result["errors"] == [
        {
            "field": "local_account_id",
            "message": "本地推投放账户ID是什么值？",
        }
    ]
    assert result["data"]["user_visible_text"] == "本地推投放账户ID是什么值？"


def test_unit_validation_failure_exposes_only_first_question():
    result = _tool_result(
        oceanengine_local_unit_tool.func(
            capability="create-unit",
            payload_json="{}",
            dry_run=True,
        )
    )

    assert result["success"] is False
    assert result["data"]["error_count"] > 1
    assert result["data"]["omitted_error_count"] == result["data"]["error_count"] - 1
    assert result["errors"] == [
        {
            "field": "local_account_id",
            "message": "本地推投放账户ID是什么值？",
        }
    ]
    assert result["data"]["user_visible_text"] == "本地推投放账户ID是什么值？"


def test_material_validation_failure_exposes_only_first_question():
    result = _tool_result(
        oceanengine_local_material_tool.func(
            runtime=_empty_runtime(),
            capability="upload-video",
            payload_json="{}",
            dry_run=True,
        )
    )

    assert result["success"] is False
    assert result["data"]["error_count"] > 1
    assert result["data"]["omitted_error_count"] == result["data"]["error_count"] - 1
    assert result["errors"] == [
        {
            "field": "local_account_id",
            "message": "本地推账号ID是什么值？",
        }
    ]
    assert result["data"]["user_visible_text"] == "本地推账号ID是什么值？"


def test_material_mcp_failure_keeps_platform_diagnostic():
    result = _tool_result(
        oceanengine_local_material_tool.func(
            runtime=_empty_runtime(),
            capability="list-video-material-attributes",
            payload_json=json.dumps(
                {
                    "account_id": 1854708763953159,
                    "account_type": "LOCAL",
                    "filtering": {"material_ids": [1001]},
                    "page": 1,
                    "page_size": 20,
                },
                ensure_ascii=False,
            ),
            dry_run=False,
        )
    )

    assert result["success"] is False
    assert result["errors"] == [
        {
            "field": "mcp_tool_name",
            "message": "获取视频素材评估标签 当前未在 platform-agent-biz 暴露对应 MCP 工具，请补齐 MCP server 后再执行。",
        }
    ]
    assert result["data"]["user_visible_text"] == "获取视频素材评估标签 当前未在 platform-agent-biz 暴露对应 MCP 工具，请补齐 MCP server 后再执行。"


def test_oceanengine_skills_forbid_direct_multi_field_clarification():
    skill_paths = [
        REPO_ROOT / "skills/custom/oceanengine-local-project/SKILL.md",
        REPO_ROOT / "skills/custom/oceanengine-local-unit/SKILL.md",
        REPO_ROOT / "skills/custom/oceanengine-local-material/SKILL.md",
    ]

    for skill_path in skill_paths:
        text = skill_path.read_text(encoding="utf-8")
        assert "不得直接调用 `ask_clarification` 自行汇总多个缺失项" in text
        assert "不得追加其它未展示缺失项" in text
