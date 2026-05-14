# Diagnose Thread Search User Context

## 背景

当前 `/api/langgraph/threads/search` 会通过 nginx 重写到 Gateway 的 `/api/threads/search`，后端查询历史会话时不会信任请求体或前端 `X-User-Id`，而是从认证中间件解析 token 后写入的运行时用户上下文获取 `user_id`。现场表现为接口返回 `200 []`，说明接口可达且鉴权未失败，但当前解析出的用户与 `threads_meta.user_id` 可能不匹配。

## 目标

添加安全的后端诊断日志，帮助确认历史会话列表查不到的根因是否为：

- token / Redis payload 解析出的 `user_id` 不符合预期；
- `AuthMiddleware` 已解析用户，但运行时 `ContextVar` 在查询阶段丢失；
- `/api/threads/search` 实际使用的用户与 `threads_meta` 已有记录的 owner 不一致；
- 查询条件、分页或状态过滤导致结果为空。

## 变更范围

- 在 Gateway 认证成功路径记录一次结构化诊断日志，包含请求路径、tenant、business_code、解析出的 `user_id`、是否 internal auth。
- 在线程搜索接口记录查询前后的结构化诊断日志，包含 `request.state.user`、运行时当前用户、查询参数摘要和返回条数。
- 日志不得记录 token 原文、请求消息正文、会话消息内容、Redis 原始 payload 或其它敏感数据。

## 非目标

- 不改变认证、授权或线程隔离逻辑。
- 不恢复前端 `X-User-Id` 作为后端信任来源。
- 不修改数据库记录或迁移历史 `threads_meta.user_id`。
- 不改变 `/api/threads/search` 的响应结构。

## 风险与约束

- 诊断日志会暴露用户 ID、租户 ID、业务线编码和 thread search 返回数量，应保持在服务端日志内，不返回给前端。
- 如果日志量过大，应仅在关键路径使用 `INFO` 或 `DEBUG` 中的一种，并保持单行摘要，避免污染生产日志。
