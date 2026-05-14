## ADDED Requirements

### Requirement: 动态 MCP 候选必须按卡片契约返回

当 OceanEngine 原生业务工具通过只读 MCP 查询获得参数候选时，系统 SHALL 将可用于用户补齐的候选按 `data.clarification.input_control.type=choice_cards` 返回。该契约 SHALL 与静态枚举缺参的卡片候选保持字段兼容，并 SHALL NOT 要求本次变更修改 `frontend/**`。

#### Scenario: 单选动态候选返回卡片结构

- **GIVEN** 用户请求命中 OceanEngine 原生业务工具
- **AND** 本地参数校验发现首个可行动缺参适合通过只读 MCP 查询生成候选
- **AND** 该缺参字段业务语义为单选
- **WHEN** MCP 查询返回可用候选
- **THEN** 返回结果 SHALL 包含 `success=false`
- **AND** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** `data.clarification.input_control.selection_mode` SHALL 为 `single`
- **AND** `data.clarification.input_control.options[]` SHALL 来自 MCP 查询结果
- **AND** 每个候选项 SHALL 包含用于回填字段的 `value`
- **AND** 每个候选项 SHALL 包含用户可读的 `label`
- **AND** 系统 SHALL NOT 因本地校验失败而调用目标 mutation MCP 工具

#### Scenario: 多选动态候选返回卡片结构

- **GIVEN** 用户请求命中 OceanEngine 原生业务工具
- **AND** 本地参数校验发现首个可行动缺参适合通过只读 MCP 查询生成候选
- **AND** 该缺参字段业务语义为多选
- **WHEN** MCP 查询返回可用候选
- **THEN** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** `data.clarification.input_control.selection_mode` SHALL 为 `multiple`
- **AND** `data.clarification.input_control.options[]` SHALL 来自 MCP 查询结果
- **AND** 候选项 SHALL 保留 MCP 查询结果中的安全展示顺序
- **AND** 系统 SHALL NOT 把动态候选写入 `rules/*.json` 的静态 `enum` 或 `item_enum`

#### Scenario: 动态候选保留安全业务摘要

- **GIVEN** MCP 查询候选包含业务摘要、绑定对象、分页或其它展示辅助字段
- **WHEN** 原生业务工具构造 `choice_cards`
- **THEN** 候选项 MAY 包含安全的 `description`
- **AND** 候选项 MAY 包含后续补齐需要的安全 `metadata`
- **AND** `input_control` MAY 包含安全的 `page_info`
- **AND** 输出 SHALL NOT 包含内部 MCP tool name、平台请求日志 ID、trace 或原始 payload JSON

### Requirement: 动态候选必须提供不依赖前端改动的文本兜底

当动态 MCP 候选以 `choice_cards` 返回时，后端 SHALL 同步生成用户可读的 `data.user_visible_text`，使当前前端不修改代码时用户仍可理解候选并继续回复。

#### Scenario: 单选候选文本兜底

- **GIVEN** `data.clarification.input_control.selection_mode` 为 `single`
- **AND** `options[]` 包含一个或多个候选
- **WHEN** 后端构造用户可见结果
- **THEN** `data.user_visible_text` SHALL 包含原始单问题追问
- **AND** `data.user_visible_text` SHALL 展示每个候选的 `label` 和 `value`
- **AND** 当候选项存在 `description` 时，`data.user_visible_text` SHOULD 展示该业务摘要
- **AND** `data.user_visible_text` SHALL 提示用户回复一个候选 ID 或名称

#### Scenario: 多选候选文本兜底

- **GIVEN** `data.clarification.input_control.selection_mode` 为 `multiple`
- **AND** `options[]` 包含一个或多个候选
- **WHEN** 后端构造用户可见结果
- **THEN** `data.user_visible_text` SHALL 包含原始单问题追问
- **AND** `data.user_visible_text` SHALL 展示每个候选的 `label` 和 `value`
- **AND** `data.user_visible_text` SHALL 提示用户可回复多个候选 ID 或名称
- **AND** 用户可见文本 SHALL NOT 暴露内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID

#### Scenario: 当前变更不修改前端

- **GIVEN** 实施人员执行本 change
- **WHEN** 检查 git diff
- **THEN** 改动 SHALL NOT 包含 `frontend/**` 下的文件
- **AND** 若现有前端无法交互式展示 `selection_mode=multiple`，该限制 SHALL 记录为当前 UI 能力边界
- **AND** 后端文本兜底 SHALL 仍允许用户通过自然语言回复继续补齐参数

