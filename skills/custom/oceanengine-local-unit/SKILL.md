---
name: oceanengine-local-unit
description: 通过 DeerFlow 原生业务工具执行巨量引擎本地推单元管理，包括创建、更新、列表、详情、状态、门店商品和审核建议查询。
---

# 巨量本地推单元管理

通过 DeerFlow 原生业务工具 `oceanengine_local_unit` 调用巨量引擎本地推单元管理模块接口。主文件只负责导航和执行流程；接口字段、枚举和示例按需读取 `references/`，机器可执行规则按需读取 `rules/`。

## 使用时机

- 用户要创建、更新、查询或暂停 / 启用本地推单元。
- 用户要按门店 ID 拉取可投商品。
- 用户要批量查询本地推单元审核建议或拒审原因。

## ReAct 流程

1. 明确用户意图并选择 `rules/index.json` 中的 `capability`。
2. 如参数、枚举或口径不明确，读取对应 `references/*.md` 和 `rules/*.json`。
3. 将用户输入整理成 JSON，字段名使用 snake_case。
4. 即使用户缺少必填参数，也不得直接调用 `ask_clarification` 自行汇总多个缺失项；必须先调用 DeerFlow 原生业务工具 `oceanengine_local_unit`，传入 `capability` 和 `payload_json`。
5. 工具返回参数校验失败时，直接按 `data.user_visible_text` 或首条中文错误向用户追问；不得追加其它未展示缺失项，也不要绕过本地校验直调 MCP。
6. 工具返回 MCP 失败时，保留 `request_id`、`mcp_tool_name` 和错误摘要，方便排查。

## Capability

| capability | 用途 | MCP 工具 |
| --- | --- | --- |
| `create-unit` | 创建单元 | `localUnitCreate` |
| `update-unit` | 更新单元 | `localUnitUpdate` |
| `list-units` | 获取单元列表 | `localUnitList` |
| `get-unit-detail` | 获取单元详情 | `localUnitDetail` |
| `batch-update-unit-status` | 批量更新单元状态 | `localUnitStatusBatchUpdate` |
| `list-products-by-poi-ids` | 根据门店 ID 拉取商品 | `localProductGetByPoiIds` |
| `batch-get-unit-reject-reasons` | 批量获取广告审核建议 | `localPromotionRejectReasonBatchGet` |

## 必填项

- 所有能力都需要 `local_account_id`。
- 单元详情和更新需要 `promotion_id`。
- 状态批量更新需要 `data[].promotion_id` 和 `data[].opt_status`。
- 根据门店拉取商品需要 `poi_ids`；`local_delivery_scene` 可选，未传时按官方默认交易广告场景处理。
- 批量获取审核建议需要 `promotion_ids`。

## 约束

- 主 Agent 必须调用 `oceanengine_local_unit`，不得直接调用 `nacos-mcp-router_use_tool` 执行上述 MCP 工具。
- 不得使用 `task` 或任何子代理执行、诊断或替代执行本 skill；必须由主 Agent 直接调用 `oceanengine_local_unit` 或返回业务工具不可用。
- 本地校验失败时不得调用 MCP。
- 创建和更新单元涉及素材、卡片等复杂字段，字段细节以 `rules/create-unit.json`、`rules/update-unit.json` 和官方文档摘要为准。
