<!-- OPENSPEC:START -->
# OpenSpec 指令

以下指令适用于在本项目中使用 OpenSpec 的 AI 编码助手。

当请求满足以下任一条件时，必须先打开 `@/openspec/AGENTS.md`：
- 提到规划、提案、规格、变更或计划（如 proposal、spec、change、plan 等）。
- 引入新能力、破坏性变更、架构调整，或较大的性能 / 安全工作。
- 需求不明确，需要在编码前确认权威规格。

通过 `@/openspec/AGENTS.md` 获取：
- 如何创建、Apply 和归档 OpenSpec 变更提案。
- 规格格式、中文输出约定和项目规范。
- `openspec apply` 阶段涉及设计或代码变更时必须使用 Superpowers 的硬性要求。

保留此托管区块，以便后续 `openspec update` 刷新指令。

<!-- OPENSPEC:END -->

## AI 治理基线
- 所有设计、代码和 skill 变更，只要会影响受版本控制的长期资产，必须先创建或更新 OpenSpec change，再进入 Apply / 实施。
- 最近的 `AGENTS.md` 优先，但任何子目录规则都不得绕过上面的 OpenSpec 硬约束。
- 包级 `AGENTS.md` 只覆盖“可执行 / 可维护源码包”；测试、mock、纯内容、生成目录，以及依赖 / 缓存目录不在这次治理范围内。
- DeerFlow 受保护源码包会在最近层级 `AGENTS.md` 中显式声明“这是 DeerFlow 源码；为方便后期合并，严禁任何修改”。
- 项目预留扩展点会在最近层级 `AGENTS.md` 中显式声明允许变更边界，但仍必须先走 OpenSpec。
- OpenSpec 的 `proposal.md`、`tasks.md`、`design.md`、`spec.md` 在写入前，必须先停下来向用户说明准备写哪些文件、各自准备改什么，并等待明确批准。
- OpenSpec 的 `proposal.md`、`tasks.md`、`design.md`、`spec.md` 完成一轮写入后，必须再次停下来向用户说明实际改了哪些文件和核心变更点，并等待明确批准；未获批准前不得继续下一轮 OpenSpec 文档写入，也不得继续后续流程。
- OpenSpec archive 前，必须先把本次需求对话中的长期规则、坑点、边界和扩展约束沉淀到合适层级的 `AGENTS.md`。
- OpenSpec archive 前，必须先停下来等待用户明确批准；未获批准前不得执行 `openspec archive <change-id> --yes`。
- 除 OpenSpec archive 阶段外，查询、设计、创建、翻译、改写、迁移、抽取或治理 skill 时，必须先使用 `codex/skills/skill-creator/`；若只是给 Codex 编码阶段使用，默认落到 `codex/skills/**`，不得直接改 `skills/public/**`。
- OpenSpec archive 完成后，必须再完成本次 change 的 git 提交，且该次提交备注必须使用中文。

# 仓库协作指南

## 适用范围与优先级
本文件适用于整个 `deer-flow/` 仓库。

- 在子目录工作时，优先遵循最近的 `AGENTS.md`。
- `backend/AGENTS.md` 与 `frontend/AGENTS.md` 在各自目录树内覆盖本文件。
- 若当前路径下没有更近的 `AGENTS.md`，则以本文件作为 Codex 默认指南。

## 按需加载
- 默认只加载最小上下文：本文件 + 当前任务直接需要的文件。
- 仅在触达对应模块时加载模块文档：
  - 后端任务：先读 `backend/AGENTS.md`，再读 `backend/CLAUDE.md` 中与改动相关的章节。
  - 前端任务：先读 `frontend/AGENTS.md`，再读 `frontend/CLAUDE.md` 中与改动相关的章节。
- 跨模块任务应分别加载前后端指南，且仅加载必要部分。
- 避免批量读取无关文档，保持上下文聚焦且稳定。

## 项目结构
- `backend/`：Python 后端（LangGraph 运行时、FastAPI Gateway、harness 包）。
- `frontend/`：Next.js 16 + React 19 Web 应用。
- `scripts/`：初始化、检查、启动、Docker 辅助脚本。
- `skills/`：DeerFlow 公共/自定义技能。
- `docs/`、`docker/`、`pr-build/`：文档、容器配置、CI 构建支撑。
- 根目录运行时配置文件：`config.yaml`、`extensions_config.json`、`.env`。

## 构建、测试与开发命令
除特别说明外，均在 `deer-flow/` 根目录执行。

