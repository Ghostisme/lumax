# Tasks

- [ ] 修改 `config.yaml`，新增 unified `database` PostgreSQL 配置。
- [ ] 移除 `config.yaml` 中 legacy `checkpointer` sqlite 配置。
- [ ] 验证 PostgreSQL 依赖可用。
- [ ] 更新 `make dev` 相关 Gateway 启动入口，确保启动时包含 PostgreSQL extra 依赖。
- [ ] 验证配置加载结果为 `database.backend=postgres` 且 `checkpointer` 不再覆盖。
- [ ] 使用 `make dev` 重启后检查日志应显示 PostgreSQL 持久化后端。
