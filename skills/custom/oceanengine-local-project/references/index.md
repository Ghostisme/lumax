# 巨量本地推项目管理接口索引

来源：巨量引擎开放平台“项目管理模块”
模块 URL：https://open.oceanengine.com/labels/37/docs/1807977111009572?origin=left_nav
同步日期：2026-04-30
MCP 服务：`platform-agent-biz`

| 接口 | 类型 | Path | doc_id | 详细文档 | Rule | 脚本 |
|---|---|---|---|---|---|---|
| 创建项目 | 增改 | `/open_api/v3.0/local/project/create/` | `1808094783305739` | `create-project.md` | `rules/create-project.json` | `scripts/endpoints/create_project.py` |
| 更新项目 | 增改 | `/open_api/v3.0/local/project/update/` | `1808440838642948` | `update-project.md` | `rules/update-project.json` | `scripts/endpoints/update_project.py` |
| 获取项目列表 | 读取 | `/open_api/v3.0/local/project/list/` | `1807977310878736` | `list-projects.md` | `rules/list-projects.json` | `scripts/endpoints/list_projects.py` |
| 获取项目详情 | 读取 | `/open_api/v3.0/local/project/detail/` | `1808441520771339` | `get-project-detail.md` | `rules/get-project-detail.json` | `scripts/endpoints/get_project_detail.py` |
| 批量更新项目状态 | 增改 | `/open_api/v3.0/local/project/status/update/` | `1809958369980564` | `batch-update-project-status.md` | `rules/batch-update-project-status.json` | `scripts/endpoints/batch_update_project_status.py` |
| 获取可投门店列表 | 读取 | `/open_api/v3.0/local/poi/get/` | `1807977760174122` | `list-promotable-pois.md` | `rules/list-promotable-pois.json` | `scripts/endpoints/list_promotable_pois.py` |
| 获取可投商品列表 | 读取 | `/open_api/v3.0/local/product/get/` | `1807978367423588` | `list-promotable-products.md` | `rules/list-promotable-products.json` | `scripts/endpoints/list_promotable_products.py` |
| 获取本地推创编可用抖音号 | 读取 | `/open_api/v3.0/local/aweme/authorized/get/` | `1807990317937690` | `list-authorized-awemes.md` | `rules/list-authorized-awemes.json` | `scripts/endpoints/list_authorized_awemes.py` |
| 查询本地推创编可用人群包 | 读取 | `/open_api/v3.0/local/custom_audience/get/` | `1808003891639609` | `list-custom-audiences.md` | `rules/list-custom-audiences.json` | `scripts/endpoints/list_custom_audiences.py` |
| 根据多门店ID拉取门店ID | 读取 | `/open_api/v3.0/local/multi_poi_id/poi_ids/get/` | `1809719485612043` | `get-poi-ids-by-multi-poi-id.md` | `rules/get-poi-ids-by-multi-poi-id.json` | `scripts/endpoints/get_poi_ids_by_multi_poi_id.py` |
| 获取可用留资组件列表 | 读取 | `/open_api/v3.0/local/tool_pack_list/get/` | `1848481263218688` | `list-tool-packs.md` | `rules/list-tool-packs.json` | `scripts/endpoints/list_tool_packs.py` |
| 获取可用留资组件详情 | 读取 | `/open_api/v3.0/local/tool_pack/detail/` | `1848481896981834` | `get-tool-pack-detail.md` | `rules/get-tool-pack-detail.json` | `scripts/endpoints/get_tool_pack_detail.py` |
| 获取可用营销页列表 | 读取 | `/open_api/v3.0/local/market_page_list/get/` | `1848482084888708` | `list-market-pages.md` | `rules/list-market-pages.json` | `scripts/endpoints/list_market_pages.py` |
| 查询营销页详情 | 读取 | `/open_api/v3.0/local/market_page/get/` | `1848482831406092` | `get-market-page-detail.md` | `rules/get-market-page-detail.json` | `scripts/endpoints/get_market_page_detail.py` |
| 获取私信接待抖音号 | 读取 | `/open_api/v3.0/local/consult_awame_list/get/` | `1848483292162059` | `list-consult-awemes.md` | `rules/list-consult-awemes.json` | `scripts/endpoints/list_consult_awemes.py` |
| 列表批量更新项目投放时段 | 增改 | `/open_api/v3.0/local/project/week_schedule/update/` | `1848483664605003` | `batch-update-project-week-schedule.md` | `rules/batch-update-project-week-schedule.json` | `scripts/endpoints/batch_update_project_week_schedule.py` |

## 执行约定

- 先读取目标接口的详细文档和规则配置，再调用对应脚本。
- 参数校验失败时不要调用 MCP。
- 读取类接口支持 dry-run 预校验。
- 增改类接口必须由脚本执行后置查询确认，最多重试 3 次。
