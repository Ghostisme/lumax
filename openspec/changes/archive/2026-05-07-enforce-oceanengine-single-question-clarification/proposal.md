# OceanEngine 参数校验一次只追问一个问题

## 背景

当前 OceanEngine 原生业务工具在参数校验失败时，会由共享校验器一次性收集全部普通必填、条件必填、批量项和其它规则错误，再由 Agent 可见结果压缩逻辑最多展示 5 条中文错误。用户在浏览器或对话入口看到的结果因此可能同时包含多个待补充参数。

这与期望的交互不一致：用户希望参数不足时按轮次补齐，一次只回答一个明确问题。该要求只适用于 OceanEngine 相关业务工具，不改变 DeerFlow 通用 `ask_clarification`、普通工具错误展示或非 OceanEngine 业务链路。

## 目标

- 将 OceanEngine 原生业务工具的参数校验失败反馈统一改为一次只展示一个可行动中文问题。
- 范围覆盖 `oceanengine_local_project`、`oceanengine_local_unit` 和 `oceanengine_local_material`。
- 将 OceanEngine 三个 runtime skill 的缺参入口统一为先调用对应原生业务工具做本地校验，不允许主 Agent 直接 `ask_clarification` 汇总多个缺失项。
- 保留本地校验一次收集完整错误列表的内部能力，便于日志、测试和后续诊断；仅收窄面向 Agent/用户的可见追问。
- 确保首个问题来自现有规则顺序，用户补充后下一轮重新校验并追问下一项。
- 不影响 MCP 缺失诊断、平台/MCP 执行失败、成功结果展示和通用 `ask_clarification` middleware。

## 非目标

- 不重写通用 `ClarificationMiddleware`。
- 不把 OceanEngine 业务工具改成真正调用 `ask_clarification` tool。
- 不改变 `rules/*.json` 中字段必填、条件必填、枚举、范围或批量规则语义。
- 不改变底层 MCP tool 绑定、payload 构造、后置确认或真实接口调用策略。
- 不改非 OceanEngine 工具的多错误展示行为。

## 影响范围

- `tools/oceanengine_local_project_runtime/agent_visible.py`：OceanEngine 单元和素材业务工具共用的 Agent 可见结果压缩逻辑。
- `tools/oceanengine_local_project.py`：项目管理业务工具当前保留了一份本地 Agent 可见结果压缩逻辑，需要与共享逻辑保持一致。
- `tools/oceanengine_local_project_runtime/validators.py`：原则上不改变内部校验收集行为；如实现需要增加错误分类，也必须保持内部完整错误列表。
- `skills/custom/oceanengine-local-project/SKILL.md`、`skills/custom/oceanengine-local-unit/SKILL.md`、`skills/custom/oceanengine-local-material/SKILL.md`：约束 OceanEngine 缺参时不得绕过原生业务工具直接多项 clarification。
- 后端定向测试：覆盖项目、单元、素材三类业务工具的校验失败只暴露首个问题。

## 风险与约束

- 只展示首个问题可能增加用户补齐轮次，但能降低一次性多参数追问造成的认知负担。
- 内部 `errors` 是否保留多条需要谨慎：若对 Agent 可见 JSON 仍暴露多条，模型可能绕过 `user_visible_text` 汇总多问；因此面向 Agent 的 `errors` 也应只保留首个可见错误，同时用计数字段保留总量。
- MCP 缺失诊断、平台执行失败和配置错误不是参数补齐问题，不应被错误地裁剪成一个“追问”。
- 该行为属于 OceanEngine 业务工具边界，不能通过修改 DeerFlow 受保护源码来实现通用化。
