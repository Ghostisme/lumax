# Package Governance

## Identity
- 类型：`extension-point`
- 说明：这是 Codex 编码阶段使用的本地 skill 资料目录，允许在本目录内新增、改写、翻译和维护项目专用 skill 指南。

## Working Rules
- 本目录内的长期资产变更仍必须先走 OpenSpec。
- 本目录中的 skill 资料只服务于 Codex 编码阶段，不自动参与 DeerFlow runtime 的 skill 加载。
- 创建、改写、翻译或迁移本目录内的 skill 时，必须先使用 `codex/skills/skill-creator/`。
- 若内容来源于 `skills/public/**`，应视为“抽取并项目化改写”，不得在未获授权时回写到上游受保护目录。

## Knowledge Capture
- 本目录形成的长期规则、坑点、边界和扩展约束，优先沉淀到本目录 `AGENTS.md`。
- OpenSpec archive 前，必须先完成长期知识沉淀检查。
