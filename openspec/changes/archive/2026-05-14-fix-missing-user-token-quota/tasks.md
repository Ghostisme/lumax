# 任务清单

## 1. 测试

- [x] 为 `check_quota_db` 增加测试：`lumax_user_quota` 查询不到记录时返回拒绝。
- [x] 为 `check_quota_db` 增加测试：`total_quota` 为 `None` 或无法解析时返回拒绝。
- [x] 为运行 worker 增加测试：quota 预校验拒绝时不调用 agent/model，也不上报结算。
- [x] 为 `_consume_user_quota` 增加测试：查询不到用户配额记录时不再插入 unlimited，而是抛出配额不足错误。
- [x] 为 `_consume_user_quota` 增加测试：已有有限总配额但本次实际用量超过剩余额度时，仍累计实际用量且不让结算失败。

## 2. 实现

- [x] 调整 `app/gateway/lumax_db_metering.py` 的 DB quota 检查逻辑。
- [x] 调整结算扣减逻辑，移除缺失 quota 时自动创建 unlimited 配额的行为。
- [x] 调整结算扣减逻辑，余额不足时记录实际用量，不再抛出结算错误。
- [x] 统一缺失配额、无效总配额和余额不足时的错误消息。

## 3. 验证

- [x] 运行后端定向测试，覆盖 lumax DB metering 相关用例。
- [x] 如定向测试暴露兼容性问题，补充必要的最小修正并重新验证。
