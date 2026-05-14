# LangGraph Stream Reconnect 规格

## ADDED Requirements

### Requirement: Stream 创建响应必须提供重连地址

Gateway 在成功创建 LangGraph run stream 时，MUST 同时返回用于 run 元信息解析的 `Content-Location` 响应头，以及用于可恢复 stream 续接的 `Location` 响应头。

#### Scenario: 线程 run stream 创建成功

- **WHEN** 客户端请求 `POST /api/threads/{thread_id}/runs/stream` 并成功创建 run
- **THEN** 响应头 `Content-Location` 必须指向 `/api/threads/{thread_id}/runs/{run_id}`
- **AND** 响应头 `Location` 必须指向 `/api/threads/{thread_id}/runs/{run_id}/stream`

#### Scenario: Stateless run stream 创建成功

- **WHEN** 客户端请求 `POST /api/runs/stream` 并成功创建 run
- **THEN** 响应头 `Content-Location` 必须指向 `/api/threads/{resolved_thread_id}/runs/{run_id}`
- **AND** 响应头 `Location` 必须指向 `/api/threads/{resolved_thread_id}/runs/{run_id}/stream`

#### Scenario: 同一 thread 已存在 active run

- **WHEN** 客户端在同一 thread 已存在 active run 时再次创建 run，且未通过 `Location` 续接已有 stream
- **THEN** Gateway 必须保留现有 active-run 并发保护行为
- **AND** 不得通过本规格放宽默认冲突拒绝语义

### Requirement: 前端提交前必须优先续接可恢复 run

前端在同一 thread 提交新消息前，MUST 检查本地可恢复 stream 元数据；当存在该 thread 的可续接 run 时，MUST 先续接已有 run，并且 MUST NOT 发起新的 run stream 创建请求。

#### Scenario: 同一 thread 存在可续接 run

- **WHEN** 用户在 thread 输入框提交新消息
- **AND** browser session 中存在 `lg:stream:{thread_id}` 对应的有效 `run_id`
- **THEN** 前端必须调用 existing run stream 续接逻辑
- **AND** 前端不得调用新 run stream 创建逻辑

#### Scenario: 同一 thread 没有可续接 run

- **WHEN** 用户在 thread 输入框提交新消息
- **AND** browser session 中不存在 `lg:stream:{thread_id}` 对应的有效 `run_id`
- **THEN** 前端可以按现有流程创建新的 run stream

### Requirement: Run 创建准备失败不得遗留 active run

Gateway 在创建 run record 后、background task 启动前发生异常时，MUST 将已创建的 run 转换为非 active 终态，并且 MUST 保留原始失败语义向调用方返回错误。

#### Scenario: start_run 准备阶段发生异常

- **WHEN** Gateway 已创建 run record
- **AND** background task 创建前的准备步骤发生异常
- **THEN** Gateway 必须将该 run 标记为 `error`
- **AND** 后续同一 thread 的新 run 创建不得因为该失败 run 被误判为 active run 而返回 `409 Conflict`
- **AND** 当前请求仍应保留原始服务端失败语义
