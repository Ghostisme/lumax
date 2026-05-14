# JSON 输出 Schema

本 reference 规定 DeerFlow skill 输出结构化 JSON 时的稳定字段。前端会根据 `input_control.type` 做精确匹配，因此字段名、枚举值和嵌套路径必须保持一致。

## 完整参数补齐结果

完整结果使用 `data.user_visible_text` 兼容文本展示路径，并在 `data.clarification.input_control` 中提供结构化控件数据。

```json
{
  "data": {
    "user_visible_text": "营销目的是什么值？",
    "clarification": {
      "version": "v1",
      "reason": "missing_required_parameter",
      "field": "marketing_goal",
      "field_label": "营销目的",
      "question": "营销目的是什么值？",
      "input_control": {
        "type": "choice_cards",
        "selection_mode": "single",
        "options": [
          {
            "value": "LIVE",
            "label": "直播"
          }
        ]
      }
    }
  }
}
```

### 必填字段

- `data.user_visible_text`：字符串，用户可见的单问题追问。
- `data.clarification.version`：字符串，当前固定为 `v1`。
- `data.clarification.reason`：字符串，例如 `missing_required_parameter`。
- `data.clarification.field`：字符串，业务字段名。
- `data.clarification.field_label`：字符串，中文字段名。
- `data.clarification.question`：字符串，应与本轮用户可见追问一致。
- `data.clarification.input_control`：对象，控件配置。

## input_control 通用规则

前端匹配路径：

- 完整结果：`data.clarification.input_control.type`
- 局部片段：`input_control.type`

`type` 是前端渲染分支的主匹配字段，必须稳定、必填、枚举化。当前只允许：

- `choice_cards`
- `text_input`

禁止输出以下形式：

- 中文：`文本输入`、`选项卡`
- 大小写变体：`textInput`、`choiceCards`
- 近义别名：`input`、`text`、`cards`、`select`

## choice_cards

用于前端展示候选卡片。

```json
{
  "input_control": {
    "type": "choice_cards",
    "selection_mode": "single",
    "options": [
      {
        "value": "LIVE",
        "label": "直播"
      }
    ]
  }
}
```

### 必填字段

- `input_control.type`：必须为 `choice_cards`。
- `input_control.selection_mode`：必须为 `single` 或 `multiple`。
- `input_control.options`：数组，顺序必须保持业务来源顺序。
- `options[].value`：必填，前端回填或提交使用的真实值。
- `options[].label`：必填，用户可见名称。

### 可选字段

- `options[].description`：候选项摘要。
- `options[].metadata`：前端或后续链路需要保留的非敏感业务元数据。

`metadata` 不得包含内部 trace、MCP tool name、平台请求日志 ID、原始请求 payload 或认证信息。

## text_input

用于前端展示文本输入框。

```json
{
  "input_control": {
    "type": "text_input",
    "value_type": "string",
    "placeholder": "请填写项目名称"
  }
}
```

### 必填字段

- `input_control.type`：必须为 `text_input`。
- `input_control.value_type`：输入值类型，例如 `string`、`number`、`integer`、`boolean`。
- `input_control.placeholder`：中文占位提示。

## 清洗规则

输出给用户或前端的 JSON 不得包含：

- 内部 tool name
- MCP tool name
- MCP server name
- trace
- request id
- 平台请求日志 ID
- 原始 payload JSON
- 认证信息
- 调试堆栈
- 多个未展示缺参项

## 输出格式规则

- 输出必须是单个合法 JSON 对象。
- 不要使用 Markdown 代码围栏。
- 不要在 JSON 前后附加解释文字。
- 字段名必须使用 snake_case。
- 候选项顺序必须与业务来源顺序一致。
- 不得臆造候选 `label`；缺少中文标签时应由业务 skill 决定是否回退为 `value`。
