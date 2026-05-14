# 获取项目列表

来源 URL：https://open.oceanengine.com/labels/37/docs/1807977310878736
Path：`/open_api/v3.0/local/project/list/`
方法：`POST`
脚本：`scripts/endpoints/list_projects.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `project_ids`：可选，项目ID列表。
- `page`：可选，页码。
- `page_size`：可选，每页数量。
- `filtering`：可选，过滤条件。

## 过滤条件

官方文档支持按项目 ID、状态、门店、商品、营销目的、营销场景、单元类型、项目名称、创建/更新时间、出价方式和投放类型过滤。若用户给出复杂筛选条件，必须按官方字段名写入 `filtering`，不得自造字段名。

项目列表查询必须把用户给出的每个筛选条件都写入 `filtering`，不得先查宽列表再用返回结果口头筛选展示。用户说“线上互动”必须写入 `filtering.local_delivery_scene=CONTENT_HEAT`；用户说“团购成交”必须写入 `filtering.local_delivery_scene=PRODUCT_PAY`；用户说“短视频图文”必须写入 `filtering.marketing_goal=VIDEO_IMAGE`；用户说“直播”必须写入 `filtering.marketing_goal=LIVE`；用户说“通投”必须写入 `filtering.ad_type=GENERAL`；用户说“搜索”必须写入 `filtering.ad_type=SEARCHING`；用户说“智能出价”必须写入 `filtering.bid_type=SMART`；用户说“手动出价”必须写入 `filtering.bid_type=MANUAL`。

用户给出不在允许范围内的项目列表筛选词时，不得先查宽项目列表，也不得删除该筛选条件后展示全部结果；应先说明当前字段支持的中文选项，或把原值交给业务工具做本地校验。比如“品牌曝光”不是 `filtering.local_delivery_scene` 的官方营销目的，不能改成不限制营销目的后查询。

常用过滤字段：

- `filtering.project_ids`：项目 ID 列表，最多 100 个。
- `filtering.project_status_first`：项目一级状态，可选 `PROJECT_STATUS_ALL`（不限，包含已删除）、`PROJECT_STATUS_DELETE`（已删除）、`PROJECT_STATUS_DISABLE`（未投放）、`PROJECT_STATUS_DONE`（已完成）、`PROJECT_STATUS_ENABLE`（启用中）、`PROJECT_STATUS_NOT_DELETE`（不限，不包含已删除，默认）。
- `filtering.project_status_second`：项目二级状态，可选 `PROJECT_STATUS_BUDGET_EXCEED`（项目超出预算）、`PROJECT_STATUS_DISABLE`（已暂停）、`PROJECT_STATUS_NOT_SCHEDULE`（不在投放时段）、`PROJECT_STATUS_NOT_START`（未达投放时间）。仅当一级状态为 `PROJECT_STATUS_DISABLE` 时有效。
- `filtering.shop_ids`：门店 ID 列表，最多 10 个。
- `filtering.product_ids`：商品 ID 列表，最多 10 个。
- `filtering.local_delivery_scene`：营销目的，可选 `ALL`（不限）、`CONTENT_HEAT`（线上互动）、`POI_RECOMMEND`（线下到店）、`PRODUCT_PAY`（团购成交）、`EXTERNAL`（获取线索）。
- `filtering.marketing_goal`：营销场景，可选 `ALL`（不限）、`LIVE`（直播）、`VIDEO_IMAGE`（短视频/图文）。
- `filtering.ad_type`：单元类型，可选 `ALL`（不限）、`GENERAL`（通投）、`SEARCHING`（搜索）。
- `filtering.project_name`：项目名称，模糊搜索。
- `filtering.project_create_time_start` / `filtering.project_create_time_end`：项目创建时间范围，格式 `yyyy-MM-dd HH:mm:ss`。
- `filtering.project_modify_time_start` / `filtering.project_modify_time_end`：项目更新时间范围，格式 `yyyy-MM-dd HH:mm:ss`。
- `filtering.bid_type`：出价方式，可选 `ALL`（不限）、`MANUAL`（手动出价）、`SMART`（智能出价）、`STABILIZE_COSTS`（稳定成本）、`MAX_CONVERSION`（最大转化）。中文“智能出价”必须映射为 `SMART`，不是 `SMART_BID`。
- `filtering.delivery_package`：投放类型，仅线索场景支持，可选 `DELIVERY_PACKAGE_NORMAL`（常规投放）、`DELIVERY_PACKAGE_UBL`（周期稳投）。

字段名纠错：

- 不要使用 `status_first`，应使用 `filtering.project_status_first`。
- 不要使用 `marketing_scene`，应使用 `filtering.marketing_goal`。
- 不要使用 `marketing_target`，应使用 `filtering.local_delivery_scene`。
- 不要使用 `campaign_type`，应使用 `filtering.ad_type`。
- 不要使用 `SMART_BID`，智能出价应使用 `SMART`。

## 输出建议

向用户展示项目ID、项目名称、状态、营销场景、营销目的、预算和关键时间字段。保留 `project_id` 便于后续更新或状态操作。
