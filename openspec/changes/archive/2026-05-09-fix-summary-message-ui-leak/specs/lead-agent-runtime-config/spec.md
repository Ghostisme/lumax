## MODIFIED Requirements

### Requirement: 用户可见消息不得展示内部 provider reasoning summary

Lead Agent runtime SHALL 阻止 provider 生成的内部 reasoning summary、runtime 生成的历史压缩 summary，以及等价内部上下文消息展示到终端用户对话 UI 中。内部摘要包括 session intent、execution summary、工具注册细节、MCP 路由细节、skill 文件路径、原始 trace 标识、参数收集状态、下一步内部执行提示，以及其它只适合模型上下文或开发者诊断、不适合作为用户可见 assistant 输出的内容。

#### Scenario: Provider 返回 reasoning summary

- **GIVEN** 模型 provider 响应包含类似 `summary_text` 的 reasoning summary
- **AND** 该摘要包含内部意图、工具选择、MCP 路由、skill 路径或执行 trace 细节
- **WHEN** runtime 将 provider 响应转换为对话消息
- **THEN** 用户可见消息状态 SHALL NOT 默认通过 `reasoning_content` 暴露该摘要
- **AND** 普通用户 UI SHALL NOT 将该摘要渲染为 assistant 答案或思考步骤

#### Scenario: 后端生成内部上下文消息

- **GIVEN** runtime 创建内部摘要、skill/reference 读取或 tool-call 上下文消息
- **AND** 这些消息包含 `SESSION INTENT`、`SUMMARY`、MCP tool 名、`nacos-mcp-router_*`、`/mnt/skills/` 路径或等价内部诊断信息
- **WHEN** runtime 为普通终端用户对话存储或流式输出这些消息
- **THEN** 这些消息 SHALL 被标记为 UI 隐藏，或其内部 reasoning 字段 SHALL 被移除
- **AND** 普通 UI SHALL 继续展示有效的 assistant 最终内容和业务工具用户可见文本

#### Scenario: 历史压缩 summary 不得短暂展示

- **GIVEN** runtime 将长对话压缩为 `HumanMessage(name="summary")`
- **AND** 该 summary 内容包含 `SESSION INTENT`、`SUMMARY`、参数收集状态或内部下一步提示
- **WHEN** 后端构造普通用户可见的 history、state、stream 或 run stream 响应
- **THEN** 后端 SHALL 隐藏或过滤该 summary 消息，即使该消息未携带 `additional_kwargs.hide_from_ui`
- **AND** 当普通用户 UI 消费重连回填或客户端合并后的消息列表时，UI SHALL NOT 展示该 summary 消息
- **AND** 该 summary SHALL NOT 以短暂卡片、human message、assistant message、思考步骤或工具步骤形式出现后再自动消失

#### Scenario: 前端渲染强制隐藏 summary

- **GIVEN** 客户端收到 `name` 为 `summary` 的消息
- **AND** 该消息缺少 `additional_kwargs.hide_from_ui=true`
- **WHEN** 前端对消息进行分组、过滤或渲染
- **THEN** 前端 SHALL 将该消息视为内部隐藏消息
- **AND** 前端 SHALL NOT 依赖关键词解析来隐藏普通用户文本

#### Scenario: 开发者诊断仍可保留内部证据

- **GIVEN** 维护者需要调试工具路由、MCP 调用、provider 行为或长对话压缩行为
- **WHEN** 维护者查看日志、trace、线程状态、checkpoint 或测试记录
- **THEN** 内部 reasoning、summary 或执行证据 MAY 保留在这些诊断渠道中
- **AND** 这些证据 SHALL 与普通终端用户消息渲染保持隔离
