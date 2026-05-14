# 获取可投门店列表

来源 URL：https://open.oceanengine.com/labels/37/docs/1807977760174122
Path：`/open_api/v3.0/local/poi/get/`
方法：`GET`
脚本：`scripts/endpoints/list_promotable_pois.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `local_delivery_scene`：必填，项目设置的营销目的，允许 `CONTENT_HEAT` 线上互动、`POI_RECOMMEND` 线下到店、`PRODUCT_PAY` 团购成交、`EXTERNAL` 获取线索。
- `page`、`page_size`：可选，分页参数。
- `filtering`：可选，过滤条件。

## 过滤条件

- `filtering.search_key_word`：可选，根据门店名称或门店 ID 筛选。
- `filtering.province` / `filtering.city`：可选，根据省市 ID 筛选。
- `filtering.product_id`：可选，通过商品 ID 筛选商品适用门店；商品投放且使用门店附近定向时应传入。

## 自然语言映射

- 用户说“名称里带 X”或“关键词 X”必须写入 `filtering.search_key_word=X`，不得省略后再用未过滤结果自行筛选展示。
- 用户给出门店 ID 关键词时，也必须写入 `filtering.search_key_word`，不得改成其它接口或其它字段。
- 用户给出商品 ID 必须写入 `filtering.product_id`，用于查询该商品适用的可投门店。
- 用户给出省市 ID 时，必须分别写入 `filtering.province` / `filtering.city` 数组。
- 用户只给出省市名称且不能确认省市 ID 时，必须追问省市 ID，不得静默删除地区条件，也不得在遗漏用户过滤条件后用未过滤结果筛选展示。

## 输出建议

展示门店ID、门店名称、省份、城市、区县、地址、门店下有无商品和分页信息。不要向用户展示请求日志 ID。创建或更新项目选择门店时优先使用该接口确认可投范围。

默认展示字段：

- `poi_list[].poi_id`：门店ID。
- `poi_list[].poi_name`：门店名称。
- `poi_list[].province`：所在省份。
- `poi_list[].city`：所在城市。
- `poi_list[].district`：所在区。
- `poi_list[].poi_address`：门店地址。
- `poi_list[].exists_product`：门店下有无商品；仅 `local_delivery_scene=PRODUCT_PAY` 时返回。
- `page_info`：分页信息。
