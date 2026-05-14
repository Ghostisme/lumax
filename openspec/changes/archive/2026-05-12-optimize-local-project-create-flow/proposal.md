# 优化本地推创建项目流程

## Why

当前 `oceanengine-local-project` 已经按官方 `localProjectCreate` 接口维护了 `create-project` 的 65 个字段、必填项、条件必填、条件禁止和出价方式场景校验；`oceanengine-local-material` 与 `oceanengine-local-unit` 也分别承担素材上传/查询和单元素材配置能力。

但用户发起“创建项目”时，实际业务流程不只是一次 `localProjectCreate` 调用：需要先按投手、营销场景、投放目标、单元类型、投放内容、定向、预算、出价和素材要求逐步收集信息；再根据场景填充固定默认项；最后在项目创建后衔接素材库视频选择和单元素材配置。现有能力如果只按底层接口缺参顺序追问，容易出现追问顺序不符合业务习惯、固定默认项未自动落地、素材/单元能力与项目创建边界混淆的问题。

## What Changes

- 为“创建项目”增加业务编排规格：先收集投手和核心业务选择，再生成 `create-project` 官方 payload。
- 明确投手是流程必填业务信息，用于项目/单元命名和验收记录；除非官方规则存在对应字段，否则不得作为自造字段透传给 `localProjectCreate`。
- 为用户定向、排期与预算定义默认策略；用户显式给出的值必须优先保留并交给原生业务工具校验。
- 获取线索场景增加专门流程：优化目标、引导页面、留资组件、抖音号、AIGC 动态创意、标题和投放卡片必须按官方字段和素材/单元边界处理。
- 视频素材流程与项目创建解耦：上传、素材库查询和视频候选选择必须走 `oceanengine_local_material`；项目创建成功后才可把已选视频交给 `oceanengine_local_unit` 配置单元素材。
- 单元名称生成规则改为业务默认：`yyyyMMdd` + 地域 + 定向类型 + 年龄 + 投手姓名首字母大写；如品牌有额外要求，再由用户明确覆盖。
- 明确团购成交默认要求 10 条视频，其它投放目标默认要求 3 到 5 条视频；不足时返回单问题中文追问或结构化候选补齐。
- 对当前规则未暴露的业务项，例如 `智能定向拓展`、`搜索出价系数`，Apply 阶段必须先确认官方字段落点；未确认前不得自造 MCP payload 字段。

## Non Goals

- 不在提案阶段编写或修改功能代码。
- 不绕过 `oceanengine_local_project`、`oceanengine_local_material` 或 `oceanengine_local_unit` 原生业务工具。
- 不直接调用受保护 MCP tool、curl、SDK 或 HTTP API 替代原生业务工具。
- 不修改 `frontend/**` 控件展示。
- 不修改 `skills/public/**`。
- 不把素材上传安全边界放宽为扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录。
- 不在 `backend/packages/harness/deerflow/**` 受保护源码包新增 OceanEngine 业务专用逻辑。

## Scope

本次变更覆盖三个既有规格：

- `oceanengine-local-project-template-migration`：创建项目业务流程、默认定向、排期预算、场景化出价、线索场景、结构化补齐和验收要求。
- `oceanengine-local-material-management`：创建项目流程中的视频上传、素材库视频选择和素材安全边界。
- `oceanengine-local-unit-management`：项目创建后的单元命名、视频素材数量、标题、卡片和封面配置。

## Impact

- Apply 阶段预计只改根目录 `tools/`、`skills/custom/oceanengine-local-*/`、Gateway 接入层或其它明确项目扩展点。
- Apply 阶段如需要修改函数、类或方法，必须先按 GitNexus 规则执行影响分析。
- Apply 阶段涉及设计、代码、测试或行为变更时，必须使用 Superpowers。
- 验收必须使用真实浏览器自然语言路径，不能通过 dry-run、mock 成功、curl、SDK、脚本直连或 MCP 直连替代主验收。

## Risks

- 将业务默认项自动落地后，可能改变缺参追问顺序；必须继续遵守“一次只追问一个问题”。
- 部分业务项目前不在 `create-project` 官方字段中；实现阶段如果臆造字段，会污染 MCP payload 并导致平台错误。
- 素材和单元联动跨三个原生业务工具，必须保持边界清晰，避免主 Agent 直接调用受保护 MCP tool。
- AI 标题、AI 投放卡片和视频分析能力依赖可用素材元数据或已授权视频内容；无法分析时必须返回中文说明或单问题追问，不得编造素材结论。

