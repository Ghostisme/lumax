# structured-parameter-clarification Specification

## ADDED Requirements

### Requirement: 后端接口必须通用返回结构化参数补齐控件数据

当原生业务工具返回 `data.clarification.input_control` 时，后端 SHALL 通过通用 history、stream 或约定线程消息接口返回结构化补齐控件数据。该能力 SHALL 适用于所有返回同一契约的 OceanEngine 本地推原生业务工具，不得只针对某个接口、字段或 capability 实现。前端控件渲染不属于本 change 范围。

#### Scenario: 静态枚举缺参通过接口返回选项数据

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 原生业务工具返回 `success=false`
- **AND** 返回结果包含 `data.clarification.input_control.type=choice_cards`
- **AND** `data.clarification.input_control.options` 来自当前 capability 的规则文件
- **WHEN** 客户端通过 history、stream 或约定线程消息接口读取本轮结果
- **THEN** 接口结果 SHALL 包含结构化澄清数据
- **AND** 结构化澄清数据 SHALL 包含 `input_control.type=choice_cards`
- **AND** 候选项 SHALL 保留后端返回的 `options[].label`
- **AND** 候选值 SHALL 保留后端返回的 `options[].value`
- **AND** 候选项顺序 SHALL 与后端返回顺序一致
- **AND** 后端 SHALL NOT 从 `data.user_visible_text` 解析或推断候选项

#### Scenario: 动态候选通过接口返回选项数据

- **GIVEN** 原生业务工具返回动态候选 `data.clarification.input_control.type=choice_cards`
- **AND** 候选项包含 `value`、`label`、`description` 或 `metadata`
- **WHEN** 客户端通过接口读取结构化澄清数据
- **THEN** 接口结果 SHALL 保留用户可读的 `label`
- **AND** 接口结果 SHALL 保留用于后续补齐的 `value`
- **AND** 接口结果 SHALL 保留安全的 `description`
- **AND** 接口结果 SHALL 保留后续交互所需的候选 `metadata`
- **AND** 后端 SHALL NOT 臆造、重排或合并动态候选

#### Scenario: 填写型缺参通过接口返回输入提示

- **GIVEN** 原生业务工具返回 `data.clarification.input_control.type=text_input`
- **WHEN** 客户端通过接口读取结构化澄清数据
- **THEN** 接口结果 SHALL 包含 `data.clarification.question`
- **AND** 接口结果 SHALL 包含后端返回的 `placeholder` 或字段中文标签
- **AND** 接口结果 SHALL NOT 包含内部字段映射、payload JSON 或工具调用细节

#### Scenario: 旧文本展示路径仍可兜底

- **GIVEN** 原生业务工具返回 `data.clarification`
- **WHEN** 后端构造用户可见接口结果
- **THEN** 接口结果 SHALL 继续包含 `data.user_visible_text` 或等价兜底文本
- **AND** 接口结果 SHALL NOT 返回空候选控件
- **AND** 后端 SHALL NOT 为缺失结构臆造候选项

### Requirement: 结构化补齐用户可见出口必须清洗内部信息

系统将原生业务工具返回的结构化补齐信息转成用户可见接口结果时，SHALL 只保留前端对接所需的安全字段。原始工具调用、底层 MCP 信息和内部调试信息 SHALL 继续隐藏。

#### Scenario: 用户可见结构不泄漏内部工具信息

- **GIVEN** 原生业务工具返回 `data.clarification.input_control`
- **WHEN** Gateway / runtime 构造 history 或 stream 用户可见消息
- **THEN** 用户可见接口结果 SHALL 包含 `version`、`reason`、`field`、`field_label`、`question`、`input_control` 和 `user_visible_text`
- **AND** 用户可见接口结果 SHALL NOT 包含 `business_tool_name`
- **AND** 用户可见接口结果 SHALL NOT 包含 `mcp_server_name`
- **AND** 用户可见接口结果 SHALL NOT 包含 `mcp_tool_name`
- **AND** 用户可见接口结果 SHALL NOT 包含原始 `payload_json`、内部 trace、平台请求日志 ID 或原始 JSON 包装

#### Scenario: 通用实现不绑定具体接口

- **GIVEN** 一个 OceanEngine 原生业务工具返回符合 `data.clarification.input_control` 契约的结果
- **WHEN** 系统构造结构化补齐接口结果
- **THEN** 后端提取逻辑 SHALL 基于结构化契约识别补齐信息
- **AND** 实现 SHALL NOT 写死 `create-project`、`marketing_goal`、`local_delivery_scene`、`opt_status`、`upload_type` 或其它具体接口字段作为展示条件

## MODIFIED Requirements

### Requirement: 本变更不得修改前端代码

结构化参数补齐的后端契约 SHALL 由原生业务工具基于 `rules/*.json` 和真实只读业务查询生成。本 change 的 Apply 阶段 SHALL 只修改后端接口契约、后端测试、OpenSpec 文档和必要的后端辅助类型或函数。前端控件展示由后续同事对接，本 change SHALL NOT 修改 `frontend/` 下任何源码、样式、测试或生成组件。

#### Scenario: 实施人员检查改动范围

- **GIVEN** Apply 阶段准备提交通用结构化补齐后端契约变更
- **WHEN** 实施人员检查 `git diff --stat` 或等价改动清单
- **THEN** 改动文件 SHALL NOT 位于 `frontend/`
- **AND** 若发现 `frontend/` 改动，实施人员 SHALL 移除该改动或另建后续 OpenSpec change 处理前端渲染
- **AND** 后端 SHALL NOT 依赖前端解析 `data.user_visible_text` 来构造候选项
