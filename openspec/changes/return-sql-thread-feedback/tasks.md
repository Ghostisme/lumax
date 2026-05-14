# 任务清单

## 1. 规格与影响确认

- [ ] 1.1 确认 `GET /api/threads/{thread_id}/feedback` 目标语义为 SQL 当前态查询。
- [ ] 1.2 确认 legacy Store 写接口保持不变，仅切换 GET 查询来源。
- [ ] 1.3 在修改 Gateway 符号前完成 GitNexus 影响分析；如工具不可用，记录约束并用静态调用关系补充影响评估。

## 2. 测试

- [ ] 2.1 更新 `backend/tests/test_feedback_router.py`，覆盖 GET 线程反馈调用 `FeedbackRepository.list_by_thread()`。
- [ ] 2.2 增加测试验证响应外层保持 `feedback` 和 `count`。
- [ ] 2.3 增加测试验证响应项返回 SQL 字段：`feedback_id`、`thread_id`、`run_id`、`user_id`、`message_id`、`rating`、`result`、`comment`、`feedback_time`、`agent_id`、`agent_name`、`created_at`。
- [ ] 2.4 增加测试验证 `rating=0` / `result=None` 的未评价记录会出现在返回中。
- [ ] 2.5 增加测试验证 GET 不再读取 Store 中的 legacy 重复记录。
- [ ] 2.6 增加测试验证 SQL feedback repository 不可用时返回服务不可用错误。

## 3. 后端实现

- [ ] 3.1 为线程反馈 SQL 当前态返回定义响应模型，避免复用 legacy `FeedbackEntry` 字符串 rating 模型。
- [ ] 3.2 修改 `list_feedback()` 使用 `get_feedback_repo(request)` 和 `get_current_user(request)`。
- [ ] 3.3 调用 `FeedbackRepository.list_by_thread(thread_id, user_id=user_id)` 获取当前态记录。
- [ ] 3.4 保持 `FeedbackListResponse` 外层兼容，或引入等价的新外层响应模型 `{ feedback, count }`。
- [ ] 3.5 确保 `POST/PATCH/DELETE /api/threads/{thread_id}/feedback...` 的 Store 行为不受影响。

## 4. 验证

- [ ] 4.1 运行定向后端测试：`uv run pytest tests/test_feedback_router.py -q`。
- [ ] 4.2 如修改 repository 或共享模型，运行反馈相关测试：`uv run pytest tests/test_feedback.py tests/test_thread_run_messages_pagination.py tests/test_feedback_router.py -q`。
- [ ] 4.3 手动验证 `GET /api/threads/{thread_id}/feedback` 返回数量与 SQL 当前态一致。
- [ ] 4.4 实施完成后运行变更范围检查，确认只影响预期反馈查询链路。
