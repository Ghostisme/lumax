# 获取可用营销页列表

来源 URL：https://open.oceanengine.com/labels/37/docs/1848482084888708
Path：`/open_api/v3.0/local/market_page_list/get/`
方法：`POST`
脚本：`scripts/endpoints/list_market_pages.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `delivery_goal`：必填，投放内容，允许 `POI` 门店、`PRODUCT` 商品。
- `poi_ids`：当 `delivery_goal=POI` 时必填，门店 ID 列表。
- `product_ids`：当 `delivery_goal=PRODUCT` 时必填，商品 ID 列表。
- `page`、`page_size`：可选，分页参数。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `data.mark_page_id_list[]` | object[] | 可用营销页列表。 |
| `data.mark_page_id_list[].market_page_id` | number | 营销页 id。 |
| `data.mark_page_id_list[].market_page_name` | string | 营销页名称。 |
| `data.mark_page_id_list[].status` | string | 营销页状态，`MARKET_PAGE_DISABLE` 不可用、`MARKET_PAGE_ENABLE` 可用。 |
| `data.mark_page_id_list[].cover_image_url` | string | 营销页图片链接；默认不展示原始链接。 |
| `data.mark_page_id_list[].tool_pack_info` | object | 关联留资组件信息。 |
| `data.mark_page_id_list[].tool_pack_info.tool_pack_id` | number | 关联留资组件 id。 |
| `data.mark_page_id_list[].tool_pack_info.tool_pack_types[]` | string | 留资方式，`TOOL_TYPE_CONSULT` 私信咨询、`TOOL_TYPE_FORM` 表单预约、`TOOL_TYPE_PHONE_SMART` 电话咨询。 |
| `data.page_info.page` | number | 页数。 |
| `data.page_info.page_size` | number | 页面大小。 |
| `data.page_info.total_number` | number | 总数。 |
| `data.page_info.total_page` | number | 总页数。 |
| `request_id` | string | 请求日志 id，仅用于诊断，不面向用户展示。 |

## 输出建议

展示营销页ID、名称、状态和适用场景。获取线索或落地页相关项目可使用返回的营销页ID。
