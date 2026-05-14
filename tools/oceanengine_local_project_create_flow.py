"""OceanEngine local project create flow orchestration."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from typing import Any

from langchain.tools import tool

from tools.oceanengine_local_material import run_oceanengine_local_material
from tools.oceanengine_local_project import run_oceanengine_local_project
from tools.oceanengine_local_unit import run_oceanengine_local_unit

BUSINESS_TOOL_NAME = "oceanengine_local_project_create_flow"
PROJECT_CAPABILITY = "create-project"
MATERIAL_LIBRARY_CAPABILITY = "get-library-videos"
MATERIAL_UPLOAD_CAPABILITY = "upload-video"
UNIT_CREATE_CAPABILITY = "create-unit"

PROJECT_PAY_VIDEO_COUNT = 10
OTHER_MIN_VIDEO_COUNT = 3
OTHER_MAX_VIDEO_COUNT = 5

PROJECT_CREATE_FIELDS = {
    "ad_type",
    "aigc_dynamic_creative_switch",
    "audience",
    "audience_package_id",
    "bid",
    "bid_type",
    "budget",
    "budget_mode",
    "consult_aweme_uid",
    "delivery_goal",
    "delivery_package",
    "delivery_poi_mode",
    "end_time",
    "external_action",
    "hide_if_exists",
    "intelligent_selection_mode",
    "is_set_peak_budget",
    "local_account_id",
    "local_asset_type",
    "local_delivery_scene",
    "market_page_ids",
    "marketing_goal",
    "name",
    "product_id",
    "promotion_poi_ids",
    "schedule_time",
    "schedule_type",
    "start_time",
    "tool_pack_id",
}

CHINESE_INITIALS = {
    "张": "Z",
    "三": "S",
    "李": "L",
    "四": "S",
    "王": "W",
    "五": "W",
    "赵": "Z",
    "钱": "Q",
    "孙": "S",
    "周": "Z",
    "吴": "W",
    "郑": "Z",
    "陈": "C",
    "刘": "L",
    "杨": "Y",
    "黄": "H",
    "何": "H",
    "林": "L",
    "朱": "Z",
    "许": "X",
    "高": "G",
    "郭": "G",
    "马": "M",
    "胡": "H",
    "罗": "L",
    "梁": "L",
    "宋": "S",
    "唐": "T",
    "冯": "F",
    "谢": "X",
    "韩": "H",
    "曹": "C",
    "曾": "Z",
    "邓": "D",
    "彭": "P",
    "肖": "X",
}


def _today(value: date | None) -> date:
    return value or date.today()


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _operator_initials(operator_name: str) -> str:
    initials: list[str] = []
    for char in operator_name.strip():
        if char.isspace():
            continue
        if char.isascii() and char.isalnum():
            initials.append(char.upper())
            continue
        initials.append(CHINESE_INITIALS.get(char, "X"))
    return "".join(initials) or "X"


def build_default_unit_name(
    *,
    operator_name: str,
    region_name: str,
    audience_relation: str,
    age_label: str,
    today: date | None = None,
) -> str:
    """Build the default unit name required by the create flow."""
    relation_label = {
        "exclude": "排除",
        "target": "定向",
        "include": "定向",
    }.get(str(audience_relation).strip().lower(), str(audience_relation).strip())
    return (
        f"{_today(today):%Y%m%d}"
        f"{region_name.strip()}"
        f"{relation_label}"
        f"{age_label.strip()}"
        f"{_operator_initials(operator_name)}"
    )


def _failure(field: str, message: str, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    result_data = {
        "execution_source": "deerflow-native-tool",
        "business_tool_name": BUSINESS_TOOL_NAME,
        "user_visible_text": message,
        "single_question_only": True,
        "blocking_clarification_field": field,
        "reply_guidance": (
            "面向用户回复时必须只展示 user_visible_text 中的当前阻断问题，"
            "不要追加任何其它问题、其它缺失字段、地域编码、内部工具名或 payload。"
        ),
    }
    if data:
        result_data.update(data)
    return {
        "success": False,
        "message": "创建项目流程需要补充信息。",
        "data": result_data,
        "errors": [{"field": field, "message": message}],
        "tool_name": BUSINESS_TOOL_NAME,
        "request_id": None,
    }


def _success(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "message": "创建项目流程已生成执行计划。",
        "data": {
            "execution_source": "deerflow-native-tool",
            "business_tool_name": BUSINESS_TOOL_NAME,
            "user_visible_text": "创建项目流程已生成执行计划，请确认后继续。",
            **data,
        },
        "errors": [],
        "tool_name": BUSINESS_TOOL_NAME,
        "request_id": None,
    }


def _default_audience(flow_payload: dict[str, Any]) -> dict[str, Any]:
    audience = deepcopy(flow_payload.get("audience") or {})
    region_city_ids = flow_payload.get("region_city_ids")
    if region_city_ids:
        region = dict(audience.get("region") or {})
        region.setdefault("location_type", "HOME")
        region.setdefault("city", region_city_ids)
        region.setdefault("region_ver", flow_payload.get("region_ver") or "2.3.2")
        audience.setdefault("district", "REGION")
        audience["region"] = region

    audience.setdefault("gender", "NONE")
    audience.setdefault("age", flow_payload.get("age") or [18, 55])
    audience.setdefault("hide_if_converted", "CUSTOMER")
    audience.setdefault("converted_time_duration", "THREE_MONTH")

    if flow_payload.get("local_delivery_scene") == "EXTERNAL":
        audience.setdefault("customized_interest_action", "INTERESTACTION_OFF")
        audience.setdefault("filter_aweme_abnormal_active", "FILTER_AWEME_ABNORMAL_ACTIVE_TYPE_ON")
        audience.setdefault("filter_aweme_fans_count", "FILTER_AWEME_FANS_COUNT_TYPE_OVER1000")

    return audience


def _default_bid_type(flow_payload: dict[str, Any]) -> str:
    if flow_payload.get("bid_type"):
        return str(flow_payload["bid_type"])
    delivery_scene = flow_payload.get("local_delivery_scene")
    if delivery_scene == "POI_RECOMMEND":
        return "SMART"
    if delivery_scene == "EXTERNAL":
        return "MAX_CONVERSION"
    return "MANUAL"


def _default_local_asset_type(flow_payload: dict[str, Any]) -> str | None:
    if flow_payload.get("local_asset_type"):
        return str(flow_payload["local_asset_type"])
    guide_page = flow_payload.get("guide_page")
    return {
        "PRIVATE_MESSAGE": "LOCAL_ASSET_TYPE_AWEME_PAGE",
        "AWEME_PAGE": "LOCAL_ASSET_TYPE_AWEME_PAGE",
        "MARKETING_PAGE": "LOCAL_ASSET_TYPE_MARKET_PAGE",
        "MARKET_PAGE": "LOCAL_ASSET_TYPE_MARKET_PAGE",
        "STORE_PAGE": "LOCAL_ASSET_TYPE_SHOP_PAGE",
        "SHOP_PAGE": "LOCAL_ASSET_TYPE_SHOP_PAGE",
        "PRODUCT_PAGE": "LOCAL_ASSET_TYPE_PRODUCT_PAGE",
    }.get(str(guide_page).strip().upper())


def _build_project_payload(flow_payload: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: deepcopy(value)
        for key, value in flow_payload.items()
        if key in PROJECT_CREATE_FIELDS and not _is_blank(value)
    }
    payload.setdefault("schedule_type", "FROM_NOW_ON")
    payload.setdefault("budget_mode", "BUDGET_MODE_DAY")
    payload.setdefault("is_set_peak_budget", False)
    payload["bid_type"] = _default_bid_type(flow_payload)
    payload["audience"] = _default_audience(flow_payload)
    if flow_payload.get("local_delivery_scene") == "EXTERNAL":
        local_asset_type = _default_local_asset_type(flow_payload)
        if local_asset_type:
            payload.setdefault("local_asset_type", local_asset_type)
        payload.setdefault("aigc_dynamic_creative_switch", "AIGC_DYNAMIC_CREATIVE_SWITCH_OFF")
    return payload


def _selected_videos(flow_payload: dict[str, Any]) -> list[Any]:
    selected = flow_payload.get("selected_videos")
    return selected if isinstance(selected, list) else []


def _set_selected_videos(flow_payload: dict[str, Any], selected_videos: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = dict(flow_payload)
    enriched["selected_videos"] = selected_videos
    return enriched


def _is_product_pay(flow_payload: dict[str, Any]) -> bool:
    return flow_payload.get("local_delivery_scene") == "PRODUCT_PAY"


def _video_count_error(flow_payload: dict[str, Any]) -> str | None:
    count = len(_selected_videos(flow_payload))
    if _is_product_pay(flow_payload):
        if count != PROJECT_PAY_VIDEO_COUNT:
            return f"团购成交需要选择 {PROJECT_PAY_VIDEO_COUNT} 条视频，当前已选择 {count} 条。"
        return None
    if count < OTHER_MIN_VIDEO_COUNT or count > OTHER_MAX_VIDEO_COUNT:
        return (
            f"当前投放目标需要选择 {OTHER_MIN_VIDEO_COUNT}-{OTHER_MAX_VIDEO_COUNT} 条视频，"
            f"当前已选择 {count} 条。"
        )
    return None


def _extract_video_candidates(material_result: dict[str, Any]) -> list[dict[str, Any]]:
    data = material_result.get("data")
    if not isinstance(data, dict):
        return []
    containers = [
        data,
        data.get("result"),
        (data.get("result") or {}).get("data") if isinstance(data.get("result"), dict) else None,
    ]
    for container in containers:
        if not isinstance(container, dict):
            continue
        candidates = (
            container.get("video_list")
            or container.get("videoList")
            or container.get("list")
            or container.get("data")
        )
        if isinstance(candidates, list):
            return [item for item in candidates if isinstance(item, dict)]
    return []


def _extract_uploaded_video(material_result: dict[str, Any], video_file_path: str) -> dict[str, Any]:
    data = material_result.get("data")
    containers = [data]
    if isinstance(data, dict):
        containers.extend(
            [
                data.get("result"),
                (data.get("result") or {}).get("data") if isinstance(data.get("result"), dict) else None,
            ]
        )
    for container in containers:
        if not isinstance(container, dict):
            continue
        video_id = container.get("video_id") or container.get("material_id")
        if video_id:
            return {
                "video_id": str(video_id),
                "video_url": container.get("video_url"),
                "video_signature": container.get("video_signature") or container.get("signature"),
                "source_file_path": video_file_path,
            }
    return {"source_file_path": video_file_path}


def _upload_authorized_videos(flow_payload: dict[str, Any]) -> dict[str, Any] | None:
    video_file_paths = flow_payload.get("video_file_paths")
    if isinstance(video_file_paths, str):
        video_file_paths = [video_file_paths]
    if not isinstance(video_file_paths, list) or not video_file_paths:
        return None

    uploaded_videos: list[dict[str, Any]] = []
    for raw_path in video_file_paths:
        if _is_blank(raw_path):
            continue
        video_file_path = str(raw_path)
        material_payload = {
            "local_account_id": flow_payload.get("local_account_id"),
            "video_file_path": video_file_path,
        }
        upload_result = run_oceanengine_local_material(
            MATERIAL_UPLOAD_CAPABILITY,
            material_payload,
            dry_run=False,
        )
        if upload_result.get("success") is not True:
            user_visible_text = (
                (upload_result.get("data") or {}).get("user_visible_text")
                if isinstance(upload_result.get("data"), dict)
                else None
            ) or "视频上传未完成，请先补充当前视频上传参数。"
            return _failure("video_file_paths", str(user_visible_text), data={"material_result": upload_result})
        uploaded_videos.append(_extract_uploaded_video(upload_result, video_file_path))

    if not uploaded_videos:
        return _failure("video_file_paths", "请提供用户明确授权的视频文件路径。")
    return _set_selected_videos(flow_payload, uploaded_videos)


def _video_candidate_options(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for item in candidates:
        value = item.get("video_id") or item.get("id") or item.get("material_id")
        label = item.get("title") or item.get("name") or item.get("video_name") or value
        if value is None or not label:
            continue
        option = {
            "value": str(value),
            "label": str(label),
            "metadata": item,
        }
        description = item.get("description") or item.get("status")
        if description:
            option["description"] = description
        options.append(option)
    return options


def _video_candidate_clarification(flow_payload: dict[str, Any]) -> dict[str, Any] | None:
    if _selected_videos(flow_payload) or not flow_payload.get("select_library_videos"):
        return None
    material_payload = {
        key: flow_payload[key]
        for key in ("local_account_id", "page", "page_size", "keyword")
        if key in flow_payload and not _is_blank(flow_payload[key])
    }
    material_payload.setdefault("page", 1)
    material_payload.setdefault("page_size", 20)
    material_result = run_oceanengine_local_material(
        MATERIAL_LIBRARY_CAPABILITY,
        material_payload,
        dry_run=False,
    )
    options = _video_candidate_options(_extract_video_candidates(material_result))
    if not options:
        return _failure("selected_videos", "未查询到可选择的视频素材，请先上传视频到素材库后再选择。")

    question = "请选择本次投放要使用的视频素材。"
    user_visible_text = "\n".join(
        [
            question,
            *[
                f"{index}. {option['label']}（ID：{option['value']}）"
                for index, option in enumerate(options, start=1)
            ],
            "请回复视频候选 ID 或名称。",
        ]
    )
    return _failure(
        "selected_videos",
        user_visible_text,
        data={
            "clarification": {
                "field": "selected_videos",
                "question": question,
                "input_control": {
                    "type": "choice_cards",
                    "selection_mode": "multiple",
                    "options": options,
                },
            }
        },
    )


def _unit_name(flow_payload: dict[str, Any], today: date | None) -> str:
    if flow_payload.get("unit_name"):
        return str(flow_payload["unit_name"])
    return build_default_unit_name(
        operator_name=str(flow_payload["operator_name"]),
        region_name=str(flow_payload.get("region_name") or "--"),
        audience_relation=str(flow_payload.get("audience_relation") or "target"),
        age_label=str(flow_payload.get("age_label") or "18-55"),
        today=today,
    )


def _extract_project_id(project_result: dict[str, Any]) -> Any:
    data = project_result.get("data")
    containers = [data]
    if isinstance(data, dict):
        containers.extend(
            [
                data.get("result"),
                (data.get("result") or {}).get("data") if isinstance(data.get("result"), dict) else None,
            ]
        )
    for container in containers:
        if isinstance(container, dict) and container.get("project_id") is not None:
            return container["project_id"]
    return None


def _build_unit_payload(flow_payload: dict[str, Any], project_id: Any, unit_name: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "local_account_id": flow_payload.get("local_account_id"),
        "project_id": project_id,
        "name": unit_name,
    }
    customer_material_list = []
    for item in _selected_videos(flow_payload):
        if not isinstance(item, dict):
            continue
        video_id = item.get("video_id") or item.get("id") or item.get("material_id")
        if not video_id:
            continue
        video_material = {"video_id": str(video_id)}
        cover_web_uri = item.get("cover_web_uri") or item.get("poster_url")
        if cover_web_uri:
            video_material["cover_web_uri"] = cover_web_uri
        customer_material_list.append(
            {
                "image_mode": "CREATIVE_IMAGE_MODE_VIDEO",
                "title_material": {
                    "title": flow_payload.get("unit_title") or flow_payload.get("title") or "本地生活精选推荐"
                },
                "video_material": video_material,
            }
        )
    if customer_material_list:
        payload["customer_material_list"] = customer_material_list

    if flow_payload.get("promotion_card_info"):
        payload["promotion_card_info"] = deepcopy(flow_payload["promotion_card_info"])
    return payload


def run_oceanengine_local_project_create_flow(
    payload: dict[str, Any],
    *,
    dry_run: bool = False,
    today: date | None = None,
) -> dict[str, Any]:
    """Run the local project create flow and dispatch to native business tools."""
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是 dict。")
    if _is_blank(payload.get("operator_name")):
        return _failure("operator_name", "投手姓名是什么值？")

    upload_result = _upload_authorized_videos(payload)
    if upload_result is not None:
        if upload_result.get("success") is False:
            return upload_result
        payload = upload_result

    candidate_result = _video_candidate_clarification(payload)
    if candidate_result:
        return candidate_result

    count_error = _video_count_error(payload)
    if count_error:
        return _failure("selected_videos", count_error)

    project_payload = _build_project_payload(payload)
    unit_name = _unit_name(payload, today)
    if dry_run:
        return _success(
            {
                "dry-run": True,
                "project_payload": project_payload,
                "unit_plan": {
                    "name": unit_name,
                    "selected_videos": _selected_videos(payload),
                },
            }
        )

    project_result = run_oceanengine_local_project(
        capability=PROJECT_CAPABILITY,
        payload=project_payload,
        dry_run=False,
    )
    data = dict(project_result.get("data") or {})
    data["unit_plan"] = {
        "name": unit_name,
        "selected_videos": _selected_videos(payload),
    }
    project_result["data"] = data
    if project_result.get("success") is not True or not payload.get("create_unit"):
        return project_result

    project_id = _extract_project_id(project_result)
    if project_id is None:
        return _failure(
            "project_id",
            "项目创建结果中缺少项目 ID，无法继续配置单元。",
            data={"project_result": project_result},
        )

    unit_payload = _build_unit_payload(payload, project_id, unit_name)
    unit_result = run_oceanengine_local_unit(UNIT_CREATE_CAPABILITY, unit_payload, dry_run=False)
    if unit_result.get("success") is not True:
        return {
            "success": False,
            "message": "项目创建成功，但单元配置失败。",
            "data": {
                "execution_source": "deerflow-native-tool",
                "business_tool_name": BUSINESS_TOOL_NAME,
                "user_visible_text": (unit_result.get("data") or {}).get(
                    "user_visible_text",
                    "项目已创建，但单元配置未完成，请先处理当前单元问题。",
                ),
                "project_result": project_result,
                "unit_result": unit_result,
            },
            "errors": unit_result.get("errors") or [],
            "tool_name": BUSINESS_TOOL_NAME,
            "request_id": None,
        }

    return _success(
        {
            "project_result": project_result,
            "unit_result": unit_result,
        }
    )


def _agent_visible_create_flow_result(result: dict[str, Any]) -> dict[str, Any]:
    visible = dict(result)
    data = dict(visible.get("data") or {})
    user_visible_text = data.get("user_visible_text")

    if visible.get("success") is False and isinstance(user_visible_text, str) and user_visible_text.strip():
        visible["message"] = user_visible_text
        compact_data: dict[str, Any] = {
            "single_question_only": bool(data.get("single_question_only")),
            "blocking_clarification_field": data.get("blocking_clarification_field"),
        }
        if isinstance(data.get("clarification"), dict):
            compact_data["clarification"] = data["clarification"]
        visible["data"] = compact_data
        errors = visible.get("errors")
        if isinstance(errors, list):
            visible["errors"] = errors[:1]
        return visible

    return visible


@tool("oceanengine_local_project_create_flow", parse_docstring=True)
def oceanengine_local_project_create_flow_tool(payload_json: str, dry_run: bool = False) -> str:
    """Execute the optimized OceanEngine local project creation flow.

    Use this tool first for natural-language requests to create a local-promotion
    project or投流项目 when the user mentions flow fields such as 投手, 营销场景,
    投放目标, 单元类型, 投放门店/商品, 用户定向, 排期预算, 出价, or 视频素材.
    Prefer it over oceanengine_local_project for end-to-end project creation.
    Map common Chinese values before calling: 短视频/图文=VIDEO_IMAGE,
    直播间=LIVE, 团购成交=PRODUCT_PAY, 线下到店=POI_RECOMMEND,
    获取线索=EXTERNAL, 线上互动=CONTENT_HEAT, 通投=GENERAL, 搜索=SEARCH.
    When the user says 从素材库选择视频, set select_library_videos=true instead of
    asking for uploaded file paths.

    Args:
        payload_json: JSON object string containing business create-flow fields.
        dry_run: Validate and build an execution plan without calling project creation when true.
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
        if not isinstance(payload, dict):
            raise ValueError("payload_json 必须是 JSON object。")
        result = run_oceanengine_local_project_create_flow(payload, dry_run=dry_run)
    except Exception as exc:
        result = {
            "success": False,
            "message": "OceanEngine 本地推创建项目流程工具执行失败。",
            "data": {
                "execution_source": "deerflow-native-tool",
                "business_tool_name": BUSINESS_TOOL_NAME,
                "user_visible_text": "创建项目流程执行失败，请检查输入后重试。",
            },
            "errors": [{"field": "tool", "message": str(exc)}],
            "tool_name": BUSINESS_TOOL_NAME,
            "request_id": None,
        }
    return json.dumps(_agent_visible_create_flow_result(result), ensure_ascii=False)
