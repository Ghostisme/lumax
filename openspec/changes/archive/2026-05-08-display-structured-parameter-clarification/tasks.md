# 任务清单

## 1. 设计与契约

- [x] 1.1 确认当前 history / stream 用户可见出口没有保留 `data.clarification.input_control`。
- [x] 1.2 定义后端通用结构化澄清接口数据结构，不包含接口名特例。
- [x] 1.3 确认 `data.user_visible_text` 作为旧展示路径继续保留。
- [x] 1.4 Apply 阶段开始前使用 Superpowers，并在实现前做必要的 GitNexus impact analysis。

## 2. 后端实现

- [x] 2.1 增加失败测试：`oceanengine_local_project` 静态枚举缺参返回 `choice_cards` 时，history/stream 可见数据包含结构化澄清。
- [x] 2.2 增加失败测试：`oceanengine_local_unit` 静态枚举缺参同样进入通用结构化澄清链路。
- [x] 2.3 增加失败测试：`oceanengine_local_material` 静态枚举缺参同样进入通用结构化澄清链路。
- [x] 2.4 增加失败测试：动态商品候选 `choice_cards` 保留 `value`、`label`、`description` 和 `metadata`。
- [x] 2.5 在 Gateway、根目录 `tools/` 或其它明确扩展点实现结构化澄清提取，不新增 `backend/packages/harness/deerflow/**` 业务专用逻辑。
- [x] 2.6 确保原始工具消息仍不泄漏内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID。
- [x] 2.7 确保 `data.user_visible_text` 继续作为当前前端的兜底文本展示路径。

## 3. 接口验证

- [x] 3.1 通过 history 接口或等价线程消息接口查看项目管理枚举缺参返回的结构化字段。
- [x] 3.2 通过 history 接口或等价线程消息接口查看单元管理枚举缺参返回的结构化字段。
- [x] 3.3 通过 history 接口或等价线程消息接口查看素材管理枚举缺参返回的结构化字段。
- [x] 3.4 通过接口验证动态候选 `choice_cards` 的 `description` / `metadata` 未丢失。
- [x] 3.5 确认本 change 不修改 `frontend/`。

## 4. 验证

- [x] 4.1 运行后端定向测试，覆盖结构化澄清提取和清洗。
- [x] 4.2 如环境可用，用自然语言复现 `c1bf3e7a-5341-4b35-bcac-5aa185d39b9d` 同类创建项目缺参场景，并通过接口确认结构化字段存在。
- [x] 4.3 如环境可用，补充单元管理和素材管理各一个枚举缺参接口验收。
- [x] 4.4 检查 `git diff --stat`，确认本 change 未修改 `frontend/`。
- [x] 4.5 运行 `openspec validate display-structured-parameter-clarification --strict`。
