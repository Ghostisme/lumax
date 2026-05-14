# 线程反馈查询返回 SQL 当前态

## 背景

当前反馈能力同时存在两套存储语义：

- `GET /api/threads/{thread_id}/feedback` 读取 LangGraph Store 中的 legacy message feedback，返回每次提交的历史记录。
- SQL `feedback` 表保存 run 级反馈当前态，按 `thread_id + run_id + user_id` 保持一条记录，并支持 `rating=0` / `result=NULL` 表示未评价。

前端和运行时已经迁移到 run 级 SQL feedback 作为当前评价状态来源，消息列表也从 SQL feedback 回填当前状态。但旧的线程反馈查询接口仍返回 Store 历史记录，导致用户看到的接口结果与 SQL `feedback` 表当前态不一致。

## 问题

当用户反复点赞、点踩同一个 run 时，legacy Store 会累计多条 `fb_xxx` 记录，而 SQL `feedback` 表会更新同一条 run 级记录。于是：

1. `GET /api/threads/{thread_id}/feedback` 返回数量可能大于 SQL `feedback` 表数量。
2. 同一 `run_id` 可能出现多条互相矛盾的 legacy 反馈记录。
3. 调用方无法通过该接口稳定获得当前用户对每个 run 的最终反馈状态。
4. 当前接口名称容易被理解为线程反馈当前态查询，但实际仍是 legacy 历史记录查询。

## 目标

- 将 `GET /api/threads/{thread_id}/feedback` 切换为 SQL feedback 当前态查询。
- 返回当前用户在该线程下的 run 级反馈记录，按 SQL `feedback` 表的 `thread_id + run_id + user_id` 当前态为准。
- 保持外层响应结构 `{ "feedback": [...], "count": n }`，降低调用方改造成本。
- 返回 SQL 字段：`feedback_id`、`thread_id`、`run_id`、`user_id`、`message_id`、`rating`、`result`、`comment`、`feedback_time`、`agent_id`、`agent_name`、`created_at`。
- 包含 `rating=0` / `result=NULL` 的未评价占位记录，让调用方能够区分未评价和无记录。
- 继续保留 legacy `POST/PATCH/DELETE /api/threads/{thread_id}/feedback...` 的 Store 写入行为，不在本次变更中迁移写接口。

## 非目标

- 不删除 Store 表中的 legacy feedback 数据。
- 不改变 run 级 `PUT /api/threads/{thread_id}/runs/{run_id}/feedback` 和 `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback` 语义。
- 不新增反馈操作审计历史表。
- 不把 SQL `feedback.rating` 从整数改为字符串。
- 不改前端按钮提交链路。
- 不改变 `/api/runs/{run_id}/feedback` 按 run 查询 SQL feedback 的既有语义。

## 方案概述

修改 Gateway 的 legacy feedback router 中 `list_feedback()` 查询路径：

1. 获取当前用户 ID。
2. 使用 `FeedbackRepository.list_by_thread(thread_id, user_id=current_user)` 查询 SQL feedback。
3. 将 SQL 行封装为新的线程反馈列表响应，保持外层 `feedback` 和 `count` 字段。
4. 不再在 GET 路径调用 `store.asearch(("feedback", thread_id))`。

为避免破坏 legacy 写接口，本次只切换 GET 读语义。`POST /api/threads/{thread_id}/feedback` 仍先写 Store，并在携带 `run_id` 时 best-effort 同步 SQL。

## 影响范围

- `backend/app/gateway/routers/feedback.py`
- `backend/tests/test_feedback_router.py`
- 必要时更新反馈相关文档说明，明确线程反馈查询接口返回 SQL 当前态。

## 风险与约束

- 返回列表项字段会从 legacy `id` / 字符串 `rating` 变为 SQL `feedback_id` / 整数 `rating` + `result`，如果仍有调用方依赖旧字段，需要同步调整。
- 接口需要依赖 SQL feedback repository；当 SQL feedback repository 不可用时，应返回明确服务不可用错误，而不是退回 Store 历史记录。
- 该变更改变已有 GET 接口语义，测试必须覆盖不再读取 Store 的行为，以及多次 legacy Store 记录不会影响 SQL 当前态返回。
