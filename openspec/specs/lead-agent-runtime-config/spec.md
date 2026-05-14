# lead-agent-runtime-config Specification

## Purpose
TBD - created by archiving change fix-lead-agent-runtime-config. Update Purpose after archive.
## Requirements
### Requirement: Lead Agent 必须统一读取运行时配置

Lead Agent SHALL normalize runtime options from `RunnableConfig` through one shared helper before building middleware or the agent graph.

#### Scenario: `configurable` 提供旧版运行时参数
- **GIVEN** `RunnableConfig` includes `configurable.model_name`, `configurable.thinking_enabled`, `configurable.is_plan_mode` or `configurable.subagent_enabled`
- **WHEN** `make_lead_agent()` and `_build_middlewares()` read runtime options
- **THEN** Lead Agent SHALL use those values instead of ignoring them
- **AND** Lead Agent SHALL NOT raise `NameError` for `_get_runtime_config`

#### Scenario: `context` 提供 LangGraph runtime 参数
- **GIVEN** `RunnableConfig` includes a dict `context` with runtime options
- **WHEN** `make_lead_agent()` resolves model, thinking, plan mode, subagent and agent identity options
- **THEN** Lead Agent SHALL read those options from `context`
- **AND** middleware construction SHALL use the same normalized options

#### Scenario: `context` 覆盖 `configurable`
- **GIVEN** `RunnableConfig.configurable` and `RunnableConfig.context` both contain the same runtime option
- **WHEN** Lead Agent normalizes runtime options
- **THEN** the `context` value SHALL take precedence
- **AND** the merge SHALL only treat `context` as overrides when it is a dict

### Requirement: 模型名解析必须支持显式 AppConfig

Lead Agent SHALL resolve model names from an explicit `AppConfig` when one has already been provided by the caller.

#### Scenario: 显式传入 `AppConfig`
- **GIVEN** `make_lead_agent()` has resolved `app_config` from its argument
- **WHEN** it calls `_resolve_model_name()`
- **THEN** `_resolve_model_name()` SHALL use that explicit `AppConfig`
- **AND** it SHALL NOT require an ambient `get_app_config()` lookup

#### Scenario: 请求模型不存在
- **GIVEN** the requested model name is not present in the resolved `AppConfig`
- **WHEN** `_resolve_model_name()` evaluates the request
- **THEN** it SHALL fall back to the first configured model
- **AND** it SHALL log a warning naming the fallback model

#### Scenario: 没有配置任何模型
- **GIVEN** the resolved `AppConfig` contains no models
- **WHEN** `_resolve_model_name()` is called
- **THEN** it SHALL raise `ValueError`
- **AND** the error message SHALL explain that at least one model must be configured

### Requirement: 修复必须由聚焦测试覆盖

The Lead Agent runtime config fix SHALL be verified by focused backend tests before delivery.

#### Scenario: Lead Agent 模型解析回归测试
- **GIVEN** the change has been applied
- **WHEN** maintainers run `cd backend && .venv/bin/python -m pytest tests/test_lead_agent_model_resolution.py -q`
- **THEN** the tests SHALL pass
- **AND** no test in that file SHALL fail with `NameError: name '_get_runtime_config' is not defined`
- **AND** no test in that file SHALL fail with `UnboundLocalError` caused by `_resolve_model_name`

#### Scenario: OpenSpec 严格校验
- **GIVEN** the proposal documents are complete
- **WHEN** maintainers run `openspec validate fix-lead-agent-runtime-config --strict`
- **THEN** OpenSpec validation SHALL pass without warnings or errors

### Requirement: 启用 Langfuse tracing 时运行必须携带稳定的 session 标识

When Langfuse tracing is enabled, DeerFlow SHALL propagate a stable Langfuse session identifier for each thread-level run so that Langfuse can group related traces into `sessions`.

#### Scenario: 调用方未显式提供 Langfuse session_id
- **GIVEN** Langfuse tracing is enabled
- **AND** a DeerFlow run is created for thread `thread-123`
- **AND** request metadata does not contain `langfuse_session_id`
- **WHEN** the runtime builds the `RunnableConfig` metadata for that run
- **THEN** the system SHALL set `metadata.langfuse_session_id` to `thread-123`
- **AND** downstream tracing callbacks SHALL receive that metadata unchanged

