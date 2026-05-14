import json
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_RULES_ROOT = REPO_ROOT / "skills" / "custom" / "oceanengine-local-project" / "rules"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.oceanengine_local_project_runtime.validators import validate_payload
from tools.oceanengine_local_project_runtime.mcp_client import build_mcp_payload
from tools.oceanengine_local_project_runtime.mutation_confirm import confirm_mutation
from tools.oceanengine_local_project_runtime import endpoint_runner
from tools.oceanengine_local_project import oceanengine_local_project_tool, run_oceanengine_local_project


def _load_rule(name: str) -> dict:
    return json.loads((PROJECT_RULES_ROOT / name).read_text(encoding="utf-8"))


def _base_create_project_payload(**overrides) -> dict:
    payload = {
        "local_account_id": 1854708763953159,
        "name": "Codex出价方式场景校验测试",
        "marketing_goal": "VIDEO_IMAGE",
        "local_delivery_scene": "PRODUCT_PAY",
        "ad_type": "GENERAL",
        "delivery_goal": "PRODUCT",
        "product_id": 1840240933753866,
        "schedule_type": "FROM_NOW_ON",
        "bid_type": "MANUAL",
        "bid": 15000,
        "budget_mode": "BUDGET_MODE_DAY",
        "budget": 100000,
        "is_set_peak_budget": False,
        "audience": {"district": "ALL"},
    }
    payload.update(overrides)
    return payload


def test_list_projects_accepts_official_filtering_fields():
    spec = _load_rule("list-projects.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "page": 1,
            "page_size": 20,
            "filtering": {
                "project_status_first": "PROJECT_STATUS_ENABLE",
                "marketing_goal": "VIDEO_IMAGE",
                "local_delivery_scene": "POI_RECOMMEND",
                "ad_type": "GENERAL",
                "bid_type": "SMART",
            },
        },
        spec,
    )

    assert errors == []


def test_list_projects_rejects_invented_filtering_fields_and_enums():
    spec = _load_rule("list-projects.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {
                "status_first": "ENABLED",
                "marketing_scene": "VIDEO_IMAGE",
                "marketing_target": "POI_CUSTOMER",
                "campaign_type": "GENERAL",
                "bid_type": "SMART_BID",
            },
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "filtering.status_first 不是官方文档支持的参数字段" in messages
    assert "filtering.marketing_scene 不是官方文档支持的参数字段" in messages
    assert "filtering.marketing_target 不是官方文档支持的参数字段" in messages
    assert "filtering.campaign_type 不是官方文档支持的参数字段" in messages
    assert "出价方式" in messages
    assert "智能出价" in messages


def test_list_projects_rejects_non_numeric_filter_id_items_locally():
    spec = _load_rule("list-projects.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {
                "project_ids": ["ABC"],
                "shop_ids": ["门店A"],
                "product_ids": ["商品B"],
            },
            "page": 1,
            "page_size": 5,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "过滤条件.项目ID列表第 1 项 类型不正确，应为数字。" in messages
    assert "过滤条件.门店ID列表第 1 项 类型不正确，应为数字。" in messages
    assert "过滤条件.商品ID列表第 1 项 类型不正确，应为数字。" in messages


def test_list_projects_rejects_page_and_page_size_less_than_one_locally():
    spec = _load_rule("list-projects.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "filtering": {"project_status_first": "PROJECT_STATUS_ENABLE"},
            "page": 0,
            "page_size": 0,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "页码 不能小于 1。" in messages
    assert "每页数量 不能小于 1。" in messages


def test_list_projects_maps_official_filtering_enums_to_mcp_payload():
    spec = _load_rule("list-projects.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "page": 1,
            "page_size": 20,
            "filtering": {
                "project_status_first": "PROJECT_STATUS_ENABLE",
                "marketing_goal": "VIDEO_IMAGE",
                "local_delivery_scene": "POI_RECOMMEND",
                "ad_type": "GENERAL",
                "bid_type": "SMART",
            },
        },
    )

    assert payload["filtering"] == {
        "projectStatusFirst": "ENABLE",
        "marketingGoal": "VIDEO_IMAGE",
        "localDeliveryScene": "POI_RECOMMEND",
        "adType": "GENERAL",
        "bidType": "SMART",
    }


def test_list_projects_maps_delivery_package_to_platform_enum():
    spec = _load_rule("list-projects.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "filtering": {
                "local_delivery_scene": "EXTERNAL",
                "delivery_package": "DELIVERY_PACKAGE_UBL",
            },
        },
    )

    assert payload["filtering"]["localDeliveryScene"] == "EXTERNAL"
    assert payload["filtering"]["deliveryPackage"] == "UBL"


def test_create_project_maps_delivery_package_to_platform_enum():
    spec = _load_rule("create-project.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "name": "Codex线索映射测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "EXTERNAL",
            "ad_type": "GENERAL",
            "external_action": "CLUE_ACQUISITION",
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-10 09:00:00",
            "end_time": "2026-05-13 21:00:00",
            "bid_type": "SMART",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 18000,
            "audience": {"district": "ALL"},
            "delivery_package": "DELIVERY_PACKAGE_NORMAL",
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "local_asset_type": "LOCAL_ASSET_TYPE_MARKET_PAGE",
            "market_page_ids": [7628817210925580351],
            "tool_pack_id": 18948445186,
            "aigc_dynamic_creative_switch": "AIGC_DYNAMIC_CREATIVE_SWITCH_OFF",
        },
    )

    assert payload["request"]["deliveryPackage"] == "NORMAL"
    assert payload["request"]["aigcDynamicCreativeSwitch"] == "OFF"
    assert payload["request"]["intelligentSelectionMode"] == "OFF"
    assert payload["request"]["localAssetType"] == "MARKET_PAGE"


def test_create_project_external_market_page_does_not_require_tool_pack_id():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex线索营销页测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "EXTERNAL",
            "ad_type": "GENERAL",
            "external_action": "CLUE_ACQUISITION",
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-10 09:00:00",
            "end_time": "2026-05-13 21:00:00",
            "bid_type": "MAX_CONVERSION",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 30000,
            "audience": {"district": "ALL"},
            "delivery_package": "DELIVERY_PACKAGE_NORMAL",
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "local_asset_type": "LOCAL_ASSET_TYPE_MARKET_PAGE",
            "market_page_ids": [7628817210925580351],
            "aigc_dynamic_creative_switch": "AIGC_DYNAMIC_CREATIVE_SWITCH_OFF",
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert all("留资组件ID" not in message for message in messages)


