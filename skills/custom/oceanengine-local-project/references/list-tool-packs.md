# 获取可用留资组件列表

来源 URL：https://open.oceanengine.com/labels/37/docs/1848481263218688
Path：`/open_api/v3.0/local/tool_pack_list/get/`
方法：`POST`
脚本：`scripts/endpoints/list_tool_packs.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `delivery_goal`：必填，投放内容，允许 `POI` 门店、`PRODUCT` 商品。
- `poi_ids`：当 `delivery_goal=POI` 时必填，门店 ID 列表，长度不超过 10000。
- `product_ids`：当 `delivery_goal=PRODUCT` 时必填，商品 ID 列表，长度不超过 10。
- `intelligent_selection_mode`：必填，获取线索方式，允许 `INTELLIGENT_SELECTION_MODE_OFF` 自定义、`INTELLIGENT_SELECTION_MODE_ON` 智能优选。
- `page`、`page_size`：可选，分页参数。

参数整理要求：用户明确说“自定义”时才传 `INTELLIGENT_SELECTION_MODE_OFF`，明确说“智能优选”时才传 `INTELLIGENT_SELECTION_MODE_ON`；不得把其他值猜成自定义或智能优选，应按原值交给业务工具校验或追问确认。

## 输出建议

展示留资组件ID、名称、类型和可用状态。获取线索场景下可用该列表选择组件。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | number | 返回码。 |
| `message` | string | 返回信息。 |
| `data.tool_pack_list[]` | object[] | 留资组件列表。 |
| `data.tool_pack_list[].tool_pack_id` | number | 留资组件 id。 |
| `data.tool_pack_list[].tool_pack_name` | string | 留资组件名称。 |
| `data.tool_pack_list[].tool_pack_types[]` | string | 组件类型，`TOOL_TYPE_CONSULT` 私信咨询、`TOOL_TYPE_FORM` 表单预约、`TOOL_TYPE_SMART` 电话咨询。 |
| `data.tool_pack_list[].enable` | bool | 组件是否可用，不可用则创编时不支持传入。 |
| `data.tool_pack_list[].enable_intelligent_selection` | bool | 是否支持智能优选。 |
| `data.pagination.page` | number | 页码。 |
| `data.pagination.page_size` | number | 页面大小。 |
| `data.pagination.total_page` | number | 总页数。 |
| `data.pagination.total_num` | number | 总数。 |
| `request_id` | string | 请求日志id，仅用于诊断，不默认展示给用户。 |