- 根目录生命周期命令：
  - `make check`：检查必需工具。
  - `make install`：安装后端（`uv sync`）和前端（`pnpm install`）依赖。
  - `make dev`：启动全栈开发模式。
  - `make dev-pro`：网关模式（不启动 LangGraph Server 进程）。
  - `make stop`：停止运行中的服务。
- 后端（`deer-flow/backend`）：
  - `make dev`：启动 LangGraph Server。
  - `make gateway`：启动 FastAPI Gateway（端口 `:8001`）。
  - `make test`：运行后端测试（`pytest`）。
  - `make lint` / `make format`：`ruff` 检查与格式化。
- 前端（`deer-flow/frontend`）：
  - `pnpm dev`：启动 Next.js 开发服务（端口 `:3000`）。
  - `pnpm check`：执行 ESLint + TypeScript 检查。
  - `pnpm test`：运行单元测试（Vitest）。
  - `pnpm test:e2e`：运行端到端测试（Playwright）。

## 编码约定
- 后端：Python `>=3.12`，优先遵循 `ruff` 风格，保持导入与类型声明清晰。
- 前端：以 TypeScript 为主，保持 `@/*` 别名导入，通过 lint/typecheck。
- 以下生成目录除非任务明确要求，否则不要手工编辑：
  - `frontend/src/components/ui/`
  - `frontend/src/components/ai-elements/`
- 同一功能改动时，保持后端 API 与前端调用同步更新。

## 测试要求
- 对行为变更涉及的路径补充或更新测试。
- 交付前至少运行有针对性的检查：
  - 后端改动：`cd backend && make test`（或定向 `pytest`）。
  - 前端改动：`cd frontend && pnpm check` + 相关测试。
- 若完整测试集成本过高，需运行聚焦测试并明确说明已执行内容。

## Agent 相关说明
- `backend/AGENTS.md` 将架构细节委托到 `backend/CLAUDE.md`。
- 前端架构说明位于 `frontend/AGENTS.md`。
- 涉及前后端联动时，优先使用根目录命令（如 `make dev`、`make stop`）保障服务协同。

## 已归档变更维护约束
- 本地推创建项目流程默认项目名与默认单元名使用同一命名规则：`yyyyMMdd` + 地域 + 定向类型 + 年龄 + 可选投手姓名首字母；拿不到投手姓名时不得追加 `X`、`None`、`null`、`未知` 或其它占位后缀，用户显式 `name` / `unit_name` 必须优先保留。
- 前端 Figma 静态资源引用应统一通过 Figma CDN helper 和 `NEXT_PUBLIC_FIGMA_ASSET_BASE_URL` 管理；不要在组件中新增长期 `/images/figma/...` 本地 public 路径引用。
- Nginx 根路径 `/` 必须显式跳转到 `/workspace/chats/new`，且不得影响 `/api/`、`/health`、ACME challenge 和其它前端路由代理。
- 前端登录态建立后应拉取 `/user/availableAgents`，按 `selected === 1` 识别 `1001` AI 智能对话、`1002` AI 智能投流、`1003` AI 内容工厂；无对应权限时必须锁定对话或隐藏入口。
- 消息点赞/点踩使用线程反馈接口提交 `rating: "positive"` / `rating: "negative"` 并回显历史状态；`401 Unauthorized` 不应弹出误导性的反馈失败 toast。
- 隐藏工作区“智能体”菜单或消息分享按钮时，按既有做法保留原 JSX 注释，不删除相关路由、API 或业务能力。
- DB 配额检查中缺少 `lumax_user_quota` 或 `total_quota` 无效必须按 Token 总配额不足拒绝调用；结算阶段不得自动创建 unlimited 配额来掩盖配置缺失。
- 会话归属保存中 `lumax_conversation.username` 优先使用认证 claims 的 `nickname`，`dept_id` 取 `deptIds` 首值；缺失时按既有回退规则处理，不额外查询用户信息。
- 聊天 IP 动画状态切换应保留 `thinkingtoresult` 和 `canceltothinking` 过渡、固定舞台容器、交叉淡入淡出、GIF 预加载和状态校准表；不要直接硬切不同画布 GIF。
- 普通 assistant 正文的可见性清洗不得因出现“技能”等普通词汇整条隐藏；summary、内部 tool call、structured clarification 原始 tool message 和内部 reasoning 仍必须隐藏或清洗。

