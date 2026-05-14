# 禁用词拦截消息写入 Checkpoint

## 背景

当前禁用词前置拦截命中后，运行不会触发大模型，这是符合预期的。但现场 session `c35a4cea-fd1a-456e-9d96-2fcd70ac4aef` 显示，`lumax_conversation_message` 已记录用户消息和拦截回复，而 LangGraph checkpoint 只有 `channel_values.title`，没有 `channel_values.messages`，`run_events` 也为空。

前端聊天回显和 `/api/langgraph/threads/{thread_id}/history` 的数据源是 LangGraph checkpoint/state，而不是 `lumax_conversation_message`。因此拦截后的用户消息和“这个话题暂时不能继续”没有进入 checkpoint，会导致 history 只返回标题，前端看起来像消息 type 错乱。

## 目标

- 禁用词命中时仍不触发大模型调用。
- 禁用词命中时，把当前用户消息和拦截 assistant 回复正常写入 LangGraph checkpoint 的 `channel_values.messages`。
- 写入 checkpoint 时保留既有 checkpoint 数据，不清空已有消息、标题、thread_data 或其它长期状态。
- 禁用词命中且属于第一次对话、当前 checkpoint 尚无有效标题时，线程标题使用本次拦截生成的 AI 默认回复，不得把违规用户输入写作标题。
- 禁用词命中但已有有效标题时，不覆盖原有标题，避免影响之前正常场景。
- `/api/langgraph/threads/{thread_id}/history` 能从 checkpoint 返回正常的 `human` + `ai` 消息类型。
- 保持 Lumax 结算、禁用词命中记录和用户可见回复语义不变。

## 非目标

- 不把前端聊天回显数据源切换为 `lumax_conversation_message`。
- 不触发被禁用词拦截请求的大模型调用、工具调用或 agent graph 执行。
- 不新增数据库字段、迁移或后台补偿历史数据任务。
- 不修改禁用词匹配规则和命中策略。
- 不改变用户可见拦截文案选择逻辑。

## 方案概述

修复禁用词前置拦截分支的 checkpoint 写入逻辑，重点检查 `_publish_banned_word_response`：

- 构造拦截回复 `AIMessage` 后，将本轮输入消息和拦截回复组成完整消息列表。
- 如果当前 thread 已有 checkpoint，则读取并保留既有 `channel_values`，在已有消息后追加本轮消息，避免覆盖历史。
- 如果当前 thread 只有初始化 checkpoint 或空 checkpoint，则创建包含本轮 `messages` 和 `title` 的 checkpoint。
- title 处理遵循最小暴露原则：已有有效 `title` 时保持不变；无有效 `title` 且禁用词拦截是第一次对话时，写入本次拦截生成的 AI 默认回复。
- checkpoint metadata 保持 LangGraph 可读取的基本字段，避免破坏 history/state 读取。
- stream 仍只发布拦截回复和 values，不进入正常 agent graph。

## 风险与约束

- 该逻辑位于 `backend/packages/harness/deerflow/runtime/runs/worker.py`，属于后端受保护源码，实施前需遵循本 change 并控制修改范围。
- 禁用词分支是短路路径，测试需要覆盖“不触发模型但 checkpoint 有消息”。
- 如果已有 checkpoint 中已经含有同一 run 的拦截消息，需要避免重复追加。
- GitNexus MCP 工具当前未在可用工具列表中暴露；实施时需用静态调用点、定向测试和数据库检查说明影响范围。
