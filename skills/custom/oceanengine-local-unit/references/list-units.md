# 获取单元列表

- path: `/open_api/v3.0/local/promotion/list/`
- MCP: `platform-agent-biz/localUnitList`
- capability: `list-units`

## 请求字段摘要

必填字段：`local_account_id`。

可选字段：`filtering`、`page`、`page_size`。`page` 默认 1；`page_size` 默认 10，最大 100。

`filtering` 字段：
- `promotion_ids`：按单元 ID 筛选，单次最多 100 个。
- `promotion_name`：按单元名称模糊搜索。
- `project_id`：按项目 ID 筛选。
- `promotion_status_first`：单元一级状态，默认 `PROMOTION_STATUS_NOT_DELETE`。
- `promotion_status_second`：单元二级状态；仅当 `promotion_status_first=PROMOTION_STATUS_DISABLE` 时有效且必填，其他情况下传入无效。
- `ad_type`：单元类型，允许 `ALL`、`GENERAL`、`SEARCHING`。
- `marketing_goal`：营销场景，允许 `ALL`、`LIVE`、`VIDEO_IMAGE`。
- `promotion_create_time_start`、`promotion_create_time_end`：单元创建时间范围，格式 `yyyy-MM-dd HH:mm:ss`，需搭配使用。
- `promotion_modify_time_start`、`promotion_modify_time_end`：单元更新时间范围，格式 `yyyy-MM-dd HH:mm:ss`，需搭配使用。
- `reject_reason_type`：审核建议类型。
- `learning_phase`：学习期状态。
- `budget_mode`：预算类型。
- `bid_type`：出价方式。
- `local_delivery_scene`：营销目的；不传时默认获取交易单元列表，即 `CONTENT_HEAT`、`POI_RECOMMEND`、`PRODUCT_PAY`。

`promotion_status_first` 官方枚举：`PROMOTION_STATUS_ALL`、`PROMOTION_STATUS_DELETED`、`PROMOTION_STATUS_DISABLE`、`PROMOTION_STATUS_DONE`、`PROMOTION_STATUS_ENABLE`、`PROMOTION_STATUS_FROZEN`、`PROMOTION_STATUS_NOT_DELETE`。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.promotion_list[]` | `object[]` | 营销列表 |
| `data.promotion_list[].project_id` | `number` | 项目ID |
| `data.promotion_list[].local_account_id` | `number` | 投放账户id |
| `data.promotion_list[].ad_type` | `string` | 单元类型；单元类型，枚举值：GENERAL 通投；SEARCHING 搜索 |
| `data.promotion_list[].promotion_id` | `number` | 单元ID |
| `data.promotion_list[].promotion_name` | `string` | 单元名称 |
| `data.promotion_list[].promotion_create_time` | `string` | 单元创建时间；单元创建时间，格式 yyyy-MM-dd HH:mm:ss |
| `data.promotion_list[].promotion_modify_time` | `string` | 单元更新时间；单元更新时间，格式 yyyy-MM-dd HH:mm:ss |
| `data.promotion_list[].promotion_status_first` | `string` | 单元一级状态 |
| `data.promotion_list[].promotion_status_second[]` | `string[]` | 单元二级状态 |
| `data.promotion_list[].learning_phase` | `string` | 学习期状态；学习期状态，枚举值：LEARNED 学习期结束；LEARNING 学习中；LEARN_FAILED 学习失败 |
| `data.promotion_list[].aweme_id` | `string` | 抖音号 |
| `data.promotion_list[].aweme_name` | `string` | 抖音号昵称 |
| `data.page_info` | `object` | 分页信息 |
| `data.page_info.page` | `number` | 页码 |
| `data.page_info.page_size` | `number` | 页面大小 |
| `data.page_info.total_number` | `number` | 总数 |
| `data.page_info.total_page` | `number` | 总页数 |
| `request_id` | `string` | 请求日志id |
