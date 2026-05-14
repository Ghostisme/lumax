---
name: skill-creator
description: 当需要为本项目创建、改写、翻译、迁移或优化 skill 时使用。适用于把现有流程沉淀成 skill、把上游 skill 抽取到 Codex 本地目录并项目化改写、补齐 SKILL.md 结构、设计 references/scripts/assets 分层，以及为 skill 制定 OpenSpec 和归档路径。
---

# Skill Creator

这是给 Codex 编码阶段使用的项目版 `skill-creator`。它的职责不是直接参与 DeerFlow runtime 的 skill 加载，而是指导你在当前仓库里正确地创建或改写长期可维护的 skill 资产。

本 skill 基于 Anthropic 原版 `skill-creator` 的思路翻译并改写，补入了本项目的 DeerFlow、Codex、OpenSpec 和 `AGENTS.md` 治理要求。

## 什么时候用

遇到下面这些情况，必须先使用本 skill：

- 用户要“创建一个 skill”
- 用户要“把某个流程沉淀成 skill”
- 用户要“翻译 / 改写 / 优化现有 skill”
- 用户要“把 `skills/public/**` 某个 skill 拿出来给 Codex 用”
- 用户要补齐 `SKILL.md`、`references/`、`scripts/`、`assets/` 结构
- 用户要为 skill 建立 OpenSpec proposal / apply / archive 路径

如果只是临时回答一个问题、执行一次性脚本、或修改不纳入版本控制的本地文件，不需要使用本 skill。

## 先做什么

在写任何 skill 文档或资源前，先做这 5 件事：

1. 判断这次变更是否会修改受版本控制的长期资产。
2. 如果会，先创建或更新 OpenSpec change。
3. 读取最近层级的 `AGENTS.md`，确认目标目录是不是允许修改的扩展点。
4. 判断这是：
   - Codex 编码阶段使用的本地 skill 资料
   - 还是 DeerFlow runtime 要加载的 skill
5. 再决定落点目录。

## 落点规则

### 1. 给 Codex 编码阶段使用

默认放到：

```text
codex/skills/<skill-name>/
```

这类 skill 是本地资料目录，不参与 DeerFlow runtime 自动加载。

### 2. 给 DeerFlow runtime 使用

只有在需求明确要求新增 DeerFlow 可加载 skill，并且最近规则允许时，才评估是否落到：

```text
skills/custom/<skill-name>/
```

不能因为“已有 public skill 可以参考”就直接去改 `skills/public/**`。

### 3. 来源于 `skills/public/**`

如果用户要求“把 `skills/public/xxx` 拿出来”，默认含义是：

- 以它为内容来源
- 复制到 `codex/skills/<skill-name>/`
- 在新目录里完成中文化和项目化改写
- 不直接改上游 `skills/public/**`

## 标准工作流

### 第一步：确认意图

优先从当前对话中提取信息，而不是立刻反问用户。先确认：

- 这个 skill 要解决什么问题
- 谁会使用它
- 它是给 Codex 用，还是给 DeerFlow runtime 用
- 期望的输出是什么
- 是否需要测试 / 验证样例

如果信息还不够，再补问最少的问题。

## 第二步：确定结构

默认使用轻量 `SKILL.md` + 渐进式辅助目录：

```text
<skill-name>/
├── SKILL.md
├── references/   # 按需加载的说明、schema、约束、示例
├── scripts/      # 需要可复用、可验证、可执行的脚本
└── assets/       # 模板、图标、HTML、样例文件等输出资源
```

原则：

- `SKILL.md` 只放触发条件、核心流程和导航
- 详细 schema、长示例、平台差异放到 `references/`
- 重复且脆弱的操作尽量沉到 `scripts/`
- 最终输出要用到但不必进上下文的文件放到 `assets/`

## 第三步：编写 SKILL.md

`SKILL.md` 至少包含：

- frontmatter
  - `name`
  - `description`
- 主体
  - 这个 skill 何时使用
  - 先做什么
  - 目录落点或执行边界
  - 需要时去读哪些 `references/`
  - 需要时运行哪些 `scripts/`
  - 不允许做什么

### Frontmatter 规则

- `name` 用 kebab-case
- `description` 写“什么时候该用”，不是过程摘要
- 尽量包含真实触发词，而不是抽象口号
- 如果这是 Codex 本地资料目录，也要在正文里写清楚“它不参与 DeerFlow runtime 自动加载”

## 第四步：写项目约束

本项目的 skill 额外要满足这些规则：

- 任何受版本控制的 skill 资产变更都必须先走 OpenSpec
- 创建或改写 skill 时必须先使用本 `skill-creator`
- 归档前必须先完成长期知识沉淀检查
- `openspec archive` 前必须先等待用户明确批准
- `openspec archive` 完成后必须再执行 git 提交
- 该次 git 提交备注必须使用中文
- 如果目标内容在 `skills/public/**`，默认不能直接修改
- 如果只是给 Codex 编码阶段使用，优先放在 `codex/skills/**`

## 第五步：做验证

不是每个 skill 都需要复杂 benchmark，但至少要做匹配的验证：

- 文档型 skill：检查目录结构、导航、规则是否清晰
- 工作流型 skill：准备 2 到 3 个真实提示词，检查是否能覆盖主要路径
- 带脚本的 skill：运行最小可行命令，确认脚本与文档一致
- 从 public skill 抽取出来的项目版：检查是否已经去掉上游特有假设，并补入本项目约束

如果任务规模大、而且用户明确想做系统性评测，可以继续复用这个目录里带过来的 `scripts/`、`references/`、`eval-viewer/` 等资源；如果用户只是想快速落一个可用版本，不必强行启用完整 benchmark 流程。

## 抽取 public skill 的专用流程

当用户说“把 `skills/public/xxx` 拿出来”时，按这个顺序做：

1. 先确认不能直接改上游目录。
2. 复制源目录到 `codex/skills/<skill-name>/`。
3. 删除复制过来的上游治理文件，避免把受保护规则错误继承到本地目录。
4. 保留可复用资源：
   - `scripts/`
   - `references/`
   - `assets/`
   - `eval-viewer/`
5. 重写 `SKILL.md`：
   - 翻译成中文
   - 改写成适合本项目的规则
   - 明确 Codex / OpenSpec / AGENTS 约束
6. 如果形成新的长期规则，把规则沉淀到最近层级 `AGENTS.md`。

## 写作风格

- 直接、具体、少空话
- 优先写触发条件和决策边界
- 不把一堆实现细节塞进 `description`
- 不要写成“复盘故事”
- 优先写成未来另一个 Codex 能拿来立刻执行的指南

## 常见错误

- 还没建 OpenSpec change 就先改 skill
- 明明是给 Codex 用的资料，却错误放进 `skills/custom/`
- 直接改 `skills/public/**`
- `SKILL.md` 过长，所有细节都塞在一个文件里
- `description` 写成流程摘要，导致后续模型不读正文
- archive 前跳过用户确认直接归档
- archive 后遗漏 git 提交
- archive 后 git 提交备注不是中文

## 交付检查清单

交付前确认：

- 是否已经明确这是给 Codex 用还是给 DeerFlow runtime 用
- 是否已经放到正确目录
- 是否已经走 OpenSpec
- 是否已经补充最近层级 `AGENTS.md`
- 是否已经写清触发条件、导航和禁止事项
- 是否做了与规模匹配的验证
- 是否已在 archive 后完成 git 提交，且备注使用中文
