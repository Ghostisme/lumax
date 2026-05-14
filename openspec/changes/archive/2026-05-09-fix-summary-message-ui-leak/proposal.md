# 变更提案：修复内部历史摘要短暂展示到用户 UI

## Why

真实对话 `4259fc0e-775e-4155-a200-d7cc81e0336a` 中，页面短暂展示了包含 `SESSION INTENT`、`SUMMARY`、`local_account_id` 等内部上下文的白色卡片，随后又自动消失。该内容不是业务工具返回的用户可见结果，而是 runtime 为压缩长对话生成的 `HumanMessage(name="summary")` 历史摘要。

当前链路已有 Gateway 用户可见过滤逻辑，会在序列化后把 `name="summary"` 消息标记为 `hide_from_ui=true`。但 checkpoint 中的原始 summary 消息本身没有携带隐藏标记，流式输出、history/state 回填或前端消息合并存在短暂窗口时，客户端可能先渲染未清洗的 summary，后续再被清洗后的状态覆盖，因此表现为“突然出现，然后自动消失”。

这违反了现有 `lead-agent-runtime-config` 中“用户可见消息不得展示内部 provider reasoning summary”和“后端生成内部上下文消息不得进入普通 UI”的边界。修复需要把 summary 隐藏从单一后端清洗补救提升为前后端共同保证的用户可见契约：后端用户可见出口不得输出可渲染 summary，前端即使收到异常或旧数据中的 summary 也不得渲染。

## What Changes

- `HumanMessage(name="summary")`、`SESSION INTENT`、`SUMMARY`、内部工具路径、MCP tool 名和等价内部诊断内容 SHALL NOT 在普通对话 UI 中展示，即使只是在流式中间态短暂出现也不允许。
- 后端用户可见出口 SHALL 覆盖 history、state、stream、run stream 和客户端重连回填路径，避免只在最终状态清洗。
- 前端消息渲染 SHALL 对 `name="summary"` 做强制隐藏；不得只依赖 `additional_kwargs.hide_from_ui` 已经存在，也不得把前端过滤视为可选兜底。
- 内部 summary MAY 继续保存在 checkpoint、日志、trace 或开发者诊断数据中，用于上下文压缩和问题排查。
- Apply 阶段涉及设计或代码变更时必须使用 Superpowers，并保持受保护源码边界；后端清洗和前端过滤均为本 change 的必做范围，具体实现应优先选择 Gateway 用户可见出口、项目扩展点和前端消息过滤入口，不扩大修改范围。

## Out of Scope

- 不改变 summary 的生成目的、压缩策略、token 计数或模型上下文注入语义。
- 不删除历史 checkpoint、日志、trace 或开发者诊断证据。
- 不改变 OceanEngine 原生业务工具的参数校验、MCP 调用、后置确认或 `data.user_visible_text` 构造规则。
- 不在 proposal 阶段修改前端、后端、配置或 skill 实现代码。

## Impact

- `lead-agent-runtime-config` 规格：强化内部 summary 消息在用户可见链路中的隐藏要求。
- Gateway 用户可见出口：需要验证 history/state/stream/run stream 序列化均会隐藏或过滤 `name="summary"` 消息。
- 前端消息渲染：需要在消息分组或过滤入口强制过滤 `message.name === "summary"`。
- 回归测试：需要分别覆盖后端输出清洗和前端异常输入过滤，确保 `HumanMessage(name="summary")` 无 `hide_from_ui` 时仍不会进入普通 UI。

## Acceptance Criteria

- `openspec validate fix-summary-message-ui-leak --strict` 通过。
- 给定 checkpoint 或 stream 事件中存在 `HumanMessage(name="summary")` 且未携带 `additional_kwargs.hide_from_ui`，后端用户可见响应不得输出可渲染的该消息内容。
- 给定前端收到异常或历史数据中的 `message.name === "summary"`，普通用户 UI 仍不得展示该消息内容。
- 用户可见 history/state/stream 响应不得包含可渲染的 `SESSION INTENT`、`SUMMARY`、内部工具路径、MCP tool 名或 `payload_json` 等内部诊断内容。
- 浏览器复现对话或等价测试线程时，页面不得短暂出现 summary 卡片；最终业务回复仍正常展示。
- 内部 summary 仍可保留在 checkpoint、日志或诊断接口中，供维护者排查上下文压缩和工具链路问题。