def test_create_project_rejects_unsupported_bid_type_for_show_without_mcp_call():
    spec = _load_rule("create-project.json")
    payload = _base_create_project_payload(
        local_delivery_scene="CONTENT_HEAT",
        external_action="SHOW",
        delivery_goal="POI",
        delivery_poi_mode="ALL",
        bid_type="SMART",
        bid=10000,
        budget=10000,
    )
    payload.pop("product_id")
    payload.pop("is_set_peak_budget")

    with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint") as invoke_endpoint:
        result = endpoint_runner.run_endpoint(spec, payload)

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "展示量优化目标仅支持 MANUAL" in messages
    invoke_endpoint.assert_not_called()


def test_create_project_rejects_unsupported_bid_type_for_live_transaction_without_mcp_call():
    spec = _load_rule("create-project.json")
    payload = _base_create_project_payload(
        marketing_goal="LIVE",
        local_delivery_scene="PRODUCT_PAY",
        external_action="LIVE_OTO_GROUP_BUYING",
        aweme_id="1122334455",
        bid_type="MANUAL",
        budget=30000,
    )
    for field in ("delivery_goal", "product_id", "is_set_peak_budget", "bid"):
        payload.pop(field)

    with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint") as invoke_endpoint:
        result = endpoint_runner.run_endpoint(spec, payload)

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "直播交易场景仅支持 SMART" in messages
    invoke_endpoint.assert_not_called()


def test_create_project_rejects_unsupported_bid_type_for_external_non_ubl_without_mcp_call():
    spec = _load_rule("create-project.json")
    payload = _base_create_project_payload(
        local_delivery_scene="EXTERNAL",
        external_action="CLUE_ACQUISITION",
        delivery_goal="PRODUCT",
        product_id=1840240933753866,
        delivery_package="DELIVERY_PACKAGE_NORMAL",
        intelligent_selection_mode="INTELLIGENT_SELECTION_MODE_ON",
        aigc_dynamic_creative_switch="AIGC_DYNAMIC_CREATIVE_SWITCH_OFF",
        bid_type="SMART",
        budget=10000,
    )
    for field in ("is_set_peak_budget", "bid"):
        payload.pop(field)

    with patch("tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint") as invoke_endpoint:
        result = endpoint_runner.run_endpoint(spec, payload)

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "非 UBL 留资场景仅支持 STABILIZE_COSTS 或 MAX_CONVERSION" in messages
    invoke_endpoint.assert_not_called()


def test_create_project_accepts_supported_bid_type_scene_combinations():
    spec = _load_rule("create-project.json")

    show_manual = _base_create_project_payload(
        local_delivery_scene="CONTENT_HEAT",
        external_action="SHOW",
        delivery_goal="POI",
        delivery_poi_mode="ALL",
        bid_type="MANUAL",
        bid=10000,
        budget=30000,
    )
    show_manual.pop("product_id")
    show_manual.pop("is_set_peak_budget")

    live_smart = _base_create_project_payload(
        marketing_goal="LIVE",
        local_delivery_scene="PRODUCT_PAY",
        external_action="LIVE_OTO_GROUP_BUYING",
        aweme_id="1122334455",
        bid_type="SMART",
        budget=10000,
    )
    for field in ("delivery_goal", "product_id", "is_set_peak_budget", "bid"):
        live_smart.pop(field)

    external_max_conversion = _base_create_project_payload(
        local_delivery_scene="EXTERNAL",
        external_action="CLUE_ACQUISITION",
        delivery_goal="PRODUCT",
        product_id=1840240933753866,
        delivery_package="DELIVERY_PACKAGE_NORMAL",
        intelligent_selection_mode="INTELLIGENT_SELECTION_MODE_ON",
        aigc_dynamic_creative_switch="AIGC_DYNAMIC_CREATIVE_SWITCH_OFF",
        bid_type="MAX_CONVERSION",
        budget=10000,
    )
    for field in ("is_set_peak_budget", "bid"):
        external_max_conversion.pop(field)

    assert validate_payload(show_manual, spec) == []
    assert validate_payload(live_smart, spec) == []
    assert validate_payload(external_max_conversion, spec) == []


def test_create_project_external_market_page_rejects_tool_pack_id():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex线索营销页测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "EXTERNAL",
            "ad_type": "GENERAL",
            "external_action": "CLUE_ACQUISITION",
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-10 09:00:00",
            "end_time": "2026-05-13 21:00:00",
            "bid_type": "MAX_CONVERSION",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 30000,
            "audience": {"district": "ALL"},
            "delivery_package": "DELIVERY_PACKAGE_NORMAL",
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "local_asset_type": "LOCAL_ASSET_TYPE_MARKET_PAGE",
            "market_page_ids": [7628817210925580351],
            "tool_pack_id": 18948445186,
            "aigc_dynamic_creative_switch": "AIGC_DYNAMIC_CREATIVE_SWITCH_OFF",
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert any("营销页" in message and "留资组件ID" in message and "不应传入" in message for message in messages)


def test_create_project_rejects_non_numeric_region_city_items_locally():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex地域类型测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "POI_RECOMMEND",
            "ad_type": "GENERAL",
            "delivery_goal": "POI",
            "delivery_poi_mode": "ALL",
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-11 00:00:00",
            "end_time": "2026-05-12 23:59:59",
            "bid_type": "SMART",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 10000,
            "is_set_peak_budget": False,
            "audience": {
                "district": "REGION",
                "region": {"city": ["重庆"], "region_ver": "2.3.2"},
            },
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "地域定向省市或者区县列表第 1 项 类型不正确，应为数字。" in messages


