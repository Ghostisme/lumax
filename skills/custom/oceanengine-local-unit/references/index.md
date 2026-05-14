# 巨量本地推单元管理接口索引

来源入口：`https://open.oceanengine.com/labels/37/docs/1808003978921193?origin=left_nav`

| 接口 | doc_id | path | capability | reference | rule | endpoint script | MCP 工具 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 创建单元 | `1808165017797977` | `/open_api/v3.0/local/promotion/create/` | `create-unit` | `references/create-unit.md` | `rules/create-unit.json` | `scripts/endpoints/create_unit.py` | `localUnitCreate` |
| 更新单元 | `1808440848912411` | `/open_api/v3.0/local/promotion/update/` | `update-unit` | `references/update-unit.md` | `rules/update-unit.json` | `scripts/endpoints/update_unit.py` | `localUnitUpdate` |
| 获取单元列表 | `1808147672950851` | `/open_api/v3.0/local/promotion/list/` | `list-units` | `references/list-units.md` | `rules/list-units.json` | `scripts/endpoints/list_units.py` | `localUnitList` |
| 获取单元详情 | `1808442943397963` | `/open_api/v3.0/local/promotion/detail/` | `get-unit-detail` | `references/get-unit-detail.md` | `rules/get-unit-detail.json` | `scripts/endpoints/get_unit_detail.py` | `localUnitDetail` |
| 批量更新单元状态 | `1809958381935689` | `/open_api/v3.0/local/promotion/status/update/` | `batch-update-unit-status` | `references/batch-update-unit-status.md` | `rules/batch-update-unit-status.json` | `scripts/endpoints/batch_update_unit_status.py` | `localUnitStatusBatchUpdate` |
| 根据门店ID拉取商品 | `1810064083323002` | `/open_api/v3.0/local/product/get_by_poiids/` | `list-products-by-poi-ids` | `references/list-products-by-poi-ids.md` | `rules/list-products-by-poi-ids.json` | `scripts/endpoints/list_products_by_poi_ids.py` | `localProductGetByPoiIds` |
| 批量获取广告审核建议 | `1848484376642649` | `/open_api/v3.0/local/promotion/reject_reason/get/` | `batch-get-unit-reject-reasons` | `references/batch-get-unit-reject-reasons.md` | `rules/batch-get-unit-reject-reasons.json` | `scripts/endpoints/batch_get_unit_reject_reasons.py` | `localPromotionRejectReasonBatchGet` |

中文字段说明按官方文档；MCP tool 名、英文字段包装和 required 差异按当前 `platform-agent-biz` MCP schema 执行。
