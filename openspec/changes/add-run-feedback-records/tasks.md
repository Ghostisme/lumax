# 任务清单

## 1. OpenSpec 与迁移

- [ ] 新增反馈能力规格，定义 `rating`、`result`、`feedback_time`、`agent_id`、`agent_name` 语义。
- [ ] 更新反馈能力规格，定义成功 run 自动创建的未评价记录应写入最终 assistant 消息 `message_id`。
- [ ] 新增 SQL 迁移，给已有 `feedback` 表补充 `result`、`feedback_time`、`agent_id`、`agent_name` 字段。
- [ ] 迁移历史数据：`rating=1` 回填 `result='positive'`，`rating=-1` 回填 `result='negative'`，其它值保持 `result=NULL`。

## 2. 测试

- [ ] 为 `FeedbackRepository` 增加未评价记录创建、点赞、点踩、取消评价、字段同步、多用户隔离测试。
- [ ] 为 `FeedbackRepository.ensure_neutral_for_run()` 增加 `message_id` 持久化测试，验证已有记录不被覆盖。
- [ ] 为 run 级反馈接口增加 PUT `result=positive/negative`、PUT 兼容 `rating=1/-1`、DELETE 重置测试。
- [ ] 为 run 生命周期增加测试：success 后创建未评价记录，error / interrupted / rollback 不创建。
- [ ] 为 run 生命周期增加测试：success 后创建未评价记录时写入最终 assistant 消息 `message_id`；无 assistant 消息时不阻断 run 收尾。
- [ ] 为消息列表回填增加测试，验证返回 `feedback_id`、`rating`、`result`、`comment`、`feedback_time`、`agent_id`、`agent_name`。
- [ ] 为统计口径增加测试，未评价记录不计入 positive / negative / 有效反馈 total。

## 3. 后端实现

- [ ] 修改 `FeedbackRow`，保持 `rating INT NOT NULL`，新增 `result`、`feedback_time`、`agent_id`、`agent_name`。
- [ ] 修改 `FeedbackRepository`：
  - [ ] `create()` / `upsert()` 兼容原有整数点赞点踩，并同步 `result`。
  - [ ] 新增 `ensure_neutral_for_run()`。
  - [ ] 新增 `upsert_by_run()`。
  - [ ] 新增 `reset_by_run()`。
  - [ ] 修改 `_row_to_dict()` 序列化 `created_at` 和 `feedback_time`。
  - [ ] 修改 `aggregate_by_run()` 只统计有效反馈。
- [ ] 扩展 `FeedbackRepository.ensure_neutral_for_run()` 支持可选 `message_id`，仅在插入新记录时写入。
- [ ] 扩展 `RunContext` 增加可选 `feedback_repo`，由 Gateway `deps.get_run_context()` 注入。
- [ ] 在 run worker 成功完成后提取最终 assistant 消息 `message_id`，创建未评价记录，且不覆盖已有评价。
- [ ] 新增 run 级 PUT / DELETE 反馈接口，并复用现有权限、配置和 LangSmith 同步语义。
- [ ] 修改线程消息列表反馈回填，返回新字段。

## 4. 验证

- [ ] 运行反馈相关定向后端测试。
- [ ] 运行 run router / run worker 相关定向后端测试。
- [ ] 运行 owner isolation 相关反馈测试。
- [ ] 若定向测试暴露兼容问题，补充最小修复后重新验证。
