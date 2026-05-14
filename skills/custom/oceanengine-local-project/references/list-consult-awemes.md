# 获取私信接待抖音号

来源 URL：https://open.oceanengine.com/labels/37/docs/1848483292162059
Path：`/open_api/v3.0/local/consult_awame_list/get/`
方法：`POST`
脚本：`scripts/endpoints/list_consult_awemes.py`

## 参数

- `local_account_id`：必填，本地推投放账户ID。
- `delivery_goal`：必填，投放内容，允许 `POI` 门店、`PRODUCT` 商品。
- `poi_ids`：当 `delivery_goal=POI` 时必填，门店 ID 列表，长度不超过 10000。
- `product_ids`：当 `delivery_goal=PRODUCT` 时必填，商品 ID 列表，长度不超过 10。
- `filtering.search_key_word`：可选，根据抖音号 ID 和名称搜索。
- `filtering.auth_type`：可选，抖音号授权类型，允许 `OFFICIAL` 官方、`SELF` 自运营；用户说“半官方”“合作授权”“达人授权”或其它未列授权类型时，不得映射成官方或自运营，必须按用户原值交给业务工具校验，或直接说明只支持官方和自运营。
- `page`、`page_size`：可选，分页参数。

## 输出建议

展示可用于私信接待的抖音号、昵称和状态。私信消息或获取线索场景需要时使用。
