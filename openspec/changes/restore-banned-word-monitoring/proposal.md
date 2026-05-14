# 恢复违禁词监测记录链路

## 背景

当前后端已经具备违禁词匹配、命中上报和 DB 落库能力：

- `app/gateway/middlewares/banned_words_middleware.py` 负责在输入/输出文本中执行违禁词检测，并在命中后调用 `UsageReporter.report_banned_word_hit`。
- `app/gateway/usage_reporter.py` 在 `LUMAX_DB_DSN` 配置存在时走 DB 模式，否则走 lumax-service HTTP collector。
- `app/gateway/lumax_db_metering.py` 会向 `lumax_banned_word_trigger` 写入命中记录，并更新分类和会话命中统计。

但近期合并后，Gateway 不再把 `BannedWordsMiddleware` 注入 agent 运行链路，运行前输入违禁词检查和命中短路响应也从 `worker.py` 中被移除。结果是违禁词监测实现仍存在，但真实 run 不再触发检测和记录。

## 问题

用户输入命中违禁词时，当前系统不会记录命中事件。日志中能看到模型 token middleware 正常执行，但没有 `Banned word hit` 或 banned-word 上报失败日志，说明问题发生在检测触发层，而不是 DB 插入或 HTTP 上报层。

现有 `tests/test_banned_words_middleware.py` 也暴露了实现与测试不一致：测试仍期望 `worker._check_banned_words_for_latest_message`、`_publish_banned_word_response` 和 `force_zero_tokens` 存在，但当前实现已删除这些符号。

## 目标

- 恢复 Gateway 对 `BannedWordsMiddleware` 的注入，使模型调用前后能执行输入/输出违禁词检测。
- 恢复 run worker 对最新用户输入的前置违禁词检查：输入命中时不调用模型，直接返回安全兜底回复。
- 输入命中短路时仍写入违禁词命中记录，并上报零 token 结算，避免命中违禁词后继续消费模型 token。
- 保持 `user_id` 字符串语义，兼容当前 Lumax varchar 用户 ID 链路和系统用户 `-1`。
- 恢复并补齐现有定向测试，防止后续合并再次切断违禁词监测链路。

## 非目标

- 不调整违禁词 Redis key 格式、DB schema 或 lumax-service HTTP collector 字段名。
- 不重构 UsageReporter、RunManager、agent middleware 架构。
- 不改变违禁词词库匹配规则、精确/模糊匹配算法或默认租户回退策略。
- 不处理与 OceanEngine 用户可见流式输出清洗无关的历史差异。

## 方案概述

按已存在过的稳定链路恢复最小实现：

1. 在 `start_run` 构建 run config 后，将 `BannedWordsMiddleware()` 放入 `config["configurable"]["__custom_middlewares"]`，并保留已有或后续新增的其它 custom middleware。
2. 在 `run_agent` 完成身份和 quota 校验、建立 metering context 后，对 `graph_input.messages` 的最新用户消息执行 `_check_banned_words_for_latest_message`。
3. 若输入命中，发布 metadata 和随机兜底 AI 回复，写入 checkpoint/title，设置 run 成功并提前返回；finally 阶段用 `force_zero_tokens=True` 上报零 token 结算。
4. 保持普通模型调用路径由 `BannedWordsMiddleware.awrap_model_call` 检测输入/输出命中并记录。
5. 更新/恢复 `tests/test_banned_words_middleware.py` 覆盖注入、输入短路、零 token 结算、DB/HTTP 上报和字符串 `user_id`。