#### Scenario: 调用方已显式提供 Langfuse session_id
- **GIVEN** Langfuse tracing is enabled
- **AND** request metadata already contains `langfuse_session_id=custom-session`
- **WHEN** the runtime builds the `RunnableConfig`
- **THEN** the system SHALL preserve `custom-session`
- **AND** it SHALL NOT overwrite it with the DeerFlow thread id

### Requirement: Langfuse session metadata 透传不得破坏现有运行配置

Adding Langfuse session metadata SHALL preserve existing runtime config, thread config, and caller-provided metadata behavior.

#### Scenario: 注入 Langfuse session metadata 时保留其他 metadata
- **GIVEN** a DeerFlow run request includes existing metadata fields other than `langfuse_session_id`
- **WHEN** the runtime injects Langfuse session metadata
- **THEN** the existing metadata fields SHALL remain present
- **AND** only missing Langfuse-specific metadata may be added

#### Scenario: Langfuse 未启用时保持现有行为
- **GIVEN** Langfuse tracing is not enabled
- **WHEN** the runtime builds `RunnableConfig`
- **THEN** the system SHALL NOT require Langfuse-specific metadata to exist
- **AND** existing run creation behavior SHALL remain unchanged

### Requirement: Lead Agent 不得硬编码 OceanEngine 业务专用 middleware

Lead Agent middleware 链 SHALL 保持业务域无关。OceanEngine 本地推的 skill gate、响应清洗、禁止 `ask_clarification` 绕过、禁止 MCP Router 直连等业务专用逻辑 SHALL 通过项目扩展点注入，而不是在 `backend/packages/harness/deerflow/agents/lead_agent/agent.py` 中硬编码 import 或 `append(...)`。

#### Scenario: 构造默认 Lead Agent middleware 链

- **GIVEN** 运行时正在构造默认 Lead Agent
- **WHEN** `_build_middlewares(...)` 生成 middleware 列表
- **THEN** 默认 harness 链路 SHALL NOT 直接实例化 `OceanEngineSkillGateMiddleware`
- **AND** 默认 harness 链路 SHALL NOT 直接实例化 `OceanEngineResponseSanitizerMiddleware`
- **AND** harness 层 SHALL NOT import OceanEngine 业务专用 middleware 模块

#### Scenario: 项目需要启用 OceanEngine 运行时守卫

- **GIVEN** 当前部署需要启用 OceanEngine 本地推运行时守卫
- **WHEN** Gateway 或调用方构造运行配置
- **THEN** 系统 SHALL 通过 `custom_middlewares`、`configurable.__custom_middlewares` 或等价通用扩展点注入 OceanEngine middleware
- **AND** 注入后的 middleware SHALL 在 `ClarificationMiddleware` 截断之前生效
- **AND** 该机制 SHALL NOT 要求修改 `backend/packages/harness/deerflow/agents/middlewares/**`

#### Scenario: 非 OceanEngine 部署使用 Lead Agent

- **GIVEN** 当前部署未注入 OceanEngine 项目级 middleware
- **WHEN** Lead Agent 处理普通 DeerFlow 任务
- **THEN** 普通任务 SHALL 保持既有 middleware 行为
- **AND** 系统 SHALL NOT 加载 OceanEngine skill gate 或 response sanitizer 业务逻辑

### Requirement: 通用 middleware 注入能力必须保留

Lead Agent runtime SHALL 保留通用 middleware 注入能力，使项目级能力可以在受保护 harness 外部接入。该能力 SHALL 表达为通用 `AgentMiddleware` 注入，而不是为某个业务域新增专用参数。

#### Scenario: Gateway 注入项目级 middleware

- **GIVEN** Gateway 已经构造一个 `AgentMiddleware` 列表
- **WHEN** Gateway 将该列表放入运行配置的项目级注入字段
- **THEN** runtime worker SHALL 将该列表传递给 agent factory
- **AND** Lead Agent SHALL 把这些 middleware 接入运行链路
- **AND** `ClarificationMiddleware` SHALL 仍保持最后执行的澄清中断边界

#### Scenario: 注入字段为空

- **GIVEN** 运行配置没有提供项目级 middleware
- **WHEN** runtime worker 构造 agent
- **THEN** Lead Agent SHALL 使用默认通用 middleware 链
- **AND** 系统 SHALL NOT 因缺少项目级 middleware 注入字段而失败

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

### Requirement: OceanEngine 用户可见结果必须隐藏内部执行链路

OceanEngine 本地推项目、单元和素材管理请求 SHALL 只向终端用户展示面向业务的中文响应。runtime SHALL NOT 在普通用户可见对话结果中展示 provider reasoning summary、MCP 注册过程、原生工具名、受保护 MCP tool 名、skill 路径、原始 JSON 包装或平台 trace 内部信息。

