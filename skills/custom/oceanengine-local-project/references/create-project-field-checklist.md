# 创建项目逐字段核对表

来源：巨量引擎开放平台“创建项目”文档，doc_id `1808094783305739`，核对日期：2026-04-30。

状态说明：`rule` 表示已进入 `rules/create-project.json` 的 `fields` 或约束；`reference` 表示已在 `references/create-project.md` 或本表记录；`validator/test` 表示由通用校验器、创建项目单测或字段覆盖测试覆盖。全部 65 个官方字段均需有结论。

| 序号 | 字段路径 | 官方必填性 | rule | reference | validator/test |
|---:|---|---|---|---|---|
| 1 | `local_account_id` | 必填 | 完成 | 完成 | 必填测试 |
| 2 | `name` | 必填 | 完成 | 完成 | 字段覆盖测试 |
| 3 | `marketing_goal` | 必填 | 完成 | 完成 | 枚举测试 |
| 4 | `local_delivery_scene` | 必填 | 完成 | 完成 | 枚举/条件测试 |
| 5 | `ad_type` | 必填 | 完成 | 完成 | 条件禁止测试 |
| 6 | `delivery_goal` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 7 | `delivery_poi_mode` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 8 | `promotion_poi_ids` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 9 | `auto_update_pois` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 10 | `product_id` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 11 | `aweme_id` | 条件必填 | 完成 | 完成 | 条件必填/禁止测试 |
| 12 | `external_action` | 条件必填 | 完成 | 完成 | 条件必填/禁止测试 |
| 13 | `audience` | 非必填 | 完成 | 完成 | 类型测试 |
| 14 | `audience.district` | 必填 | 完成 | 完成 | 嵌套路径测试 |
| 15 | `audience.region` | 条件必填 | 完成 | 完成 | 嵌套路径测试 |
| 16 | `audience.region.city` | 必填 | 完成 | 完成 | 嵌套路径测试 |
| 17 | `audience.region.city_divide` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 18 | `audience.region.location_type` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 19 | `audience.region.region_ver` | 必填 | 完成 | 完成 | 嵌套路径测试 |
| 20 | `audience.custom_area` | 条件必填 | 完成 | 完成 | 数组项路径测试 |
| 21 | `audience.custom_area.geolocation` | 非必填 | 完成 | 完成 | 数组项路径测试 |
| 22 | `audience.custom_area.geolocation[].name` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 23 | `audience.custom_area.geolocation[].area_radius` | 必填 | 完成 | 完成 | 数组项路径测试 |
| 24 | `audience.custom_area.geolocation[].long` | 必填 | 完成 | 完成 | 数组项路径测试 |
| 25 | `audience.custom_area.geolocation[].lat` | 必填 | 完成 | 完成 | 数组项路径测试 |
| 26 | `audience.poi_around` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 27 | `audience.poi_around.poi_around_ids` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 28 | `audience.poi_around.poi_around_radius` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 29 | `audience.age` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 30 | `audience.gender` | 非必填 | 完成 | 完成 | 非必填枚举测试 |
| 31 | `audience.retargeting_tags` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 32 | `audience.retargeting_tags_exclude` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 33 | `audience.hide_if_converted` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 34 | `audience.converted_time_duration` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 35 | `audience.filter_aweme_abnormal_active` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 36 | `audience.filter_aweme_fans_count` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 37 | `audience.customized_interest_action` | 非必填 | 完成 | 完成 | 字段覆盖测试 |
| 38 | `audience.interest_config` | 条件必填 | 完成 | 完成 | 条件规则测试 |
| 39 | `audience.interest_config.interest_categories` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 40 | `audience.interest_config.interest_words` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 41 | `audience.action_config` | 条件必填 | 完成 | 完成 | 条件规则测试 |
| 42 | `audience.action_config.action_categories` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 43 | `audience.action_config.action_words` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 44 | `audience.action_config.action_days` | 条件必填 | 完成 | 完成 | 条件规则测试 |
| 45 | `schedule_type` | 必填 | 完成 | 完成 | 必填/枚举测试 |
| 46 | `schedule_fixed_seconds` | 条件必填 | 完成 | 完成 | 条件必填/整数倍测试 |
| 47 | `start_time` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 48 | `end_time` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 49 | `schedule_time` | 非必填 | 完成 | 完成 | 长度/格式测试 |
| 50 | `bid_type` | 必填 | 完成 | 完成 | 必填/枚举测试 |
| 51 | `bid` | 非必填 | 完成 | 完成 | 范围/金额归一测试 |
| 52 | `budget_mode` | 必填 | 完成 | 完成 | 必填/映射测试 |
| 53 | `budget` | 必填 | 完成 | 完成 | 范围/金额归一测试 |
| 54 | `is_set_peak_budget` | 条件必填 | 完成 | 完成 | 条件必填测试 |
| 55 | `peak_week_days` | 非必填 | 完成 | 完成 | 至少一项测试 |
| 56 | `peak_holidays` | 非必填 | 完成 | 完成 | 至少一项测试 |
| 57 | `high_budget_rate` | 条件必填 | 完成 | 完成 | 条件必填/范围测试 |
| 58 | `daily_delivery_seconds` | 条件必填 | 完成 | 完成 | 条件必填/整数倍测试 |
| 59 | `delivery_package` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 60 | `aigc_dynamic_creative_switch` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 61 | `intelligent_selection_mode` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 62 | `local_asset_type` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 63 | `tool_pack_id` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
| 64 | `market_page_ids` | 条件必填 | 完成 | 完成 | 数量限制测试 |
| 65 | `consult_aweme_uid` | 条件必填 | 完成 | 完成 | 字段覆盖测试 |
