# 任务清单

## 1. 定位日志点

- [x] 确认前端聊天页使用 `useThreadStream` 的 `thread.messages` 作为 MessageList 输入。
- [x] 确认后端 thread state/search/history 从 checkpointer `channel_values` 返回消息，而不是从 `lumax_conversation_message` 返回。
- [x] 确认 run stream 默认 stream mode 和 OceanEngine 安全约束后的实际 stream mode。

## 2. 后端诊断日志

- [x] 在 run 启动边界记录 `thread_id`、`run_id`、assistant、请求 stream mode、实际 stream mode。
- [x] 在 SSE 输出边界记录每类事件计数、`end`、断开或取消状态。
- [x] 在 thread state 读取边界记录 checkpoint 是否存在、`messages` 数量、角色分布。
- [x] 日志中不得输出消息正文、鉴权头、Cookie、完整 payload、内部 trace 或底层 tool payload。

## 3. 前端诊断日志

- [x] 在 `sendMessage` 提交前记录 threadId、server message count、optimistic message count。
- [x] 在 server messages 数量变化时记录变化前后数量和乐观消息清理条件。
- [x] 在 `onFinish` 记录最终 state message count 和 threadId。
- [x] 日志默认仅在开发环境或显式开关下输出。

## 4. 验证

- [x] 运行后端相关定向测试，确认删除日志后不影响 run/thread API 行为。
- [x] 运行前端类型检查或定向 lint，确认删除日志后不破坏构建。
- [x] 确认临时 visibility 回显恢复测试仍通过。

## 5. 临时恢复回显

- [x] 临时跳过 `_INTERNAL_ASSISTANT_CONTENT_RE` 对普通 assistant 正文的整条隐藏处理。
- [x] 保留 summary、内部 tool call、structured clarification、reasoning_content 的现有隐藏/清洗逻辑。
- [x] 增加或更新后端定向测试，覆盖包含“技能”的正常 assistant 回复不会被清空或标记 `hide_from_ui`。
- [x] 运行可见性清洗相关定向测试。

## 6. 删除诊断日志

- [x] 删除 `app.gateway.services` 中 run/SSE 诊断日志和仅为日志服务的辅助代码。
- [x] 删除 `app.gateway.routers.threads` 中 thread state/history 诊断日志和仅为日志服务的辅助代码。
- [x] 删除 `frontend/src/core/threads/hooks.ts` 中 `[thread-stream]` 开发期 console 诊断日志和仅为日志服务的辅助代码。
- [x] 保留 `app.gateway.visibility` 的临时回显恢复逻辑和相关测试。
- [x] 运行后端定向测试、后端 ruff、前端单文件 lint 和 diff 检查。
