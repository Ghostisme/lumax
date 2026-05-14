# 获取可投商品列表

来源 URL：https://open.oceanengine.com/labels/37/docs/1807978367423588
Path：`/open_api/v3.0/local/product/get/`
方法：`GET`
脚本：`scripts/endpoints/list_promotable_products.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `local_delivery_scene`：必填，营销目的，允许 `CONTENT_HEAT` 线上互动、`EXTERNAL` 销售线索收集、`POI_RECOMMEND` 线下到店、`PRODUCT_PAY` 团购成交。
- `page`、`page_size`：可选，分页参数。
- `filtering`：可选，过滤条件。

## 过滤条件

- `filtering.search_key_word`：可选，根据商品名称或商品 ID 搜索。

## 输出建议

默认展示官方响应中的商品ID、商品名称、价格、商品图片、适用门店数和分页信息；不要向用户展示请求日志 ID。创建商品投放项目时使用返回的 `product_id`。

## 响应字段

- `data.products[].product_id`：商品ID。
- `data.products[].product_name`：商品名称。
- `data.products[].price`：价格。
- `data.products[].product_pics`：商品图片。
- `data.products[].applicable_poi_num`：适用门店数。
- `data.products[].bind_market_page_infos[].market_page_id`：绑定营销页ID。
- `data.products[].bind_market_page_infos[].bind_tool_pack_info.tool_pack_id`：绑定留资组件ID。
- `data.page_info.page`：页码。
- `data.page_info.page_size`：页面大小。
- `data.page_info.total_page`：总页数。
- `data.page_info.total_number`：总数。
- `request_id`：请求日志id。

## 调用约束

- 用户要求获取可投商品列表时，必须使用 `capability=list-promotable-products`，不得改用 `list-projects`。
- 这是查询接口，不需要创建、更新、状态修改或后置项目列表确认。
