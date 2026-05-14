# OceanEngine Local Project Native Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `oceanengine-local-project` 的全部 capability 固化为通过 `oceanengine_local_project` 原生业务工具统一调用。

**Architecture:** 继续采用单原生业务工具加 capability 路由。业务工具读取 `rules/index.json`，加载对应规则并复用公共 endpoint runner；MCP guard 负责阻断主 Agent 直调受管理 MCP 工具。

**Tech Stack:** Python 3.12、LangChain tool、OpenSpec、pytest、unittest、DeerFlow 前端页面验收。

---

### Task 1: 补齐原生业务工具路由测试

**Files:**
- Modify: `backend/tests/test_oceanengine_native_tool.py`

- [ ] **Step 1: 写失败测试**

新增测试覆盖创建项目之外的读取、详情、批量 capability，并断言 `execution_source`、`business_tool_name` 和 `mcp_tool_name` 来自同一原生业务工具。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_oceanengine_native_tool.py -q`

- [ ] **Step 3: 最小实现**

如测试失败，修改 `tools/oceanengine_local_project.py`，只补齐 capability 路由、错误诊断或结果 enrich 缺口。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_oceanengine_native_tool.py -q`

### Task 2: 补齐 MCP guard 覆盖

**Files:**
- Modify: `backend/tests/test_oceanengine_native_tool.py`
- Modify: `tools/managed_mcp_guard.py` if needed

- [ ] **Step 1: 写失败测试**

新增测试遍历 `rules/index.json` 中 16 个能力的 `mcp.tool`，验证 direct router 调用被阻断，`allow_managed_mcp_calls("oceanengine_local_project")` 内允许。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_oceanengine_native_tool.py -q`

- [ ] **Step 3: 最小实现**

如果有工具未被管理，补齐 `tools/managed_mcp_guard.py` 的映射。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_oceanengine_native_tool.py -q`

### Task 3: 补齐 skill endpoint dry-run 证明

**Files:**
- Modify: `skills/custom/oceanengine-local-project/scripts/tests/test_oceanengine_local_project.py`

- [ ] **Step 1: 写失败测试**

新增测试覆盖非创建项目 endpoint 脚本 dry-run，证明独立脚本仍按 rule 文件执行。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest skills/custom/oceanengine-local-project/scripts/tests/test_oceanengine_local_project.py`

- [ ] **Step 3: 最小实现**

如 endpoint 脚本不一致，只调整对应 endpoint 的 `RULE_FILE` 或公共加载逻辑。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest skills/custom/oceanengine-local-project/scripts/tests/test_oceanengine_local_project.py`

### Task 4: 页面验收与任务状态

**Files:**
- Modify: `openspec/changes/update-oceanengine-local-project-native-dispatch/tasks.md`

- [ ] **Step 1: 运行 OpenSpec 校验**

Run: `openspec validate update-oceanengine-local-project-native-dispatch --strict`

- [ ] **Step 2: 运行项目测试**

Run: `cd backend && pytest tests/test_oceanengine_native_tool.py -q`

Run: `python -m unittest skills/custom/oceanengine-local-project/scripts/tests/test_oceanengine_local_project.py`

- [ ] **Step 3: 页面验收**

启动前端、Gateway 和 agent runtime，用账号 `1854708763953159` 在页面发起获取本地推项目列表或详情的对话请求，确认调用路径经过 `oceanengine_local_project`。

- [ ] **Step 4: 更新任务状态**

只有实际完成的任务改为 `- [x]`，并在交付中说明未完成或受阻项。

