# 任务清单

## 1. 现状确认

- [x] 确认禁用词前置拦截命中后不进入大模型和 agent graph。
- [x] 确认 `/api/langgraph/threads/{thread_id}/history` 读取 checkpoint `channel_values.messages`。
- [x] 复核现有 `_publish_banned_word_response` 写 checkpoint 的路径，定位为什么现场只留下 `title`。

## 2. 实现

- [x] 修复禁用词拦截分支的 checkpoint 写入逻辑，确保写入本轮 `human` + `ai` 消息。
- [x] 保留已有 checkpoint 的 `channel_values`，追加消息而不是覆盖历史。
- [x] 避免同一 run 的拦截回复重复写入 checkpoint。
- [x] 保持禁用词命中时不触发大模型调用。
- [x] 首轮禁用词拦截且无既有标题时，将 checkpoint title 设置为本次拦截生成的 AI 默认回复。
- [x] 已有有效 title 时，禁用词拦截不得覆盖原 title。

## 3. 测试

- [x] 增加或更新后端定向测试，覆盖禁用词拦截后 checkpoint 中包含 `human` 和 `ai` 消息。
- [x] 测试已有历史消息时，禁用词拦截只追加本轮消息，不清空历史。
- [x] 测试 run 仍为成功短路，不产生 LLM 调用。
- [x] 测试首轮禁用词拦截 title 为本次拦截生成的 AI 默认回复。
- [x] 测试已有 title 的会话命中禁用词时 title 不被覆盖。

## 4. 验证

- [x] 运行相关后端定向测试。
- [x] 视成本运行 `cd backend && make test` 或说明未运行完整测试的原因。
- [x] 用目标接口或等价 checkpointer 读取确认 `/history` 返回 `values.messages`，且消息 type 正确。

## 验证记录

- `cd backend && PYTHONPATH=. uv run pytest tests/test_banned_words_middleware.py tests/test_run_agent_settlement.py -q`：30 passed。
- `cd backend && PYTHONPATH=. uv run ruff check packages/harness/deerflow/runtime/runs/worker.py tests/test_banned_words_middleware.py`：通过。
- 使用真实 Postgres checkpointer 创建临时 thread 并调用禁用词拦截写入函数，读回 checkpoint 包含 `messages=[human, ai]` 和 `title`。
- 使用真实 Postgres checkpointer 验证首轮禁用词 title 为本次 AI 拦截回复，已有 title 的会话保持原 title 且追加拦截消息。
