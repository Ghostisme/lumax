# oceanengine-local-material-management Specification

## ADDED Requirements

### Requirement: 素材管理参数校验失败一次只追问一个问题

`oceanengine_local_material` SHALL 在参数校验失败时只向 Agent 和用户暴露首个可行动中文问题。内部校验 MAY 继续收集完整错误列表用于计数、日志和测试，但面向 Agent 的结构化结果 SHALL NOT 同时暴露多个缺参问题，避免最终回复一次追问多个参数。

#### Scenario: 多个普通必填缺失时只展示首个问题

- **GIVEN** 用户请求命中 `oceanengine_local_material`
- **AND** 本地参数校验发现多个普通必填字段缺失
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.user_visible_text` SHALL 只包含规则顺序中的第一个缺失字段中文问题
- **AND** `errors` SHALL 只保留该第一个可见错误
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量

#### Scenario: 上传参数缺失时只展示当前首个问题

- **GIVEN** 用户请求上传视频、异步上传视频或上传图片
- **AND** 用户缺少多个文件、URL、签名或文件元数据参数
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** 用户可见结果 SHALL 只展示校验顺序中的首个可行动中文问题
- **AND** 系统 SHALL NOT 在同一轮要求用户同时补充多个素材参数
- **AND** 后续问题 SHALL 等用户补充首个问题后在下一轮重新校验时继续追问

#### Scenario: Skill 入口不得直接汇总多个缺失项

- **GIVEN** 用户通过自然语言请求上传、查询或评估本地推素材
- **AND** 用户缺少多个官方请求参数
- **WHEN** 主 Agent 已识别请求属于 `oceanengine-local-material`
- **THEN** 主 Agent SHALL 先调用 `oceanengine_local_material` 原生业务工具执行本地校验
- **AND** 主 Agent SHALL NOT 直接调用 `ask_clarification` 自行汇总多个缺失项
- **AND** 最终用户可见结果 SHALL 只展示一个中文补充问题

#### Scenario: MCP 缺失诊断不被单问题追问掩盖

- **GIVEN** `oceanengine_local_material` 的本地参数校验已经通过
- **AND** 目标官方接口当前未在 `platform-agent-biz` 暴露对应 MCP tool
- **WHEN** 业务工具生成失败结果
- **THEN** 用户可见结果 SHALL 保留 MCP 缺失中文诊断
- **AND** 系统 SHALL NOT 将 MCP 缺失诊断改写为素材参数追问
- **AND** 系统 SHALL NOT 建议或尝试 curl、HTTP API、SDK 或其它绕路方式
