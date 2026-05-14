# 任务清单

## 1. 定位与影响

- [x] 1.1 定位消息工具栏点赞/点踩渲染位置。
- [x] 1.2 确认现有反馈 API 封装和新接口差异。
- [x] 1.3 在可用工具范围内完成影响分析并记录风险。

## 2. 实现

- [x] 2.1 更新反馈 API 封装为 `POST /api/threads/{thread_id}/feedback`。
- [x] 2.2 为 assistant 消息点赞/点踩按钮接入 `positive` / `negative` 提交。
- [x] 2.3 处理提交中禁用、成功提示、失败提示和缺少 `run_id` 的兜底。
- [x] 2.4 对话加载时调用 `GET /api/threads/{thread_id}/feedback` 获取当前线程反馈列表。
- [x] 2.5 按 `message_id` / `run_id` 将已有反馈映射到 assistant 消息，并回显点赞/点踩选中态。
- [x] 2.6 feedback 加载或提交遇到 `401 Unauthorized` 时，不弹出 feedback 失败提示。

## 3. 验证

- [x] 3.1 运行本次修改文件的 lints / 类型检查或记录无法运行原因。

## 4. 旧接口同步 SQL 修正

- [x] 4.1 为 `POST /api/threads/{thread_id}/feedback` 增加带 `run_id` 时同步 SQL run 级反馈的后端测试。
- [x] 4.2 在 legacy feedback 创建逻辑中保留 Store 写入，并在 Store 成功后调用现有 `FeedbackRepository.upsert_by_run()`。
- [x] 4.3 确保缺少 `run_id`、仓库不可用或 SQL 同步失败时不破坏旧 Store feedback 成功响应，并记录服务端日志。
- [x] 4.4 运行聚焦后端测试，至少覆盖 `backend/tests/test_feedback_router.py` 中新增/相关用例。
