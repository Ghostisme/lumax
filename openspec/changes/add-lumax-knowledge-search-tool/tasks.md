# 任务清单

## 1. OpenSpec

- [ ] 更新 `lumax-knowledge-search` 规格，聚焦 Agent 知识库检索 tools。
- [ ] 校验本 change 不包含 SQL 表迁移、PG 知识库表读取/写入、管理后台、前端或 Gateway 管理 API。
- [ ] 校验既有代码改动只落在：`config.yaml` / `config.example.yaml`、`backend/pyproject.toml`、`.env`（仓库未维护 `.env.example`）；`tools/oceanengine_local_*`、`tools/managed_mcp_guard.py`、`mcp/context.py`、`runtime/tenant.py`、`runtime/user_context.py`、`auth_middleware.py`、`config/app_config.py`、middleware 链与 lead agent 装配代码不得修改。
- [ ] 不新增 `get_effective_tenant_id` 等 helper；只通过既有 `get_request_context()` 读取。

## 2. Agent 工具层

- [ ] 新增 `tools/lumax_knowledge_base.py`。
- [ ] 暴露 `lumax_knowledge_base_tool(capability: str, payload_json: str) -> str`。
- [ ] 仅支持 `capability="search-knowledge"`。
- [ ] 解析 `payload_json` 并调用内部服务类。
- [ ] 工具层必须忽略 `payload_json` 中可能携带的 `tenant_id`，不允许 Agent 覆盖身份。
- [ ] 工具层必须忽略 `payload_json` 中其它未知字段（如 `kb_id`、`region`），不报错。
- [ ] 拒绝或忽略 Agent 传入的底层知识库配置。
- [ ] 在 `config.yaml` 的 `tools[]` 与 `tool_groups` 中注册 `lumax_knowledge_base`，对齐 `tools/oceanengine_local_*` 的注册风格。

## 3. 内部服务类

- [ ] 新增 `tools/lumax_knowledge_base_runtime/service.py`，定义 `LumaxKnowledgeBaseService.search(tenant_id, query, top_k=None, tag_filters=None)`。
- [ ] 校验 `query` 必填，且去除首尾空白后不得为空。
- [ ] 校验 `top_k` 默认 `5`、必须为 `[1, 上限]` 整数；上限作为模块级常量集中定义。
- [ ] 校验 `tag_filters` 可选，且格式为 `{"key": "...", "value": "..."}` 列表；将其翻译为火山 SDK 期望的过滤结构。
- [ ] 通过 `backend/packages/harness/deerflow/mcp/context.py` 的 `get_request_context()` 读取上下文 `tenant_id`；显式传入参数优先。
- [ ] 经 `runtime/tenant.py:normalize_tenant_id()` 校验后为 `None`（缺失、空串、全 0）时返回结构化失败、禁止回退；`DEFAULT_TENANT_ID="1"` 是合法租户，不拒绝。
- [ ] 读取 `config.yaml` 中的 `lumax_knowledge_base.tenant_collections` 映射（`tenant_id → {collection_name, project_name}`，`project_name` 缺省回退 `"default"`）；通过 `yaml.safe_load(AppConfig.resolve_config_path())` 读 raw YAML，不修改 `AppConfig` schema；缺失对应租户配置时返回结构化失败。
- [ ] 调用火山 SDK client 执行知识库检索。
- [ ] 返回与 `tools/oceanengine_local_*` 一致的统一字段集合：`success`、`message`、`data.user_visible_text`、`data.reply_guidance`、`errors[]`、`tool_name`、`request_id`。

## 4. 火山 SDK 适配层

- [ ] `uv add vikingdb-python-sdk`（PyPI 包名 `vikingdb-python-sdk`，源码 https://github.com/volcengine/vikingdb-python-sdk），写入 `backend/pyproject.toml`。
- [ ] 新增 `tools/lumax_knowledge_base_runtime/client.py`，定义 `VolcengineKnowledgeClient.search_knowledge(collection_name, query, top_k, tag_filters=None, *, project_name="default")`，**不接收 `tenant_id`**。
- [ ] 使用 `vikingdb-python-sdk`（`from vikingdb import IAM` + `from vikingdb.knowledge import VikingKnowledge, SearchKnowledgeRequest`）调用知识库检索接口；`client.collection(collection_name=..., project_name=...)` 必须同时指定两字段。
- [ ] SDK 鉴权读取 `VOLC_ACCESSKEY` / `VOLC_SECRETKEY`，缺失时回退别名 `VOLC_AK` / `VOLC_SK`；`VIKINGDB_REGION` 必填，`VIKINGDB_HOST` 缺省时拼为 `api-knowledgebase.mlp.{region}.volces.com`。
- [ ] 占位**只**写入 `.env`（`# Optional:` 注释块；仓库未维护 `.env.example`），不写入 `config.example.yaml`。
- [ ] 不在代码、日志或返回结果中暴露密钥、签名串或内部 trace。
- [ ] 清洗 SDK 异常，区分"凭证未配置"与"查询失败"两类诊断。

## 5. 测试

- [ ] 新增 `backend/tests/test_lumax_knowledge_base.py`，mock 风格参考 `backend/tests/test_oceanengine_local_unit_native_tool.py:75-88`。
- [ ] mock 火山 SDK，覆盖正常检索。
- [ ] 覆盖 `query` 缺失、空字符串、纯空白。
- [ ] 覆盖租户标识缺失（无上下文 / 空串 / 全 0），`DEFAULT_TENANT_ID="1"` 必须放行。
- [ ] 覆盖 `payload_json` 中携带 `tenant_id` 时被工具层忽略。
- [ ] 覆盖 `payload_json` 中携带未知字段（如 `kb_id`、`region`）时被工具层忽略且不报错。
- [ ] 覆盖跨线程 / subagent 下 `get_request_context()` 经 `contextvars.copy_context()` 仍能正确读到租户。
- [ ] 覆盖租户 → collection 映射缺失。
- [ ] 覆盖 `top_k` 默认值、`top_k=0`、`top_k` 为负数、`top_k` 超上限。
- [ ] 覆盖 `tag_filters` 合法、缺省和非法结构。
- [ ] 覆盖 SDK 凭证缺失与 SDK 异常清洗。
- [ ] 覆盖空命中（火山 SDK 返回 0 条结果）。
- [ ] 覆盖返回结构化 chunks。
- [ ] 覆盖 service 类直接调用（显式 `tenant_id` 优先于上下文）。
- [ ] 覆盖 Agent tool JSON 调用。

## 6. 验证

- [ ] 运行知识库工具定向测试。
- [ ] 运行相关工具注册测试。
- [ ] 运行 `openspec validate add-lumax-knowledge-search-tool --strict`。
