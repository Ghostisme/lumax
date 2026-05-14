<!-- gitnexus:start -->
# GitNexus — 代码智能

本项目已在 GitNexus 中索引为 **lumax**（24520 个 symbol、38570 条 relationship、300 条 execution flow）。使用 GitNexus MCP 工具理解代码、评估影响范围并安全导航。

> 如果任何 GitNexus 工具提示索引过期，先在终端运行 `npx gitnexus analyze`。

## 必须执行

- **修改任何 symbol 前必须运行 impact analysis。** 修改 function、class 或 method 前，运行 `gitnexus_impact({target: "symbolName", direction: "upstream"})`，并向用户报告 blast radius（直接调用方、受影响流程、风险等级）。
- **提交前必须运行 `gitnexus_detect_changes()`**，确认改动只影响预期 symbol 和 execution flow。
- 如果 impact analysis 返回 HIGH 或 CRITICAL 风险，继续编辑前必须先警告用户。
- 探索不熟悉的代码时，使用 `gitnexus_query({query: "concept"})` 查找 execution flow，而不是直接 `grep`；它会按流程分组并按相关性排序返回结果。
- 需要查看某个 symbol 的完整上下文时，使用 `gitnexus_context({name: "symbolName"})` 查看调用方、被调用方以及该 symbol 参与的 execution flow。

## 禁止事项

- 禁止在未运行 `gitnexus_impact` 的情况下修改 function、class 或 method。
- 禁止忽略 impact analysis 返回的 HIGH 或 CRITICAL 风险警告。
- 禁止用查找替换重命名 symbol；应使用理解调用图的 `gitnexus_rename`。
- 禁止在未运行 `gitnexus_detect_changes()` 检查影响范围的情况下提交改动。

## 资源

| Resource | 用途 |
|----------|---------|
| `gitnexus://repo/lumax/context` | 代码库概览，检查索引新鲜度 |
| `gitnexus://repo/lumax/clusters` | 所有功能区域 |
| `gitnexus://repo/lumax/processes` | 所有 execution flow |
| `gitnexus://repo/lumax/process/{name}` | 分步骤 execution trace |

## CLI

| 任务 | 读取这个 skill 文件 |
|------|---------------------|
| 理解架构 / “X 是怎么工作的？” | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| 影响范围 / “改 X 会破坏什么？” | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| 追踪 bug / “为什么 X 失败？” | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| 重命名 / 抽取 / 拆分 / 重构 | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| 工具、资源、schema 参考 | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| 索引、状态、清理、wiki CLI 命令 | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

## 生成 Skill

| 工作区域 | 读取这个 skill 文件 |
|----------|---------------------|
| Tests（1308 个 symbol） | `.claude/skills/generated/tests/SKILL.md` |
| Ui（278 个 symbol） | `.claude/skills/generated/ui/SKILL.md` |
| Scripts（212 个 symbol） | `.claude/skills/generated/scripts/SKILL.md` |
| Channels（127 个 symbol） | `.claude/skills/generated/channels/SKILL.md` |
| Oceanengine_local_project_runtime（120 个 symbol） | `.claude/skills/generated/oceanengine-local-project-runtime/SKILL.md` |
| Memory（118 个 symbol） | `.claude/skills/generated/memory/SKILL.md` |
| Middlewares（106 个 symbol） | `.claude/skills/generated/middlewares/SKILL.md` |
| Gateway（98 个 symbol） | `.claude/skills/generated/gateway/SKILL.md` |
| Settings（96 个 symbol） | `.claude/skills/generated/settings/SKILL.md` |
| Routers（71 个 symbol） | `.claude/skills/generated/routers/SKILL.md` |
| Aio_sandbox（68 个 symbol） | `.claude/skills/generated/aio-sandbox/SKILL.md` |
| Store（62 个 symbol） | `.claude/skills/generated/store/SKILL.md` |
| Models（61 个 symbol） | `.claude/skills/generated/models/SKILL.md` |
| Auth（52 个 symbol） | `.claude/skills/generated/auth/SKILL.md` |
| Config（46 个 symbol） | `.claude/skills/generated/config/SKILL.md` |
| Mcp（44 个 symbol） | `.claude/skills/generated/mcp/SKILL.md` |
| Messages（43 个 symbol） | `.claude/skills/generated/messages/SKILL.md` |
| Ai-elements（39 个 symbol） | `.claude/skills/generated/ai-elements/SKILL.md` |
| Workspace（37 个 symbol） | `.claude/skills/generated/workspace/SKILL.md` |
| Tools（37 个 symbol） | `.claude/skills/generated/tools/SKILL.md` |

<!-- gitnexus:end -->