### Requirement: 浏览器验收必须使用真实用户路径

动态 MCP 候选卡片契约完成后，验收 SHALL 通过真实浏览器和真实用户自然语言输入验证，不得用指定工具、脚本直连或 MCP 直连替代用户路径。

#### Scenario: 浏览器自然语言触发动态候选

- **GIVEN** 验收人员已经登录本地页面
- **AND** 测试参数包含本地提账号 `1854708763953159`
- **WHEN** 验收人员在浏览器对话框中输入本地推参数补齐相关自然语言请求
- **THEN** 输入内容 SHALL NOT 包含 `oceanengine-local-project`、`oceanengine_local_project`、`capability`、`payload_json`、底层 MCP tool 名、脚本路径或“直接调用某工具”等提示
- **AND** 验收 SHALL 证明真实 Agent 被触发
- **AND** 验收 SHALL 证明 OceanEngine 原生业务工具被触发
- **AND** 验收 SHALL 证明只读 MCP 候选查询链路被触发
- **AND** 验收 SHALL NOT 以 dry-run、mock 成功、curl、脚本直连或 MCP 直连结果替代浏览器结果

#### Scenario: 验收失败先结合本地日志排查

- **GIVEN** 浏览器验收失败或链路证据不清晰
- **WHEN** 验收人员排查原因
- **THEN** 验收人员 SHALL 先结合本地 Gateway、backend、frontend 和 MCP 相关日志定位问题
- **AND** 本地日志证据 SHALL 用于诊断失败原因或链路缺口
- **AND** 本地日志 SHALL NOT 替代最终浏览器自然语言验收

#### Scenario: 本地日志不足时使用 Langfuse sessionId 辅助

- **GIVEN** 浏览器验收失败或链路证据不清晰
- **AND** 本地日志仍不足以定位问题
- **WHEN** 本轮请求存在可用于追踪的 `sessionId`
- **THEN** 验收人员 MAY 使用该 `sessionId` 查询 Langfuse 日志
- **AND** Langfuse 日志 SHALL 仅作为问题定位和链路证明辅助
- **AND** Langfuse 日志 SHALL NOT 替代最终浏览器自然语言验收

#### Scenario: 问题排除后重新浏览器验收

- **GIVEN** 验收失败问题已经通过本地日志、Langfuse 或代码分析排除
- **WHEN** 验收人员验证修复结果
- **THEN** 验收人员 SHALL 重新使用浏览器自然语言输入测试
- **AND** 重新测试 SHALL 遵守禁止指定工具名、`capability`、`payload_json` 和底层 MCP tool 名的规则
- **AND** 只有重新浏览器验收通过，才可将该验收项标记为完成

### Requirement: 动态候选异常路径不得生成虚假卡片

当动态 MCP 候选查询无法得到可用候选时，系统 SHALL 返回清晰的中文失败或继续追问结果，并 SHALL NOT 生成空的、臆造的或与当前参数上下文不匹配的 `choice_cards.options`。

#### Scenario: 前置参数不足时不查询候选

- **GIVEN** 首个可行动缺参理论上可通过动态 MCP 候选补齐
- **AND** 当前 payload 缺少候选查询所需的前置参数
- **WHEN** 原生业务工具生成参数补齐结果
- **THEN** 系统 SHALL NOT 发起候选查询 MCP 调用
- **AND** 返回结果 SHALL 继续只追问首个缺失的前置参数
- **AND** 返回结果 SHALL NOT 生成 `choice_cards.options`

#### Scenario: 候选查询失败时不生成卡片

- **GIVEN** 原生业务工具已经发起只读 MCP 候选查询
- **WHEN** MCP 工具缺失、MCP 调用失败或平台业务失败
- **THEN** 返回结果 SHALL 说明候选查询失败
- **AND** 返回结果 SHALL NOT 生成虚假候选卡片
- **AND** 用户可见结果 SHALL NOT 展示内部 trace、平台请求日志 ID 或底层 MCP tool name

#### Scenario: 候选为空时不生成空卡片

- **GIVEN** 原生业务工具已经发起只读 MCP 候选查询
- **WHEN** MCP 查询成功但候选列表为空
- **THEN** 返回结果 SHALL 说明暂无可选候选
- **AND** 返回结果 SHALL NOT 生成空的 `choice_cards.options`
- **AND** 返回结果 MAY 引导用户更换关键词、前置参数或手动提供目标字段值
