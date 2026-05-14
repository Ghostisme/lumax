# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

## 项目简介

DeerFlow 2.0 —— 基于 LangGraph 的"超级智能体框架（super agent harness）"，由 Python 后端 + Next.js 前端组成。智能体运行时内置沙箱、持久化记忆、子智能体（sub-agents）、技能（skills）以及 MCP 集成，并同时以 HTTP 网关和嵌入式 Python 客户端两种形式对外提供。

本仓库内部代号为 **lumax**（参见 `gitnexus://repo/lumax/context`）。

## 顶层目录结构

```
backend/    # Python 3.12 —— harness 包 + FastAPI Gateway（详见 backend/CLAUDE.md）
frontend/   # Next.js 16 + React 19 Web 前端（详见 frontend/CLAUDE.md）
skills/     # 智能体技能 —— public/（已提交）和 custom/（已 gitignore）
scripts/    # 安装、诊断、启动、Docker、部署相关脚本
docker/     # Compose 与容器配置
openspec/   # 进行中的 OpenSpec 变更提案（详见 AGENTS.md）
codex/      # Codex 侧的技能（请勿直接编辑 skills/public/**，详见 AGENTS.md）
config.yaml             # 主运行时配置（模型、沙箱、记忆、渠道……）
extensions_config.json  # MCP 服务器 + 技能启用配置（可通过 Gateway 在运行时修改）
```

## 整体架构

由 Nginx 在前端统一代理三个进程：

- **Gateway**（`:8001`，`backend/app/gateway/`）—— FastAPI 应用，**同时**承载 REST 接口（`/api/models`、`/api/skills`、`/api/memory`、`/api/threads/...` 等）**和**嵌入式的、兼容 LangGraph 的智能体运行时。对外的 LangGraph 路径以 `/api/langgraph/*` 暴露，内部会被改写到原生的 `/api/*` 路由器。
- **Frontend**（`:3000`，`frontend/`）—— Next.js App Router，通过 `langgraph-sdk` 客户端访问 Gateway。
- **Nginx**（`:2026`）—— 单一入口。`/api/langgraph/*` → Gateway 运行时，其他 `/api/*` → Gateway 路由器，`/` → 前端。
- **Provisioner**（`:8002`，可选）—— 仅在 `sandbox.use` 配置为 provisioner / Kubernetes 模式时启动。

后端被严格拆分，依赖方向由 CI 强制保证：

- `backend/packages/harness/deerflow/` —— 可发布的智能体框架（`import deerflow.*`）。包含 agents、middlewares、sandbox、sub-agents、models、MCP、skills、memory、config 以及嵌入式 `DeerFlowClient`。
- `backend/app/` —— 不发布的应用层（`import app.*`）。包含 FastAPI Gateway 和 IM 渠道集成（飞书、Slack、Telegram、微信/企业微信、钉钉）。
- **规则：** `app` 可以 import `deerflow`；`deerflow` 绝对不能 import `app`。由 `backend/tests/test_harness_boundary.py` 强制约束。

主智能体（lead agent）在 `deerflow/agents/lead_agent/agent.py` 中装配，串联约 18 个中间件（thread data → uploads → sandbox → guardrails → tool error handling → summarization → todos → memory → vision → loop detection → clarification）。身份信息（`user_id / tenant_id / business_code`）从前端会话 → Gateway 的 `AuthMiddleware` → MCP 的 `ContextVar` 一路向下传递，下游 Java MCP 服务（`platform-upms`、`platform-sales`）通过 `X-User-Id` / `TenantId` / `BUSINESS_CODE` 请求头完成鉴权 —— **`tenantId` 是数字字符串，可能超过 `Number.MAX_SAFE_INTEGER`，绝对不要用 `Number()` 转换它**。完整握手流程见 `backend/CLAUDE.md` 中的 "MCP System" 章节。

