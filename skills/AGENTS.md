# Package Governance

## Identity
- 类型：`extension-point`
- 说明：这是项目的 skill 总入口目录，用于区分 DeerFlow runtime skills 与供 Codex 编码阶段使用的本地 skill 资料的治理边界。

## Working Rules
- 本目录相关的长期资产变更仍必须先走 OpenSpec。
- `skills/public/**` 属于 DeerFlow 受保护源码，原则上不得直接改写上游 skill 来满足项目定制需求。
- `skills/custom/**` 仅用于 DeerFlow runtime 需要加载的项目 custom skill。
- `skills/custom/json-output-formatter/` 是通用 JSON 输出格式约束 skill，仅用于规范其它 runtime skill 的结构化输出和前端 `input_control.type` 匹配字段；不得把它当作业务参数校验、候选查询、MCP 调用或后置确认工具。
- `skills/custom/oceanengine-local-project/scripts/**` 的真实 MCP 调用必须复用根目录 `tools.oceanengine_local_project_runtime` 共享运行时，并通过 Nacos 解析 `platform-agent-biz` 的真实 endpoint；不得恢复脚本内 `http://127.0.0.1:18000/mcp/` 或其它本机固定 Router 默认业务兜底。
- 如果需求是创建、翻译、改写或抽取一个给 Codex 编码阶段使用的 skill，必须先使用 `codex/skills/skill-creator/`，并优先落到 `codex/skills/**`，而不是直接写入 `skills/public/**`。

## Knowledge Capture
- 本目录形成的长期规则、坑点、边界和扩展约束，优先沉淀到本目录 `AGENTS.md` 或最近父级 `AGENTS.md`。
- OpenSpec archive 前，必须先完成长期知识沉淀检查。