def test_list_projects_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-projects.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-list-projects",
            "data": {
                "pageInfo": {"page": 1, "pageSize": 20, "totalNumber": 1, "totalPage": 1},
                "projectList": [
                    {
                        "projectId": 7632772460803522587,
                        "name": "Codex干净路径复测-20260426-0253",
                        "projectStatusFirst": "ENABLE",
                        "projectStatusSecond": [],
                        "marketingGoal": "VIDEO_IMAGE",
                        "localDeliveryScene": "POI_RECOMMEND",
                        "adType": "GENERAL",
                        "projectBudget": "300.00",
                        "projectBid": "--",
                        "projectCreateTime": "2026-04-26 02:58:16",
                        "projectModifyTime": "2026-04-26 02:58:16",
                    }
                ],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProjectList", "raw": raw, "request_id": "req-list-projects"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "page": 1,
                "page_size": 20,
                "filtering": {
                    "project_status_first": "PROJECT_STATUS_ENABLE",
                    "marketing_goal": "VIDEO_IMAGE",
                    "local_delivery_scene": "POI_RECOMMEND",
                    "ad_type": "GENERAL",
                    "bid_type": "SMART",
                },
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "项目ID：7632772460803522587" in display
    assert "项目名称：Codex干净路径复测-20260426-0253" in display
    assert "项目一级状态：启用" in display
    assert "营销场景：短视频/图文" in display
    assert "营销目的：线下到店" in display
    assert "单元类型：通投" in display
    assert "项目预算：300.00" in display
    assert "请求日志id" not in display


def test_get_project_detail_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("get-project-detail.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-project-detail",
            "data": {
                "projectId": 7632772460803522587,
                "name": "Codex干净路径复测-20260426-0253",
                "marketingGoal": "VIDEO_IMAGE",
                "localDeliveryScene": "POI_RECOMMEND",
                "adType": "GENERAL",
                "budget": 30000,
                "bid": 16000,
                "bidType": "SMART",
                "budgetMode": "DAY",
                "startTime": None,
                "endTime": None,
                "localAssetType": "SHOP_PAGE",
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProjectDetail", "raw": raw, "request_id": "req-project-detail"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "project_id": 7632772460803522587,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "项目ID：7632772460803522587" in display
    assert "项目名称：Codex干净路径复测-20260426-0253" in display
    assert "营销场景：短视频/图文" in display
    assert "营销目的：线下到店" in display
    assert "单元类型：通投" in display
    assert "项目预算（分）：30000" in display
    assert "项目出价（分）：16000" in display
    assert "出价方式：智能出价" in display
    assert "项目预算类型：日预算" in display
    assert "跳转页面：推门店页" in display
    assert "请求日志id" not in display


def test_get_project_detail_rejects_project_id_less_than_one_locally():
    spec = _load_rule("get-project-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "project_id": 0,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "项目ID 不能小于 1。" in messages


def test_get_project_detail_rejects_project_id_above_int64_locally():
    spec = _load_rule("get-project-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "project_id": 999999999999999999999999999999,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "项目ID 不能大于 9223372036854775807。" in messages


def test_list_promotable_pois_accepts_official_filtering_fields():
    spec = _load_rule("list-promotable-pois.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "POI_RECOMMEND",
            "page": 1,
            "page_size": 20,
            "filtering": {
                "search_key_word": "膜一姐",
                "province": [500000],
                "city": [500100],
                "product_id": 123456789,
            },
        },
        spec,
    )

    assert errors == []


def test_list_promotable_pois_rejects_non_numeric_region_ids_locally():
    spec = _load_rule("list-promotable-pois.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "POI_RECOMMEND",
            "page": 1,
            "page_size": 3,
            "filtering": {
                "province": ["重庆"],
                "city": ["ABC"],
            },
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "省份ID第 1 项 类型不正确，应为数字。" in messages
    assert "城市ID第 1 项 类型不正确，应为数字。" in messages


def test_list_promotable_pois_rejects_page_less_than_one_locally():
    spec = _load_rule("list-promotable-pois.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "POI_RECOMMEND",
            "page": 0,
            "page_size": 3,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "页码 不能小于 1。" in messages


def test_list_promotable_pois_maps_official_filtering_keyword_to_mcp_payload():
    spec = _load_rule("list-promotable-pois.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "POI_RECOMMEND",
            "page": 1,
            "page_size": 5,
            "filtering": {
                "search_key_word": "膜一姐",
                "province": [500000],
                "city": [500100],
                "product_id": 1801076849133609,
            },
        },
    )

    assert payload["searchKeyWord"] == "膜一姐"
    assert payload["province"] == [500000]
    assert payload["city"] == [500100]
    assert payload["productId"] == 1801076849133609
    assert "filtering" not in payload


def test_list_promotable_pois_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-promotable-pois.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-poi-list",
            "data": {
                "pageInfo": {"page": 1, "pageSize": 20, "totalNumber": 1, "totalPage": 1},
                "poiList": [
                    {
                        "poiId": 6932952586303604740,
                        "poiName": "膜一姐汽车贴膜(巴国城店)",
                        "province": "重庆市",
                        "city": "重庆市",
                        "district": "九龙坡区",
                        "poiAddress": "红狮大道6号龙力巴国城平1层",
                        "existsProduct": True,
                    }
                ],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localPoiGet", "raw": raw, "request_id": "req-poi-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "local_delivery_scene": "POI_RECOMMEND",
                "page": 1,
                "page_size": 20,
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "门店ID：6932952586303604740" in display
    assert "门店名称：膜一姐汽车贴膜(巴国城店)" in display
    assert "所在省份：重庆市" in display
    assert "所在城市：重庆市" in display
    assert "所在区：九龙坡区" in display
    assert "门店地址：红狮大道6号龙力巴国城平1层" in display
    assert "门店下有无商品：是" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_list_promotable_pois_rejects_response_page_mismatch():
    spec = _load_rule("list-promotable-pois.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-poi-page-mismatch",
            "data": {
                "pageInfo": {"page": 4, "pageSize": 100, "totalNumber": 304, "totalPage": 4},
                "poiList": [],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localPoiGet", "raw": raw, "request_id": "req-poi-page-mismatch"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "local_delivery_scene": "POI_RECOMMEND",
                "page": 1,
                "page_size": 5,
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "页码" in messages
    assert "每页数量" in messages


def test_list_promotable_products_accepts_official_filtering_fields():
    spec = _load_rule("list-promotable-products.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "PRODUCT_PAY",
            "page": 1,
            "page_size": 20,
            "filtering": {"search_key_word": "膜一姐"},
        },
        spec,
    )

    assert errors == []


def test_list_promotable_products_maps_official_filtering_keyword_to_mcp_payload():
    spec = _load_rule("list-promotable-products.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "PRODUCT_PAY",
            "page": 1,
            "page_size": 5,
            "filtering": {"search_key_word": "膜一姐"},
        },
    )

    assert payload["searchKeyWord"] == "膜一姐"
    assert "filtering" not in payload


def test_list_promotable_products_rejects_page_less_than_one_locally():
    spec = _load_rule("list-promotable-products.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "POI_RECOMMEND",
            "page": 0,
            "page_size": 3,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "页码 不能小于 1。" in messages


def test_list_promotable_products_rejects_non_string_keyword_locally():
    spec = _load_rule("list-promotable-products.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "PRODUCT_PAY",
            "page": 1,
            "page_size": 3,
            "filtering": {"search_key_word": 12345},
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "搜索关键词 类型不正确，应为字符串。" in messages


def test_list_promotable_products_accepts_flat_keyword_as_filtering_alias():
    spec = _load_rule("list-promotable-products.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "local_account_id": 1854708763953159,
            "local_delivery_scene": "PRODUCT_PAY",
            "search_key_word": "膜一姐",
        },
        dry_run=True,
    )

    assert result["success"] is True
    fields = result["data"]["payload"].keys()
    assert "filtering" in fields
    assert "search_key_word" not in fields


def test_create_project_normalizes_datetime_to_official_date_fields():
    spec = _load_rule("create-project.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "local_account_id": 1854708763953159,
            "name": "Codex日期归一化测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "PRODUCT_PAY",
            "ad_type": "GENERAL",
            "delivery_goal": "PRODUCT",
            "product_id": 1840240933753866,
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-07 00:00:00",
            "end_time": "2026-05-08 23:59:59",
            "bid_type": "MANUAL",
            "bid": 15000,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 100000,
            "is_set_peak_budget": False,
            "audience": {"district": "ALL"},
        },
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["payload"]["start_time"] == "2026-05-07"
    assert result["data"]["payload"]["end_time"] == "2026-05-08"


def test_create_project_rejects_store_ids_when_delivery_goal_is_product():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex商品指定门店冲突测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "PRODUCT_PAY",
            "ad_type": "GENERAL",
            "delivery_goal": "PRODUCT",
            "promotion_poi_ids": [6932952586303604740],
            "product_id": 1840240933753866,
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-07",
            "end_time": "2026-05-08",
            "bid_type": "MANUAL",
            "bid": 15000,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 100000,
            "is_set_peak_budget": False,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "推门店ID列表 不应传入" in messages
    assert "投放内容选择商品时，门店ID列表不可传值" in messages


def test_create_project_rejects_numeric_peak_week_days_locally():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex高峰日自然周类型测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "POI_RECOMMEND",
            "ad_type": "GENERAL",
            "delivery_goal": "POI",
            "delivery_poi_mode": "PART",
            "promotion_poi_ids": [6932952586303604740],
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-09",
            "end_time": "2026-05-12",
            "bid_type": "SMART",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 22000,
            "is_set_peak_budget": True,
            "high_budget_rate": 20,
            "peak_week_days": [5, 6],
            "audience": {"district": "ALL"},
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "高峰日-自然周第 1 项 类型不正确，应为字符串。" in messages
    assert "高峰日-自然周第 2 项 类型不正确，应为字符串。" in messages


def test_create_project_accepts_official_peak_week_days():
    spec = _load_rule("create-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "name": "Codex高峰日自然周枚举测试",
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "POI_RECOMMEND",
            "ad_type": "GENERAL",
            "delivery_goal": "POI",
            "delivery_poi_mode": "PART",
            "promotion_poi_ids": [6932952586303604740],
            "schedule_type": "START_TO_END",
            "start_time": "2026-05-09",
            "end_time": "2026-05-12",
            "bid_type": "SMART",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": 22000,
            "is_set_peak_budget": True,
            "high_budget_rate": 20,
            "peak_week_days": ["FRIDAY", "SATURDAY"],
            "audience": {"district": "ALL"},
        },
        spec,
    )

    assert errors == []


def test_update_project_normalizes_end_datetime_to_official_date_field():
    spec = _load_rule("update-project.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "local_account_id": 1854708763953159,
            "project_id": 7636742197837561910,
            "schedule_type": "START_TO_END",
            "end_time": "2026-05-09 23:59:59",
        },
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["payload"]["end_time"] == "2026-05-09"


def test_update_project_rejects_start_time_because_official_update_request_does_not_support_it():
    spec = _load_rule("update-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "project_id": 7636742197837561910,
            "start_time": "2026-05-08",
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "start_time 不是官方文档支持的参数字段" in messages


def test_update_project_accepts_market_page_and_consult_aweme_fields():
    spec = _load_rule("update-project.json")

    payload = {
        "local_account_id": 1854708763953159,
        "project_id": 7636911226907590699,
        "market_page_ids": [7628817210925580351],
        "consult_aweme_uid": "59131133648",
    }

    assert validate_payload(payload, spec) == []
    mcp_payload = build_mcp_payload(spec, payload)
    assert mcp_payload["request"]["marketPageIds"] == [7628817210925580351]
    assert mcp_payload["request"]["consultAwemeUid"] == "59131133648"


def test_update_project_confirmation_respects_configured_fields():
    spec = _load_rule("update-project.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "data": {
                "projectId": 7636902785212874758,
                "name": "Codex浏览器验收0507指定门店B-更新",
                "budget": 26000,
                "budgetMode": "DAY",
                "endTime": "2026-05-14 23:59:59",
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mutation_confirm.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProjectDetail", "raw": raw},
    ):
        result = confirm_mutation(
            spec,
            {
                "local_account_id": 1854708763953159,
                "project_id": 7636902785212874758,
                "name": "Codex浏览器验收0507指定门店B-更新",
                "budget": 26000,
                "budget_mode": "BUDGET_MODE_DAY",
                "schedule_type": "START_TO_END",
                "end_time": "2026-05-14",
            },
            {"raw": {"data": {"code": 0, "data": {"projectId": 7636902785212874758}}}},
        )

    assert result["confirmed"] is True


def test_update_project_rejects_numeric_peak_week_days_locally():
    spec = _load_rule("update-project.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "project_id": 7636902785212874758,
            "marketing_goal": "VIDEO_IMAGE",
            "local_delivery_scene": "POI_RECOMMEND",
            "delivery_goal": "POI",
            "delivery_poi_mode": "PART",
            "promotion_poi_ids": [6932952586303604740],
            "is_set_peak_budget": True,
            "peak_week_days": [7],
            "high_budget_rate": 30,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "高峰日-自然周第 1 项 类型不正确，应为字符串。" in messages


def test_list_promotable_products_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-promotable-products.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-product-list",
            "data": {
                "pageInfo": {"page": 1, "pageSize": 20, "totalNumber": 1, "totalPage": 1},
                "products": [
                    {
                        "productId": 123456789,
                        "productName": "膜一姐测试团购商品",
                        "price": "99.00",
                        "productPics": ["https://example.invalid/product.png"],
                        "applicablePoiNum": 5,
                    }
                ],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProductGet", "raw": raw, "request_id": "req-product-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "local_delivery_scene": "PRODUCT_PAY",
                "page": 1,
                "page_size": 20,
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "商品ID：123456789" in display
    assert "商品名称：膜一姐测试团购商品" in display
    assert "价格：99.00" in display
    assert "适用门店数：5" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_list_promotable_products_rejects_response_page_mismatch():
    spec = _load_rule("list-promotable-products.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-product-page-mismatch",
            "data": {
                "pageInfo": {"page": 2, "pageSize": 100, "totalNumber": 135, "totalPage": 2},
                "products": [],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProductGet", "raw": raw, "request_id": "req-product-page-mismatch"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "local_delivery_scene": "PRODUCT_PAY",
                "page": 1,
                "page_size": 5,
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "页码" in messages
    assert "每页数量" in messages


def test_list_promotable_products_applies_default_pagination_before_postcondition():
    spec = _load_rule("list-promotable-products.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-product-default-page-mismatch",
            "data": {
                "pageInfo": {"page": 2, "pageSize": 100, "totalNumber": 135, "totalPage": 2},
                "products": [],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={
            "tool_name": "nacos-mcp-router_use_tool:localProductGet",
            "raw": raw,
            "request_id": "req-product-default-page-mismatch",
        },
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "local_delivery_scene": "PRODUCT_PAY",
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "页码请求值为 1" in messages
    assert "每页数量请求值为 20" in messages


def test_list_authorized_awemes_accepts_official_filtering_fields():
    spec = _load_rule("list-authorized-awemes.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "marketing_goal": "VIDEO_IMAGE",
            "page": 1,
            "page_size": 20,
            "filtering": {"search_key_word": "膜一姐"},
        },
        spec,
    )

    assert errors == []


def test_list_authorized_awemes_maps_official_filtering_keyword_to_mcp_payload():
    spec = _load_rule("list-authorized-awemes.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "marketing_goal": "VIDEO_IMAGE",
            "page": 2,
            "page_size": 3,
            "filtering": {"search_key_word": "膜一姐"},
        },
    )

    assert payload["searchKeyWord"] == "膜一姐"
    assert "filtering" not in payload


def test_list_authorized_awemes_rejects_page_and_page_size_boundaries_locally():
    spec = _load_rule("list-authorized-awemes.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "marketing_goal": "VIDEO_IMAGE",
            "page": 0,
            "page_size": 101,
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "页码 不能小于 1。" in messages
    assert "每页数量 不能大于 100。" in messages


def test_list_authorized_awemes_rejects_non_string_keyword_locally():
    spec = _load_rule("list-authorized-awemes.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "marketing_goal": "VIDEO_IMAGE",
            "page": 1,
            "page_size": 3,
            "filtering": {"search_key_word": 12345},
        },
        spec,
    )

    messages = [item["message"] for item in errors]
    assert "搜索关键词 类型不正确，应为字符串。" in messages


def test_list_authorized_awemes_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-authorized-awemes.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-aweme-list",
            "data": {
                "pageInfo": {"page": 1, "pageSize": 20, "totalNumber": 1, "totalPage": 1},
                "awemeIdList": [
                    {
                        "awemeId": "1234567890",
                        "awemeName": "膜一姐官方号",
                        "awemeAvatar": "https://example.invalid/avatar.png",
                        "authType": "OFFICIAL",
                        "awemeHasUniProm": False,
                        "canCreateRoi2Ad": True,
                    }
                ],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localAwemeAuthorizedGet", "raw": raw, "request_id": "req-aweme-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "marketing_goal": "VIDEO_IMAGE",
                "page": 1,
                "page_size": 20,
                "filtering": {"search_key_word": "膜一姐"},
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "抖音号：1234567890" in display
    assert "抖音号名称：膜一姐官方号" in display
    assert "抖音号授权类型：官方" in display
    assert "该抖音号是否有直播roi2计划投放：否" in display
    assert "该抖音号是否能创建roi2单元：是" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_list_consult_awemes_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-consult-awemes.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-consult-aweme-list",
            "data": {
                "pageInfo": {"page": 1, "pageSize": 5, "totalNumber": 1, "totalPage": 1},
                "consultAwemeList": [
                    {
                        "consultAwemeUid": "34162141808",
                        "awemeName": "膜一姐品牌管理有限公司",
                        "awemeAvatar": "https://example.invalid/consult-avatar.png",
                        "authType": "OFFICIAL",
                    }
                ],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localImAccountGet", "raw": raw, "request_id": "req-consult-aweme-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "delivery_goal": "POI",
                "poi_ids": [6932952586303604740],
                "page": 1,
                "page_size": 5,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "私信接待抖音号：34162141808" in display
    assert "抖音号名称：膜一姐品牌管理有限公司" in display
    assert "抖音号授权类型：官方" in display
    assert "页面大小：5" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_list_consult_awemes_rejects_invalid_auth_type_items_locally():
    spec = _load_rule("list-consult-awemes.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "auth_type": ["HALF_OFFICIAL"],
            "page": 1,
            "page_size": 3,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "抖音号授权类型" in messages
    assert "HALF_OFFICIAL" in messages
    assert "OFFICIAL（官方）" in messages
    assert "SELF（自运营）" in messages


def test_batch_update_project_status_partial_platform_errors_are_user_visible_without_request_id():
    spec = _load_rule("batch-update-project-status.json")
    raw_payload = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-status-partial",
            "data": {
                "projectIds": [7636841423678226451],
                "errors": [
                    {
                        "projectId": 999999999999999999,
                        "errorMessage": "项目不存在或者项目已被删除",
                    }
                ],
            },
        },
    }
    raw = [{"type": "text", "text": f"[TextContent(type='text', text='{json.dumps(raw_payload, ensure_ascii=False)}')]"}]

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localProjectStatusBatchUpdate", "raw": raw, "request_id": None},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "items": [
                    {"project_id": 7636841423678226451, "opt_status": "PAUSED"},
                    {"project_id": 999999999999999999, "opt_status": "PAUSED"},
                ],
            },
        )

    assert result["success"] is False
    message = result["errors"][0]["message"]
    assert "项目ID 7636841423678226451：平台已受理" in message
    assert "项目ID 999999999999999999：项目不存在或者项目已被删除" in message
    assert "requestId" not in message
    assert "req-status-partial" not in message
    assert "{" not in message


def test_batch_update_project_week_schedule_platform_error_array_is_user_visible_without_request_id():
    spec = _load_rule("batch-update-project-week-schedule.json")
    raw_payload = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-week-schedule-partial",
            "data": {
                "projectIds": None,
                "error": [
                    {
                        "projectId": 999999999999999999,
                        "errorMessage": "项目不存在或已被删除",
                    }
                ],
            },
        },
    }
    raw = [{"type": "text", "text": f"[TextContent(type='text', text='{json.dumps(raw_payload, ensure_ascii=False)}')]"}]

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={
            "tool_name": "nacos-mcp-router_use_tool:localProjectWeekScheduleBatchUpdate",
            "raw": raw,
            "request_id": None,
        },
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "items": [
                    {
                        "project_id": 999999999999999999,
                        "schedule_scene": "REALTIME",
                        "schedule_time": "1" * 336,
                    },
                ],
            },
        )

    assert result["success"] is False
    message = result["errors"][0]["message"]
    assert "项目ID 999999999999999999：项目不存在或已被删除" in message
    assert "requestId" not in message
    assert "req-week-schedule-partial" not in message
    assert "{" not in message


def test_list_custom_audiences_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-custom-audiences.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-custom-audience-list",
            "data": {
                "customAudienceList": [
                    {
                        "customAudienceId": 10001,
                        "customAudienceName": "膜一姐会员人群",
                        "coverNum": 1234,
                        "status": "AVAILABLE",
                    }
                ],
                "pageInfo": {"page": 1, "pageSize": 5, "totalNumber": 1, "totalPage": 1},
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localCustomAudienceGet", "raw": raw, "request_id": "req-custom-audience-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "tags_type": "CUSTOM",
                "page": 1,
                "page_size": 5,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "人群包ID：10001" in display
    assert "人群包名称：膜一姐会员人群" in display
    assert "覆盖量：1234" in display
    assert "状态：可用" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_list_custom_audiences_keeps_official_tags_type_for_mcp_payload():
    spec = _load_rule("list-custom-audiences.json")

    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "tags_type": "SYS_RECOMMEND",
            "page": 2,
            "page_size": 1000,
        },
    )

    assert payload["tagsType"] == "SYS_RECOMMEND"
    assert payload["pageSize"] == 1000


def test_list_custom_audiences_displays_textcontent_wrapped_mcp_response():
    spec = _load_rule("list-custom-audiences.json")
    raw = [
        {
            "type": "text",
            "text": (
                "[TextContent(type='text', text='"
                '{"code":0,"msg":"请求成功","data":{"code":0,"data":{"customAudienceList":[],'
                '"pageInfo":{"page":1,"pageSize":5,"totalNumber":0,"totalPage":0}},'
                '"message":"OK","requestId":"req-empty-custom-audience"}}'
                "', annotations=None, meta=None)]"
            ),
        }
    ]

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localCustomAudienceGet", "raw": raw, "request_id": "req-empty-custom-audience"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "tags_type": "CUSTOM",
                "page": 1,
                "page_size": 5,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "页码：1" in display
    assert "页面大小：5" in display
    assert "总数：0" in display
    assert "请求日志id" not in display


def test_list_custom_audiences_requires_tags_type_before_mcp_call():
    spec = _load_rule("list-custom-audiences.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "page": 1,
            "page_size": 5,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "人群包属性是什么值？" in messages
    assert "自定义人群包" in messages
    assert "系统推荐人群包" in messages


def test_list_custom_audiences_rejects_page_less_than_one_locally():
    spec = _load_rule("list-custom-audiences.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "tags_type": "CUSTOM",
            "page": 0,
            "page_size": 5,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "页码 不能小于 1。" in messages


def test_list_tool_packs_uses_platform_intelligent_selection_mode_values():
    spec = _load_rule("list-tool-packs.json")

    valid_errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "page": 1,
            "page_size": 5,
        },
        spec,
    )
    invalid_errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "intelligent_selection_mode": "OFF",
            "page": 1,
            "page_size": 5,
        },
        spec,
    )
    payload = build_mcp_payload(
        spec,
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "page": 1,
            "page_size": 5,
        },
    )

    assert valid_errors == []
    assert "获取线索方式" in "\n".join(error["message"] for error in invalid_errors)
    assert payload["intelligentSelectionMode"] == "INTELLIGENT_SELECTION_MODE_OFF"


def test_list_tool_packs_rejects_page_less_than_one_locally():
    spec = _load_rule("list-tool-packs.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "page": 0,
            "page_size": 5,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "页码 不能小于 1。" in messages


def test_list_tool_packs_rejects_page_size_less_than_one_locally():
    spec = _load_rule("list-tool-packs.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
            "page": 1,
            "page_size": 0,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "每页数量 不能小于 1。" in messages


def test_list_tool_packs_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-tool-packs.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-tool-pack-list",
            "data": {
                "toolPackList": [
                    {
                        "toolPackId": 10001,
                        "toolPackName": "预约表单",
                        "toolPackTypes": ["TOOL_TYPE_FORM"],
                        "enable": True,
                        "enableIntelligentSelection": False,
                    }
                ],
                "pagination": {"page": 1, "pageSize": 5, "totalPage": 1, "totalNum": 1},
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localToolPackListGet", "raw": raw, "request_id": "req-tool-pack-list"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "delivery_goal": "POI",
                "poi_ids": [6932952586303604740],
                "intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF",
                "page": 1,
                "page_size": 5,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "留资组件ID：10001" in display
    assert "留资组件名称：预约表单" in display
    assert "组件类型：表单预约" in display
    assert "组件是否可用：是" in display
    assert "是否支持智能优选：否" in display
    assert "页码：1" in display
    assert "页面大小：5" in display
    assert "总页数：1" in display
    assert "总数：1" in display
    assert "请求日志id" not in display


def test_get_tool_pack_detail_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("get-tool-pack-detail.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-tool-pack-detail",
            "data": {
                "toolPackInfo": {
                    "toolPackId": 30629751298,
                    "toolPackName": "陈舵主",
                    "toolPackTypes": ["TOOL_TYPE_FORM", "TOOL_TYPE_PHONE_SMART"],
                    "enable": True,
                    "enableIntelligentSelection": True,
                }
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localToolPackDetailGet", "raw": raw, "request_id": "req-tool-pack-detail"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "tool_pack_id": 30629751298,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "留资组件ID：30629751298" in display
    assert "留资组件名称：陈舵主" in display
    assert "组件类型：表单预约" in display
    assert "组件类型：电话咨询" in display
    assert "组件是否可用：是" in display
    assert "是否支持智能优选：是" in display
    assert "请求日志id" not in display


def test_list_market_pages_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("list-market-pages.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-market-pages",
            "data": {
                "markPageIdList": [
                    {
                        "marketPageId": 987654321,
                        "marketPageName": "门店预约页",
                        "status": "MARKET_PAGE_ENABLE",
                        "coverImageUrl": "https://example.com/cover.jpg",
                        "toolPackInfo": {
                            "toolPackId": 30629751298,
                            "toolPackTypes": ["TOOL_TYPE_FORM", "TOOL_TYPE_PHONE_SMART"],
                        },
                    }
                ],
                "pageInfo": {"page": 1, "pageSize": 5, "totalNumber": 1, "totalPage": 1},
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localMarketPageListGet", "raw": raw, "request_id": "req-market-pages"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "delivery_goal": "POI",
                "poi_ids": [6932952586303604740],
                "page": 1,
                "page_size": 5,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "营销页ID：987654321" in display
    assert "营销页名称：门店预约页" in display
    assert "营销页状态：可用" in display
    assert "关联留资组件ID：30629751298" in display
    assert "关联留资方式：表单预约" in display
    assert "关联留资方式：电话咨询" in display
    assert "页码：1" in display
    assert "页面大小：5" in display
    assert "总数：1" in display
    assert "总页数：1" in display
    assert "请求日志id" not in display


def test_list_market_pages_rejects_page_less_than_one_locally():
    spec = _load_rule("list-market-pages.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [6932952586303604740],
            "page": 0,
            "page_size": 5,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "页码 不能小于 1。" in messages


def test_list_market_pages_rejects_empty_required_id_lists_locally():
    spec = _load_rule("list-market-pages.json")

    poi_errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "POI",
            "poi_ids": [],
            "page": 1,
            "page_size": 5,
        },
        spec,
    )
    product_errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "delivery_goal": "PRODUCT",
            "product_ids": [],
            "page": 1,
            "page_size": 5,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in [*poi_errors, *product_errors])
    assert "门店ID列表 至少需要 1 项。" in messages
    assert "商品ID列表 至少需要 1 项。" in messages


def test_get_tool_pack_detail_rejects_tool_pack_id_less_than_one_locally():
    spec = _load_rule("get-tool-pack-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "tool_pack_id": 0,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "留资组件ID 不能小于 1。" in messages


def test_get_tool_pack_detail_rejects_tool_pack_id_above_int64_locally():
    spec = _load_rule("get-tool-pack-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "tool_pack_id": 999999999999999999999999999999,
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "留资组件ID 不能大于 9223372036854775807。" in messages


def test_get_market_page_detail_exposes_official_response_fields_for_agent_display():
    spec = _load_rule("get-market-page-detail.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-market-page-detail",
            "data": {
                "markPageInfo": [
                    {
                        "marketPageId": 7628817210925580351,
                        "marketPageName": "门店营销页4.15李",
                        "status": "MARKET_PAGE_ENABLE",
                        "coverImageUrl": "https://example.com/market-page.jpg",
                        "toolPackInfo": {
                            "toolPackId": 18948445186,
                            "toolPackTypes": ["TOOL_TYPE_FORM", "TOOL_TYPE_CONSULT"],
                        },
                    }
                ]
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localMarketPageGet", "raw": raw, "request_id": "req-market-page-detail"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "market_page_ids": [7628817210925580351],
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "营销页ID：7628817210925580351" in display
    assert "营销页名称：门店营销页4.15李" in display
    assert "营销页状态：可用" in display
    assert "关联留资组件ID：18948445186" in display
    assert "关联留资方式：表单预约" in display
    assert "关联留资方式：私信咨询" in display
    assert "请求日志id" not in display


def test_get_market_page_detail_empty_result_omits_request_id_from_display():
    spec = _load_rule("get-market-page-detail.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-empty-market-page",
            "data": {
                "markPageInfo": [],
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localMarketPageGet", "raw": raw, "request_id": "req-empty-market-page"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "market_page_ids": [999999999999999999],
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "营销页详情：空" in display
    assert "请求日志id" not in display
    assert "req-empty-market-page" not in display


def test_get_market_page_detail_rejects_non_numeric_market_page_id_locally():
    spec = _load_rule("get-market-page-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "market_page_ids": ["ABC"],
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "营销页ID列表第 1 项 类型不正确，应为数字。" in messages


def test_get_market_page_detail_rejects_market_page_id_less_than_one_locally():
    spec = _load_rule("get-market-page-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "market_page_ids": [0],
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "营销页ID列表第 1 项 不能小于 1。" in messages


def test_get_market_page_detail_rejects_market_page_id_above_int64_locally():
    spec = _load_rule("get-market-page-detail.json")

    errors = validate_payload(
        {
            "local_account_id": 1854708763953159,
            "market_page_ids": [999999999999999999999999999999],
        },
        spec,
    )

    messages = "\n".join(error["message"] for error in errors)
    assert "营销页ID列表第 1 项 不能大于 9223372036854775807。" in messages


def test_mcp_runtime_exception_message_is_sanitized_for_user_display():
    spec = _load_rule("get-poi-ids-by-multi-poi-id.json")
    raw = [
        {
            "type": "text",
            "text": (
                "[TextContent(type='text', text='"
                "{\"code\":0,\"msg\":\"请求成功\",\"data\":{\"code\":40000,\"data\":null,"
                "\"message\":\"\\'NoneType\\' object has no attribute \\'items\\'\","
                "\"requestId\":\"req-runtime-exception\"}}"
                "', annotations=None, meta=None)]"
            ),
        }
    ]

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localMultiPoiIdPoiIdsGet", "raw": raw, "request_id": "req-runtime-exception"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "multi_poi_ids": [6932952586303604740],
                "need_enable": True,
            },
        )

    assert result["success"] is False
    message = result["errors"][0]["message"]
    assert message == "MCP 工具返回内部异常，请检查输入是否属于当前账户且资源有效。"
    assert "NoneType" not in message
    assert "items" not in message


def test_mcp_exception_group_message_is_sanitized_for_user_display():
    spec = _load_rule("list-market-pages.json")
    exc = ExceptionGroup("unhandled errors in a TaskGroup", [RuntimeError("Server disconnected without sending a response.")])

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        side_effect=exc,
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "delivery_goal": "PRODUCT",
                "product_ids": [1840240933753866],
                "page": 1,
                "page_size": 10,
            },
    )

    assert result["success"] is False
    text = result["errors"][0]["message"]
    assert "MCP 连接中断" in text
    assert "Server disconnected without sending a response" in text
    assert "TaskGroup" not in text


def test_get_poi_ids_by_multi_poi_id_exposes_response_fields_for_agent_display():
    spec = _load_rule("get-poi-ids-by-multi-poi-id.json")
    raw = {
        "code": 0,
        "msg": "请求成功",
        "data": {
            "code": 0,
            "message": "OK",
            "requestId": "req-multi-poi",
            "data": {
                "multiPoiInfo": [
                    {
                        "multiPoiId": 1863469399952475,
                        "poiIds": [6932952586303604740, 7075207981536643086],
                    }
                ]
            },
        },
    }

    with patch(
        "tools.oceanengine_local_project_runtime.mcp_client.invoke_endpoint",
        return_value={"tool_name": "nacos-mcp-router_use_tool:localMultiPoiIdPoiIdsGet", "raw": raw, "request_id": "req-multi-poi"},
    ):
        result = endpoint_runner.run_endpoint(
            spec,
            {
                "local_account_id": 1854708763953159,
                "multi_poi_ids": [1863469399952475],
                "need_enable": True,
            },
        )

    assert result["success"] is True
    display = result["data"]["display_text"]
    assert "多门店ID：1863469399952475" in display
    assert "门店ID：6932952586303604740" in display
    assert "门店ID：7075207981536643086" in display
    assert "请求日志id" not in display


def test_get_poi_ids_by_multi_poi_id_accepts_singular_natural_alias_before_required_check():
    spec = _load_rule("get-poi-ids-by-multi-poi-id.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "multi_poi_id": 1863469399952475,
            "need_enable": True,
        },
    )

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "本地推投放账户ID是什么值？" in messages
    assert "multi_poi_id 不是官方文档支持的参数字段" not in messages
    assert "多门店ID列表 为必填参数" not in messages


def test_get_poi_ids_by_multi_poi_id_accepts_natural_account_alias_and_string_id():
    spec = _load_rule("get-poi-ids-by-multi-poi-id.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "account_id": "1854708763953159",
            "multi_poi_ids": "1863469399952475",
            "need_enable": True,
        },
        dry_run=True,
    )

    assert result["success"] is True
    assert result["data"]["payload"]["local_account_id"] == 1854708763953159
    assert result["data"]["payload"]["multi_poi_ids"] == [1863469399952475]


def test_get_poi_ids_by_multi_poi_id_rejects_non_numeric_array_item_locally():
    spec = _load_rule("get-poi-ids-by-multi-poi-id.json")

    result = endpoint_runner.run_endpoint(
        spec,
        {
            "local_account_id": 1854708763953159,
            "multi_poi_ids": ["ABC"],
            "need_enable": True,
        },
    )

    assert result["success"] is False
    messages = "\n".join(error["message"] for error in result["errors"])
    assert "多门店ID列表第 1 项 类型不正确，应为数字。" in messages
    assert "Cannot deserialize" not in messages


def test_oceanengine_local_project_accepts_mcp_style_capability_alias(monkeypatch):
    observed = {}

    def fake_run_endpoint(spec, payload, *, dry_run=False):
        observed["rule_name"] = spec["name"]
        observed["mcp_tool"] = spec["mcp"]["tool"]
        observed["payload"] = payload
        observed["dry_run"] = dry_run
        return {"success": True, "message": "ok", "data": {}}

    monkeypatch.setattr(endpoint_runner, "run_endpoint", fake_run_endpoint)

    result = run_oceanengine_local_project(
        "local-poi-get",
        {"local_account_id": 1854708763953159},
        dry_run=True,
    )

    assert result["success"] is True
    assert observed == {
        "rule_name": "list-promotable-pois",
        "mcp_tool": "localPoiGet",
        "payload": {"local_account_id": 1854708763953159},
        "dry_run": True,
    }


def test_oceanengine_local_project_skill_preserves_page_size_boundary_and_avoids_output_field_prompts():
    skill_text = (REPO_ROOT / "skills/custom/oceanengine-local-project/SKILL.md").read_text(encoding="utf-8")
    tool_pack_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/list-tool-packs.md"
    ).read_text(encoding="utf-8")
    consult_aweme_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/list-consult-awemes.md"
    ).read_text(encoding="utf-8")
    status_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/batch-update-project-status.md"
    ).read_text(encoding="utf-8")
    schedule_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/batch-update-project-week-schedule.md"
    ).read_text(encoding="utf-8")
    poi_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/list-promotable-pois.md"
    ).read_text(encoding="utf-8")
    authorized_aweme_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/list-authorized-awemes.md"
    ).read_text(encoding="utf-8")
    list_project_reference = (
        REPO_ROOT / "skills/custom/oceanengine-local-project/references/list-projects.md"
    ).read_text(encoding="utf-8")

    assert "用户说“每页 N 条”时，N 必须作为 `page_size` 原样传入" in skill_text
    assert "用户说“第 N 页”或“页码 N”时，N 必须作为 `page` 原样传入" in skill_text
    assert "不得把用户给出的其他获取线索方式猜成自定义或智能优选" in skill_text
    assert "不得把其他值猜成自定义或智能优选" in tool_pack_reference
    assert "不得追问用户希望展示哪些返回字段" in skill_text
    assert "用户要求根据多门店ID拉取门店ID" in skill_text
    assert "只缺少本地推投放账户ID时，只追问本地推投放账户ID" in skill_text
    assert "缺少字段时只使用中文业务字段名追问" in skill_text
    assert "用户明确说空列表时，必须把空数组原样传给业务工具校验" in skill_text
    assert "用户给出的数组项数量超过规则上限时，也必须把全量数组原样交给业务工具校验" in skill_text
    assert "半官方授权”不得猜成“官方授权" in skill_text
    assert "品牌曝光”不得猜成“线上互动" in skill_text
    assert "不得映射成官方或自运营" in consult_aweme_reference
    assert "营销页列表/详情查询" in skill_text
    assert "不要先搜索或直连 `nacos-mcp-router`" in skill_text
    assert "暂停投放”必须整理为 `items=[{\"project_id\": 用户项目ID, \"opt_status\": \"PAUSED\"}]`" in skill_text
    assert "启用项目”必须整理为 `items=[{\"project_id\": 用户项目ID, \"opt_status\": \"ENABLE\"}]`" in skill_text
    assert "不得使用 `project_ids`、`status`、`PROJECT_STATUS_DISABLE` 或 `PROJECT_STATUS_ENABLE` 构造状态更新 payload" in skill_text
    assert "重复给出的项目 ID 必须在 `items` 中按出现次数原样保留" in skill_text
    assert "暂停投放”必须整理为 `items[].opt_status=PAUSED`" in status_reference
    assert "启用项目”必须整理为 `items[].opt_status=ENABLE`" in status_reference
    assert "重复项目 ID 不得合并、去重或改为查询其它项目" in status_reference
    assert "不得创建脚本或文件来计算 `schedule_time`" in skill_text
    assert "WORKDAY_9_18_SCHEDULE_TIME" in schedule_reference
    assert "WORKDAY_PEAK_SCHEDULE_TIME" in schedule_reference
    assert "不得在缺少项目 ID 时查询全部项目并批量修改投放时段" in schedule_reference
    assert "名称里带 X”或“关键词 X”必须写入 `filtering.search_key_word=X`" in poi_reference
    assert "商品 ID 必须写入 `filtering.product_id`" in poi_reference
    assert "不能确认省市 ID 时，必须追问省市 ID，不得静默删除地区条件" in poi_reference
    assert "不得在遗漏用户过滤条件后用未过滤结果筛选展示" in poi_reference
    assert "长视频”不是官方支持的抖音号使用场景" in skill_text
    assert "不得把“长视频”猜成 `VIDEO_IMAGE`" in authorized_aweme_reference
    assert "项目列表查询必须把用户给出的每个筛选条件都写入 `filtering`" in skill_text
    assert "更新项目请求缺少项目 ID 时，只追问项目 ID，不得改查项目列表" in skill_text
    assert "不得从项目详情中复用旧的高峰日预算上调比例" in skill_text
    assert "不得先查宽列表再用返回结果口头筛选展示" in list_project_reference
    assert "用户给出不在允许范围内的项目列表筛选词时，不得先查宽项目列表" in list_project_reference
    assert "线上互动”必须写入 `filtering.local_delivery_scene=CONTENT_HEAT`" in list_project_reference
    assert "智能出价”必须写入 `filtering.bid_type=SMART`" in list_project_reference


def test_oceanengine_local_project_tool_description_preserves_empty_list_boundary():
    description = oceanengine_local_project_tool.description

    assert "empty list boundary" in description
    assert "call this tool" in description
    assert "do not guess" in description
    assert "custom or intelligent selection" in description
