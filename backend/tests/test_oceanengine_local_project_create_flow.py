import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _base_flow_payload(**overrides):
    payload = {
        "operator_name": "张三",
        "local_account_id": 1854708763953159,
        "name": "Codex创建项目流程测试",
        "marketing_goal": "VIDEO_IMAGE",
        "local_delivery_scene": "PRODUCT_PAY",
        "ad_type": "GENERAL",
        "delivery_goal": "PRODUCT",
        "product_id": 1840240933753866,
        "region_city_ids": [310000],
        "region_name": "上海",
        "audience_relation": "exclude",
        "budget": 100000,
        "bid": 15000,
        "selected_videos": [{"video_id": f"video-{index}", "material_id": 1000 + index} for index in range(10)],
    }
    payload.update(overrides)
    return payload


def test_create_flow_missing_operator_asks_single_question_without_calling_project_tool():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    payload = _base_flow_payload()
    payload.pop("operator_name")

    with patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_project") as project_tool:
        result = run_oceanengine_local_project_create_flow(payload, dry_run=False, today=date(2026, 5, 12))

    assert result["success"] is False
    assert result["errors"] == [{"field": "operator_name", "message": "投手姓名是什么值？"}]
    assert result["data"]["user_visible_text"] == "投手姓名是什么值？"
    project_tool.assert_not_called()


def test_create_flow_builds_project_payload_defaults_without_invented_fields():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    result = run_oceanengine_local_project_create_flow(
        _base_flow_payload(
            smart_targeting_expansion=False,
            search_bid_ratio=None,
        ),
        dry_run=True,
        today=date(2026, 5, 12),
    )

    assert result["success"] is True
    payload = result["data"]["project_payload"]
    assert payload["schedule_type"] == "FROM_NOW_ON"
    assert payload["budget_mode"] == "BUDGET_MODE_DAY"
    assert payload["is_set_peak_budget"] is False
    assert payload["audience"]["region"]["location_type"] == "HOME"
    assert payload["audience"]["region"]["city"] == [310000]
    assert payload["audience"]["region"]["region_ver"] == "2.3.2"
    assert payload["audience"]["gender"] == "NONE"
    assert payload["audience"]["age"] == [18, 55]
    assert payload["audience"]["hide_if_converted"] == "CUSTOMER"
    assert payload["audience"]["converted_time_duration"] == "THREE_MONTH"
    assert "operator_name" not in payload
    assert "smart_targeting_expansion" not in payload
    assert "search_bid_ratio" not in payload


def test_create_flow_defaults_bid_type_by_delivery_scene():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    poi_result = run_oceanengine_local_project_create_flow(
        _base_flow_payload(
            local_delivery_scene="POI_RECOMMEND",
            delivery_goal="POI",
            product_id=None,
            promotion_poi_ids=[1712695600134144],
            selected_videos=[{"video_id": "video-1"} for _ in range(3)],
        ),
        dry_run=True,
        today=date(2026, 5, 12),
    )
    external_result = run_oceanengine_local_project_create_flow(
        _base_flow_payload(
            local_delivery_scene="EXTERNAL",
            external_action="PRIVATE_MESSAGE",
            guide_page="PRIVATE_MESSAGE",
            selected_videos=[{"video_id": "video-1"} for _ in range(3)],
        ),
        dry_run=True,
        today=date(2026, 5, 12),
    )

    assert poi_result["data"]["project_payload"]["bid_type"] == "SMART"
    assert external_result["data"]["project_payload"]["bid_type"] == "MAX_CONVERSION"
    assert external_result["data"]["project_payload"]["external_action"] == "PRIVATE_MESSAGE"
    assert external_result["data"]["project_payload"]["local_asset_type"] == "LOCAL_ASSET_TYPE_AWEME_PAGE"
    assert external_result["data"]["project_payload"]["aigc_dynamic_creative_switch"] == "AIGC_DYNAMIC_CREATIVE_SWITCH_OFF"
    assert external_result["data"]["project_payload"]["audience"]["customized_interest_action"] == "INTERESTACTION_OFF"
    assert external_result["data"]["project_payload"]["audience"]["filter_aweme_abnormal_active"] == "FILTER_AWEME_ABNORMAL_ACTIVE_TYPE_ON"
    assert external_result["data"]["project_payload"]["audience"]["filter_aweme_fans_count"] == "FILTER_AWEME_FANS_COUNT_TYPE_OVER1000"


