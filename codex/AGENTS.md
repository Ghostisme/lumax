# Package Governance

## Identity
- 类型：`extension-point`
- 说明：这是项目为 Codex 协作预留的本地资料目录，允许在本目录内演进 Codex 编码阶段使用的规则、skill 和辅助资源。

## Working Rules
- 本目录内的设计、文档和本地 skill 资料变更仍必须先走 OpenSpec。
- 本目录用于 Codex 编码阶段读取的本地资料，不等同于 DeerFlow runtime 的 `skills/public/**` 或 `skills/custom/**`。
- 若需求是把上游 `skills/public/**` 的内容“拿出来”给 Codex 使用，应优先复制到 `codex/` 下再改写，不得直接覆盖上游受保护源码。

## Knowledge Capture
- 本目录形成的长期规则、坑点、边界和扩展约束，优先沉淀到本目录或最近父级 `AGENTS.md`。
- OpenSpec archive 前，必须先完成长期知识沉淀检查。
