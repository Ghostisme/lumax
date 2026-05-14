# Persist Conversation Nickname Dept Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `lumax_conversation` save the displayed user name from `nickname` and save `dept_id` from the first value in `deptIds`.

**Architecture:** Extend the authenticated user context at the Gateway boundary, keep the normalized values in `configurable.user_context`, and carry them through metering settlement into DB persistence. The DB writer updates both insert and update paths so new and existing conversations get the same metadata behavior.

**Tech Stack:** Python 3.12, FastAPI Gateway, DeerFlow run worker, psycopg direct SQL metering, pytest.

---

### Task 1: Auth And Gateway Context

**Files:**
- Modify: `backend/app/gateway/auth_middleware.py`
- Modify: `backend/app/gateway/services.py`
- Test: `backend/tests/test_auth_middleware_business_code.py`
- Test: `backend/tests/test_gateway_tenant_id.py`

- [ ] **Step 1: Write failing auth tests**

Add assertions that platform claims with `nickname="Alice N"` and `deptIds=["dept-1", "dept-2"]` produce `UserContext.nickname == "Alice N"` and `UserContext.dept_id == "dept-1"`.

- [ ] **Step 2: Write failing Gateway merge test**

Update the Gateway context merge test so request user fields `nickname` and `dept_id` appear under `config["configurable"]["user_context"]`.

- [ ] **Step 3: Implement auth parsing**

Add `nickname` and `dept_id` to `UserContext`. Parse `nickname` from claims and parse `dept_id` from the first `deptIds` entry; if the first entry is empty, keep `dept_id` empty and do not scan later entries.

- [ ] **Step 4: Implement Gateway merge**

Have `_user_context_from_request()` and `_normalize_user_context()` preserve `nickname` and `dept_id`, accepting `deptIds` as an input alias for `dept_id`.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest backend/tests/test_auth_middleware_business_code.py backend/tests/test_gateway_tenant_id.py -q`

### Task 2: Settlement Payload

**Files:**
- Modify: `backend/packages/harness/deerflow/metering.py`
- Modify: `backend/packages/harness/deerflow/runtime/runs/worker.py`
- Modify: `backend/app/gateway/usage_reporter.py`
- Test: `backend/tests/test_run_agent_settlement.py`
- Test: `backend/tests/test_lumax_conversation_metadata.py`

- [ ] **Step 1: Write failing worker test**

Capture settlement creation and assert `username == "Alice N"` when user context has both `nickname` and `username`, and `dept_id == "dept-1"`.

- [ ] **Step 2: Write failing payload test**

Assert `_settlement_payload(UsageSettlement(..., dept_id="dept-1"))["dept_id"] == "dept-1"`.

- [ ] **Step 3: Implement metering fields**

Add `dept_id` to `MeteringRunContext` and `UsageSettlement`. In `run_agent`, compute settlement username as `nickname or username`, and copy `dept_id`.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest backend/tests/test_run_agent_settlement.py backend/tests/test_lumax_conversation_metadata.py -q`

### Task 3: DB Persistence

**Files:**
- Modify: `backend/app/gateway/lumax_db_metering.py`
- Modify: `backend/docs/LUMAX_METERING.md`
- Test: `backend/tests/test_lumax_conversation_metadata.py`

- [ ] **Step 1: Write failing DB tests**

Update the settlement DB test so the conversation insert SQL contains `dept_id`, the insert params include `"dept-1"`, the select reads prior `dept_id`, and the update SQL sets `dept_id = %s`.

- [ ] **Step 2: Implement DB insert/update**

Select `dept_id` from `lumax_conversation`, insert `dept_id` on new conversations, and update `dept_id` using the new settlement value or the previous value when the new value is empty.

- [ ] **Step 3: Update metering docs**

Mention that `lumax_conversation` stores `username` from `nickname` fallback to account username, plus `dept_id` from the first `deptIds` value.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest backend/tests/test_lumax_conversation_metadata.py -q`

### Task 4: Verification

**Files:**
- Modify: `openspec/changes/persist-conversation-nickname-dept/tasks.md`

- [ ] **Step 1: Run all targeted tests**

Run: `python -m pytest backend/tests/test_auth_middleware_business_code.py backend/tests/test_gateway_tenant_id.py backend/tests/test_run_agent_settlement.py backend/tests/test_lumax_conversation_metadata.py -q`

- [ ] **Step 2: Run OpenSpec validation if CLI is available**

Run: `npx openspec validate persist-conversation-nickname-dept --strict`

- [ ] **Step 3: Record verification**

Mark completed tasks in `openspec/changes/persist-conversation-nickname-dept/tasks.md` only for checks that actually passed.

- [ ] **Step 4: Inspect diff**

Run: `git diff -- backend/app/gateway/auth_middleware.py backend/app/gateway/services.py backend/app/gateway/usage_reporter.py backend/packages/harness/deerflow/metering.py backend/packages/harness/deerflow/runtime/runs/worker.py backend/app/gateway/lumax_db_metering.py backend/tests/test_auth_middleware_business_code.py backend/tests/test_gateway_tenant_id.py backend/tests/test_run_agent_settlement.py backend/tests/test_lumax_conversation_metadata.py backend/docs/LUMAX_METERING.md openspec/changes/persist-conversation-nickname-dept docs/superpowers/plans/2026-05-11-persist-conversation-nickname-dept.md`

Expected: diff is limited to nickname/dept propagation, tests, docs, and the OpenSpec task record.