#### Scenario: OceanEngine 正常读取或查询成功

- **GIVEN** 用户提交自然语言 OceanEngine 本地推请求
- **AND** agent 调用 OceanEngine 原生业务工具并收到成功的结构化结果
- **WHEN** 对话 UI 渲染最终结果
- **THEN** 可见响应 SHALL 展示中文业务摘要、列表结果、空列表说明或相关业务值
- **AND** 可见响应 SHALL NOT 展示 provider `SESSION INTENT`、`SUMMARY`、`oceanengine_local_*`、`nacos-mcp-router_*`、受保护 MCP tool 名或 `/mnt/skills/` 路径

#### Scenario: OceanEngine 参数校验失败

- **GIVEN** 用户提交缺少参数或参数无效的 OceanEngine 本地推请求
- **AND** 原生业务工具返回中文 `data.user_visible_text` 或等价单问题追问
- **WHEN** 对话 UI 渲染结果
- **THEN** 可见响应 SHALL 只展示中文业务追问或失败诊断
- **AND** provider reasoning summary SHALL NOT 追加额外内部解释或多个隐藏校验细节

#### Scenario: OceanEngine MCP 或平台失败

- **GIVEN** 原生业务工具通过本地校验，但 MCP 注册、MCP 调用或平台业务执行失败
- **WHEN** 对话 UI 渲染结果
- **THEN** 可见响应 SHALL 展示受控业务链路返回的中文失败诊断
- **AND** 可见响应 SHALL NOT 默认暴露原始 MCP 注册日志、平台请求日志、trace ID、原始 JSON 包装或内部路由摘要

### Requirement: Hot reload Docker 后端必须暴露仓库根目录工具包

When the hot reload backend Docker image starts DeerFlow from `/app/backend`, the process SHALL include both `/app` and `/app/backend` on Python import path so configured repository-root business tools such as `tools.oceanengine_local_project` can be resolved.

#### Scenario: Hot reload backend resolves root tools package

- **GIVEN** the backend container is built from `docker/Dockerfile.backend.hot`
- **AND** the application files are available under `/app`
- **WHEN** the default CMD starts Gateway from `/app/backend`
- **THEN** `PYTHONPATH` SHALL include `/app`
- **AND** `PYTHONPATH` SHALL include `/app/backend`
- **AND** configured `tools.oceanengine_local_*` modules SHALL be importable without installing a third-party `tools` package

#### Scenario: Hot reload image is built without mounting the full repository

- **GIVEN** the backend container is built from `docker/Dockerfile.backend.hot`
- **WHEN** the image is created
- **THEN** the image SHALL copy repository-root `tools/` to `/app/tools`
- **AND** configured `tools.oceanengine_local_*` modules SHALL exist in the image filesystem

### Requirement: 生产 Docker Gateway 必须暴露仓库根目录工具包

When the production Gateway container starts DeerFlow from `/app/backend`, the image and process SHALL include repository-root business tools so configured modules such as `tools.oceanengine_local_project` can be imported.

#### Scenario: Production Gateway image contains root tools package

- **GIVEN** the Gateway image is built from `backend/Dockerfile`
- **WHEN** the production runtime stage is assembled
- **THEN** the image SHALL copy repository-root `tools/` to `/app/tools`
- **AND** configured `tools.oceanengine_local_*` modules SHALL exist in the image filesystem

#### Scenario: Production Gateway process resolves root tools package

- **GIVEN** `docker/docker-compose.yaml` starts the production Gateway service
- **WHEN** Gateway starts from `/app/backend`
- **THEN** `PYTHONPATH` SHALL include `/app`
- **AND** `PYTHONPATH` SHALL include `/app/backend`
- **AND** configured `tools.oceanengine_local_*` modules SHALL be importable without installing a third-party `tools` package

#### Scenario: Production Gateway resolves OceanEngine project root

- **GIVEN** `docker/docker-compose.yaml` starts the production Gateway service
- **WHEN** OceanEngine native business tools resolve MCP configuration
- **THEN** the container SHALL expose `config.yaml` at `/app/config.yaml`
- **AND** the container SHALL expose skills at `/app/skills`
- **AND** `DEER_FLOW_PROJECT_ROOT` SHALL be set to `/app`
- **AND** OceanEngine MCP runtime SHALL be able to read project-root configuration from `/app`

