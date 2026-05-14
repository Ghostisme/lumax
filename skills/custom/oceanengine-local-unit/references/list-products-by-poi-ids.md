# 根据门店 ID 拉取商品

- path: `/open_api/v3.0/local/product/get_by_poiids/`
- MCP: `platform-agent-biz/localProductGetByPoiIds`
- capability: `list-products-by-poi-ids`

## 请求字段摘要

必填字段：`local_account_id`、`poi_ids`。

可选字段：`local_delivery_scene`。

`local_delivery_scene` 可选值：
- `CONTENT_HEAT`: 线上互动
- `EXTERNAL`: 销售线索收集
- `POI_RECOMMEND`: 线下到店
- `PRODUCT_PAY`: 团购成交

不传时采用官方默认语义：交易广告，即 `CONTENT_HEAT`、`POI_RECOMMEND`、`PRODUCT_PAY`。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.product_ids[]` | `number[]` | 商品ID列表 |
| `request_id` | `string` | 请求日志id |
