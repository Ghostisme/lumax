# 修复 LangGraph Stream 重连导致的 Run 冲突

## 背景

前端请求 `POST /api/langgraph/threads/{thread_id}/runs/stream` 时出现 `409 Conflict`。排查发现，后端在同一 `thread_id` 已存在 `pending` 或 `running` run 时拒绝创建新 run，这是预期的并发保护；当前异常来自前端可恢复 stream 断开后没有拿到 SDK 期望的 `Location` 重连地址，后续再次提交同一 thread 时改为重新 `POST` 创建 run，从而触发后端 active-run 冲突。

现有 Gateway stream 响应只返回 `Content-Location`，用于暴露 run 元信息；LangGraph SDK 的 stream retry 逻辑使用 `Location` 作为 reconnect path。两者语义不同，缺少 `Location` 会让 SDK 无法从初始 POST 切换为 GET 续接已有 run stream。

进一步验证发现，仅补齐后端 `Location` 只能覆盖已经建立 stream 后的网络重连；如果 SSE 断开后后端 run 继续执行，而当前前端 hook 因页面状态变化、组件重建或重连窗口期误判为空闲，用户再次提交同一 thread 时仍会发起新的 `POST /threads/{thread_id}/runs/stream`，触发 active-run `409 Conflict`。因此需要在前端提交前增加同 thread 可续接 run 防线。

浏览器验证还发现另一条后端防漏场景：`start_run()` 在创建 `RunRecord` 后、后台 task 启动前如果发生异常，会向客户端返回 `500`，但已创建的 run 仍保持 `pending`，后续同 thread 再提交会被误判为 active run 并返回 `409 Conflict`。本次不处理触发 `500` 的具体业务导入失败，只保证失败路径不会遗留脏 active run。

## 目标

- Gateway 创建 stream run 成功后，同时返回 SDK 可识别的 `Location` 响应头。
- 保留现有 `Content-Location` 响应头，避免破坏当前 run 元信息解析和兼容行为。
- 让 resumable stream 断线后优先续接已有 run，避免同一 thread 重复创建 run 并触发 `409 Conflict`。
- 为线程 run stream 和 stateless run stream 保持一致的响应头行为。
- 前端提交新消息前如发现同 thread 存在可续接 run，必须优先续接该 run 并阻止本次重复创建请求。
- 后端 run 创建准备阶段发生异常时，必须将已创建但未启动的 run 标记为终态错误，避免后续请求被脏 active run 阻塞。

## 非目标

- 不取消后端同一 thread active run 的并发保护。
- 不改变默认 `multitask_strategy="reject"` 语义。
- 不修改 LangGraph SDK 或前端 SDK 依赖代码。
- 不引入新的 run 去重、排队或强制取消策略。
- 不调整 DeerFlow runtime run manager 的状态机。
- 不在前端静默丢弃用户输入；本次只阻止会撞 active-run 的重复创建请求。
- 不修复或绕过触发 `500` 的具体业务模块导入问题；该错误仍应按原始异常暴露为服务端失败。

## 影响范围

- Gateway LangGraph stream 创建接口的响应头兼容性。
- 前端现有 `streamResumable: true` 断线重连路径。
- 后端定向测试，覆盖 stream 创建响应同时包含 `Content-Location` 和 `Location`。
- 前端 thread 提交流程，在发送新 run stream 前检查 browser session 中的 resumable run 元数据。
- 后端 `start_run()` 失败清理逻辑，覆盖 run record 已创建但 background task 尚未启动的异常窗口。

## 风险与约束

- 本次修复只解决 SDK 因缺少 `Location` 而无法续接的问题；如果调用方主动并发提交同一 thread，后端仍应返回 `409 Conflict`。
- `Location` 应指向可 GET 续接的 run stream 地址，不能替代 `Content-Location` 的 run 资源地址。
- `backend/app/**` 属于受保护源码；本次变更限定为 Gateway 接入层协议兼容修复，不触碰 DeerFlow runtime 并发控制。
- `frontend/src/core/**` 属于受保护源码；本次变更限定为 thread hook 的提交前保护，不调整页面级布局和输入组件所有权。
- 后端失败清理必须保留原始异常语义，不应把 `500` 转换为成功、重试、排队或静默 join。
