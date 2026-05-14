# 创建项目

来源：巨量引擎开放平台“创建项目”文档，doc_id `1808094783305739`，接口 `/open_api/v3.0/local/project/create/`，POST。

## 字段覆盖

本接口按官方请求参数逐字段维护规则。完整 65 字段核对表见 `references/create-project-field-checklist.md`；每个字段都必须有 rule、reference、校验逻辑、测试或差异说明结论，不得只用 `audience` 整体透传替代子字段。

## 普通必填参数

- `local_account_id`：本地推投放账户ID。
- `name`：项目名称，1 到 50 个字。
- `marketing_goal`：营销场景，允许 `LIVE` 直播、`VIDEO_IMAGE` 短视频/图文。
- `local_delivery_scene`：营销目的，允许 `CONTENT_HEAT` 线上互动、`POI_RECOMMEND` 线下到店、`PRODUCT_PAY` 团购成交、`EXTERNAL` 获取线索。
- `ad_type`：单元类型，允许 `GENERAL` 通投、`SEARCHING` 搜索。
- `schedule_type`：投放日期类型设置，允许 `FROM_NOW_ON`、`START_TO_END`、`FIXED_TIME`、`DELIVERY_7DAY`、`DAILY_DELIVERY_DURATION`。
- `bid_type`：出价方式，允许 `MANUAL`、`SMART`、`STABILIZE_COSTS`、`MAX_CONVERSION`。
- `budget_mode`：预算模式设置，允许 `BUDGET_MODE_DAY`、`BUDGET_MODE_TOTAL`、`BUDGET_MODE_7DAY_TOTAL`。
- `budget`：项目预算，单位为分。

`audience` 自身为非必填对象；当传入 `audience` 时，其内部官方必填字段按完整路径校验，例如 `audience.district`、`audience.region.region_ver`、`audience.custom_area.geolocation[].lat`。

## 条件必填与禁止规则

- `marketing_goal=VIDEO_IMAGE` 时，`delivery_goal` 必填；`marketing_goal=LIVE` 时，`delivery_goal` 无效。
- `marketing_goal=VIDEO_IMAGE` 且 `delivery_goal=POI` 时，`delivery_poi_mode` 必填。
- `delivery_goal=POI` 且 `delivery_poi_mode=PART` 时，`promotion_poi_ids` 必填。
- `marketing_goal=VIDEO_IMAGE` 且 `delivery_goal=PRODUCT` 时，`product_id` 必填。
- `marketing_goal=VIDEO_IMAGE` 且 `delivery_goal=PRODUCT` 时，`promotion_poi_ids` 不可传；如果用户同时要求投商品和指定门店，必须保留门店 ID 交给业务工具校验并返回中文冲突原因，不得静默忽略门店。
- `marketing_goal=LIVE` 且 `local_delivery_scene=CONTENT_HEAT` 或 `PRODUCT_PAY` 时，`aweme_id` 必填。
- `local_delivery_scene=EXTERNAL` 时，`external_action` 必填，且不支持传入 `aweme_id`。
- `marketing_goal=VIDEO_IMAGE` 且 `local_delivery_scene=POI_RECOMMEND` 或 `PRODUCT_PAY` 时，不支持传入 `external_action`。
- `marketing_goal=VIDEO_IMAGE` 且 `local_delivery_scene=POI_RECOMMEND` 时，`delivery_goal` 仅支持 `POI`。
- 传入 `audience` 时，`audience.district` 必填。
- `audience.district=REGION` 时，`audience.region`、`audience.region.city`、`audience.region.region_ver` 必填。
- `audience.district=LOCAL` 时，`audience.custom_area` 必填；传入 `audience.custom_area.geolocation` 时，每一项必须填写 `area_radius`、`long`、`lat`。
- `audience.district=POI` 时，`audience.poi_around` 必填；直播门店附近定向还必须填写 `audience.poi_around.poi_around_ids`。
- `local_delivery_scene=EXTERNAL` 且 `audience.customized_interest_action=INTERESTACTION_CUSTOM` 时，兴趣和行为至少填写一类。
- 传入 `audience.interest_config` 时，`interest_categories` 与 `interest_words` 至少填写一个。
- 传入 `audience.action_config` 时，`action_days` 必填，且 `action_categories` 与 `action_words` 至少填写一个。
- `schedule_type=FIXED_TIME` 时，`schedule_fixed_seconds` 必填，且不支持传入 `schedule_time`。
- `schedule_type=START_TO_END` 时，`start_time`、`end_time` 必填；`schedule_type=DELIVERY_7DAY` 时，`start_time` 必填。
- `marketing_goal=VIDEO_IMAGE` 且 `local_delivery_scene=POI_RECOMMEND` 或 `PRODUCT_PAY` 时，`is_set_peak_budget` 必填。
- `is_set_peak_budget=true` 时，`high_budget_rate` 必填，且 `peak_week_days` 与 `peak_holidays` 至少填写一个；`is_set_peak_budget=false` 时不得填写高峰日和上调比例。
- `marketing_goal=LIVE` 且 `schedule_type=DAILY_DELIVERY_DURATION` 时，`daily_delivery_seconds` 必填。
- `marketing_goal=VIDEO_IMAGE` 且 `local_delivery_scene=EXTERNAL` 时，`delivery_package`、`intelligent_selection_mode` 必填。
- `marketing_goal=VIDEO_IMAGE`、`local_delivery_scene=EXTERNAL`、`ad_type=GENERAL` 时，`aigc_dynamic_creative_switch` 必填。
- 自定义获取线索方式 `intelligent_selection_mode=INTELLIGENT_SELECTION_MODE_OFF` 时，`local_asset_type` 必填；选择营销页时 `market_page_ids` 必填。
- `tool_pack_id` 在获取线索场景按官方规则校验；官方说明中的无需传入场景依赖外部接口结果时，应记录为需要预查询。