## 巨量本地推 Skill 边界
- 本地推“项目管理”请求使用 `oceanengine-local-project` / `oceanengine_local_project`，本地推“单元管理”请求使用 `oceanengine-local-unit` / `oceanengine_local_unit`，本地推“素材管理”请求使用 `oceanengine-local-material` / `oceanengine_local_material`；不要把项目、单元、素材管理能力互相混入。
- 本地推项目、单元、素材请求必须先读取对应 `SKILL.md`，再调用 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material` 原生业务工具；缺少必填参数、枚举值或批量项字段时也不得直接调用 `ask_clarification`，必须由原生业务工具参数校验器返回 `data.clarification` 和单问题中文追问。
- 本地推项目、单元、素材请求不得在主 Agent 中直接调用 `nacos-mcp-router_search_mcp_server`、`nacos-mcp-router_add_mcp_server`、`nacos-mcp-router_use_tool` 或其它 MCP Router 管理工具绕过原生业务工具；原生业务工具返回 MCP 缺失、注册或平台失败时，应直接按其 `user_visible_text` 或错误摘要回复用户。
- 端到端创建本地推投流项目请求如果同时包含投手、营销场景、投放目标、单元类型、投放内容、定向/预算/出价或素材要求，应优先使用 `oceanengine_local_project_create_flow` 编排项目、素材和单元链路；不得先用 `oceanengine_local_material` 查询素材库或上传视频替代创建流程入口。
- 本地推单元管理必须通过 `oceanengine_local_unit` 原生业务工具和 `rules/*.json` 本地校验链路执行，不得让主 Agent 直接调用受保护的 `localUnit*`、`localProductGetByPoiIds` 或 `localPromotionRejectReasonBatchGet` MCP 工具。
- 本地推素材管理必须通过 `oceanengine_local_material` 原生业务工具和 `rules/*.json` 本地校验链路执行，不得让主 Agent 直接调用受保护的 `localFileUploadTaskCreate`、`localFileVideoUploadTaskList`、`localFileVideoUpload`、`localFileVideoGet`、`localFileVideoAwemeGet`、`localFileCarouselList` 或 `localImageUpload` MCP 工具。
- 创建项目流程需要视频且用户说“从素材库选择”时，应由 `oceanengine_local_project_create_flow` 在流程内调用素材原生工具查询候选；素材库为空时必须以当前素材问题单点阻断，不得继续追加地域编码、门店、商品或其它缺失项追问，也不得把空素材库结果当作流程成功。
- 素材上传类请求只允许使用用户在当前任务中明确提供或授权的 `video_url`、`video_file_path`、`image_file_path`、签名和文件元数据；不得扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录来猜测素材。
- 本地推素材上传浏览器验收必须使用真实用户自然语言和真实附件控件，不得用 direct MCP、curl、SDK、跳过 MCP 的 Java Controller HTTP / 开放平台 API 调用、脚本上传或浏览器 DevTools 构造请求替代验收。
- 本地推视频素材判重只以 `localFileVideoUpload` MCP 返回信息为准；当 MCP 明确返回重复、已存在、已上传、幂等命中或已有 `materialId` / `videoId` 且带重复语义时，用户可见结果应提示“素材已上传”。
- `localFileVideoUpload` MCP 未返回可确认素材结果时，不得编造素材 ID、视频 ID、上传成功或“素材已上传”；应说明上传接口未返回可确认的素材结果，并提示需要通过素材中心或后续查询确认。
- 新增视频素材稳定性验收必须使用内容签名不同的视频变体，并用素材中心数量增长作为辅助确认；仅修改文件名不能证明新增素材成功。
- 同步 `oceanengine-local-material` 官方文档时，请求参数和响应字段必须一起校验；响应字段需同步到 `rules/*.json` 的 `output.response_fields` 与 `references/*.md` 的 `## 响应字段` 表，动态网页优先通过 `skiff/api/doc/client/node/get/` 抽取官方内容。
- `oceanengine-local-material` 的“获取视频素材评估标签”接口目前在 `platform-agent-biz` 未暴露 MCP tool；应返回中文缺失诊断，不得臆造工具名，也不得绕过 MCP 改用 HTTP API、curl 或 SDK 直连。
- 对 `oceanengine-local-material` 的 MCP 缺失能力，仍必须先执行本地参数校验；只有参数通过后才返回 MCP 缺失诊断，不得用“工具缺失”掩盖必填、枚举、数组数量或分页边界错误。
- `oceanengine-local-material` 获取图文素材时，标题关键词必须保留官方字段 `keyword` 进入平台链路；测试环境实测把关键词映射为 `itemTitle` 会触发平台时间参数异常。
- 单元管理文案应沿用官方术语“单元类型”，不要写成“广告类型”。
- `oceanengine_local_project`、`oceanengine_local_unit`、`oceanengine_local_material` 参数校验失败时，用户可见结果一次只追问 `data.user_visible_text` 中的一个问题；不得把其它缺失参数、枚举或条件必填项追加到同一轮追问。内部可保留完整错误计数用于诊断。
- 对齐巨量官方开发文档时，请求参数和响应字段都必须同步修改；`references/*.md` 应记录 `## 响应字段`，`rules/*.json` 应维护 `output.response_fields`，用于成功响应展示和未映射字段诊断。
- 本地推商品投流项目创建或更新缺少 `product_id` 时，若已有 `local_account_id` 和 `local_delivery_scene`，应由 `oceanengine_local_project` 原生业务工具在 `create-project` / `update-project` 校验链路中动态查询可投商品候选，返回 `data.clarification.input_control.type=choice_cards` 与中文 `data.user_visible_text`；不得把商品候选静态写入 `rules/*.json`，也不得先绕开创建/更新链路单独调用商品列表能力替代补齐。
- OceanEngine 原生业务工具为 `rules/*.json` 静态 `enum` / `item_enum` 生成 `data.clarification.input_control.type=choice_cards` 时，候选 `value`、`label` 与顺序必须来自当前 capability 的规则文件，并按当前 payload 的 `forbidden_when`、`mutually_exclusive` 等依赖禁止规则做确定性过滤；不得展示当前已选参数组合下必然非法的枚举值。
- OceanEngine 原生业务工具为 `boolean` 缺参生成结构化追问时，应使用 `choice_cards` 单选卡片展示“是 / 否”，不得退回普通文本输入框。
- OceanEngine 静态枚举稳定性不适用于平台实时查询候选；商品、门店、抖音号、人群包、营销页、组件等动态候选只验证结构、链路与用户可见清洗，不要求固定候选集合，也不得为了测试稳定把平台候选写入 `rules/*.json` 的静态枚举。
- OceanEngine 原生业务工具返回 `data.clarification.input_control` 时，Gateway 用户可见接口必须保留为 `structured_clarifications` 或等价结构化字段，并保留 `value`、`label`、`description`、`metadata` 与候选顺序；原始工具消息、内部 tool name、MCP tool name、payload JSON、trace 和平台请求日志 ID 仍必须隐藏。
- Gateway 用户可见出口向前端历史消息返回结构化追问时，必须把 `structured_clarifications` 保留在对应消息的 `additional_kwargs` 或等价消息级字段上；不得只挂在外层 payload，避免历史消息列表只读取 `messages` 时丢失候选卡片。
- Gateway 输出 `choice_cards.options[].value` 时必须使用前端可稳定消费的字符串值；若原始业务 ID 为数字，原始数字应保留在 `metadata` 中，不得丢失。
- OceanEngine 原生业务工具中同时声明 `page` 与 `page_size` 的分页 MCP 接口，用户未指定分页时统一默认 `page=1`、`page_size=20`；用户显式指定 `page` 或 `page_size` 时必须保留原值交给业务工具校验，不得改写、截断或回退到默认值。
- 本地推项目创建的 `bid_type` 必须按业务场景在本地校验链路中拦截：`external_action=SHOW` 仅支持 `MANUAL`，直播 `CONTENT_HEAT` / `PRODUCT_PAY` 仅支持 `SMART`，非 UBL `EXTERNAL` 仅支持 `STABILIZE_COSTS` / `MAX_CONVERSION`；非法组合不得透传到 MCP 后等待平台返回 `code=40000`。
- OceanEngine 原生业务工具直连 Nacos MCP 服务时，必须使用 `config.yaml` 中的 Nacos namespace 查询 MCP detail 和实例，并优先使用 Nacos 返回的 `backendEndpoints[]` / `frontendEndpoints[]` 中的地址、端口和 `path` 组成实际 MCP endpoint；只有 endpoint 自身缺少 `path` 时才可用 `remoteServerConfig.exportPath` 兜底，不得写死或默认兜底到本机 `127.0.0.1:18000`。
- OceanEngine 原生业务工具优先走 Nacos MCP Router 时，如果 Router 返回目标 MCP server 不存在或未注册，但 Nacos detail 和实例可解析出真实 streamable HTTP endpoint，应回退到直连 Nacos endpoint；不得直接把 Router 的 `mcp server not found` 当作最终平台失败。
- OceanEngine 原生业务工具直连 streamable HTTP MCP endpoint 时，必须先发送 `initialize` 获取 `Mcp-Session-Id`，再发送 `notifications/initialized`，后续 `tools/list` / `tools/call` 必须携带该 session header；不得把缺少 session 导致的 400 误判为 endpoint 地址错误。
- OceanEngine 本地推意图路由要优先识别明确业务对象：包含“项目”的商品投流创建/更新请求必须走项目管理，即使文本中同时出现“短视频/图文”或“单元类型”；“单元类型”是项目创建字段，不应单独触发单元管理。
- 本地推项目管理浏览器验收必须使用真实用户自然语言输入，不得在浏览器输入中点名 `oceanengine-local-project`、`oceanengine_local_project`、`capability`、`payload_json`、`dry_run`、底层 MCP tool 名、脚本路径或“直接调用某工具”等提示。
- 本地推项目管理浏览器验收必须证明真实 Agent、原生业务工具和 MCP 接口链路被触发；dry-run、mock 成功、本地校验成功、curl、SDK、脚本直连或 MCP 直连只能作为定位证据，不能替代浏览器验收成功标准。
- 验收本地推动态候选卡片时，应使用创建 / 更新请求中缺少对应动态字段且前置参数已足够的自然语言，让原生业务工具在参数校验链路中补齐候选；如果用户明确说“先给候选列表”，Agent 可能合理路由到只读列表查询并返回普通列表文本，这不能证明创建 / 更新缺参卡片链路。
- 本地推项目管理用户可见结果不得展示平台请求日志 ID、原始 JSON 包装或内部 trace；列表类结果应优先展示真实业务 ID 与名称，必要时再补充状态、分页和失败原因。
- 用户可见对话结果不得展示内部 reasoning summary、`SESSION INTENT`、`SUMMARY`、skill 文件路径、MCP Router 管理工具名、底层 MCP tool 名、`user_visible_text`、`reply_guidance`、`payload_json` 或内部参数字段；这类清洗和可见性控制必须放在 Gateway 用户可见出口、根目录 `tools/` 扩展点或其它明确项目扩展点，不得放入 `backend/packages/harness/deerflow/**` 受保护源码包。
- Gateway 用户可见清洗必须同时覆盖普通 `dict` payload 与 LangChain `BaseMessage` / `HumanMessage(name="summary")` 对象；不得让 `json.dumps(default=str)` 或等价 fallback 把内部 summary 对象字符串化后泄漏到 history、state、stream、run stream 或普通 UI。
- 本地推项目管理测试中，投放账号使用业务字段 `local_account_id` 表达；不得把 `advertiser_id` 或其他平台字段混作本地推账号字段。
- OceanEngine 原生业务工具主实现放在根目录 `tools/`；`managed_mcp_guard` 只保留 `tools.managed_mcp_guard` 这一条主路径，不保留 `deerflow.tools.managed_mcp_guard` 模块路径。
- OceanEngine 运行时守卫、业务 middleware、响应清洗和原生工具链路等项目业务专用逻辑必须放在根目录 `tools/`、Gateway 接入层或其它明确项目扩展点；不得新增、恢复或长期保留在 `backend/packages/harness/deerflow/**` 受保护源码包中。
- `oceanengine_local_project`、`oceanengine_local_unit`、`oceanengine_local_material` 只允许通过根目录 `tools.oceanengine_local_*` 路径注册和引用；不得新增或恢复 `backend/packages/harness/deerflow/tools/oceanengine_local_*` 同名 wrapper，也不得依赖 `deerflow.tools.oceanengine_local_*` 兼容导入路径。
- Docker hot reload 后端镜像必须复制根目录 `tools/` 到 `/app/tools`，且启动 Gateway 时 `PYTHONPATH` 必须包含 `/app:/app/backend`，确保 `config.yaml` 中的 `tools.oceanengine_local_*` 路径在容器内可导入；不得通过安装第三方 `tools` 包替代。
- 生产 Docker Gateway 镜像必须把根目录 `tools/` 复制到 `/app/tools`；`docker/docker-compose.yaml` 的 Gateway 服务必须使用 `PYTHONPATH=/app:/app/backend`，并同时提供 `/app/config.yaml`、`/app/skills` 与 `DEER_FLOW_PROJECT_ROOT=/app`，确保 OceanEngine MCP 运行时能以 `/app` 作为项目根目录读取配置。

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lumax** (26104 symbols, 40915 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/lumax/context` | Codebase overview, check index freshness |
| `gitnexus://repo/lumax/clusters` | All functional areas |
| `gitnexus://repo/lumax/processes` | All execution flows |
| `gitnexus://repo/lumax/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
