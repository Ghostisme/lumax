# 任务清单

## 1. OpenSpec

- [x] 将 change 范围调整为后端 / Gateway 的 MCP 动态候选卡片契约。
- [x] 明确本次变更不得修改 `frontend/**`。
- [x] 补充 `structured-parameter-clarification` 规格增量，覆盖动态候选单选、多选、文本兜底和安全清洗。
- [x] 运行 `openspec validate clarification-card-interactions --strict` 并修复所有文档问题。
- [x] 写入后向用户汇报实际文档变更，并等待批准进入后续流程。

## 2. 后端候选契约

- [x] 梳理现有静态枚举 `choice_cards` 输出结构，确认动态 MCP 候选沿用同一字段契约。
- [x] 对适合动态候选补齐的字段，明确 `selection_mode=single` 或 `selection_mode=multiple` 的判定来源。
- [x] 确保候选项至少包含 `value` 和 `label`，并在安全时保留 `description`、`metadata`。
- [x] 候选查询返回分页信息时，保留安全的 `page_info`。
- [x] 候选查询失败、为空或前置参数不足时，不生成空的或臆造的 `choice_cards.options`。

## 3. Gateway 用户可见出口

- [x] 确认 `structured_clarifications` 或等价结构化字段保留 `input_control.selection_mode`。
- [x] 确认用户可见出口保留候选 `value`、`label`、`description`、`metadata` 与候选顺序。
- [x] 确认用户可见出口保留安全的 `page_info`。
- [x] 确认输出隐藏内部 tool name、MCP tool name、payload JSON、trace 和平台请求日志 ID。
- [x] 确认 `data.user_visible_text` 兜底能展示单选和多选候选，并提示用户回复候选 ID 或名称。

## 4. 测试与验证

- [x] 增加或更新后端单测，覆盖动态 MCP 候选生成 `choice_cards`。
- [x] 增加或更新后端单测，覆盖 `selection_mode=single` 与 `selection_mode=multiple`。
- [x] 增加或更新 Gateway 清洗测试，覆盖 `description`、`metadata`、`page_info` 保留和内部字段隐藏。
- [x] 增加或更新失败路径测试，覆盖候选查询失败、为空和前置参数不足。
- [x] 运行相关后端定向测试；若完整测试成本过高，记录已执行的聚焦命令和未覆盖风险。

## 5. 浏览器验收与问题排查

- [x] 使用真实浏览器打开本地页面并完成登录；登录凭据只作为本地测试运行时信息使用，不写入长期文档。
- [x] 使用真实用户自然语言触发本地推动态候选补齐流程，测试参数包含本地提账号 `1854708763953159`。
- [x] 浏览器输入 SHALL NOT 指定工具名、`capability`、`payload_json`、底层 MCP tool 名、脚本路径或“直接调用某工具”等作弊提示。
- [x] 浏览器验收必须证明真实 Agent、OceanEngine 原生业务工具和只读 MCP 候选查询链路被触发。
- [x] 若浏览器验收失败或链路不清晰，先结合本地 Gateway、backend、frontend 和 MCP 相关日志排查问题。
- [x] 本地日志仍无法定位时，通过本轮 `sessionId` 查询 Langfuse 日志作为辅助诊断证据。（本轮本地日志已定位问题，未触发 Langfuse 查询。）
- [x] 排除问题并完成必要修复后，必须重新执行真实浏览器自然语言验收；本地日志、Langfuse、curl、脚本或 MCP 直连结果不得替代最终验收。