## 非必填字段

非必填字段缺失时不阻断创建；一旦用户传入，脚本仍会校验类型、枚举、数量、范围、格式和条件禁止规则。典型字段包括 `auto_update_pois`、`schedule_time`、`bid`、`peak_week_days`、`peak_holidays`、`audience.gender`、`audience.retargeting_tags`、`audience.hide_if_converted`、`audience.converted_time_duration` 等。

## 关键限制

- `schedule_time` 必须是 336 位 `0`/`1` 字符串。
- `schedule_fixed_seconds`、`daily_delivery_seconds` 必须不小于 1800，且为 1800 的整数倍。
- `budget` 单位为分：日预算智能出价范围 `[10000, 999999999]`；日预算手动出价和总预算范围 `[30000, 999999999]`。
- `bid` 单位为分：展示量范围 `[400,10000]`；其他场景基础范围 `[1,1000000]`。
- `market_page_ids` 最多 10 个。
- `audience.custom_area.geolocation` 最多 1000 个。
- `audience.poi_around.poi_around_ids` 最多 2000 个。
- `audience.retargeting_tags`、`audience.retargeting_tags_exclude` 最多 200 个。

## 官方差异说明

- 官方说明段落中的 `VIDEO_AND_IMAGE`、`VIDEO__IMAGE` 统一归一为基础参数表枚举 `VIDEO_IMAGE`；不得暴露为用户可传枚举。
- 官方说明段落中的 `PRODUCT_PURCHASE` 统一归一为基础参数表枚举 `PRODUCT_PAY`；不得暴露为用户可传枚举。
- 依赖外部结果的规则，例如门店数量是否超过 2000、商品适用门店、留资组件或营销页是否包含私信组件，只能在具备预查询结果时完全确认；否则应返回需补充或预查询说明，不得声称已完全校验。

## MCP 映射说明

- 历史输入 `budget_mode=DAY/TOTAL/ALL` 会在脚本调用 MCP 时映射为接口枚举；官方推荐直接使用 `BUDGET_MODE_DAY`、`BUDGET_MODE_TOTAL`、`BUDGET_MODE_7DAY_TOTAL`。
- 本地 MCP 工具固定为 `localProjectCreate`，请求 path 固定为 `/open_api/v3.0/local/project/create/`。

## 执行确认

创建成功后使用返回的 `project_id` 查询项目详情或项目列表，确认项目存在且核心字段一致。确认失败最多重试 3 次。

## 示例

```json
{
  "local_account_id": 123456,
  "name": "测试项目",
  "marketing_goal": "VIDEO_IMAGE",
  "local_delivery_scene": "CONTENT_HEAT",
  "ad_type": "GENERAL",
  "delivery_goal": "POI",
  "delivery_poi_mode": "ALL",
  "schedule_type": "FROM_NOW_ON",
  "bid_type": "SMART",
  "budget_mode": "BUDGET_MODE_DAY",
  "budget": 10000
}
```
