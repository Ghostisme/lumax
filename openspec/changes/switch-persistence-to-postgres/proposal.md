# Switch Persistence To Postgres

## 背景

当前 `.env` 已配置 `DEERFLOW_POSTGRES_DSN`，但 Gateway 启动日志显示仍初始化为 SQLite：

- `Persistence engine initialized: backend=sqlite`
- `Store: using AsyncSqliteStore (...)`

原因是 `config.yaml` 未配置统一 `database:` 段，同时仍保留 legacy `checkpointer:` 段。现有代码中 legacy `checkpointer:` 优先级高于 unified `database:`，因此会话状态、线程 store 和应用 ORM 仍走本地 SQLite。

## 目标

将 DeerFlow 会话、线程元数据、运行记录、checkpointer/store 等统一持久化切换到 PostgreSQL，使用 `.env` 中已存在的 `DEERFLOW_POSTGRES_DSN`。

## 变更范围

- 在 `config.yaml` 增加统一持久化配置：
  - `database.backend: postgres`
  - `database.postgres_url: $DEERFLOW_POSTGRES_DSN`
- 移除 `config.yaml` 中 legacy `checkpointer:` sqlite 配置，避免它继续覆盖 unified database 配置。
- 更新本地开发启动入口，使 `make dev` 启动 Gateway 时保留 PostgreSQL extra 依赖，避免普通 `uv run` 同步环境后移除 `asyncpg`。

## 非目标

- 不修改 `.env` 中的 DSN 值。
- 不迁移本地 SQLite 历史数据到 PostgreSQL。
- 不修改认证、线程隔离或 `/api/threads/search` 查询逻辑。
- 不修改 Lumax 计量库配置；`LUMAX_DB_DSN` 仍只用于计量和相关业务表。

## 风险与约束

- 切换后，本地 SQLite 中已有会话不会自动出现在 PostgreSQL 中；如果需要保留历史，需要单独执行数据迁移。
- PostgreSQL 连接不可用时 Gateway 启动会失败或持久化初始化失败。
- 需要重启 Gateway 才能让配置变更生效。
- 本地开发启动脚本必须与 PostgreSQL backend 配置保持一致；否则 `make dev` 会在 Gateway 启动前把 `asyncpg` 从 uv 环境中移除，导致启动失败。
