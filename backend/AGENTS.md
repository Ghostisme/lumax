# Backend 协作规则

本文件适用于 `backend/` 目录下、且没有更近 `AGENTS.md` 覆盖的路径。

- 后端设计、代码和 skill 支撑变更必须先走 OpenSpec，再进入 Apply。
- `backend/app/**` 与 `backend/packages/harness/deerflow/**` 默认视为 DeerFlow 受保护源码；若进入更深目录，优先遵循更近的 `AGENTS.md`。
- 若目录被标注为受保护源码，严禁为了顺手修复、清理或重构而直接改动；优先寻找扩展点或外围接入层。
- 涉及 Langfuse tracing 的对话链路时，默认使用 `thread_id` 作为 `metadata.langfuse_session_id`；新增独立 `create_chat_model(...).ainvoke(...)` 调用链路时，必须复用统一配置补齐逻辑并保留调用方显式传入的 session 值。
- 禁用词前置拦截不得触发大模型或 agent graph，但必须把本轮 human 输入和拦截 ai 回复写入 LangGraph checkpoint `channel_values.messages`；Postgres checkpointer 写入非 primitive channel 时必须同步更新对应 `channel_versions` / `new_versions`，避免 history 只剩 title。
- 禁用词首轮拦截且无已有 title 时，checkpoint title 使用本次生成的 AI 拦截回复默认值；已有有效 title 的会话命中禁用词时不得覆盖原 title。
- PostgreSQL 后端依赖通过 `postgres` extra 管理；调整本地后端安装或启动链路时，必须确保 `backend/Makefile` 与根目录 `scripts/serve.sh` 的后端 `uv sync` 路径继续携带 `--extra postgres`，避免 `make dev` 同步环境后移除 `asyncpg` / `psycopg` 等依赖。
- 触达后端实现时，继续按需阅读 `backend/CLAUDE.md` 中与当前改动相关的章节。

## 架构文档
- 后端架构与设计模式说明：`@./CLAUDE.md`
