# lumax-knowledge-search Specification

## Purpose

定义 Lumax Agent 原生知识库检索 tools。该能力只负责查询，不负责知识库、文档或后台管理。

## ADDED Requirements

### Requirement: Agent 必须通过原生工具检索知识库

Agent 必须通过 `lumax_knowledge_base` 工具执行知识库检索。

#### Scenario: 执行知识库检索

- **GIVEN** Agent 需要检索当前租户的知识库内容
- **WHEN** Agent 调用 `lumax_knowledge_base` 的 `search-knowledge`
- **THEN** 系统必须根据请求上下文中的租户标识执行检索
- **AND** 系统必须调用火山官方 `vikingdb-python-sdk` 的知识库检索接口

#### Scenario: 缺少租户标识

- **GIVEN** 请求上下文中的 `tenant_id` 经 `normalize_tenant_id()` 校验后为 `None`（缺失、空串或全 0）
- **WHEN** 工具执行检索
- **THEN** 系统必须返回结构化失败结果
- **AND** 系统必须用中文说明缺少有效租户标识
- **AND** 系统不得回退到任何默认值继续检索

#### Scenario: 平台级租户允许检索

- **GIVEN** 请求上下文中的 `tenant_id` 为 `DEFAULT_TENANT_ID`（"1"）
- **WHEN** 工具执行检索
- **THEN** 系统必须按平台级合法租户处理，不得拒绝
- **AND** 系统必须按 `tenant_id="1"` 解析对应的 collection 配置

#### Scenario: 忽略 payload_json 中的 tenant_id

- **GIVEN** Agent 在 `payload_json` 中传入 `tenant_id` 字段
- **WHEN** 工具解析输入
- **THEN** 工具层必须忽略该字段
- **AND** 工具必须只从请求上下文（`get_request_context()`）读取真实 `tenant_id`
- **AND** 系统不得允许 Agent 通过 payload 覆盖身份

#### Scenario: 忽略 payload_json 中的未知字段

- **GIVEN** Agent 在 `payload_json` 中传入 `kb_id`、`region` 等未知字段
- **WHEN** 工具解析输入
- **THEN** 工具层必须忽略这些字段
- **AND** 工具不得因为未知字段返回失败
- **AND** 工具仍按 `query` / `top_k` / `tag_filters` 正常执行检索

### Requirement: 工具参数必须保持最小查询契约

`lumax_knowledge_base` 工具必须只接收检索所需的最小输入。

#### Scenario: Agent 发起查询

- **GIVEN** Agent 调用 `search-knowledge`
- **WHEN** 工具解析输入
- **THEN** 系统必须接收查询文本 `query`
- **AND** 系统可以接收可选 `top_k`
- **AND** 系统可以接收可选 `tag_filters`
- **AND** 系统不得要求 Agent 传入底层知识库配置

#### Scenario: 查询文本为空

- **GIVEN** Agent 传入的 `query` 缺失、为空字符串或去除首尾空白后为空
- **WHEN** 工具校验参数
- **THEN** 系统必须返回结构化失败结果
- **AND** 系统必须用中文说明查询文本不能为空

#### Scenario: top_k 越界

- **GIVEN** Agent 传入的 `top_k` 为 `0`、负数或超过服务类内部上限
- **WHEN** 工具校验参数
- **THEN** 系统必须返回结构化失败结果
- **AND** 系统必须用中文说明 `top_k` 必须为 `[1, 上限]` 的整数

#### Scenario: 使用标签过滤

- **GIVEN** Agent 传入 `tag_filters`
- **WHEN** 工具执行检索
- **THEN** 系统必须将标签过滤翻译为火山 SDK 期望的过滤结构
- **AND** 系统不得维护标签
- **AND** 系统不得校验标签是否存在

#### Scenario: 标签过滤格式非法

- **GIVEN** Agent 传入非法 `tag_filters`
- **WHEN** 工具校验参数
- **THEN** 系统必须返回结构化失败结果
- **AND** 系统必须用中文说明标签过滤参数格式错误

### Requirement: 必须提供代码内部可复用服务类

除 Agent tool 外，系统必须提供项目内部代码可直接调用的知识库检索服务类。

#### Scenario: 内部代码调用检索服务

