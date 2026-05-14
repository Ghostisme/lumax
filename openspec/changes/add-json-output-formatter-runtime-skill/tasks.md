# 任务清单

## 1. 设计

- [x] 1.1 确认 `json-output-formatter` 是 DeerFlow runtime custom skill，落点为 `skills/custom/json-output-formatter/`。
- [x] 1.2 确认本 skill 只提供 JSON 输出格式化约束，不承担 MCP 调用、参数校验或业务候选查询。
- [x] 1.3 确认需要覆盖完整工具结果 JSON 与局部 `input_control` JSON 两类输出。
- [x] 1.4 确认 `input_control.type` 是前端控件渲染的主匹配字段，必须使用稳定枚举值。

## 2. 实现

- [x] 2.1 创建 `skills/custom/json-output-formatter/SKILL.md`。
- [x] 2.2 在 `SKILL.md` 中写清触发条件、使用流程、输出边界和禁止事项。
- [x] 2.3 创建按需读取的 reference，记录完整 JSON schema、`choice_cards` 示例、`text_input` 示例和清洗规则。
- [x] 2.4 提供用户给定样例对应的标准化 JSON 示例。
- [x] 2.5 如形成长期规则，更新最近层级 `AGENTS.md`。
- [x] 2.6 在 reference 中写明 `choice_cards`、`text_input` 的必填字段、允许枚举和禁止别名。

## 3. 验证

- [x] 3.1 检查 skill frontmatter 是否包含可触发的 `name` 和 `description`。
- [x] 3.2 检查 JSON 示例是否可被解析。
- [x] 3.3 检查示例不包含 Markdown 代码围栏、内部 tool name、trace、request id 或原始 payload。
- [x] 3.4 检查未修改 `skills/public/**`、`frontend/**` 或受保护 DeerFlow 源码。
- [x] 3.5 检查所有示例中的 `input_control.type` 只使用 `choice_cards` 或 `text_input`。

## 4. 归档准备

- [ ] 4.1 OpenSpec archive 前完成长期知识沉淀检查。
- [ ] 4.2 OpenSpec archive 前等待用户明确批准。
- [ ] 4.3 OpenSpec archive 完成后执行中文 git 提交。