def test_create_flow_rejects_insufficient_product_pay_videos():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    result = run_oceanengine_local_project_create_flow(
        _base_flow_payload(selected_videos=[{"video_id": "video-1"} for _ in range(9)]),
        dry_run=True,
        today=date(2026, 5, 12),
    )

    assert result["success"] is False
    assert result["errors"][0]["field"] == "selected_videos"
    assert "团购成交需要选择 10 条视频" in result["data"]["user_visible_text"]


def test_create_flow_library_video_candidates_use_choice_cards():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    material_result = {
        "success": True,
        "message": "ok",
        "data": {
            "result": {
                "data": {
                    "video_list": [
                        {
                            "video_id": "video-1",
                            "material_id": 1001,
                            "video_name": "门店探店视频",
                            "duration": 12.5,
                            "poster_url": "https://example.test/poster.jpg",
                            "can_delivery": True,
                        }
                    ]
                }
            }
        },
        "errors": [],
    }

    with patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_material", return_value=material_result) as material_tool:
        result = run_oceanengine_local_project_create_flow(
            _base_flow_payload(selected_videos=[], select_library_videos=True),
            dry_run=False,
            today=date(2026, 5, 12),
        )

    material_tool.assert_called_once()
    assert result["success"] is False
    clarification = result["data"]["clarification"]
    assert clarification["field"] == "selected_videos"
    assert clarification["input_control"]["type"] == "choice_cards"
    assert clarification["input_control"]["selection_mode"] == "multiple"
    assert clarification["input_control"]["options"] == [
        {
            "value": "video-1",
            "label": "门店探店视频",
            "metadata": {
                "video_id": "video-1",
                "material_id": 1001,
                "video_name": "门店探店视频",
                "duration": 12.5,
                "poster_url": "https://example.test/poster.jpg",
                "can_delivery": True,
            },
        }
    ]
    assert "请回复视频候选 ID 或名称" in result["data"]["user_visible_text"]


def test_create_flow_uploads_only_user_authorized_video_files_before_project_payload():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    upload_result = {
        "success": True,
        "message": "ok",
        "data": {
            "result": {
                "data": {
                    "video_id": "uploaded-video-1",
                    "video_url": "https://example.test/video.mp4",
                    "video_signature": "sig-1",
                }
            }
        },
        "errors": [],
    }

    with patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_material", return_value=upload_result) as material_tool:
        result = run_oceanengine_local_project_create_flow(
            _base_flow_payload(
                local_delivery_scene="POI_RECOMMEND",
                delivery_goal="POI",
                product_id=None,
                promotion_poi_ids=[1712695600134144],
                audience_relation="target",
                selected_videos=[],
                video_file_paths=["/tmp/user-authorized-a.mp4", "/tmp/user-authorized-b.mp4", "/tmp/user-authorized-c.mp4"],
            ),
            dry_run=True,
            today=date(2026, 5, 12),
        )

    assert material_tool.call_count == 3
    assert [call.args[0] for call in material_tool.call_args_list] == ["upload-video", "upload-video", "upload-video"]
    assert [call.args[1]["video_file_path"] for call in material_tool.call_args_list] == [
        "/tmp/user-authorized-a.mp4",
        "/tmp/user-authorized-b.mp4",
        "/tmp/user-authorized-c.mp4",
    ]
    assert result["success"] is True
    assert [item["video_id"] for item in result["data"]["unit_plan"]["selected_videos"]] == [
        "uploaded-video-1",
        "uploaded-video-1",
        "uploaded-video-1",
    ]


def test_create_flow_does_not_guess_video_sources_when_missing_authorization():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    with patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_material") as material_tool:
        result = run_oceanengine_local_project_create_flow(
            _base_flow_payload(selected_videos=[]),
            dry_run=False,
            today=date(2026, 5, 12),
        )

    material_tool.assert_not_called()
    assert result["success"] is False
    assert result["errors"][0]["field"] == "selected_videos"
    assert "当前已选择 0 条" in result["data"]["user_visible_text"]


