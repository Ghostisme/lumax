# 任务清单

## 1. 测试

- [ ] 为前端 auth session 增加测试或现有测试覆盖：长数字字符串租户 `2052263773707833345` 保存为原始字符串，不经过 `Number()`。
- [ ] 为前端 auth request 增加测试或现有测试覆盖：字符串 `tenantId` 会写入 `TENANT-ID` 请求头。
- [ ] 为 Gateway 上下文合并增加测试：`tenant_id` 输入为 `"2052263773707833345"` 时，`configurable.tenant_id` 保持原始字符串。
- [ ] 为运行时 quota 预检增加测试：长数字字符串 `tenant_id` 以字符串传给 `UsageReporter.check_quota`。
- [ ] 为 Lumax DB metering 增加测试：quota 查询、结算、模型价格兜底查询、用户额度扣减均使用字符串租户参数。
- [ ] 为敏感词链路增加测试：字符串租户正常拼 Redis key、查询 DB，并回退到默认租户 `"1"`。

## 2. 后端实现

- [ ] 在 Gateway/计量可复用位置增加租户 ID 校验辅助函数，按字符串语义处理输入，输出 `str | None`，不得通过数值转换处理长数字字符串。
- [ ] 调整 `app/gateway/auth_middleware.py`，让 `UserContext.tenant_id` 输出规范化数字字符串。
- [ ] 调整 `app/gateway/services.py`，合并用户上下文时保留规范化字符串租户。
- [ ] 调整 `backend/packages/harness/deerflow/runtime/runs/worker.py` 和 `deerflow/metering.py`，运行计量上下文使用字符串租户。
- [ ] 调整 `app/gateway/usage_reporter.py` 的 dataclass、校验、HTTP payload 和 DB payload。
- [ ] 调整 `app/gateway/lumax_db_metering.py`，移除 `tenant_id` 的 `int()` 转换，所有 DB 参数使用字符串租户，并把全局租户兜底改为 `"0"`。
- [ ] 调整 `app/gateway/lumax_pricing_cache.py`，价格缓存接受字符串租户并使用 `"0"` 兜底 key。
- [ ] 调整 `app/gateway/banned_words_guard.py` 与 `middlewares/banned_words_middleware.py`，租户校验和默认租户回退使用字符串语义。

## 3. 前端实现

- [ ] 调整 `frontend/src/core/auth/api.ts` 的 `tenantId` 类型为 `string`。
- [ ] 调整 `frontend/src/core/auth/session.ts`，保存、读取、更新 `tenantId` 时统一为字符串。
- [ ] 调整 `frontend/src/core/auth/request.ts`，非空字符串租户写入 `TENANT-ID`。
- [ ] 调整 `frontend/src/components/workspace/workspace-sidebar.tsx` 的租户选择状态和登录传参为字符串。

## 4. 文档

- [ ] 更新 `frontend/CLAUDE.md` 中 `tenantId` 相关说明。
- [ ] 更新 `backend/docs/LUMAX_METERING.md` 中 `tenant_id` 类型说明。
- [ ] 更新 `docs/lumax-token-pricing-redis.md` 与 `docs/lumax-token-pricing-deerflow.md` 中 `tenantId` 类型和 `"0"` 兜底说明。

## 5. 验证

- [ ] 运行前端定向测试或 `pnpm check`；若被既有 import/order 问题阻塞，记录阻塞文件和错误。
- [ ] 运行后端定向测试：`test_auth_middleware_business_code.py`、`test_lumax_quota.py`、`test_run_agent_settlement.py`、`test_banned_words_middleware.py`、`test_mcp_request_context.py`。
- [ ] 使用检索确认不再存在 `tenant_id: int`、`tenantId?: number`、`int(settlement["tenant_id"])`、`tenant_id IN (%s, 0)` 等已知风险模式。
