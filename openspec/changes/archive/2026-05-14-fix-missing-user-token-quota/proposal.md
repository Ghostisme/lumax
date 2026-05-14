# 修复缺失用户 Token 配额时的拒绝提示

## 背景

当前后端在 DB 模式下执行用量配额检查时，会从 `lumax_user_quota` 查询用户配额：

- 若查询不到用户配额记录，现有逻辑会返回 `unlimited` 并允许继续执行。
- 若结算阶段查询不到用户配额记录，现有逻辑会自动插入一条 `total_quota = -1` 的 unlimited 记录。

这会导致未配置 Token 总配额的用户仍然可以发起模型调用，并且真实问题可能在结算阶段表现为 `用量结算重试后仍失败`。

## 问题

当用户没有 Token 配额记录，或 `lumax_user_quota.total_quota` 没有有效值时，系统不应继续执行模型调用，也不应在结算阶段自动补 unlimited 配额。

这些情况应该统一提示用户 Token 总配额不足，避免：

1. 未配置配额的用户继续消耗模型 Token。
2. 结算阶段才暴露异常，导致用户看到用量结算失败而不是配额不足。
3. 自动创建 unlimited 配额记录，掩盖配置缺失。

## 目标

- 当 `lumax_user_quota` 查询不到当前租户和用户的配额记录时，直接拒绝调用。
- 当 `lumax_user_quota.total_quota` 为 `NULL`、空值或无法解析为整数时，直接拒绝调用。
- 拒绝信息统一表达为 Token 总配额不足。
- 结算扣减阶段不再为缺失用户配额自动创建 unlimited 记录。
- 增加定向测试覆盖缺失记录和 `total_quota` 无效的 DB quota 行为。

## 非目标

- 不调整 `total_quota = -1` 表示 unlimited 的既有语义。
- 不调整 HTTP 模式下 lumax-service 的配额接口协议。
- 不调整模型价格、消费明细、会话统计或禁用词逻辑。
- 不重构 UsageReporter 或 metering 模块结构。

## 方案概述

在 DB quota 检查入口中，将“用户配额记录不存在”和“`total_quota` 无有效值”都视为配额不足，返回 `allowed = False`、`remaining = 0` 和统一中文提示。

在结算扣减 `_consume_user_quota` 中，若配额记录不存在或 `total_quota` 无效，直接抛出同样的配额不足错误，不再插入 unlimited 记录。这样即使调用绕过了前置检查，结算阶段也不会默默放行或生成错误配置。
