# 获取项目详情

来源 URL：https://open.oceanengine.com/labels/37/docs/1808441520771339
Path：`/open_api/v3.0/local/project/detail/`
方法：`GET`
脚本：`scripts/endpoints/get_project_detail.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `project_id`：项目ID。

## 输出建议

返回项目详情摘要，并保留原始关键字段。该接口也是创建、更新、状态变更和投放时段变更后的确认查询接口之一。

默认展示字段按官方详情响应和平台实际返回配置：

- `project_id`：项目ID。
- `name`：项目名称。
- `marketing_goal`：营销场景。
- `local_delivery_scene`：营销目的。
- `ad_type`：单元类型。
- `budget`：项目预算，平台返回单位为分。
- `bid`：项目出价；智能出价时可能为空。
- `bid_type`：出价方式。
- `budget_mode`：项目预算类型。
- `start_time`：投放开始时间；未固定开始日期时可能为空。
- `end_time`：投放结束时间；未固定结束日期时可能为空。
- `local_asset_type`：跳转页面。
- `request_id`：请求日志id。

注意：

- 用户明确要求“获取项目详情”时，必须使用 `capability=get-project-detail`；不得用 `list-projects` 的项目列表结果替代详情接口。
- 官方详情接口不返回的字段应说明“详情响应未返回”，不得从其它接口或历史上下文拼成详情接口成功结果。
