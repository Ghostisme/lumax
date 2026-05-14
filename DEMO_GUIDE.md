# DeerFlow 多 Agent 协作 Demo 部署与使用手册

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 架构说明](#2-架构说明)
- [3. 环境准备](#3-环境准备)
- [4. 快速部署](#4-快速部署)
- [5. 配置详解](#5-配置详解)
- [6. Demo 场景：Master Agent 调用 Helper Agent](#6-demo-场景master-agent-调用-helper-agent)
- [7. 前端操作指南](#7-前端操作指南)
- [8. 常见问题排查](#8-常见问题排查)
- [9. 进阶：自定义 Agent](#9-进阶自定义-agent)

---

## 1. 项目概述

本 Demo 基于 **DeerFlow** (Deep Exploration and Efficient Research Flow) 构建，实现了一个完整的多 Agent 协作系统：

- **Master Agent（主代理）**：默认的 Lead Agent，接收用户对话，具备委派子任务给其他 Agent 的能力
- **Helper Agent（助手代理）**：自定义代理，专门处理信息查询、文本摘要和知识整理等子任务

### 核心流程

```
用户 ──对话──> Master Agent (Lead Agent)
                    │
                    ├── 直接回答简单问题
                    │
                    └── 委派复杂任务 ──> Helper Agent (自定义代理)
                                              │
                                              └── 完成任务后返回结果给 Master Agent
                                                        │
                                                        └── Master Agent 整合结果回复用户
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16 + React 19 + Tailwind CSS 4 + LangGraph SDK |
| 后端网关 | FastAPI + Uvicorn |
| Agent 运行时 | LangGraph + LangChain |
| 反向代理 | Nginx |
| 包管理 | uv (Python) + pnpm (Node.js) |

---

## 2. 架构说明

### 服务架构

```
浏览器 (localhost:2026)
    │
    └── Nginx (反向代理, 端口 2026)
            ├── /api/langgraph/*  ──>  LangGraph Server (端口 2024) ── Agent 运行时
            ├── /api/*            ──>  Gateway (端口 8001) ── REST API
            └── /*                ──>  Frontend (端口 3000) ── Next.js Web UI
```

### Agent 架构

```
Lead Agent (make_lead_agent)
    ├── 系统提示词 (SOUL.md + 内置提示模板)
    ├── 工具集 (web_search, web_fetch, file ops, bash...)
    ├── 子代理系统 (subagents)
    │     ├── general-purpose (通用子代理 - 内置)
    │     └── bash (命令行子代理 - 内置)
    ├── 自定义代理 (via agent_name)
    │     └── helper-agent (本 Demo 创建的自定义代理)
    └── 中间件链 (摘要、记忆、标题、工具错误处理...)
```

### 文件结构 (Demo 相关)

```
lumax/
├── .env                              # API Key 环境变量
├── config.yaml                       # 应用配置 (模型、工具、子代理等)
├── DEMO_GUIDE.md                     # 本手册
├── Makefile                          # 统一命令入口
│
├── backend/
│   ├── .deer-flow/
│   │   └── agents/
│   │       └── helper-agent/         # 自定义 Helper Agent
│   │           ├── config.yaml       # Agent 配置
│   │           └── SOUL.md           # Agent 人格/行为定义
│   ├── langgraph.json                # LangGraph 图注册
│   └── packages/harness/deerflow/
│       ├── agents/                   # Lead Agent 核心代码
│       │   └── lead_agent/
│       │       ├── agent.py          # make_lead_agent 工厂函数
│       │       └── prompt.py         # 系统提示词模板
│       └── subagents/                # 子代理系统
│           ├── executor.py           # 子代理执行器
│           ├── registry.py           # 子代理注册表
│           └── builtins/             # 内置子代理
│               ├── general_purpose.py
│               └── bash_agent.py
│
└── frontend/
    ├── .env                          # 前端环境变量
    ├── next.config.js                # Next.js 配置 (含 API 代理)
    └── src/
        ├── app/
        │   ├── workspace/            # 工作区页面
        │   │   ├── chats/            # 对话页面
        │   │   └── agents/           # Agent 管理页面
        │   └── mock/api/             # Mock API (演示模式)
        └── core/
            ├── api/                  # API 客户端
            ├── agents/               # Agent CRUD
            └── threads/              # 对话管理
```

---

## 3. 环境准备

### 3.1 必需软件

| 软件 | 最低版本 | 安装方式 |
|------|---------|---------|
| **Node.js** | >= 22 | https://nodejs.org/ |
| **pnpm** | >= 10 | `npm install -g pnpm` 或 `corepack enable` |
| **Python** | >= 3.12 | https://www.python.org/ |
| **uv** | 最新版 | 见下方安装说明 |
| **Nginx** | 任意版本 | 见下方安装说明 |
| **Git** | 任意版本 | https://git-scm.com/ |

### 3.2 安装 uv (Python 包管理器)

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后重启终端，验证安装：
```
uv --version
```

### 3.3 安装 Nginx

**Windows:**
1. 从 https://nginx.org/en/download.html 下载 Windows 版本
2. 解压到任意目录（如 `C:\nginx`）
3. 将 nginx 目录添加到系统 PATH
4. 或者使用 WSL/Docker 模式运行

**macOS:**
```bash
brew install nginx
```

**Ubuntu/Debian:**
```bash
sudo apt install nginx
```

### 3.4 获取模型 API Key

本 Demo 默认配置使用**通义千问 (DashScope)**，您也可以选择其他模型：

| 模型提供商 | 申请地址 | 环境变量名 |
|-----------|---------|-----------|
| **通义千问 (推荐)** | https://dashscope.console.aliyun.com/ | `DASHSCOPE_API_KEY` |
| DeepSeek | https://platform.deepseek.com/ | `DEEPSEEK_API_KEY` |
| OpenAI | https://platform.openai.com/ | `OPENAI_API_KEY` |

---

## 4. 快速部署

### 4.1 步骤一：检查依赖

```bash
make check
```

该命令会检测 Node.js、pnpm、uv、nginx 是否已安装。确保所有项都显示 "OK"。

### 4.2 步骤二：配置 API Key

编辑项目根目录的 `.env` 文件：

```bash
# 方案1: 通义千问 (默认)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 方案2: DeepSeek (需同时修改 config.yaml)
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

> **切换模型提供商：** 如果使用 DeepSeek 或 OpenAI，需要编辑 `config.yaml`，注释掉通义千问配置，取消注释对应模型配置。

### 4.3 步骤三：安装依赖

```bash
make install
```

该命令会执行：
- `cd backend && uv sync` — 安装 Python 后端依赖
- `cd frontend && pnpm install` — 安装 Node.js 前端依赖

### 4.4 步骤四：启动服务

**开发模式（推荐，支持热重载）：**
```bash
make dev
```

**生产模式：**
```bash
make start
```

**后台运行：**
```bash
make dev-daemon
```

启动成功后会看到：
```
==========================================
  ✓ DeerFlow is running!  [DEV (hot-reload enabled)]
==========================================

  🌐 http://localhost:2026

  Routing: Frontend → Nginx → LangGraph + Gateway
  API:     /api/langgraph/*  →  LangGraph server (2024)
           /api/*            →  Gateway REST API (8001)

  📋 Logs: logs/{langgraph,gateway,frontend,nginx}.log
```

### 4.5 步骤五：访问 Web UI

打开浏览器访问 **http://localhost:2026**

- 首页是 DeerFlow 的宣传页
- 点击导航栏的 "Workspace" 进入工作区
- 或直接访问 **http://localhost:2026/workspace**

### 4.6 停止服务

```bash
make stop
```

---

## 5. 配置详解

### 5.1 config.yaml 关键配置

#### 模型配置

```yaml
models:
  - name: qwen-plus                   # 模型标识符
    display_name: 通义千问 Plus        # 显示名称
    use: langchain_openai:ChatOpenAI   # LangChain 提供者类
    model: qwen-plus                   # API 模型名
    api_key: $DASHSCOPE_API_KEY        # 从环境变量读取
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    request_timeout: 600.0
    max_tokens: 8192
    temperature: 0.7
    supports_vision: true
```

#### 子代理配置（Demo 关键）

```yaml
subagents:
  timeout_seconds: 300                 # 默认超时 5 分钟
  agents:
    general-purpose:
      timeout_seconds: 600             # 通用子代理超时 10 分钟
      max_turns: 80                    # 最大对话轮次
```

#### Agent API（Demo 关键）

```yaml
agents_api:
  enabled: true                        # 启用自定义 Agent 管理 API
```

### 5.2 Helper Agent 配置

**位置：** `backend/.deer-flow/agents/helper-agent/`

**config.yaml:**
```yaml
name: helper-agent
description: "智能助手代理 - 可被主代理调用，专门处理信息查询、文本摘要和知识整理任务"
model: null                            # null 表示使用默认模型
tool_groups:
  - web                                # 网络搜索和抓取
  - file:read                          # 文件读取
  - file:write                         # 文件写入
```

**SOUL.md** 定义了 Agent 的人格和行为准则（参见 `backend/.deer-flow/agents/helper-agent/SOUL.md`）。

---

## 6. Demo 场景：Master Agent 调用 Helper Agent

### 6.1 场景一：直接对话（使用 Master Agent）

1. 访问 http://localhost:2026/workspace
2. 点击 "New Chat" 创建新对话
3. 在对话模式选择器中选择 **Ultra** 模式（启用子代理功能）
4. 输入问题，例如：

   > "请帮我搜索最近关于人工智能的新闻，整理成一份简报"

5. Master Agent 会：
   - 分析任务需求
   - 委派给 general-purpose 子代理执行网络搜索
   - 整合结果回复用户

### 6.2 场景二：通过 Helper Agent 对话

1. 访问 http://localhost:2026/workspace/agents
2. 可以看到已创建的 **helper-agent**
3. 点击 helper-agent，进入该 Agent 的专属对话界面
4. 发送消息：

   > "帮我查询 Python 3.12 的新特性并整理成文档"

5. 此时 Master Agent 会加载 helper-agent 的 SOUL.md 作为额外上下文，使其行为更聚焦于信息查询和整理

### 6.3 场景三：Master Agent 自动委派（核心 Demo）

这是展示双 Agent 协作的核心场景：

1. 创建新对话，选择 **Ultra** 模式
2. 输入复杂任务：

   > "我需要做一个关于 DeerFlow 项目的技术调研报告。请先搜索相关资料，然后整理成一份结构化的 Markdown 报告，保存到文件中。"

3. Master Agent 的处理流程：
   - **步骤1**：分析任务，判断需要委派子任务
   - **步骤2**：调用 `task` 工具，将"搜索资料"任务委派给子代理
   - **步骤3**：子代理执行搜索、整理、写文件
   - **步骤4**：子代理返回结果给 Master Agent
   - **步骤5**：Master Agent 整合结果，回复用户

4. 在对话界面中可以看到：
   - Master Agent 的思考过程
   - 子任务的启动通知 ("Task started...")
   - 子任务的运行状态 ("Task running...")
   - 子任务的完成结果 ("Task completed")
   - Master Agent 的最终整合回复

### 6.4 对话模式说明

| 模式 | 说明 | 子代理 |
|------|------|--------|
| **Flash** | 快速回答，关闭思考 | ❌ |
| **Thinking** | 开启思考，低推理 | ❌ |
| **Pro** | 计划模式，中等推理 | ❌ |
| **Ultra** | 完整模式，高推理 | ✅ 启用子代理 |

> 只有 **Ultra** 模式启用子代理功能，这是 Demo 的核心模式。

---

## 7. 前端操作指南

### 7.1 工作区首页

- **URL**: http://localhost:2026/workspace
- 自动重定向到 `/workspace/chats/new` （新对话）

### 7.2 创建新对话

1. 在左侧栏点击 "New Chat"
2. 在底部输入框输入消息
3. 选择对话模式（Flash/Thinking/Pro/Ultra）
4. 按 Enter 发送

### 7.3 Agent 管理页面

- **URL**: http://localhost:2026/workspace/agents
- 查看所有已注册的自定义 Agent
- 点击 Agent 进入其专属对话界面
- 支持创建新 Agent

### 7.4 创建新 Agent

1. 访问 http://localhost:2026/workspace/agents
2. 点击 "New Agent"
3. 输入 Agent 名称（仅英文、数字、连字符）
4. 系统会启动 bootstrap 流程，通过对话方式配置 Agent
5. 完成后 Agent 将出现在 Agent 列表中

### 7.5 查看 API 文档

- **Swagger UI**: http://localhost:2026/api/docs
- **ReDoc**: http://localhost:2026/api/redoc

---

## 8. 常见问题排查

### Q1: `make dev` 报错 "uv not found"

安装 uv：
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```
重启终端后重试。

### Q2: `make dev` 报错 "nginx not found"

Windows 用户需要手动安装 nginx 并添加到 PATH。

替代方案：不使用 nginx，直接分别启动各服务，通过 Next.js 的 rewrites 功能代理 API 请求：

```powershell
# 终端1: 启动 LangGraph
cd backend
uv run langgraph dev --no-browser

# 终端2: 启动 Gateway
cd backend
$env:PYTHONPATH = "."
uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001 --reload

# 终端3: 启动 Frontend
cd frontend
pnpm run dev
```

然后访问 **http://localhost:3000**（不经过 nginx，直接通过 Next.js 的 rewrites 代理）。

### Q3: 启动后看不到 Helper Agent

确认以下文件存在：
- `backend/.deer-flow/agents/helper-agent/config.yaml`
- `backend/.deer-flow/agents/helper-agent/SOUL.md`

确认 `config.yaml` 中 `agents_api.enabled: true`。

检查 Gateway 日志：
```bash
# 查看日志
type logs\gateway.log
```

### Q4: 对话没有调用子代理

确保：
1. 对话模式选择了 **Ultra**（只有 Ultra 模式启用子代理）
2. `config.yaml` 中 `subagents` 部分已配置
3. 提出的问题足够复杂，需要委派子任务

### Q5: API Key 无效或模型调用失败

1. 检查 `.env` 文件中的 API Key 是否正确
2. 检查 `config.yaml` 中模型配置的 `api_key` 字段引用的环境变量名是否匹配
3. 测试 API Key 是否有效：

```bash
# 测试通义千问
curl https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"hello"}]}'
```

### Q6: Windows 上 `make` 命令不可用

安装 GNU Make：
- 通过 Chocolatey: `choco install make`
- 或使用 Git Bash 中自带的 make

### Q7: 端口被占用

```powershell
# 查看端口占用
netstat -ano | findstr ":2024 :8001 :3000 :2026"

# 终止占用进程
taskkill /PID <PID> /F
```

### Q8: 前端页面白屏或加载失败

1. 检查前端日志：`type logs\frontend.log`
2. 确保 `frontend/.env` 文件存在
3. 尝试清理缓存重建：
```bash
cd frontend
pnpm run build
```

---

## 9. 进阶：自定义 Agent

### 9.1 手动创建 Agent

在 `backend/.deer-flow/agents/` 下创建新目录：

```
backend/.deer-flow/agents/
└── my-agent/
    ├── config.yaml
    └── SOUL.md
```

**config.yaml 模板：**
```yaml
name: my-agent
description: "自定义 Agent 描述"
model: null                    # null 使用默认模型，或指定模型名
tool_groups:                   # 可用工具组
  - web
  - file:read
  - file:write
  - bash
skills: null                   # null 加载所有技能，[] 禁用技能
```

**SOUL.md 模板：**
```markdown
# My Agent

## 身份
你是一个[角色描述]...

## 核心能力
- 能力1
- 能力2

## 工作准则
1. 准则1
2. 准则2
```

### 9.2 通过 API 管理 Agent

```bash
# 列出所有 Agent
curl http://localhost:2026/api/agents

# 获取单个 Agent
curl http://localhost:2026/api/agents/helper-agent

# 创建新 Agent
curl -X POST http://localhost:2026/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "research-agent",
    "description": "Research specialist",
    "soul": "# Research Agent\n\nYou are a research specialist..."
  }'

# 更新 Agent
curl -X PUT http://localhost:2026/api/agents/research-agent \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'

# 删除 Agent
curl -X DELETE http://localhost:2026/api/agents/research-agent
```

### 9.3 Agent 的工作原理

1. **用户发起对话** → 前端调用 LangGraph SDK 的 `useStream`
2. **LangGraph Server** 调用 `make_lead_agent(config)` 构建 Agent
3. 如果指定了 `agent_name`（如 `helper-agent`），Lead Agent 会：
   - 从 `backend/.deer-flow/agents/helper-agent/config.yaml` 加载配置
   - 从 `backend/.deer-flow/agents/helper-agent/SOUL.md` 加载人格
   - 将 SOUL.md 内容注入系统提示词
   - 使用配置中指定的工具组和模型
4. **子代理调用**（Ultra 模式）：
   - Lead Agent 分析用户输入，判断是否需要委派
   - 通过 `task` 工具启动 `SubagentExecutor`
   - 子代理使用独立的执行上下文完成任务
   - 结果通过 SSE 流式返回前端

---

## 附录

### A. 完整命令参考

| 命令 | 说明 |
|------|------|
| `make check` | 检查系统依赖 |
| `make setup` | 交互式配置向导 |
| `make install` | 安装所有依赖 |
| `make dev` | 开发模式启动（热重载） |
| `make dev-pro` | Gateway 模式启动（实验性） |
| `make dev-daemon` | 后台开发模式 |
| `make start` | 生产模式启动 |
| `make stop` | 停止所有服务 |
| `make clean` | 清理临时文件 |
| `make doctor` | 诊断配置问题 |

### B. 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 2026 | 统一入口（反向代理） |
| LangGraph | 2024 | Agent 运行时 |
| Gateway | 8001 | REST API |
| Frontend | 3000 | Next.js Web UI |

### C. 日志位置

| 日志文件 | 说明 |
|---------|------|
| `logs/langgraph.log` | LangGraph 运行日志 |
| `logs/gateway.log` | Gateway API 日志 |
| `logs/frontend.log` | Next.js 前端日志 |
| `logs/nginx.log` | Nginx 代理日志 |
| `logs/nginx-access.log` | Nginx 访问日志 |
| `logs/nginx-error.log` | Nginx 错误日志 |

### D. 关键 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agents` | GET | 列出所有自定义 Agent |
| `/api/agents/{name}` | GET | 获取 Agent 详情 |
| `/api/agents` | POST | 创建 Agent |
| `/api/agents/{name}` | PUT | 更新 Agent |
| `/api/agents/{name}` | DELETE | 删除 Agent |
| `/api/models` | GET | 列出可用模型 |
| `/api/skills` | GET | 列出可用技能 |
| `/api/memory` | GET | 获取记忆数据 |
| `/api/docs` | GET | Swagger API 文档 |
| `/api/threads/search` | POST | 搜索对话线程 |

---

*本手册由 DeerFlow Demo 自动生成，最后更新时间：2026-04-21*