- **GIVEN** 项目内部代码需要检索知识库
- **WHEN** 代码调用 `LumaxKnowledgeBaseService.search(tenant_id, query, top_k=None, tag_filters=None)`
- **THEN** 服务类必须执行参数校验
- **AND** 服务类必须调用火山 SDK 适配层
- **AND** 服务类必须返回统一结构化结果

#### Scenario: 服务类的 tenant_id 解析优先级

- **GIVEN** 服务类被调用时未显式传入 `tenant_id`
- **WHEN** 服务类需要确定租户
- **THEN** 服务类必须调用 `backend/packages/harness/deerflow/mcp/context.py` 的 `get_request_context()` 读取 `tenant_id` 字段
- **AND** 调用方显式传入的 `tenant_id` 必须优先于上下文值
- **AND** 显式或上下文中的 `tenant_id` 都必须经 `normalize_tenant_id()` 校验，校验为 `None` 时按缺失处理

#### Scenario: 跨线程 / subagent 调用

- **GIVEN** 服务类在 subagent 或后台线程中被调用
- **WHEN** 调用方按仓库现有约定使用 `contextvars.copy_context()` 传播上下文
- **THEN** 服务类必须仍能通过 `get_request_context()` 读到上游请求的 `tenant_id`
- **AND** 系统不得在子线程中静默回退到无上下文路径

### Requirement: 必须封装火山 SDK 适配层

系统必须通过 SDK 适配层调用火山官方知识库检索接口。

#### Scenario: 调用火山知识库检索

- **GIVEN** 服务类需要执行知识库检索
- **WHEN** 服务类调用 `VolcengineKnowledgeClient.search_knowledge(collection_name, query, top_k, tag_filters=None, project_name="default")`
- **THEN** SDK 适配层必须调用火山官方 `vikingdb-python-sdk`（`VikingKnowledge.collection(collection_name=..., project_name=...).search_knowledge(SearchKnowledgeRequest(...))`）
- **AND** SDK 适配层签名不得包含 `tenant_id`，租户身份在上层服务类完成解析
- **AND** SDK 适配层不得解析 Agent 的 `payload_json`
- **AND** SDK 适配层不得拼装 Agent 可见中文文案

#### Scenario: SDK 凭证未配置

- **GIVEN** 运行环境同时缺失 `VOLC_ACCESSKEY` / `VOLC_AK` 与 `VOLC_SECRETKEY` / `VOLC_SK` 任一组合
- **OR** 运行环境缺少 `VIKINGDB_REGION`
- **WHEN** 服务类尝试调用 SDK
- **THEN** 工具必须返回结构化失败结果
- **AND** 工具必须用中文提示运维"火山知识库凭证未配置"
- **AND** 工具不得透传 SDK 内部错误的 headers、签名串或 trace

#### Scenario: 凭证别名兼容

- **GIVEN** 运行环境只设置了 `VOLC_AK` / `VOLC_SK`（vikingdb 官方文档别名）而未设置 `VOLC_ACCESSKEY` / `VOLC_SECRETKEY`
- **WHEN** 服务类调用 SDK
- **THEN** SDK 适配层必须正常完成鉴权
- **AND** 系统不得因为环境变量名差异而误判为凭证缺失

### Requirement: 必须解析租户到知识库的映射

系统必须根据租户标识解析具体的知识库 collection。

#### Scenario: 租户已配置 collection

- **GIVEN** `config.yaml` 中 `lumax_knowledge_base.tenant_collections` 为当前租户配置 `{collection_name, project_name}`
- **WHEN** 服务类执行检索
- **THEN** 服务类必须把对应 `collection_name` 与 `project_name` 一并传入 SDK 适配层
- **AND** `project_name` 缺省或为空时必须回退为 `"default"`

#### Scenario: 租户未配置 collection

- **GIVEN** `config.yaml` 中 `lumax_knowledge_base.tenant_collections` 未为当前租户配置 `collection_name`
- **WHEN** 服务类尝试解析映射
- **THEN** 工具必须返回结构化失败结果
- **AND** 工具必须用中文提示运维补配租户对应的知识库
- **AND** 工具不得回退到任意 KB 继续检索

#### Scenario: 不修改 AppConfig schema

