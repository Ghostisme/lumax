# 修正项目管理出价方式场景校验

## Why

本地推项目创建请求中，`bid_type` 当前主要按字段枚举和金额区间校验。`skills/custom/oceanengine-local-project/rules/create-project.json` 允许 `MANUAL`、`SMART`、`STABILIZE_COSTS`、`MAX_CONVERSION`，但没有把出价方式与 `marketing_goal`、`local_delivery_scene`、`delivery_package` 等交易场景组合做完整约束。

实际请求因此可能通过 `oceanengine_local_project` 本地校验并继续调用 `platform-agent-biz` MCP tool，最终由巨量平台返回 `code=40000: 交易场景不支持传该出价方式`。这类错误在调用前已经可以由本地规则确定，应在本地参数校验阶段拦截，并以中文校验错误返回给用户，避免无效 MCP / 平台调用。

## What Changes

- 为 `create-project` 增加 `bid_type` 与业务场景的本地交叉校验。
- 使不支持的出价方式在 `oceanengine_local_project` 参数校验阶段失败，且不得调用 MCP。
- 让用户可见结果返回清晰中文错误，说明当前交易场景支持的出价方式。
- 增加定向测试覆盖本次发现的非法组合和代表性合法组合。

## Non Goals

- 不扩大到其它参数的交叉校验修复；后续如果发现其它字段同类问题，再单独走变更。
- 不改变 `bid_type` 的官方枚举值集合。
- 不修改底层 MCP tool 名、payload 映射、Nacos endpoint 解析或后置确认链路。
- 不绕过 `oceanengine_local_project` 原生业务工具改用 curl、SDK、HTTP API 或直接 MCP 调用。

## Scope

本次 Apply 阶段应按现有官方生成文档和 Java 模型注释对齐以下约束：

- `external_action=SHOW` 仅支持 `bid_type=MANUAL`。
- `marketing_goal=LIVE` 且 `local_delivery_scene=CONTENT_HEAT` 或 `PRODUCT_PAY` 时，仅支持 `bid_type=SMART`。
- `local_delivery_scene=EXTERNAL` 且不是 UBL 相关链路时，仅支持 `bid_type=STABILIZE_COSTS` 或 `MAX_CONVERSION`。

如果实现阶段发现 UBL 识别需要依赖 `delivery_package` 或其它已有字段，应保持最小改动，只补齐本次 `bid_type` 约束所需判断，不顺手修复其它参数问题。

## Impact

- `openspec/specs/oceanengine-local-project-template-migration/spec.md`：归档后新增项目管理创建项目出价方式场景校验要求。
- `skills/custom/oceanengine-local-project/rules/create-project.json`：Apply 阶段补充 `bid_type` 场景交叉校验规则。
- `tools/oceanengine_local_project_runtime/validators.py` 或相关规则解释器：如现有规则表达能力不足，Apply 阶段可做最小扩展以支持该交叉校验。
- 项目管理定向测试：覆盖非法 `bid_type` 在本地失败且不调用 MCP，以及合法组合继续通过本地校验。

## Risks

- 本次变更会让原本透传到平台的非法组合提前失败，属于预期行为变化。
- 规则错误过严会误拦合法投放场景；测试必须覆盖至少一个合法代表组合，避免只验证失败路径。
- 修改代码前必须按 GitNexus 规则对目标函数或符号做影响分析；如影响分析返回 HIGH 或 CRITICAL，需先向用户说明风险再继续。
- Apply / 实现阶段涉及设计、代码、测试或行为变更时，必须使用 Superpowers。
