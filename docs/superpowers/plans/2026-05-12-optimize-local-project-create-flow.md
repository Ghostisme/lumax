# Optimize Local Project Create Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为本地推创建项目增加一个最小业务编排工具，负责业务默认项、视频数量、单元命名和跨原生工具边界，不改受保护 DeerFlow 源码。

**Architecture:** 新增根目录 `tools/oceanengine_local_project_create_flow.py`，只负责流程态和 payload 组装；真实执行继续委托 `oceanengine_local_project`、`oceanengine_local_material`、`oceanengine_local_unit`。新增聚焦测试覆盖默认项、禁止自造字段、素材候选、视频数量、单元名称和用户可见清洗。

**Tech Stack:** Python 3.12、LangChain `@tool`、现有 OceanEngine root `tools/`、pytest、OpenSpec。

---

### Task 1: 流程编排工具和项目 payload 默认项

**Files:**
- Create: `tools/oceanengine_local_project_create_flow.py`
- Test: `backend/tests/test_oceanengine_local_project_create_flow.py`
- Modify: `config.yaml`
- Modify: `config.example.yaml`

- [ ] **Step 1: 写失败测试**

覆盖缺少投手只追问投手、投手不进入 `localProjectCreate` payload、默认定向/排期/出价落地、未声明字段不进入 payload。

- [ ] **Step 2: 运行测试确认失败**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

- [ ] **Step 3: 实现最小工具**

新增 `run_oceanengine_local_project_create_flow(payload, dry_run=False)` 和 LangChain tool wrapper；dry-run 返回流程生成结果，非 dry-run 在项目参数完整时委托 `run_oceanengine_local_project("create-project", ...)`。

- [ ] **Step 4: 运行测试确认通过**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

### Task 2: 素材候选与视频数量

**Files:**
- Modify: `tools/oceanengine_local_project_create_flow.py`
- Test: `backend/tests/test_oceanengine_local_project_create_flow.py`

- [ ] **Step 1: 写失败测试**

覆盖素材库候选 `choice_cards`、团购成交 10 条视频、其它目标 3 到 5 条视频、未授权素材不扫描本地路径。

- [ ] **Step 2: 运行测试确认失败**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

- [ ] **Step 3: 实现素材流程分支**

只调用 `run_oceanengine_local_material` 查询/上传；不足数量时返回中文单问题，不静默裁剪。

- [ ] **Step 4: 运行测试确认通过**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

### Task 3: 单元名称和项目后单元配置边界

**Files:**
- Modify: `tools/oceanengine_local_project_create_flow.py`
- Test: `backend/tests/test_oceanengine_local_project_create_flow.py`

- [ ] **Step 1: 写失败测试**

覆盖 `yyyyMMdd` + 地域 + 定向 + 年龄 + 投手姓名首字母大写、单元失败不伪造成完整成功、单元配置委托 `run_oceanengine_local_unit`。

- [ ] **Step 2: 运行测试确认失败**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

- [ ] **Step 3: 实现单元流程分支**

项目创建成功后才调用单元工具；失败时返回“项目已创建、单元配置失败”的中文结果。

- [ ] **Step 4: 运行测试确认通过**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

### Task 4: 验证和任务状态

**Files:**
- Modify: `openspec/changes/optimize-local-project-create-flow/tasks.md`

- [ ] **Step 1: 运行聚焦测试**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_create_flow.py -q`

- [ ] **Step 2: 运行相关回归**

Run: `PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests/test_oceanengine_local_project_rules.py backend/tests/test_oceanengine_local_material_native_tool.py backend/tests/test_oceanengine_local_unit_native_tool.py backend/tests/test_gateway_visibility.py -q`

- [ ] **Step 3: 运行 OpenSpec 严格校验**

Run: `openspec validate optimize-local-project-create-flow --strict`

- [ ] **Step 4: 运行 GitNexus 变更检测**

Run: `gitnexus detect_changes` 或 MCP `detect_changes(scope="all", repo="lumax")`

- [ ] **Step 5: 更新 `tasks.md`**

仅把实际完成并验证过的条目标记为 `[x]`，未做浏览器真实验收的条目保持未完成。
