# 查询营销页详情

来源 URL：https://open.oceanengine.com/labels/37/docs/1848482831406092
Path：`/open_api/v3.0/local/market_page/get/`
方法：`POST`
脚本：`scripts/endpoints/get_market_page_detail.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `market_page_ids`：营销页ID列表，至少 1 项。官方请求字段为复数列表，不使用单个 `market_page_id`。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `data.mark_page_info` | object[] | 营销页详情。 |
| `data.mark_page_info[].market_page_id` | number | 营销页 id。 |
| `data.mark_page_info[].market_page_name` | string | 营销页名称。 |
| `data.mark_page_info[].status` | string | 营销页状态，`MARKET_PAGE_DISABLE` 营销页不可用、`MARKET_PAGE_ENABLE` 营销页可用。 |
| `data.mark_page_info[].cover_image_url` | string | 营销页图片链接。 |
| `data.mark_page_info[].tool_pack_info` | object | 关联留资组件信息。 |
| `data.mark_page_info[].tool_pack_info.tool_pack_id` | number | 关联留资组件 id。 |
| `data.mark_page_info[].tool_pack_info.tool_pack_types[]` | string | 留资方式，`TOOL_TYPE_CONSULT` 私信咨询、`TOOL_TYPE_FORM` 表单预约、`TOOL_TYPE_PHONE_SMART` 电话咨询。 |
| `request_id` | string | 请求日志 id，仅用于诊断，不面向用户展示。 |

## 输出建议

展示营销页详情、状态和组件信息。用于确认营销页是否可用于当前项目。
