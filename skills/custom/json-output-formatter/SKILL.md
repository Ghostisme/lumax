---
name: json-output-formatter
description: DeerFlow runtime 通用 JSON 输出格式化 skill；当其它 skill 需要返回结构化 JSON、参数补齐 clarification、choice_cards 或 text_input 控件数据，并且前端需要按 input_control.type 精确匹配渲染时使用。
---

# JSON 输出格式化

本 skill 为 DeerFlow runtime custom skill 提供通用 JSON 输出格式约束。它只负责指导其它 skill 生成稳定、可解析、前端可匹配的 JSON，不负责业务参数校验、候选查询、MCP 调用或后置确认。

## 什么时候使用

其它 skill 遇到以下场景时，先读取本 skill：

- 需要输出 `data.user_visible_text` 和 `data.clarification`。
- 需要输出 `data.clarification.input_control`。
- 需要输出局部 `input_control` 片段。
- 前端需要根据 `input_control.type` 渲染控件。
- 需要生成 `choice_cards` 或 `text_input`。

## 使用流程

1. 先确认业务结果已经由对应业务 skill 或原生业务工具生成。
2. 读取 `references/schema.md`，确认目标 JSON 结构和必填字段。
3. 按场景输出完整结果 JSON 或局部 `input_control` JSON。
4. 输出必须是合法 JSON，不要使用 Markdown 代码围栏，不要附加解释文字。
5. 输出前检查 `input_control.type` 是否为前端可识别枚举。

## 前端匹配硬约束

前端按以下路径精确匹配控件类型：

- 完整结果：`data.clarification.input_control.type`
- 局部片段：`input_control.type`

`type` 必须是稳定枚举值，只允许：

- `choice_cards`
- `text_input`

不得输出中文、大小写变体或近义别名，例如不得使用 `textInput`、`text`、`input`、`文本输入`、`choiceCards` 或 `cards`。

## 输出边界

- 本 skill 不生成业务候选项；候选项必须来自业务 skill、规则文件或真实只读查询。
- 本 skill 不判断缺哪个参数；缺参判断必须来自业务工具或业务 skill。
- 本 skill 不直接调用 MCP、curl、HTTP API、SDK 或原生业务工具。
- 结构化追问一次只表达一个当前问题，不得合并多个缺参问题。
- 用户可见输出不得包含内部 tool name、MCP tool name、trace、request id、平台请求日志 ID、原始 payload JSON 或调试字段。

## 文件导航

- JSON schema、字段约束和示例：`references/schema.md`
