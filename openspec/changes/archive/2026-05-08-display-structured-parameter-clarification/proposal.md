# 后端通用返回结构化参数补齐控件数据

## 背景

OceanEngine 本地推原生业务工具已经能在本地参数校验失败时返回 `data.clarification.input_control`。静态枚举字段会返回 `choice_cards`，动态候选字段也可以返回来自真实只读查询的 `choice_cards`。

真实对话 `c1bf3e7a-5341-4b35-bcac-5aa185d39b9d` 暴露了展示链路缺口：`oceanengine_local_project` 在 `create-project` 缺少 `marketing_goal` 时已返回 `choice_cards.options=[LIVE, VIDEO_IMAGE]`，但最终用户只看到 `data.user_visible_text` 纯文本“营销场景是什么值？可选：直播、短视频/图文。”。这说明问题不在某个接口的规则枚举，而在通用用户可见出口和前端消息渲染没有消费结构化补齐契约。

本 change 只解决后端通用契约输出：通过 history、stream 或约定的线程消息接口，让前端同事可以直接拿到结构化 `clarification` 数据。前端控件渲染和点击交互由后续前端对接实现。

## 目标

- 所有 OceanEngine 原生业务工具返回的 `data.clarification.input_control` 都必须通过后端通用接口契约返回给客户端。
- 后端返回结构不得绑定项目、单元、素材或某个 capability 特例。
- `choice_cards.options[].value`、`label`、`description`、`metadata` 和顺序必须保持原生业务工具返回内容。
- 旧的 `data.user_visible_text` 继续作为 Markdown / 文本兜底展示路径，兼容当前前端未对接控件的状态。

## 非目标

- 不新增或修改某个具体 OceanEngine 接口的枚举定义。
- 不实现前端 `choice_cards` 或 `text_input` 控件渲染。
- 不实现点击卡片后的自动回填或字段级提交协议。
- 不改变原生业务工具的参数校验顺序、MCP 调用授权或单问题追问规则。
- 不把内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID 展示给用户。

## 影响范围

- Gateway / runtime 用户可见出口：需要保留并转发原生业务工具返回的结构化澄清数据。
- 线程 history / stream 或约定消息接口：需要能通过 API 直接查看结构化补齐字段。
- OceanEngine 项目、单元、素材缺参场景：统一受益，不按接口分别实现。
- 测试：增加后端契约测试和通过接口查看结构化字段的验证路径。

## 风险与约束

- 结构化控件是用户可见能力，必须保持内部字段清洗，不得泄漏 `oceanengine_local_*`、底层 MCP tool 或原始 JSON 包装。
- `backend/packages/harness/deerflow/**` 为受保护源码；实现阶段应优先放在 Gateway、根目录 `tools/` 或其它明确扩展点。
- 本 change 不修改 `frontend/`。
- Apply 阶段涉及设计或代码变更时必须使用 Superpowers。
