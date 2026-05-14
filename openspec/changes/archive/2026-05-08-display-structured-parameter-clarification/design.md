# 设计：后端通用结构化参数补齐接口契约

## 问题定位

后端原生业务工具已经生成结构化补齐契约，但当前用户可见链路仍以普通 AI 文本为主。工具消息里的 `data.clarification.input_control` 没有通过通用 history / stream / 消息接口稳定暴露给客户端，前端同事无法只依赖接口数据完成控件对接。

因此，某个接口缺少选项枚举时，后端规则和工具返回可能都是正确的，但客户端只能拿到中文兜底文本。修复必须作用于后端通用结构化澄清契约输出，而不是补单个字段或单个 capability。

## 推荐方案

推荐在后端用户可见出口引入统一的结构化澄清数据块，例如 `structured_clarification` 或等价字段。该字段由 Gateway / runtime 从原生业务工具结果中提取，并随 history / stream / 约定消息接口返回。

数据来源只允许是原生业务工具返回的 `data.clarification`：

- `oceanengine_local_project`
- `oceanengine_local_unit`
- `oceanengine_local_material`
- 后续同域原生业务工具，只要返回相同 `data.clarification.input_control` 契约即可复用

后端负责把工具结果中的结构化澄清转换为用户可见接口数据，同时保留 `data.user_visible_text`。前端渲染不在本 change 范围内；前端同事后续只需要按接口里的统一结构对接控件。

## 备选方案

### 方案 A：让 Agent 继续把选项写成 Markdown 列表

改动小，但仍依赖模型复述工具结果，无法保证结构稳定，也无法支持前端后续读取动态候选元数据。不推荐。

### 方案 B：让前端解析 `data.user_visible_text`

看似不改后端，但会把“可选：直播、短视频/图文”这类自然语言当协议解析。字段顺序、中文标点、动态候选摘要都会造成不稳定，也违背枚举来自后端规则元数据的要求。不推荐。

### 方案 C：后端通用结构化澄清接口契约

后端继续作为唯一数据源，通过接口直接返回标准 `input_control`。该方案覆盖静态枚举、动态候选、填写型字段和未来同类业务工具，前端可独立对接，风险可通过接口契约测试控制。推荐采用。

## 数据流

1. 用户提出 OceanEngine 本地推业务请求。
2. Agent 按 skill 约束调用对应原生业务工具。
3. 原生业务工具本地校验失败，返回 `success=false`、`data.user_visible_text` 和 `data.clarification.input_control`。
4. Gateway / runtime 用户可见出口识别该结构化澄清结果，生成或附加统一结构化澄清数据块。
5. history / stream / 约定消息接口返回该数据块，同时保留现有文本消息。
6. 测试通过接口直接检查结构化字段，不依赖前端渲染。

## 结构约定

后端接口返回的结构化澄清数据应至少包含：

- `version`
- `reason`
- `field`
- `field_label`
- `question`
- `input_control`
- `user_visible_text`

`choice_cards.options[]` 应保留后端返回的：

- `value`
- `label`
- `description`
- `metadata`

后端不得新增、删除或重排候选项。

## 清洗与可见性

- 普通用户可见文本不得展示内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID。
- 原始工具消息可继续按现有规则隐藏，但接口返回的结构化澄清数据必须保留对前端对接必要的安全字段。
- 如果结构化字段缺失或格式异常，接口仍必须保留 `user_visible_text`，不能返回空候选或臆造候选。

## 测试策略

- 后端契约测试：从原生业务工具返回体提取 `data.clarification.input_control` 并进入 history / stream / 约定消息接口用户可见数据。
- 接口验证：通过 curl 或等价 API 调用查看 `structured_clarification` 或等价字段。
- 回归样例：至少覆盖项目、单元、素材三类原生业务工具各一个静态枚举缺参场景。
- 动态候选样例：覆盖商品候选 `choice_cards` 的 `description` / `metadata` 不被丢失。
- 清洗样例：确认接口结构不包含 `business_tool_name`、`mcp_tool_name`、payload JSON 或内部 trace。

## 风险与缓解

- 风险：接口同时返回文本和结构化数据，前端对接时可能重复展示。缓解：后端清晰区分 `user_visible_text` 兜底字段和结构化澄清字段，由前端后续选择展示策略。
- 风险：内部工具字段进入接口。缓解：只转发白名单字段，继续隐藏原始 `oceanengine_local_*` 工具消息。
- 风险：通用实现过度绑定 OceanEngine。缓解：渲染组件只依赖 `input_control` 契约；后端提取源可先限定为 OceanEngine 原生业务工具。
- 风险：前端自动回填协议未定义。缓解：本次只要求后端接口返回结构化数据，自动回填作为后续前端或联调增强。
