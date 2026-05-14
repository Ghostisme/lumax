# 任务清单

## 1. 定位与影响分析

- [x] 1.1 确认 `409 Conflict` 来自同一 thread 已存在 active run 时的后端并发保护。
- [x] 1.2 确认前端通过 LangGraph SDK `thread.submit()` 发起 `POST /threads/{thread_id}/runs/stream`。
- [x] 1.3 确认 SDK stream retry 使用 `Location` 响应头作为重连地址，而 Gateway 当前只返回 `Content-Location`。
- [x] 1.4 实施前对拟修改的 Gateway stream handler 执行 GitNexus impact analysis；当前工具列表未暴露 GitNexus MCP，已读取 GitNexus impact skill 并用静态调用关系兜底，影响限定为 Gateway stream 创建响应头。

## 2. 实现

- [x] 2.1 在线程 run stream 创建响应中新增 `Location` 头，指向该 run 的 stream 续接地址。
- [x] 2.2 在 stateless run stream 创建响应中新增 `Location` 头，保持与线程 run stream 一致。
- [x] 2.3 保留现有 `Content-Location` 头，不改变 run metadata 解析兼容性。
- [x] 2.4 避免修改 runtime active-run 冲突保护和默认 multitask 策略。
- [x] 2.5 在前端 thread 提交前检查 `lg:stream:{threadId}` 中的可续接 run。
- [x] 2.6 如存在可续接 run，优先调用 `thread.joinStream(runId)` 并阻止本次新的 `thread.submit()`。
- [x] 2.7 防线触发时清理本次乐观消息与上传状态，避免 UI 展示未发送的新消息。
- [x] 2.8 后端 `start_run()` 在 run record 创建后、background task 创建前发生异常时，将该 run 标记为 `error` 并保留原始异常。

## 3. 验证

- [x] 3.1 添加或更新后端定向测试，覆盖 stream 创建响应包含 `Content-Location` 与 `Location`。
- [x] 3.2 运行相关后端 pytest：`PYTHONPATH=. uv run pytest tests/test_run_stream_headers.py -q`。
- [x] 3.3 运行 `openspec validate fix-langgraph-stream-reconnect-conflict --strict`。
- [x] 3.4 添加或更新前端定向测试，覆盖可续接 run id 解析和存储规范化。
- [x] 3.5 运行相关前端测试或检查：`pnpm test tests/unit/core/thread-run-metadata-storage.test.ts` 与 touched-file ESLint 通过；完整 `pnpm check` 仍受既有 `feedback.ts` import/order 阻断，`pnpm typecheck` 仍受既有 `better-auth` 类型依赖缺失阻断。
- [x] 3.6 添加或更新后端定向测试，覆盖 `start_run()` 准备阶段异常不会遗留 `pending` active run。
- [ ] 3.7 如本地服务可用，验证断线/刷新后的 stream 重连不再重新创建同一 thread 的 run，且 `500` 后同 thread 不再因脏 run 继续返回 `409`。
