# oceanengine-local-unit-management Specification

## ADDED Requirements

### Requirement: 单元管理参数校验失败一次只追问一个问题

`oceanengine_local_unit` SHALL 在参数校验失败时只向 Agent 和用户暴露首个可行动中文问题。内部校验 MAY 继续收集完整错误列表用于计数、日志和测试，但面向 Agent 的结构化结果 SHALL NOT 同时暴露多个缺参问题，避免最终回复一次追问多个参数。

#### Scenario: 多个普通必填缺失时只展示首个问题

- **GIVEN** 用户请求命中 `oceanengine_local_unit`
- **AND** 本地参数校验发现多个普通必填字段缺失
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.user_visible_text` SHALL 只包含规则顺序中的第一个缺失字段中文问题
- **AND** `errors` SHALL 只保留该第一个可见错误
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量

#### Scenario: 条件必填缺失时只展示当前首个问题

- **GIVEN** 用户输入触发单元管理条件必填规则
- **AND** 本地参数校验发现多个条件必填或批量项错误
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** 用户可见结果 SHALL 只展示校验顺序中的首个可行动中文问题
- **AND** 后续问题 SHALL 等用户补充首个问题后在下一轮重新校验时继续追问

#### Scenario: Skill 入口不得直接汇总多个缺失项

- **GIVEN** 用户通过自然语言请求创建、更新、查询或批量处理本地推单元
- **AND** 用户缺少多个官方请求参数
- **WHEN** 主 Agent 已识别请求属于 `oceanengine-local-unit`
- **THEN** 主 Agent SHALL 先调用 `oceanengine_local_unit` 原生业务工具执行本地校验
- **AND** 主 Agent SHALL NOT 直接调用 `ask_clarification` 自行汇总多个缺失项
- **AND** 最终用户可见结果 SHALL 只展示一个中文补充问题

#### Scenario: 非参数补齐类失败不被改写为追问

- **GIVEN** `oceanengine_local_unit` 已通过本地参数校验
- **WHEN** 失败原因是 MCP 工具缺失、MCP 调用失败、平台业务失败、后置确认失败或响应展示异常
- **THEN** 业务工具 SHALL 按现有中文诊断展示失败原因
- **AND** 系统 SHALL NOT 将这些失败裁剪成单个参数追问
