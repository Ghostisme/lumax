# 任务清单

## 1. 测试

- [ ] 恢复/新增 auth middleware 测试：JWT 中的 `user_id` 解析后保留字符串。
- [ ] 恢复/新增 run worker quota 测试：`UsageReporter.check_quota` 收到字符串 `user_id`。
- [ ] 恢复/新增 Lumax DB quota 测试：`check_quota_db` 查询参数中的 `user_id` 为字符串。
- [ ] 恢复/新增结算扣减测试：`_consume_user_quota` 查询和更新参数中的 `user_id` 为字符串。

## 2. 实现

- [ ] 调整 `app/gateway/auth_middleware.py`，让 `UserContext.user_id` 保持字符串。
- [ ] 调整 `backend/packages/harness/deerflow/runtime/runs/worker.py`，运行时 quota 检查使用字符串 user_id。
- [ ] 调整 `app/gateway/usage_reporter.py` dataclass、校验和 DB/HTTP payload 的 user_id 类型。
- [ ] 调整 `app/gateway/lumax_db_metering.py`，DB 参数统一使用规范化字符串 user_id，并保留系统用户 `-1` 逻辑。

## 3. 验证

- [ ] 运行后端定向测试：`test_auth_middleware_business_code.py`、`test_lumax_quota.py`、`test_run_agent_settlement.py`、`test_banned_words_middleware.py`。
- [ ] 检查 diff，确认没有覆盖用户已有的 `scripts/serve.py` 改动。
