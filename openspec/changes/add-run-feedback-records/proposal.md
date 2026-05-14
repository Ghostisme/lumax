# 增加 Run 级点赞点踩反馈记录

## 背景

当前后端同时存在两套反馈相关能力：

- `app/gateway/routers/feedback.py` 提供基于 LangGraph Store 的线程级反馈 CRUD，`rating` 使用 `positive` / `negative` 字符串。
- `deerflow.persistence.feedback` 提供 SQL `feedback` 表与 `FeedbackRepository`，`rating` 当前是整数，语义为 `1` 点赞、`-1` 点踩。

前端已有 `PUT /api/threads/{thread_id}/runs/{run_id}/feedback` 和 `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback` 的调用封装，但后端尚未实现对应 run 级写入接口；消息列表只会回填 SQL 表里的反馈。

业务侧需要在用户未进行点赞或点踩时，也能在反馈表中保留一条记录，用于记录本次 agent 结果和后续评价状态。

## 问题

如果只有用户点击点赞或点踩后才写反馈表，会导致：

1. 未评价的 AI run 在反馈表中不可见，无法区分“尚未评价”和“没有产生可评价结果”。
2. 后续按 agent、run 或评价状态统计时，需要跨 run 表和 feedback 表做额外推断。
3. 前端已有 run 级反馈 API 封装，但后端缺少对应接口，点击链路无法稳定落到 SQL 表。

同时，直接修改 `rating` 字段类型会破坏现有 SQL 仓库、测试和历史数据兼容性。

## 目标

- 保持 `feedback.rating` 字段类型为 `int`，字段名不变。
- 保持历史兼容语义：`1` 表示点赞，`-1` 表示点踩。
- 扩展 `rating=0` 表示“未评价占位”。
- 新增 `result` 作为业务展示字段：`positive` 表示点赞，`negative` 表示点踩，`NULL` 表示未评价。
- 每个 `thread_id + run_id + user_id` 保持一条 SQL feedback 记录。
- run 成功完成后自动创建未评价记录，并记录本次 run 最终 assistant 消息的 `message_id`；点赞、点踩、取消评价时更新同一条记录。
- 新增 run 级 PUT / DELETE 后端接口，写入 SQL feedback 表。
- 保留旧 Store 版线程级反馈接口行为，不把它作为新 run 级点赞点踩链路。

## 非目标

- 不接入前端按钮点击逻辑。
- 不删除旧 Store 版 `/api/threads/{thread_id}/feedback` CRUD。
- 不把 `feedback.rating` 从整数改为字符串。
- 不为失败、取消、回滚的 run 自动创建未评价记录。
- 不引入完整反馈操作审计历史；本次仍是每个 run 每个用户一条当前状态记录。
- 不在本次变更中回填历史 feedback 记录缺失的 `message_id`。

## 方案概述

在 SQL `feedback` 表上增加 `result`、`feedback_time`、`agent_id`、`agent_name` 字段。`rating` 继续作为整数兼容字段，但允许 `0` 表示未评价。

run worker 在 `RunStatus.success` 后从最终 checkpoint/current turn 消息中提取本次 run 的最后一条 assistant 消息 `id`，再调用 `FeedbackRepository.ensure_neutral_for_run()` 创建未评价记录。该方法只在记录不存在时插入，不覆盖已有点赞或点踩状态；若无法提取 assistant `message_id`，不得阻断 run 收尾。

新增 run 级反馈接口：

- `PUT /api/threads/{thread_id}/runs/{run_id}/feedback`：以 `result` 为主，兼容 `rating=1/-1`，更新同一条记录。
- `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback`：重置为未评价状态，不物理删除。

接口、仓库和消息回填都返回 `rating` 与 `result`，其中新业务展示优先使用 `result`。
