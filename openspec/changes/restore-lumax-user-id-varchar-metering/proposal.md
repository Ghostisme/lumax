# 恢复 Lumax 计量链路 user_id 字符串传参

## 背景

`dev1` 已经将 Lumax 鉴权与计量链路中的 `user_id` 按字符串传递，以匹配平台数据库中 `lumax_user_quota.user_id` 等 varchar 字段。`dev2` 合并后部分代码回退为 `int` 语义，导致 DB quota 检查执行 `varchar = bigint` 比较时报错，随后 fallback 到 lumax-service 失败并把运行标记为额度不足。

## 问题

当前 `/api/langgraph/threads/{thread_id}/runs/stream` 可以通过 Gateway 鉴权并创建 run，但运行前 quota 检查会因为 `user_id` 参数类型不匹配失败。前端再把 429 按鉴权阻断流程处理，表现为用户侧看到 token 过期或需要重新登录。

## 目标

- 在 Lumax DB quota 检查、结算扣减、敏感词上报和运行时计量上下文中恢复 `user_id` 字符串传参。
- 保持 `tenant_id` 继续使用数字字符串语义，不做数值转换。
- 保持系统用户 `-1` 不限额语义。
- 补回定向回归测试，覆盖 `user_id` 从 JWT、runtime config、quota DB 参数到结算扣减的字符串传递。

## 非目标

- 不调整数据库 schema。
- 不改变平台 token 解析、Redis key 格式或 lumax-service HTTP API 字段名。
- 不重构 UsageReporter、RunManager 或 Gateway 鉴权架构。

## 方案概述

复用 `dev1` 的字符串归一化策略：鉴权上下文保留 `user_id` 的原始字符串表示；运行 worker 使用 `_as_user_id` 而不是 `_as_int`；UsageReporter dataclass 和 DB metering 函数接受字符串 user_id，并在进入 DB 参数前统一 `str(value).strip()`。相关测试断言 DB 参数为字符串，避免再次回退为 bigint。
