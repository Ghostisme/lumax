# 设计说明：前后端共同隐藏内部 summary 消息

## 背景

`DeerFlowSummarizationMiddleware` 会在长对话中用 `RemoveMessage(id=REMOVE_ALL_MESSAGES)` 替换旧消息，并插入 `HumanMessage(name="summary")` 作为模型后续上下文。该 summary 文本包含 `SESSION INTENT`、`SUMMARY`、参数收集状态和下一步执行提示，只适合模型上下文和开发者诊断，不适合作为终端用户消息。

当前 Gateway 用户可见过滤器已经能在序列化时识别 `name="summary"` 并补充 `hide_from_ui=true`。但真实对话显示，前端仍可能短暂看到未隐藏的 summary。这说明只依赖后端清洗后的最终 state 不足以覆盖流式中间态、history 回填、客户端重连或消息合并窗口；因此本 change 要求后端和前端都实施修复。

## 决策

采用前后端双层强制防线，而不是只在单点修复：

1. **后端用户可见出口必须清洗**：history、state、stream 和 run stream 返回给普通用户前，必须隐藏或过滤 `name="summary"`。
2. **前端渲染必须过滤**：消息进入分组或渲染前，只要 `message.name === "summary"`，就视为隐藏消息，即使 `additional_kwargs.hide_from_ui` 缺失。
3. **保留诊断证据**：checkpoint、日志、trace 和开发者诊断渠道仍可保留 summary 原文，避免破坏长对话上下文压缩和问题排查。

该方案范围小，能覆盖真实泄漏路径；同时不要求改变 summary 生成机制，也不要求清理历史数据。

## 关键链路

1. runtime 生成 summary 消息。
2. checkpoint 保存模型上下文状态。
3. Gateway / LangGraph-compatible API 输出 history、state 或 stream 数据。
4. 前端 `useStream` 合并流式消息和 history 回填。
5. 消息分组和渲染逻辑决定是否展示。

任何普通用户可见入口都必须把 summary 视为内部消息；只有诊断入口可以保留。

## 取舍

### 不直接删除 summary

summary 是长对话上下文压缩的一部分，删除会影响模型理解历史上下文，也会破坏排查能力。因此只约束用户可见展示，不改变内部存储和模型上下文。

### 前后端都必须修复

真实现象说明最终状态清洗可以让内容“自动消失”，但不能保证不短暂展示。后端修复负责防止新的可见响应继续输出 summary；前端修复负责覆盖异常流式片段、历史旧数据、重连回填或客户端合并窗口。两者都属于本 change 的交付范围。

### 不在受保护源码中扩张业务逻辑

Apply 阶段如需修改 runtime summary 生成代码，必须先评估受保护源码边界和 Superpowers 约束。优先选择 Gateway 用户可见出口和前端过滤入口的最小修复。

## 验证策略

- 后端单元测试：构造 `HumanMessage(name="summary")`，确认用户可见序列化结果隐藏或过滤该消息。
- 前端单元测试：构造无 `hide_from_ui` 的 `message.name === "summary"`，确认分组结果不渲染。
- 流式/回填测试：覆盖 `messages`、`messages-tuple`、`values` 或等价事件输入，不出现可见 summary 内容。
- 浏览器验证：使用自然语言触发或复现长对话 summary 插入，确认 UI 不短暂展示 `SESSION INTENT` / `SUMMARY` 卡片。

## 风险

- 风险：前端兜底误隐藏用户真实消息。
  - 缓解：只隐藏 `name === "summary"` 的内部约定消息，不按普通文本关键词直接隐藏用户消息。
- 风险：后端过滤过度影响诊断。
  - 缓解：限制在普通用户可见出口；checkpoint、日志、trace 仍保留原始证据。
- 风险：历史线程已存在无隐藏标记 summary。
  - 缓解：前端强制过滤和 Gateway 输出过滤可覆盖旧数据展示，不需要迁移历史 checkpoint。
