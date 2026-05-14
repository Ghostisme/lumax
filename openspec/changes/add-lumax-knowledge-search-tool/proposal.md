# 新增 Lumax 知识库检索 Tools

## 背景

Lumax 需要让 Agent 能检索火山云知识库内容，用于补充业务问答上下文。每个请求都带有租户标识，本次只封装大模型可调用的知识库检索 tools。

## 问题

当前 Agent 缺少统一的 Lumax 知识库检索工具，项目内部代码也缺少可复用的知识库检索服务类。需要把火山官方 SDK 的知识库检索能力封装为稳定的 tools 和代码调用接口。

## 目标

- 新增 Agent 原生工具 `lumax_knowledge_base`。
- 第一版只支持 `search-knowledge` 查询能力。
- 工具根据请求中的租户标识执行知识库检索。
- 工具支持可选标签过滤参数 `tag_filters`。
- 新增项目内部可复用的 `LumaxKnowledgeBaseService.search()`。
- 新增火山 SDK 适配层 `VolcengineKnowledgeClient.search_knowledge()`。
- 返回结构化检索片段、来源、相关性和中文诊断，方便大模型生成回答。

## 非目标

- 不创建、绑定、删除或重建火山知识库。
- 不导入、更新、删除或同步文档。
- 不读取或写入 PG 知识库管理表。
- 不新增或迁移 SQL 表。
- 不维护标签、不校验标签是否存在。
- 不实现管理后台、前端页面或 Gateway 管理 API。
- 不让 Agent 直接调用火山 SDK 或传入底层知识库配置。
- 不接入 `tools/managed_mcp_guard`：本工具直接调用火山 SDK，不存在受保护的 MCP 路径。
- 不实现缓存、重试和限频，由调用方或后续 change 处理。

## 实施约束：最小化对既有代码的改动

- 本变更**只新增以下文件**（对齐 OceanEngine 工具的 `tools/oceanengine_local_project_runtime/` 模式）：
  - `tools/lumax_knowledge_base.py`：Agent 工具入口。
  - `tools/lumax_knowledge_base_runtime/__init__.py`
  - `tools/lumax_knowledge_base_runtime/service.py`：`LumaxKnowledgeBaseService`。
  - `tools/lumax_knowledge_base_runtime/client.py`：`VolcengineKnowledgeClient`。
  - `backend/tests/test_lumax_knowledge_base.py`：单元测试。
- 允许的既有文件改动**仅限**：
  - `config.yaml` / `config.example.yaml`：新增工具注册项与 `tenant_id → {collection_name, project_name}` 映射段（仅业务配置，不放环境变量）。
  - `backend/pyproject.toml`：通过 `uv add vikingdb-python-sdk` 添加依赖。
  - `.env`（仓库未维护 `.env.example`，占位写入 `.env` 的 `# Optional:` 注释块）：补 `VOLC_ACCESSKEY`、`VOLC_SECRETKEY`、`VIKINGDB_REGION`、可选 `VIKINGDB_HOST`（环境变量占位只放此处，不写进 `config.example.yaml`）。
- **不修改**：`tools/oceanengine_local_*`、`tools/managed_mcp_guard.py`、`backend/packages/harness/deerflow/mcp/context.py`、`runtime/tenant.py`、`runtime/user_context.py`、`backend/app/gateway/auth_middleware.py`、`backend/packages/harness/deerflow/config/app_config.py`、任何已有 middleware 与 lead agent 装配代码。
- 读取上下文复用 `get_request_context()`，不新增 ContextVar、不新增 helper（如 `get_effective_tenant_id`），避免污染既有抽象。
- 读取 tenant→collection 映射时，服务类直接 `yaml.safe_load(AppConfig.resolve_config_path())` 读 raw YAML，**不进 `AppConfig` 的 pydantic schema**，从而避免改动 `config/app_config.py`。

## 命名约定

为避免歧义，本变更涉及的三个名字明确如下：

- OpenSpec 能力规格名：`lumax-knowledge-search`（`openspec/specs/` 下目录名）。
- Agent 原生工具名：`lumax_knowledge_base`（`config.yaml` 注册名 + `tools/lumax_knowledge_base.py` 入口）。
- capability 字符串：`search-knowledge`（`payload_json` 入口的第一个参数值）。

## 方案概述

新增 `tools/lumax_knowledge_base.py` 作为唯一暴露给 Agent 的工具入口。工具接收 `capability` 和 `payload_json`，目前只支持 `search-knowledge`。

`payload_json` 的最小查询契约为：

```json
{
  "query": "用户要检索的问题",
  "top_k": 5,
  "tag_filters": [
    {"key": "business_name", "value": "某业务"}
  ]
}
```

