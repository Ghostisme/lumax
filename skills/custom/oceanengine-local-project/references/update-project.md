# 更新项目

来源 URL：https://open.oceanengine.com/labels/37/docs/1808440838642948
Path：`/open_api/v3.0/local/project/update/`
方法：`POST`
脚本：`scripts/endpoints/update_project.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `project_id`：项目ID。

## 可更新字段

可沿用创建项目中的项目名称、营销场景、营销目的、投放内容、门店、商品、抖音号、定向、投放时间、出价和预算相关字段。脚本会复用创建项目的类型、枚举和条件校验，但官方更新接口只强制 `local_account_id` 与 `project_id` 必填；其他字段按“传入即校验、未传不更新”处理。

## 参数约束

- `name`：项目名称，1 到 50 个字。
- `district=REGION` 时，`region` 有效且必填；`district=LOCAL` 时，`custom_area` 有效且必填；`district=POI` 时，`poi_around` 有效且必填。
- `retargeting_tags`、`retargeting_tags_exclude` 如需清空，需要传空数组；不传视为不更新。
- `schedule_type=FIXED_TIME` 时，`schedule_fixed_seconds` 有效；`schedule_type=START_TO_END` 时，`end_time` 有效。
- 当前官方 `LocalProjectUpdateV30Request` 不支持 `start_time`；用户要求修改开始投放时间时应返回中文不支持字段原因，不得把 `start_time` 传入平台导致部分更新误判。
- 用户要求“投放时间改成 A 到 B”时包含开始日期变更，应保留 `start_time=A` 进入本地校验并返回不支持字段原因；不得只更新 `end_time=B` 造成部分完成。
- 出价、预算和高峰日预算相关字段沿用创建项目的官方枚举与组合约束。

## 执行确认

更新成功后重新查询项目详情，并比对本次要求变更的字段。确认失败最多重试 3 次。