def test_create_flow_creates_unit_only_after_project_success():
    from tools.oceanengine_local_project_create_flow import run_oceanengine_local_project_create_flow

    project_result = {
        "success": True,
        "message": "created",
        "data": {"result": {"data": {"project_id": 88001}}},
        "errors": [],
    }
    unit_result = {
        "success": True,
        "message": "unit created",
        "data": {"result": {"data": {"unit_id": 99001}}},
        "errors": [],
    }

    with (
        patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_project", return_value=project_result) as project_tool,
        patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_unit", return_value=unit_result) as unit_tool,
    ):
        result = run_oceanengine_local_project_create_flow(
            _base_flow_payload(
                create_unit=True,
                local_delivery_scene="POI_RECOMMEND",
                delivery_goal="POI",
                product_id=None,
                promotion_poi_ids=[1712695600134144],
                audience_relation="target",
                selected_videos=[
                    {"video_id": "video-1", "cover_web_uri": "cover-1"},
                    {"video_id": "video-2", "cover_web_uri": "cover-2"},
                    {"video_id": "video-3", "cover_web_uri": "cover-3"},
                ],
            ),
            dry_run=False,
            today=date(2026, 5, 12),
        )

    project_tool.assert_called_once()
    unit_tool.assert_called_once()
    assert unit_tool.call_args.args[0] == "create-unit"
    unit_payload = unit_tool.call_args.args[1]
    assert unit_payload["project_id"] == 88001
    assert unit_payload["local_account_id"] == 1854708763953159
    assert unit_payload["name"] == "20260512上海定向18-55ZS"
    assert unit_payload["customer_material_list"][0]["video_material"]["video_id"] == "video-1"
    assert result["success"] is True
    assert result["data"]["project_result"]["success"] is True
    assert result["data"]["unit_result"]["success"] is True


def test_create_flow_default_unit_name_uses_current_date_region_audience_age_and_operator_initials():
    from tools.oceanengine_local_project_create_flow import build_default_unit_name

    assert build_default_unit_name(
        operator_name="张三",
        region_name="上海",
        audience_relation="exclude",
        age_label="18-55",
        today=date(2026, 5, 12),
    ) == "20260512上海排除18-55ZS"


def test_create_flow_tool_hides_internal_payload_and_tool_names_from_agent_visible_text():
    from tools.oceanengine_local_project_create_flow import oceanengine_local_project_create_flow_tool

    output = oceanengine_local_project_create_flow_tool.func(
        payload_json=json.dumps(_base_flow_payload(), ensure_ascii=False),
        dry_run=True,
    )

    result = json.loads(output)
    visible_text = result["data"]["user_visible_text"]
    assert "localProjectCreate" not in visible_text
    assert "oceanengine_local_project" not in visible_text
    assert "payload_json" not in visible_text
    assert "创建项目流程已生成执行计划" in visible_text


def test_create_flow_tool_failure_instructs_single_question_only():
    from tools.oceanengine_local_project_create_flow import oceanengine_local_project_create_flow_tool

    material_result = {
        "success": True,
        "message": "ok",
        "data": {"result": {"data": {"video_list": []}}},
        "errors": [],
    }

    with patch("tools.oceanengine_local_project_create_flow.run_oceanengine_local_material", return_value=material_result):
        output = oceanengine_local_project_create_flow_tool.func(
            payload_json=json.dumps(
                _base_flow_payload(selected_videos=[], select_library_videos=True),
                ensure_ascii=False,
            ),
            dry_run=False,
        )

    result = json.loads(output)
    assert result["success"] is False
    assert result["data"]["blocking_clarification_field"] == "selected_videos"
    assert result["data"]["single_question_only"] is True
    assert result["message"] == "未查询到可选择的视频素材，请先上传视频到素材库后再选择。"
    assert "reply_guidance" not in result["data"]
    assert "user_visible_text" not in output


def test_create_flow_tool_description_guides_agent_routing_from_chinese_request():
    from tools.oceanengine_local_project import oceanengine_local_project_tool
    from tools.oceanengine_local_project_create_flow import oceanengine_local_project_create_flow_tool

    create_flow_description = oceanengine_local_project_create_flow_tool.description
    project_description = oceanengine_local_project_tool.description

    assert "Use this tool first" in create_flow_description
    assert "投手" in create_flow_description
    assert "线下到店=POI_RECOMMEND" in create_flow_description
    assert "select_library_videos=true" in create_flow_description
    assert "use oceanengine_local_project_create_flow instead" in project_description


def test_create_flow_tool_is_registered_before_lower_level_project_tool():
    config = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
    tool_names = [tool["name"] for tool in config["tools"]]

    assert tool_names.index("oceanengine_local_project_create_flow") < tool_names.index("oceanengine_local_project")