- `query` 必填，去除首尾空白后不得为空。
- `top_k` 可选，默认 `5`，必须为 `[1, 上限]` 的整数；上限默认 `20`，由服务类内部常量集中定义。
- `tag_filters` 可选，固定为 `{"key": "...", "value": "..."}` 列表；服务层负责把它翻译为火山 SDK 期望的过滤结构，Agent 不直接接触底层结构。
- `tenant_id` 优先来自请求上下文；内部服务类和测试可以显式传入，显式参数优先于上下文。

工具层只负责 Agent 适配和 JSON 输入输出；`LumaxKnowledgeBaseService` 负责参数校验、租户 → KB 映射解析、租户检索和统一响应；`VolcengineKnowledgeClient` 负责调用火山官方 SDK 的知识库检索接口。

### tenant_id 读取入口

仓库内 `tenant_id` 当前只通过 `backend/packages/harness/deerflow/mcp/context.py` 的 `McpRequestContext` ContextVar 流通；`runtime/user_context.py` 没有 tenant 帮助函数。本变更：

- `LumaxKnowledgeBaseService` 通过 `mcp/context.py` 已经公开的 `get_request_context()` 读取当前请求的 `tenant_id` 字段。
- 工具层必须忽略 `payload_json` 中可能携带的 `tenant_id`，避免 Agent 自行覆盖身份导致跨租户检索；其它未知字段（如 `kb_id`、`region`）一律忽略不报错，避免因 Agent 多余字段把正常请求挂掉。
- 经 `runtime/tenant.py:normalize_tenant_id()` 校验后为 `None`（缺失、空串或全 0）时，工具必须返回结构化失败结果，**不得**回退任何默认值；`DEFAULT_TENANT_ID="1"` 是平台级合法租户，不在拒绝范围。
- 内部服务类显式传入 `tenant_id` 时跳过上下文读取，但仍走相同的 `normalize_tenant_id` 校验。
- 跨线程 / subagent 调用必须沿用仓库已有的 `contextvars.copy_context()` 传播机制（参见 `backend/CLAUDE.md` 中 SubagentExecutor 的现有实现），本变更不重复造轮子。

### 租户 → 知识库映射

`vikingdb-python-sdk` 的 `client.collection(...)` 同时需要 `collection_name` 和 `project_name`，因此映射结构保留两字段。本变更不读 PG 知识库管理表，约定如下：

- 在 `config.yaml` 新增配置段 `lumax_knowledge_base.tenant_collections`，结构为 `tenant_id → {collection_name, project_name}`，例如：

  ```yaml
  lumax_knowledge_base:
    tenant_collections:
      "1":
        collection_name: kb_platform
        project_name: default
      "12345":
        collection_name: kb_tenant_12345
        project_name: tenant_12345
  ```

- `project_name` 缺省时回退为 `"default"`。
- 服务类直接 `yaml.safe_load(AppConfig.resolve_config_path())` 读 raw YAML，不进 `AppConfig` schema；YAML 整数 key（`1:`）也会被强制 `str()` 后匹配。
- 映射缺失或当前租户未配置 collection 时，工具必须返回结构化失败结果并提示运维补配，**不得**回退到任意 KB。

### 火山 SDK 与凭证

- `VolcengineKnowledgeClient` 通过官方 `vikingdb-python-sdk`（PyPI 包名 `vikingdb-python-sdk`，源码 https://github.com/volcengine/vikingdb-python-sdk）调用知识库检索接口。
- SDK 适配层方法签名为 `search_knowledge(collection_name, query, top_k, tag_filters=None)`，**不接收 `tenant_id` 参数**：租户身份由上层服务类负责解析与日志记录，SDK 适配层只负责按 `collection_name` 调 SDK，避免参数冗余和跨层耦合。
- SDK 鉴权依赖 `.env` 或运行环境，约定使用以下环境变量：`VOLC_ACCESSKEY`、`VOLC_SECRETKEY`、`VIKINGDB_REGION`（如 `cn-beijing`）、`VIKINGDB_HOST`（可选，自定义端点；缺省时拼为 `api-knowledgebase.mlp.{region}.volces.com`）。
- 同时兼容 vikingdb 官方文档示例使用的别名 `VOLC_AK` / `VOLC_SK`（适配层先读 `VOLC_ACCESSKEY` / `VOLC_SECRETKEY`，缺失时回退到别名）；规范文档以 `VOLC_ACCESSKEY` / `VOLC_SECRETKEY` 为主。
- 环境变量占位写入仓库已有的 `.env`（`# Optional:` 注释块；当前仓库未维护 `.env.example`，未来若新增可同步迁移）；`config.example.yaml` 仅写工具注册项与 `tenant_id → {collection_name, project_name}` 映射占位。
- 不在代码、日志或返回结果中暴露密钥、签名串或内部 trace。