- **WHEN** 服务类需要读取 tenant→collection 映射
- **THEN** 服务类必须直接通过 `yaml.safe_load(AppConfig.resolve_config_path())` 读 raw YAML
- **AND** 系统不得为本变更在 `backend/packages/harness/deerflow/config/app_config.py` 新增字段或调整 pydantic schema
- **AND** YAML 中 `tenant_id` 整数 key 必须强制 `str()` 后参与匹配

### Requirement: 工具只封装查询能力

`lumax_knowledge_base` 工具只封装知识库查询能力，不管理知识库资源。

#### Scenario: 查询工具不管理知识库

- **WHEN** Agent 调用 `search-knowledge`
- **THEN** 系统不得创建、绑定、删除或重建火山知识库
- **AND** 系统不得导入、更新、删除或同步火山文档

#### Scenario: 查询工具不读写后台表

- **WHEN** Agent 调用 `search-knowledge`
- **THEN** 系统不得读取或写入 PG 知识库管理表
- **AND** 系统不得要求 SQL 表迁移

### Requirement: 必须最小化对既有代码的改动

本变更必须以新增为主，避免重构既有模块。

#### Scenario: 仅新增本变更专属文件

- **WHEN** 实施本变更
- **THEN** 系统必须只新增以下文件：`tools/lumax_knowledge_base.py`、`tools/lumax_knowledge_base_runtime/__init__.py`、`tools/lumax_knowledge_base_runtime/service.py`、`tools/lumax_knowledge_base_runtime/client.py`、`backend/tests/test_lumax_knowledge_base.py`
- **AND** 服务类与 SDK 适配层必须放在 `tools/lumax_knowledge_base_runtime/` 子目录，对齐 `tools/oceanengine_local_project_runtime/` 的现有模式
- **AND** 系统不得修改 `tools/oceanengine_local_*`、`tools/managed_mcp_guard.py`、`backend/packages/harness/deerflow/mcp/context.py`、`runtime/tenant.py`、`runtime/user_context.py`、`backend/app/gateway/auth_middleware.py`、`backend/packages/harness/deerflow/config/app_config.py`、既有 middleware 链与 lead agent 装配代码

#### Scenario: 仅在配置类文件做注册改动

- **WHEN** 注册新工具与依赖
- **THEN** 既有文件的改动必须限定在以下三处：`config.yaml` / `config.example.yaml`（工具注册 + `tenant_id → {collection_name, project_name}` 映射，**不放环境变量**）、`backend/pyproject.toml`（添加 `vikingdb-python-sdk`）、`.env`（**仅此处**写 `VOLC_ACCESSKEY` 等环境变量占位；仓库未维护 `.env.example`）
- **AND** 系统不得为本变更新增 `get_effective_tenant_id` 等帮助函数，必须复用既有 `get_request_context()`

### Requirement: 检索结果必须结构化返回

工具必须返回结构化检索结果，供 Agent 生成最终回答。

#### Scenario: 返回字段最小集合

- **WHEN** 工具生成结果
- **THEN** 结果必须至少包含 `success`、`message`、`data.user_visible_text`、`data.reply_guidance`、`errors`、`tool_name`、`request_id` 字段
- **AND** 字段语义必须与 `tools/oceanengine_local_*` 现有工具保持一致，便于 lead agent 复用现有处理逻辑

#### Scenario: 检索命中

- **GIVEN** 火山 SDK 返回命中片段
- **WHEN** 工具生成结果
- **THEN** 结果必须在 `data.chunks` 字段下返回片段数组（与 OceanEngine 工具的 `data.*` 命名空间保持一致）
- **AND** 每个 chunk 应当尽量包含内容、来源、文档名和相关性分数

#### Scenario: 检索无命中

- **GIVEN** 火山 SDK 返回空结果集合
- **WHEN** 工具生成结果
- **THEN** 结果必须为成功（`success=true`）且 `data.chunks=[]`
- **AND** `data.user_visible_text` 必须用中文说明"未检索到相关内容"
- **AND** 工具不得把空命中作为失败处理

#### Scenario: SDK 调用失败

- **GIVEN** 火山 SDK 初始化或检索失败
- **WHEN** 工具处理异常
- **THEN** 工具必须返回结构化失败结果
- **AND** 工具不得暴露 AK/SK、headers、签名串、原始 trace 或敏感 URL