需要更深入的细节时按需加载：
- 后端内部、中间件顺序、沙箱、记忆、MCP、渠道 → **`backend/CLAUDE.md`**
- 前端数据流、auth/MCP 身份透传、生成式组件规则 → **`frontend/CLAUDE.md`**
- 仓库级治理规范（OpenSpec、包边界、巨量引擎本地推广技能规则） → **`AGENTS.md`**（以及该文件顶部的 OpenSpec 区块）

## 常用命令

除非特别说明，均在仓库根目录执行。Windows 下请使用 Git Bash 运行 `serve.sh`/`docker.sh` 相关命令；Makefile 会通过 `scripts/run-with-git-bash.cmd` 自动转发，并使用 Python 启动器管理核心生命周期。

安装与诊断：
```bash
make setup          # 交互式向导 —— 生成 config.yaml + .env
make doctor         # 校验配置和系统环境（出现异常时运行）
make check          # 检查 Node 22+、pnpm、uv、nginx 是否已安装
make install        # uv sync（后端）+ pnpm install（前端）+ pre-commit 钩子
make config-upgrade # 把 config.example.yaml 中的新字段合并到现有 config.yaml
```

启动完整服务（Gateway + 前端 + Nginx → http://localhost:2026）：
```bash
make dev            # 前台运行，热重载
make dev-daemon     # 后台运行
make start          # 生产模式（无热重载）
make stop           # 停止全部
```

只启动前端（当 Gateway/LangGraph 已经在调试器等场景中运行时）：
```bash
make dev-fe         # 仅启动 Nginx + Next.js
make stop-fe
```

Docker：
```bash
make docker-init    # 拉取沙箱镜像（首次或更新时）
make docker-start   # 开发模式（热重载、源码挂载）—— 根据 config.yaml 自动识别沙箱模式
make docker-stop
make up / make down # 生产模式：构建本地镜像并启动 / 停止
```

后端测试与 lint（在 `backend/` 目录下）：
```bash
make test                                         # 全量 pytest
PYTHONPATH=. uv run pytest tests/test_<x>.py -v   # 单个文件
make lint   # ruff check
make format # ruff format
```

前端检查（在 `frontend/` 目录下）：
```bash
pnpm check     # ESLint + tsc --noEmit（提交前必跑）
pnpm test      # Vitest 单测（tests/unit/ 与 src/ 一一对应）
pnpm test:e2e  # Playwright（Chromium），后端通过 page.route() mock
```

## 必须了解的约定

- **配置查找顺序：** `config_path` 参数 → `DEER_FLOW_CONFIG_PATH` 环境变量 → `./config.yaml` → `../config.yaml`。推荐放在项目根目录。以 `$` 开头的值会按环境变量解析。配置会被缓存，但会按文件 mtime 自动重载 —— 大多数修改无需重启。
- **后端改动必须 TDD。** 在 `backend/tests/test_<feature>.py` 中新增/更新测试，并在声明完成前执行 `make test`。后端 ruff 行宽 240；Python 3.12+，使用双引号。
- **不要手改自动生成的 UI：** `frontend/src/components/ui/` 与 `frontend/src/components/ai-elements/` 由 registry 生成，且已被 ESLint 忽略。
- **OpenSpec 管控所有长期资产。** 涉及版本化资产的设计/代码/技能改动，必须先走 OpenSpec 变更流程 —— 详见 `AGENTS.md` 顶部的 OpenSpec 区块，包括 `proposal.md` / `tasks.md` / `design.md` / `spec.md` 以及 `openspec archive` 之前的多个"停下来等待用户明确批准"检查点。
- **巨量引擎本地推广技能**（`oceanengine_local_project` / `_unit` / `_material`）有严格的路由和校验规则 —— 不要让主智能体直接调用受保护的 `localUnit*`、`localPromotion*`、`localFile*`、`localImageUpload` 等 MCP 工具，也不要把项目/单元/素材的能力混在一起使用。完整规则列表见 `AGENTS.md`。

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lumax** (26104 symbols, 40915 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/lumax/context` | Codebase overview, check index freshness |
| `gitnexus://repo/lumax/clusters` | All functional areas |
| `gitnexus://repo/lumax/processes` | All execution flows |
| `gitnexus://repo/lumax/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
