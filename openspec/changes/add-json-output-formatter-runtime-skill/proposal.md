# 新增 DeerFlow JSON 输出格式化 Skill

## 背景

当前 OceanEngine 本地推等 DeerFlow custom skill 已经开始返回结构化参数补齐信息，例如 `data.user_visible_text`、`data.clarification` 和 `data.clarification.input_control`。这类结果既要方便前端或 Gateway 消费，也要保证用户可见文本干净、不泄漏内部工具链路信息。

不同 skill 后续都可能需要输出同类 JSON，如果各自手写格式，容易出现字段不一致、候选顺序丢失、Markdown 包裹 JSON、内部 trace 泄漏或多问题追问等问题。因此需要新增一个 DeerFlow runtime 可加载的 custom skill，作为其它 skill 生成结构化 JSON 输出时的格式化约束与示例来源。

## 目标

- 新增 DeerFlow runtime custom skill：`skills/custom/json-output-formatter/`。
- 规范完整 JSON 输出结构，重点覆盖：
  - `data.user_visible_text`
  - `data.clarification`
  - `data.clarification.input_control`
- 规范局部 `input_control` 片段输出，覆盖：
  - `choice_cards`
  - `text_input`
- 明确 `input_control.type` 是前端渲染分支的主匹配字段，必须稳定、必填、枚举化。
- `input_control.type` 只允许使用前端可识别的精确字符串，例如 `choice_cards` 和 `text_input`，不得输出中文、大小写变体或近义别名。
- 要求其它 skill 需要生成结构化追问或控件 JSON 时，可以先读取本 skill 并按其格式输出。
- 要求输出必须是可解析 JSON，不使用 Markdown 代码围栏，不夹杂解释性文本。
- 要求用户可见结果隐藏内部 tool name、MCP tool name、trace、request id、平台请求日志 ID、原始 payload JSON 等内部信息。
- 保留候选项 `value`、`label`、`description`、`metadata` 和原始顺序。

## 非目标

- 不修改 `skills/public/**` 上游公共 skill。
- 不新增或修改 OceanEngine 原生业务工具。
- 不新增 MCP 调用能力，不替代业务 tool 的参数校验、候选查询或后置确认。
- 不修改前端渲染组件。
- 不修改 Gateway 响应清洗逻辑；如需 runtime 出口清洗，应另建变更。

## 影响范围

- 新增 `skills/custom/json-output-formatter/` 下的 skill 文档和必要 reference。
- 可能补充 `skills/AGENTS.md` 中关于通用格式化 skill 的长期边界说明。
- 不触达 `backend/packages/harness/deerflow/**` 受保护源码。
- 不触达 `frontend/**`。

## 风险与约束

- 该 skill 只能提供输出格式约束和示例，不得声明自己能够调用 MCP 或执行业务查询。
- 其它业务 skill 仍必须使用各自原生业务工具生成真实业务结果，本 skill 不得成为绕过业务工具的路径。
- 对结构化追问，用户可见文本仍必须只追问一个当前问题，不得把多个缺失参数合并追问。
- 前端会根据 `data.clarification.input_control.type` 或局部 `input_control.type` 做匹配；该字段不稳定会导致控件无法渲染，因此示例和规则必须把它作为硬约束。
- `text_input` 必须包含 `value_type` 和 `placeholder`，`choice_cards` 必须包含 `selection_mode` 和 `options`。
- JSON 示例必须保持字段最小化，避免鼓励下游 skill 输出内部调试字段。
- OpenSpec archive 前必须完成长期知识沉淀检查，并等待用户明确批准后再归档。
