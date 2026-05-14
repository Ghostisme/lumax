# 消息点赞点踩反馈

## 背景

消息工具栏中已经展示点赞和点踩按钮，但当前按钮没有调用后端反馈接口。用户要求点击点赞时向当前线程反馈接口提交 `positive`，点击点踩时提交 `negative`。

## 目标

- 在 assistant 消息工具栏中为点赞/点踩按钮接入 `/api/threads/{thread_id}/feedback`。
- 点赞提交 `rating: "positive"`，点踩提交 `rating: "negative"`。
- 请求体按后端示例包含 `message_id`、`run_id`、`rating`、`comment` 和 `tags` 字段。
- 对话加载时调用 `GET /api/threads/{thread_id}/feedback` 获取当前线程全部反馈，并按 `message_id` / `run_id` 回显每条 assistant 消息的点赞或点踩状态。
- 提交成功/失败时给用户明确反馈，并避免重复点击造成并发提交。
- 当 feedback 接口返回 `401 Unauthorized` 时，不弹出“反馈提交失败，请重试”等失败提示，避免未登录/登录过期场景出现多余 toast。

## 非目标

- 不新增反馈评论弹窗或标签编辑 UI。
- 不改造后端接口。
- 不改变复制、分享、消息 Markdown 渲染和线程提交链路。

## 影响范围

- 前端反馈 API 封装：`frontend/src/core/api/feedback.ts`。
- 消息列表组件：`frontend/src/components/workspace/messages/message-list.tsx`。
- 消息工具栏组件：`frontend/src/components/workspace/messages/message-list-item.tsx`。

## 风险与约束

- 前端需要从消息对象中提取 `run_id`；若当前消息没有可用 `run_id`，应提示无法提交反馈，而不是发送不完整请求。
- 回显时优先使用后端返回的 `message_id` 匹配当前消息；若缺失则使用 `run_id` 兜底匹配。
- `401` 仍由统一鉴权封装处理登录态，本变更只抑制 feedback 功能自己的失败提示。
- 当前 Cursor MCP 列表未暴露 GitNexus 工具；实施前会在可用工具范围内尝试影响分析，若不可用则记录工具约束并按静态调用边界评估。

## 补充范围：旧反馈接口同步 SQL

本轮修正要求后端旧接口 `POST /api/threads/{thread_id}/feedback` 在保持原有 Store 写入和响应结构不变的前提下，补充同步 SQL run 级反馈记录：

- 当请求体包含可用 `run_id` 时，旧接口应调用现有 SQL `FeedbackRepository.upsert_by_run()`，按当前用户、`thread_id` 与 `run_id` 更新同一条 run 级反馈记录。
- `rating: "positive"` 映射为 SQL `result="positive"` 与 `rating=1`；`rating: "negative"` 映射为 SQL `result="negative"` 与 `rating=-1`。
- `comment` 原样同步到 SQL 反馈记录，`feedback_time` 由现有仓库方法设置为提交时间。
- 若请求缺少 `run_id`，旧接口继续只写 Store，不新增 SQL 记录。
- 若 SQL 同步因 run 记录不存在、仓库不可用或其它异常失败，旧接口仍应保留原有 Store 写入成功语义，并记录服务端日志，避免破坏 legacy message feedback 行为。
- 本轮不改变 `PUT /api/threads/{thread_id}/runs/{run_id}/feedback` 与 `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback` 的既有语义。
