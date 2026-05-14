# 任务清单

## 1. 现状确认

- [x] 1.1 复核对话 `4259fc0e-775e-4155-a200-d7cc81e0336a` 的 checkpoint 证据，确认泄漏内容来自 `HumanMessage(name="summary")`。
- [x] 1.2 确认 Gateway 用户可见过滤器当前已识别 `name="summary"`，但无法独立覆盖短暂流式展示窗口。
- [x] 1.3 确认前端当前只按 `additional_kwargs.hide_from_ui` 过滤消息。

## 2. 后端用户可见出口修复与验证

- [x] 2.1 实现后端用户可见出口修复：history/state/stream/run stream 输出前必须隐藏或过滤 `name="summary"`。
- [x] 2.2 新增或更新后端测试：`HumanMessage(name="summary")` 无 `hide_from_ui` 时，经用户可见序列化后不得作为可渲染消息展示。
- [x] 2.3 覆盖 history/state 响应路径，确认 `SESSION INTENT`、`SUMMARY` 不进入普通用户可见消息。
- [x] 2.4 覆盖 stream/run stream 事件路径，确认流式中间态不会透传可渲染 summary 内容。
- [x] 2.5 确认 checkpoint、日志或开发者诊断证据仍可保留内部 summary。

## 3. 前端渲染修复与验证

- [x] 3.1 在消息过滤或分组入口强制隐藏 `message.name === "summary"`。
- [x] 3.2 新增或更新前端测试：无 `hide_from_ui` 的 summary 消息不会进入渲染分组。
- [x] 3.3 确认普通用户消息、assistant 最终回复、业务工具中文追问和结构化补齐控件不受影响。

## 4. 验证与验收

- [x] 4.1 运行后端聚焦测试，覆盖 Gateway 用户可见过滤和 summary 隐藏。
- [x] 4.2 运行前端聚焦测试或 `pnpm check` 中相关检查。
- [x] 4.3 使用真实浏览器或等价自动化复现长对话/历史回填场景，确认页面不会短暂展示 `SESSION INTENT` / `SUMMARY` 卡片。
- [x] 4.4 运行 `openspec validate fix-summary-message-ui-leak --strict`。

## 5. 边界要求

- [x] 5.1 Apply 阶段涉及设计或代码变更时必须使用 Superpowers。
- [x] 5.2 不修改 OceanEngine 原生业务工具参数校验、MCP 调用或 `data.user_visible_text` 构造规则。
- [x] 5.3 不删除 checkpoint、日志、trace 中的内部 summary 诊断证据。
