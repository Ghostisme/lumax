# 任务清单

## 1. 测试

- [ ] 恢复/补齐 `tests/test_banned_words_middleware.py` 中运行前输入违禁词检查测试，覆盖命中后调用 `BannedWordsMiddleware._check` 并记录命中。
- [ ] 恢复/补齐命中短路响应测试，覆盖随机兜底 AI 回复、SSE `messages`/`values` 输出和 checkpoint/title 写入。
- [ ] 恢复/补齐零 token 结算测试，覆盖违禁词短路路径不消耗 token 且保留当前轮 user/assistant 消息。
- [ ] 增加 Gateway run config 测试或等价覆盖，确认 `BannedWordsMiddleware` 被注入 `__custom_middlewares`，避免真实运行链路再次断开。

## 2. 实现

- [ ] 调整 `backend/app/gateway/services.py`，在 `start_run` 中注入 `BannedWordsMiddleware()`，并兼容已有 `__custom_middlewares`。
- [ ] 调整 `backend/packages/harness/deerflow/runtime/runs/worker.py`，恢复输入违禁词前置检查、随机安全回复、checkpoint/title 写入和 SSE 发布逻辑。
- [ ] 调整 `_report_lumax_settlement` 支持 `force_zero_tokens`，用于违禁词短路路径的零 token 结算。
- [ ] 确认所有新增/恢复逻辑继续使用字符串 `user_id`，并保留系统用户 `-1` 行为。

## 3. 验证

- [ ] 运行 `backend\.venv\Scripts\python.exe -m pytest tests/test_banned_words_middleware.py -q`。
- [ ] 如改动触达 Gateway run config，运行相关 Gateway 定向测试。
- [ ] 检查 diff，确认改动只集中在违禁词监测链路和对应 OpenSpec 文档。
