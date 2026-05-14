# 确保 `make dev` 自动安装 PostgreSQL 依赖

## 背景

当前后端把 PostgreSQL 支持依赖放在 `backend/pyproject.toml` 的可选依赖 `postgres` 中，但 `backend/Makefile` 的 `install` 目标只执行 `uv sync`，没有带上 `--extra postgres`。这会导致开发者直接执行 `make dev` 时，`asyncpg`、`psycopg` 等 PostgreSQL 相关包不会自动进入本地 uv 环境。

## 目标

- 让 `make dev` 相关的安装链路在开发环境自动拉起 PostgreSQL extra 依赖。
- 保持现有默认依赖结构不变，只补齐开发启动所需的安装参数。
- 避免开发环境因为缺少 PostgreSQL 包而在启用数据库后端时启动失败。

## 范围

- 更新后端安装/开发启动入口，使其在需要时同步 PostgreSQL extra。
- 必要时补充最小验证，确认 `make dev` 会安装 postgres 依赖。

## 非目标

- 不修改 PostgreSQL 功能本身的运行逻辑。
- 不改变 `backend/pyproject.toml` 中 PostgreSQL 依赖的归属方式。
- 不做数据库迁移或配置切换。
