# 任务清单

## 1. 规格与设计确认

- [x] 1.1 确认变更范围仅包含 `oceanengine_local_project`、`oceanengine_local_unit`、`oceanengine_local_material` 的参数校验失败反馈。
- [x] 1.2 确认通用 `ClarificationMiddleware`、非 OceanEngine 工具和平台/MCP 执行失败展示不纳入本次行为变更。
- [x] 1.3 运行 `openspec validate enforce-oceanengine-single-question-clarification --strict`。

## 2. 测试先行

- [x] 2.1 为共享 `agent_visible_result` 增加失败测试：多个参数校验错误时，`data.user_visible_text` 只包含第一条问题，`errors` 只保留第一条可见错误，并保留总错误数量。
- [x] 2.2 为 `oceanengine_local_project` 项目管理专用压缩逻辑增加对应失败测试。
- [x] 2.3 覆盖 MCP 缺失或平台/MCP 执行失败不被误当作参数补齐追问的行为。

## 3. 实现

- [x] 3.1 调整共享 OceanEngine Agent 可见错误压缩逻辑，使参数校验失败只暴露首个可行动中文问题。
- [x] 3.2 调整项目管理专用 Agent 可见错误压缩逻辑，与共享逻辑保持一致。
- [x] 3.3 确保内部校验仍可返回完整错误列表，且可见结果通过 `error_count` 和 `omitted_error_count` 保留隐藏错误数量。
- [x] 3.4 确保非参数补齐类错误继续按现有诊断语义展示。
- [x] 3.5 调整 `oceanengine-local-project`、`oceanengine-local-unit`、`oceanengine-local-material` 的 `SKILL.md`，要求缺参时先调用原生业务工具校验，不得直接 `ask_clarification` 汇总多个缺失项。

## 4. 验证

- [x] 4.1 运行 OceanEngine Agent 可见结果相关单元测试。
- [x] 4.2 运行项目、单元、素材原生业务工具的定向测试。
- [x] 4.3 搜索确认没有新增或恢复受保护的 `backend/packages/harness/deerflow/tools/oceanengine_local_*` wrapper 路径。
- [x] 4.4 如修改 function、class 或 method，按仓库规则完成 GitNexus impact analysis 并报告 blast radius。
- [x] 4.5 用浏览器自然语言请求验证 OceanEngine 缺参场景只向用户展示一个问题。

## 5. 交付前检查

- [x] 5.1 运行 `openspec validate enforce-oceanengine-single-question-clarification --strict`。
- [x] 5.2 检查是否需要把新的长期规则沉淀到最近层级 `AGENTS.md`。
- [x] 5.3 提交前运行 `gitnexus_detect_changes()`，确认受影响范围符合 OceanEngine 业务工具边界。
