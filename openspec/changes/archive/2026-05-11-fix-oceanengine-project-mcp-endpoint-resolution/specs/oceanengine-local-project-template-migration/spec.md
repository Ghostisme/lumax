## ADDED Requirements

### Requirement: 项目管理 MCP 调用必须通过 Nacos 解析真实服务端点

`oceanengine-local-project` 在通过原生业务工具调用 `platform-agent-biz` 项目管理 MCP tool 前，SHALL 以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源解析目标 MCP server 的实际地址、端口和路径。业务工具和项目管理脚本 SHALL NOT 将 `127.0.0.1:18000` 或其它本机固定 Router 地址作为默认业务兜底端点。

#### Scenario: Nacos 解析到项目管理 MCP 服务端点

- **GIVEN** 用户请求命中 `oceanengine-local-project` 中任一需要 MCP 调用的 capability
- **AND** 本地参数校验已通过
- **AND** Nacos 中存在 `platform-agent-biz` 并能解析出实际 MCP endpoint
- **WHEN** 原生业务工具或项目管理脚本调用目标项目管理 MCP tool
- **THEN** 调用 SHALL 发送到 Nacos 解析出的实际 MCP endpoint
- **AND** payload SHALL 继续按项目管理 rule 中的 MCP 字段映射构造
- **AND** 系统 SHALL NOT 使用 `http://127.0.0.1:18000/mcp/` 作为默认业务兜底地址

#### Scenario: Nacos 未注册项目管理目标 MCP server

- **GIVEN** 用户请求命中项目管理 capability
- **AND** 本地参数校验已通过
- **WHEN** 系统无法从 Nacos 或 DeerFlow Nacos MCP 配置解析到 `platform-agent-biz`
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明 Nacos 中未找到目标 MCP server 或配置不可用
- **AND** 系统 SHALL NOT 继续请求本机固定 Router 地址
- **AND** 系统 SHALL NOT 改用 curl、SDK、HTTP API、mock 或其它 MCP server

#### Scenario: 项目管理目标 MCP endpoint 不可达

- **GIVEN** Nacos 已返回 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 本地参数校验已通过
- **WHEN** 系统连接该 endpoint 失败、超时或返回不可用错误
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明解析到的 MCP 服务不可达
- **AND** 失败结果 SHALL NOT 声称项目管理操作已完成
- **AND** 系统 SHALL NOT 自动切换到本机固定 Router、curl、SDK、HTTP API 或 mock

#### Scenario: 项目管理目标 MCP tool 缺失

- **GIVEN** Nacos 已解析到 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 目标项目管理 capability 声明了 `mcp_tool_name`
- **WHEN** 解析到的 MCP 服务未暴露该 tool
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明目标 MCP tool 未注册或不可用
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用其它 tool 或其它调用协议
