# MCP 动态候选卡片契约 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 OceanEngine 动态 MCP 候选按 `choice_cards` 契约返回，并提供不依赖前端改动的中文文本兜底。

**Architecture:** 后端保持现有原生业务工具链路：`endpoint_runner` 负责生成结构化 `data.clarification.input_control`，`agent_visible_result` 负责用户可见文本兜底，Gateway `visibility` 负责结构化字段清洗与透传。实现只触碰后端、测试和 OpenSpec 任务状态，不修改 `frontend/**`。

**Tech Stack:** Python 3.12、pytest、OpenSpec、GitNexus、Superpowers TDD。

---

### Task 1: 标记已完成的 OpenSpec 文档任务

**Files:**
- Modify: `openspec/changes/clarification-card-interactions/tasks.md`

- [x] **Step 1: 确认规格增量已存在**

Run: `test -f openspec/changes/clarification-card-interactions/specs/structured-parameter-clarification/spec.md`
Expected: exit 0

- [x] **Step 2: 确认 OpenSpec 严格校验通过**

Run: `openspec validate clarification-card-interactions --strict`
Expected: `Change 'clarification-card-interactions' is valid`

- [x] **Step 3: 更新 OpenSpec 任务状态**

把 `tasks.md` 中 1.3、1.4、1.5 从 `- [ ]` 改为 `- [x]`，因为规格增量、严格校验和用户批准都已完成。

### Task 2: 用 TDD 补动态候选文本兜底

**Files:**
- Modify: `backend/tests/test_oceanengine_dependent_clarification_options.py`
- Modify: `tools/oceanengine_local_project_runtime/agent_visible.py`

- [x] **Step 1: 写失败测试**

在 `test_dynamic_product_candidate_options_remain_platform_driven_not_static_enum` 后增加断言，要求 `data.user_visible_text` 包含原问题、候选 `label`、候选 `value`、描述摘要和单选提示。

- [x] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH=.. uv run pytest tests/test_oceanengine_dependent_clarification_options.py::test_dynamic_product_candidate_options_remain_platform_driven_not_static_enum -q`
Expected: FAIL，失败点为 `user_visible_text` 缺少候选文本兜底。

- [x] **Step 3: 最小实现**

在 `tools/oceanengine_local_project_runtime/agent_visible.py` 中新增后端内部格式化 helper：
- `_choice_card_lines(input_control)`
- `_clarification_user_visible_text(clarification)`

在 `_compact_agent_visible_errors` 写入普通错误消息后，如果 `data.clarification.input_control.type=choice_cards` 且存在候选，则用 helper 生成 `data.user_visible_text`，并保持单问题追问约束。

- [x] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH=.. uv run pytest tests/test_oceanengine_dependent_clarification_options.py::test_dynamic_product_candidate_options_remain_platform_driven_not_static_enum -q`
Expected: PASS

### Task 3: 用 TDD 补多选文本兜底和 Gateway 透传

**Files:**
- Modify: `backend/tests/test_oceanengine_dependent_clarification_options.py`
- Modify: `backend/tests/test_gateway_visibility.py`
- Modify: `tools/oceanengine_local_project_runtime/agent_visible.py`

- [x] **Step 1: 写多选文本兜底测试**

增加一个直接调用 `agent_visible_result` 的测试，构造 `selection_mode=multiple` 的 `choice_cards`，断言 `user_visible_text` 提示可回复多个候选 ID 或名称。

- [x] **Step 2: 写 Gateway 多选透传测试**

在 `test_gateway_visibility.py` 中增加测试，构造 `selection_mode=multiple`、两个候选、`description`、`metadata`、`page_info`，断言 `sanitize_user_visible_payload` 原样保留安全字段并隐藏内部字段。

- [x] **Step 3: 运行测试确认失败或确认已有行为**

Run: `cd backend && PYTHONPATH=.. uv run pytest tests/test_oceanengine_dependent_clarification_options.py::test_multiple_dynamic_choice_cards_user_visible_text_allows_multiple_answers tests/test_gateway_visibility.py::test_gateway_visibility_preserves_multiple_dynamic_choice_cards -q`
Expected: 至少文本兜底测试在实现前 FAIL；Gateway 若已通过，记录为已有能力。

- [x] **Step 4: 最小实现或确认无需改 Gateway**

若 Task 2 helper 已满足多选文本兜底，仅保留测试；Gateway 若已保留 `selection_mode`、`description`、`metadata`、`page_info`，不改生产代码。

- [x] **Step 5: 运行测试确认通过**

Run: `cd backend && PYTHONPATH=.. uv run pytest tests/test_oceanengine_dependent_clarification_options.py::test_multiple_dynamic_choice_cards_user_visible_text_allows_multiple_answers tests/test_gateway_visibility.py::test_gateway_visibility_preserves_multiple_dynamic_choice_cards -q`
Expected: PASS

### Task 4: 更新任务状态并做后端验证

**Files:**
- Modify: `openspec/changes/clarification-card-interactions/tasks.md`

- [x] **Step 1: 运行聚焦测试**

Run: `cd backend && PYTHONPATH=.. uv run pytest tests/test_oceanengine_dependent_clarification_options.py tests/test_gateway_visibility.py -q`
Expected: PASS

- [x] **Step 2: 运行 OpenSpec 严格校验**

Run: `openspec validate clarification-card-interactions --strict`
Expected: `Change 'clarification-card-interactions' is valid`

- [x] **Step 3: 更新 tasks.md**

把已完成的后端契约、Gateway 出口、测试验证任务打勾；浏览器验收任务只有真实浏览器验证完成后才能打勾。

- [x] **Step 4: 确认没有前端改动**

Run: `git diff --name-only | rg '^frontend/'`
Expected: no output, exit 1
