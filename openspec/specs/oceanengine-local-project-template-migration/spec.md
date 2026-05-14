# oceanengine-local-project-template-migration Specification

## Purpose
TBD - created by archiving change verify-oceanengine-local-project-browser-acceptance. Update Purpose after archive.
## Requirements
### Requirement: 项目管理浏览器验收必须覆盖全部官方接口

`oceanengine-local-project` SHALL 在浏览器对话入口完成项目管理模块全接口自然语言验收，覆盖 `rules/index.json` 中声明且与官方 `doc_id=1807977111009572` 文档树对齐的 16 个 capability，并在测试前先形成逐接口高覆盖测试用例矩阵。矩阵 SHALL NOT 为每个接口指定固定测试用例数量，而 SHALL 按接口已声明规则、官方边界和可执行业务路径持续补充用例，直到覆盖证据充分。

#### Scenario: 验收前建立 16 接口覆盖矩阵

- **GIVEN** Apply 阶段准备测试 `oceanengine-local-project`
- **WHEN** 测试人员开始浏览器验收前
- **THEN** 测试矩阵 SHALL 包含 `create-project`、`update-project`、`list-projects`、`get-project-detail`、`batch-update-project-status`、`list-promotable-pois`、`list-promotable-products`、`list-authorized-awemes`、`list-custom-audiences`、`get-poi-ids-by-multi-poi-id`、`list-tool-packs`、`get-tool-pack-detail`、`list-market-pages`、`get-market-page-detail`、`list-consult-awemes` 和 `batch-update-project-week-schedule`
- **AND** 每个 capability SHALL 列出需要覆盖的正向真实调用、普通必填、条件必填、条件禁止、类型、枚举、数组、分页、金额、长度、时间、批量项、输出展示和失败恢复维度
- **AND** 测试人员 SHALL 先完成覆盖矩阵登记，再执行浏览器提交

#### Scenario: 覆盖充分性不按固定数量判断

- **GIVEN** 某 capability 的浏览器验收正在执行
- **WHEN** 测试人员判断该 capability 是否完成
- **THEN** 系统 SHALL 根据该 capability 的已声明字段、条件规则、枚举值、边界限制、真实调用路径和输出展示证据判断覆盖是否充分
- **AND** 系统 SHALL NOT 因达到某个固定用例数量就自动认为覆盖完成
- **AND** 如果发现未覆盖字段、未覆盖枚举、未覆盖条件分支或未覆盖边界，测试人员 SHALL 继续补充用例并执行

#### Scenario: 读取类接口完成真实调用验收

- **GIVEN** 某项目管理 capability 属于读取类接口
- **WHEN** 测试人员通过浏览器对话页面验收该 capability
- **THEN** 正向用例 SHALL 触发真实 `oceanengine_local_project` 业务工具调用
- **AND** 证据 SHALL 显示业务工具内部调用对应 `platform-agent-biz` MCP tool
- **AND** 用户可见结果 SHALL 以中文展示平台返回的数据摘要、空列表说明或平台业务失败原因

#### Scenario: 增改和批量接口完成后置确认验收

- **GIVEN** 某项目管理 capability 属于创建、更新、批量状态变更或批量投放时段变更
- **WHEN** 测试人员通过浏览器对话页面执行正向用例
- **THEN** 用例 SHALL 使用测试环境可控数据真实调用对应 MCP tool
- **AND** 系统 SHALL 通过平台响应、详情查询、列表查询或规则配置声明的后置确认方式证明目标项目、状态或投放时段符合预期
- **AND** 若平台返回业务失败，验收记录 SHALL 区分测试数据问题、平台业务限制、环境问题和代码 bug

### Requirement: 项目管理浏览器测试输入必须模拟真实用户表达

浏览器验收 SHALL 使用自然语言业务请求触发项目管理能力。测试输入 SHALL NOT 显式指定 skill、业务工具、capability、底层 MCP tool、脚本路径或 JSON tool payload 来降低路由难度。

#### Scenario: 浏览器输入禁止点名内部工具

- **GIVEN** 测试人员准备在浏览器对话框提交项目管理请求
- **WHEN** 编写浏览器输入内容
- **THEN** 输入 SHALL NOT 包含 `oceanengine-local-project`
- **AND** 输入 SHALL NOT 包含 `oceanengine_local_project`
- **AND** 输入 SHALL NOT 包含 `capability`、`payload_json` 或 `dry_run`
- **AND** 输入 SHALL NOT 包含底层 MCP tool 名，例如 `localProjectCreate`、`localProjectList`、`localPoiGet`、`localToolPackListGet`
- **AND** 输入 SHALL NOT 要求 Agent “直接调用某工具”或“使用某 skill”

#### Scenario: 浏览器输入保留业务参数

- **GIVEN** 某用例需要账号、项目 ID、门店 ID、商品 ID、页码、预算、出价、投放时段、营销场景、营销目的、枚举中文含义或批量数组
- **WHEN** 测试人员编写自然语言输入
- **THEN** 输入 MAY 包含本轮明确提供或前序测试真实获得的业务参数
- **AND** 输入 SHALL 以用户业务意图描述目标接口
- **AND** 输入 SHALL NOT 直接粘贴 `oceanengine_local_project` 的 JSON tool payload 作为验收输入

#### Scenario: 证据记录允许出现内部标识

- **GIVEN** 浏览器输入已经按自然语言提交
- **WHEN** 测试人员记录日志、trace、线程历史或工具调用证据
- **THEN** 证据 MAY 包含 `oceanengine_local_project`、capability 和 MCP tool 名
- **AND** 这些内部标识 SHALL 只用于证明真实调用路径
- **AND** 证据 SHALL NOT 被反向复制到后续浏览器输入中降低测试难度

### Requirement: 项目管理浏览器验收不得通过绕过真实接口作弊

浏览器验收 SHALL 证明真实浏览器、真实 Agent 路径、原生业务工具和真实 `platform-agent-biz` MCP 接口调用链路可用。系统 SHALL NOT 通过指定空工具、mock 成功、不调用真实接口、脚本直调、curl、HTTP API、SDK 或直接 MCP 调用替代主验收。

#### Scenario: 正向用例必须有真实接口调用证据

- **GIVEN** 某正向用例已经在浏览器提交
- **WHEN** 测试人员判断该用例是否通过
- **THEN** 证据 SHALL 显示该轮进入 `oceanengine_local_project`
- **AND** 证据 SHALL 显示业务工具内部发起对应 MCP tool 调用，或在本地校验通过后收到平台可追踪业务响应
- **AND** 仅有本地 dry-run、脚本输出、curl 输出、mock 响应或模型口头说明 SHALL NOT 计入正向成功

#### Scenario: 负向用例必须证明调用被正确拦截

- **GIVEN** 某负向或边界用例预期由本地规则拦截
- **WHEN** 浏览器请求完成
- **THEN** 用户可见结果 SHALL 返回中文校验错误
- **AND** 证据 SHALL 显示对应 MCP tool 未被调用
- **AND** 如果 MCP tool 被调用或平台才发现本地可判断错误，该用例 SHALL 标记为失败并触发修复

#### Scenario: 环境阻断不能冒充接口通过

- **GIVEN** 浏览器验收因登录、前端、Gateway、agent runtime、MCP Router、`platform-agent-biz` 或网络环境不可用而失败
- **WHEN** 根因确认属于环境阻断
- **THEN** 该轮 SHALL 记录为环境失败
- **AND** 该轮 SHALL NOT 计入 capability 正向成功或负向校验覆盖
- **AND** 环境恢复后 SHALL 重新执行受影响用例

### Requirement: 项目管理浏览器验收参数必须多样化

测试矩阵 SHALL 明确每条用例的参数差异点，并通过不同项目、门店、商品、分页、筛选、枚举、时间范围、预算、出价、投放时段、批量数组和布尔值组合提高覆盖率，避免使用同一组参数反复提交。

#### Scenario: 读取类接口参数多样化

- **GIVEN** 测试人员验收项目列表、详情、门店、商品、抖音号、人群包、留资组件、营销页或私信接待抖音号查询类 capability
- **WHEN** 编写和执行查询类测试用例
- **THEN** 用例 SHALL 覆盖不同分页或页大小
- **AND** 用例 SHALL 覆盖该接口规则中适用的筛选条件、数组筛选、枚举筛选或依赖前序接口返回 ID 的查询
- **AND** 多条正向用例 SHALL NOT 使用完全相同的参数组合

#### Scenario: 增改和批量接口参数多样化

- **GIVEN** 测试人员验收创建、更新、批量状态变更或批量投放时段变更 capability
- **WHEN** 编写和执行变更类测试用例
- **THEN** 用例 SHALL 覆盖该接口规则中适用的不同项目名、营销场景、营销目的、投放内容、预算、出价、投放时段、状态操作或批量数组组合
- **AND** 测试项目 SHALL 使用本轮明确创建或授权的测试数据
- **AND** 后续更新、详情、状态和投放时段用例 SHALL 记录与创建项目用例的依赖关系

#### Scenario: 重复参数不能充当覆盖率

- **GIVEN** 同一 capability 已存在正向用例
- **WHEN** 新用例只重复相同账号、相同项目、相同筛选、相同分页、相同批量数组或相同投放时段
- **THEN** 新用例 SHALL NOT 作为新的覆盖证据
- **AND** 测试人员 SHALL 调整至少一个实质业务参数后再记录为新覆盖

### Requirement: 项目管理浏览器验收状态必须逐用例维护

浏览器验收 SHALL 以单条用例作为最小完成单元。任务状态、验收记录和接口级汇总 SHALL 反映真实执行进度，不得在未逐条完成证据记录时批量标记完成。

#### Scenario: 单条用例完成后才允许勾选

- **GIVEN** `tasks.md` 中存在某个浏览器验收用例或覆盖项 checkbox
- **WHEN** 测试人员完成该用例的浏览器提交
- **AND** 验收记录已经保存线程 ID 或 trace ID、业务工具调用证据、MCP 调用或拦截证据、用户可见结果摘要和通过或失败结论
- **THEN** 该用例或覆盖项 checkbox MAY 标记为完成
- **AND** 未执行或缺少证据的用例 SHALL 保持未完成

#### Scenario: 接口级完成依赖覆盖闭环

- **GIVEN** 某项目管理 capability 下仍有未覆盖字段、未覆盖枚举、未覆盖条件分支、未覆盖边界或待重测用例
- **WHEN** 测试人员汇总该 capability 的验收状态
- **THEN** 该 capability SHALL NOT 标记为整体完成
- **AND** 汇总 SHALL 列出剩余未覆盖项或待重测项
- **AND** 汇总 SHALL 区分正向成功、负向校验通过、平台业务失败、环境失败和待重测状态

#### Scenario: 修复后重测按覆盖项重置状态

- **GIVEN** 某用例失败后实施人员完成修复
- **WHEN** 该修复影响同一 capability 的多个覆盖项
- **THEN** 受影响覆盖项 SHALL 标记为待重测
- **AND** 这些覆盖项 SHALL 在重新通过浏览器提交并记录证据后才可再次标记完成
- **AND** 受影响 capability 的覆盖结论 SHALL 按重测后的结果重新计算

### Requirement: 项目管理浏览器验收发现问题后必须修复并重测

浏览器验收发现工具未被选择、校验绕过、MCP guard 绕过、结果展示异常、认证失败、环境缺失、真实接口调用失败或平台返回可由本地避免的业务错误时，实施人员 SHALL 先定位根因并修复，再重新执行受影响用例组。

#### Scenario: 调用路径异常后修复重测

- **GIVEN** 浏览器用例已经提交
- **WHEN** 证据显示主 Agent 未经过 `oceanengine_local_project`、直接调用受保护项目管理 MCP tool、或未按规则执行本地校验
- **THEN** 实施人员 SHALL 定位并修复工具注册、skill 导航、调用保护或参数整理问题
- **AND** 修复后 SHALL 重新执行受影响 capability 的浏览器用例组
- **AND** 受影响 capability 的覆盖项 SHALL 从待重测状态重新计算

#### Scenario: 展示或输出异常后修复重测

- **GIVEN** 业务工具已返回结构化结果
- **WHEN** 页面最终回复只展示英文 API 字段名、英文枚举值、原始 JSON、未翻译错误或缺少关键中文结果摘要
- **THEN** 实施人员 SHALL 修复结果压缩、中文摘要或前端展示问题
- **AND** 修复后 SHALL 重新执行同类浏览器用例
- **AND** 验收记录 SHALL 保存修复前失败摘要和修复后中文展示证据

#### Scenario: 平台业务失败分层处理

- **GIVEN** 浏览器正向用例真实调用了目标 MCP tool
- **WHEN** 平台返回业务失败
- **THEN** 测试人员 SHALL 判断失败是否由测试数据缺失、平台业务限制、环境问题或代码 bug 导致
- **AND** 如果失败可通过补齐测试数据或修复代码解决，受影响用例 SHALL 修复后重测
- **AND** 如果失败属于稳定平台限制或平台内部错误，验收记录 SHALL 保存真实调用证据和中文失败原因，且该轮 SHALL NOT 被伪造成业务成功

### Requirement: 项目管理参数校验失败一次只追问一个问题

`oceanengine_local_project` SHALL 在参数校验失败时只向 Agent 和用户暴露首个可行动中文问题。内部校验 MAY 继续收集完整错误列表用于计数、日志和测试，但面向 Agent 的结构化结果 SHALL NOT 同时暴露多个缺参问题，避免最终回复一次追问多个参数。

#### Scenario: 多个普通必填缺失时只展示首个问题

- **GIVEN** 用户请求命中 `oceanengine_local_project`
- **AND** 本地参数校验发现多个普通必填字段缺失
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.user_visible_text` SHALL 只包含规则顺序中的第一个缺失字段中文问题
- **AND** `errors` SHALL 只保留该第一个可见错误
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量

#### Scenario: 用户补充后下一轮追问下一个问题

- **GIVEN** 上一轮项目管理请求因缺少首个参数而失败
- **AND** 用户在下一轮补充了该参数
- **WHEN** Agent 使用更新后的参数再次调用 `oceanengine_local_project`
- **THEN** 本地校验 SHALL 重新计算缺失项
- **AND** 如果仍缺少其它参数，用户可见结果 SHALL 只展示新的首个缺失参数问题
- **AND** 系统 SHALL NOT 在同一轮把剩余缺失参数合并成多个追问

#### Scenario: Skill 入口不得直接汇总多个缺失项

- **GIVEN** 用户通过浏览器自然语言请求创建、更新或查询本地推项目
- **AND** 用户缺少多个官方请求参数
- **WHEN** 主 Agent 已识别请求属于 `oceanengine-local-project`
- **THEN** 主 Agent SHALL 先调用 `oceanengine_local_project` 原生业务工具执行本地校验
- **AND** 主 Agent SHALL NOT 直接调用 `ask_clarification` 自行汇总多个缺失项
- **AND** 最终用户可见结果 SHALL 只展示一个中文补充问题

#### Scenario: 非参数补齐类失败不被改写为追问

- **GIVEN** `oceanengine_local_project` 已通过本地参数校验
- **WHEN** 失败原因是 MCP 工具缺失、MCP 调用失败、平台业务失败、后置确认失败或响应展示异常
- **THEN** 业务工具 SHALL 按现有中文诊断展示失败原因
- **AND** 系统 SHALL NOT 将这些失败裁剪成单个参数追问
- **AND** 系统 SHALL NOT 要求用户补充与官方请求参数无关的信息

### Requirement: 项目管理 MCP 调用必须通过 Nacos 解析真实服务端点

`oceanengine-local-project` 在通过原生业务工具调用 `platform-agent-biz` 项目管理 MCP tool 前，SHALL 以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源解析目标 MCP server 的实际地址、端口和路径。业务工具和项目管理脚本 SHALL NOT 将 `127.0.0.1:18000` 或其它本机固定 Router 地址作为默认业务兜底端点。

#### Scenario: Nacos 解析到项目管理 MCP 服务端点

- **GIVEN** 用户请求命中 `oceanengine-local-project` 中任一需要 MCP 调用的 capability
- **AND** 本地参数校验已通过
- **AND** Nacos 中存在 `platform-agent-biz` 并能解析出实际 MCP endpoint
- **WHEN** 原生业务工具或项目管理脚本调用目标项目管理 MCP tool
- **THEN** 调用 SHALL 发送到 Nacos 解析出的实际 MCP endpoint
- **AND** payload SHALL 继续按项目管理 rule 中的 MCP 字段映射构造
- **AND** 系统 SHALL NOT 使用 `http://127.0.0.1:18000/mcp/` 作为默认业务兜底地址

#### Scenario: Nacos 未注册项目管理目标 MCP server

- **GIVEN** 用户请求命中项目管理 capability
- **AND** 本地参数校验已通过
- **WHEN** 系统无法从 Nacos 或 DeerFlow Nacos MCP 配置解析到 `platform-agent-biz`
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明 Nacos 中未找到目标 MCP server 或配置不可用
- **AND** 系统 SHALL NOT 继续请求本机固定 Router 地址
- **AND** 系统 SHALL NOT 改用 curl、SDK、HTTP API、mock 或其它 MCP server

#### Scenario: 项目管理目标 MCP endpoint 不可达

- **GIVEN** Nacos 已返回 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 本地参数校验已通过
- **WHEN** 系统连接该 endpoint 失败、超时或返回不可用错误
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明解析到的 MCP 服务不可达
- **AND** 失败结果 SHALL NOT 声称项目管理操作已完成
- **AND** 系统 SHALL NOT 自动切换到本机固定 Router、curl、SDK、HTTP API 或 mock

#### Scenario: 项目管理目标 MCP tool 缺失

- **GIVEN** Nacos 已解析到 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 目标项目管理 capability 声明了 `mcp_tool_name`
- **WHEN** 解析到的 MCP 服务未暴露该 tool
- **THEN** 原生业务工具或项目管理脚本 SHALL 返回中文失败诊断，说明目标 MCP tool 未注册或不可用
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用其它 tool 或其它调用协议

### Requirement: 项目管理创建项目必须本地校验出价方式适用场景

`oceanengine_local_project` 在执行 `create-project` 时，SHALL 在调用 `platform-agent-biz` MCP tool 前校验 `bid_type` 是否被当前业务场景支持。对于可由本地规则确定不支持的出价方式，系统 SHALL 返回中文参数校验失败结果，并 SHALL NOT 调用 MCP 或等待平台返回 `code=40000`。

#### Scenario: 展示量优化目标只允许手动出价

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `external_action` 为 `SHOW`
- **WHEN** `bid_type` 不是 `MANUAL`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前展示量优化目标仅支持 `MANUAL`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 直播交易场景只允许智能出价

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `marketing_goal` 为 `LIVE`
- **AND** 参数中 `local_delivery_scene` 为 `CONTENT_HEAT` 或 `PRODUCT_PAY`
- **WHEN** `bid_type` 不是 `SMART`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前直播交易场景仅支持 `SMART`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 非 UBL 留资场景只允许稳定成本或最大转化

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中 `local_delivery_scene` 为 `EXTERNAL`
- **AND** 当前组合不属于 UBL 相关链路
- **WHEN** `bid_type` 不是 `STABILIZE_COSTS` 或 `MAX_CONVERSION`
- **THEN** `oceanengine_local_project` SHALL 返回中文参数校验失败
- **AND** 错误 SHALL 说明当前非 UBL 留资场景仅支持 `STABILIZE_COSTS` 或 `MAX_CONVERSION`
- **AND** 系统 SHALL NOT 调用 `localProjectCreate` MCP tool

#### Scenario: 合法出价方式组合继续进入正常链路

- **GIVEN** 用户请求创建本地推项目
- **AND** 参数中的 `bid_type` 被当前 `marketing_goal`、`local_delivery_scene` 和 UBL 相关组合支持
- **WHEN** 其它本地参数校验也通过
- **THEN** `oceanengine_local_project` SHALL 继续按现有 payload 映射构造 `localProjectCreate` 请求
- **AND** 系统 SHALL 保持现有 MCP endpoint 解析、MCP 调用、后置确认和用户可见清洗逻辑不变

### Requirement: 创建项目流程必须先收集业务必填项

`oceanengine-local-project` SHALL 为自然语言创建项目请求提供业务流程级参数收集顺序。该流程 SHALL 先收集投手、营销场景、投放目标、单元类型、投放内容、地域、人群、日预算、出价和素材要求，再生成符合 `rules/create-project.json` 的官方 `create-project` payload。

#### Scenario: 按业务顺序收集创建项目信息

- **GIVEN** 用户通过自然语言请求创建本地推项目
- **WHEN** 当前流程缺少创建项目业务必填项
- **THEN** 系统 SHALL 优先按投手、`marketing_goal`、`local_delivery_scene`、`ad_type`、投放内容、地域、人群、`budget`、`bid` 和视频素材要求的顺序补齐
- **AND** 每轮只向用户展示一个中文问题
- **AND** 缺少官方请求参数时 SHALL 继续通过 `oceanengine_local_project` 原生业务工具生成 `data.user_visible_text` 或 `data.clarification`
- **AND** 系统 SHALL NOT 直接调用 `ask_clarification` 汇总多个缺失项

#### Scenario: 投手仅作为流程态和命名来源

- **GIVEN** 用户请求创建项目
- **AND** 当前请求缺少投手姓名
- **WHEN** 系统进入创建项目流程
- **THEN** 系统 SHALL 先追问投手姓名
- **AND** 投手姓名 SHALL 用于项目或单元命名、验收记录和用户可见上下文
- **AND** 除非官方规则明确提供对应字段，系统 SHALL NOT 把投手姓名作为自造字段写入 `localProjectCreate` payload

#### Scenario: 官方字段优先于业务别名

- **GIVEN** 用户使用中文业务表达提供营销场景、投放目标、单元类型或投放内容
- **WHEN** 系统整理 `create-project` payload
- **THEN** 短视频/图文 SHALL 映射为 `marketing_goal=VIDEO_IMAGE`
- **AND** 直播间 SHALL 映射为 `marketing_goal=LIVE`
- **AND** 团购成交、线下到店、获取线索、线上互动 SHALL 分别映射为 `local_delivery_scene=PRODUCT_PAY`、`POI_RECOMMEND`、`EXTERNAL`、`CONTENT_HEAT`
- **AND** 通投、搜索 SHALL 分别映射为 `ad_type=GENERAL`、`SEARCHING`
- **AND** 投放门店、投放商品 SHALL 分别映射为 `delivery_goal=POI`、`delivery_goal=PRODUCT`

### Requirement: 创建项目流程必须应用可映射的默认定向

创建项目流程 SHALL 在用户未显式提供定向字段时应用业务默认项。默认项只有在当前 `rules/create-project.json` 存在官方字段时才可进入 payload；当前规则未声明的业务项 SHALL NOT 被自造为 MCP 字段。

#### Scenario: 默认用户定向可映射字段

- **GIVEN** 用户请求创建项目
- **AND** 用户没有显式覆盖用户定向字段
- **WHEN** 系统生成 `create-project` payload
- **THEN** 地域内人群定向 SHALL 使用 `audience.region.location_type=HOME`
- **AND** 性别 SHALL 使用 `audience.gender=NONE`
- **AND** 年龄 SHALL 表达 18 到 55 岁
- **AND** 过滤已转化用户 SHALL 使用 `audience.hide_if_converted=CUSTOMER`
- **AND** 过滤时间 SHALL 使用 `audience.converted_time_duration=THREE_MONTH`
- **AND** 人群包不限和抖音达人不限 SHALL 不传对应人群包或达人字段，除非用户明确指定

#### Scenario: 自定义人群包按定向或排除保留

- **GIVEN** 用户请求创建项目
- **AND** 用户指定某个人群包用于定向或排除
- **WHEN** 系统生成 `audience` payload
- **THEN** 定向人群包 SHALL 写入 `audience.retargeting_tags`
- **AND** 排除人群包 SHALL 写入 `audience.retargeting_tags_exclude`
- **AND** 系统 SHALL 保留用户明确给出的全部人群包 ID
- **AND** 数量、类型和条件错误 SHALL 由本地规则校验返回中文错误

#### Scenario: 未声明的默认项不得自造字段

- **GIVEN** 业务默认项包含智能定向拓展不启用或搜索出价系数不填
- **AND** 当前 `rules/create-project.json` 未声明对应官方字段
- **WHEN** 系统生成 `localProjectCreate` payload
- **THEN** 系统 SHALL NOT 自造智能定向拓展或搜索出价系数字段
- **AND** 系统 MAY 在流程态记录该业务决策用于后续确认
- **AND** 若实现阶段发现官方字段位于其它 capability，必须通过对应原生业务工具和 OpenSpec 范围处理

### Requirement: 创建项目排期预算必须使用业务默认项并保留用户覆盖

创建项目流程 SHALL 默认使用从今天起长期投放、不限投放时段、日预算、关闭高峰日预算等业务设置。用户显式提供的排期、预算或出价值 SHALL 原样保留并交给本地规则校验，不得静默改写。

#### Scenario: 默认排期和预算

- **GIVEN** 用户请求创建项目
- **AND** 用户没有显式指定投放日期、投放时段、预算模式或高峰日预算
- **WHEN** 系统生成 `create-project` payload
- **THEN** 投放日期 SHALL 使用 `schedule_type=FROM_NOW_ON`
- **AND** 预算模式 SHALL 使用 `budget_mode=BUDGET_MODE_DAY`
- **AND** 投放时段 SHALL 不传 `schedule_time`，表达不限
- **AND** 高峰日预算在当前场景需要传值时 SHALL 使用 `is_set_peak_budget=false`

#### Scenario: 出价方式按投放目标默认

- **GIVEN** 用户请求创建项目
- **AND** 用户没有显式指定 `bid_type`
- **WHEN** 投放目标为线下到店
- **THEN** 系统 SHALL 使用 `bid_type=SMART`
- **AND** 系统 SHALL NOT 让用户选择 `MANUAL` 作为线下到店默认出价方式
- **WHEN** 投放目标为获取线索
- **THEN** 系统 SHALL 使用 `bid_type=MAX_CONVERSION`

#### Scenario: 用户显式参数不被默认覆盖

- **GIVEN** 用户显式提供了投放日期、投放时段、预算、出价或出价方式
- **WHEN** 系统生成 `create-project` payload
- **THEN** 系统 SHALL 保留用户显式值
- **AND** 系统 SHALL NOT 把显式非法值改写成默认合法值
- **AND** 非法组合 SHALL 由 `oceanengine_local_project` 本地校验返回中文错误

### Requirement: 获取线索创建流程必须处理专属字段

当创建项目投放目标为获取线索时，系统 SHALL 使用获取线索专属字段和默认项，覆盖优化目标、引导页面、留资组件、抖音号、AIGC 动态创意、行为兴趣和过滤项。

#### Scenario: 获取线索优化目标映射

- **GIVEN** 用户请求创建获取线索项目
- **WHEN** 用户选择获取线索、私信消息、确认意向或预付定金作为优化目标
- **THEN** 系统 SHALL 分别映射为 `external_action=CLUE_ACQUISITION`、`PRIVATE_MESSAGE`、`CLUE_CONFIRM` 或 `CLUE_HIGH_INTENTION`
- **AND** 不在当前枚举范围内的优化目标 SHALL 原样交给本地校验或返回中文支持范围

#### Scenario: 获取线索引导页面映射

- **GIVEN** 用户请求创建获取线索项目
- **WHEN** 用户选择引导到营销页、门店页或私信页
- **THEN** 系统 SHALL 按当前规则映射到 `local_asset_type`
- **AND** 营销页 SHALL 使用 `market_page_ids` 或动态候选补齐
- **AND** 留资组件 SHALL 使用 `tool_pack_id` 或动态候选补齐
- **AND** 私信页相关抖音号 SHALL 使用 `consult_aweme_uid` 或动态候选补齐

#### Scenario: 获取线索默认定向和创意

- **GIVEN** 用户请求创建获取线索项目
- **AND** 用户没有显式覆盖获取线索专属设置
- **WHEN** 系统生成 payload
- **THEN** 行为兴趣 SHALL 使用 `audience.customized_interest_action=INTERESTACTION_OFF`
- **AND** 过滤高活跃用户 SHALL 使用 `audience.filter_aweme_abnormal_active=FILTER_AWEME_ABNORMAL_ACTIVE_TYPE_ON`
- **AND** 过滤高关注用户 SHALL 使用 `audience.filter_aweme_fans_count=FILTER_AWEME_FANS_COUNT_TYPE_OVER1000`
- **AND** AIGC 动态创意 SHALL 使用 `aigc_dynamic_creative_switch=AIGC_DYNAMIC_CREATIVE_SWITCH_OFF`

### Requirement: 创建项目浏览器验收必须覆盖业务流程而非单接口成功

创建项目优化验收 SHALL 证明浏览器自然语言请求能够完成业务流程级参数收集、默认项落地、原生业务工具调用、素材候选衔接和用户可见清洗。单次 `localProjectCreate` 成功 SHALL NOT 单独代表本流程验收完成。

#### Scenario: 浏览器验收覆盖四类投放目标

- **GIVEN** Apply 阶段执行创建项目流程验收
- **WHEN** 测试人员通过浏览器自然语言提交请求
- **THEN** 验收 SHALL 覆盖团购成交、线下到店、获取线索和线上互动
- **AND** 至少一个用例 SHALL 覆盖直播间营销场景
- **AND** 每个用例 SHALL 记录真实 Agent、原生业务工具和 MCP 调用或本地拦截证据
- **AND** dry-run、mock、curl、SDK、脚本直连或 MCP 直连 SHALL NOT 替代浏览器主验收

#### Scenario: 用户可见结果隐藏内部链路

- **GIVEN** 创建项目流程返回成功、失败或参数补齐结果
- **WHEN** Gateway 生成用户可见消息
- **THEN** 用户可见消息 SHALL 使用中文业务摘要
- **AND** 用户可见消息 SHALL NOT 展示内部 tool name、MCP tool name、payload JSON、trace、平台请求日志 ID、`SESSION INTENT` 或 skill 文件路径
- **AND** 结构化候选 SHALL 保留在 `structured_clarifications` 或等价消息级字段

### Requirement: 创建项目流程默认项目名必须与单元名保持一致

创建项目流程在用户未显式提供项目名时，系统 SHALL 使用与默认单元名相同的业务规则生成项目名。默认项目名 SHALL 使用执行日期、地域、定向类型和年龄组成；当流程态包含非空投手姓名时，默认项目名 SHALL 在末尾追加投手姓名首字母大写。项目名和单元名在无显式覆盖时 SHALL 默认一致。

#### Scenario: 未提供项目名和单元名时生成一致名称

- **GIVEN** 用户请求创建本地推项目
- **AND** 流程态包含地域、定向类型和年龄
- **AND** 用户没有显式提供 `name`
- **AND** 用户没有显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 可选投手姓名首字母大写
- **AND** `unit_plan.name` SHALL 与 `project_payload.name` 完全一致
- **AND** 系统 SHALL NOT 追加 `X`、`--`、`未知`、`None`、`null` 或其它投手占位符

#### Scenario: 只提供项目名时单元名默认复用项目名

- **GIVEN** 用户请求创建本地推项目
- **AND** 用户显式提供 `name`
- **AND** 用户没有显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用用户提供的 `name`
- **AND** `unit_plan.name` SHALL 默认复用同一个 `name`
- **AND** 系统 SHALL NOT 再按默认规则生成不同的单元名

#### Scenario: 项目名和单元名都显式提供时分别保留

- **GIVEN** 用户请求创建本地推项目
- **AND** 用户显式提供 `name`
- **AND** 用户显式提供 `unit_name`
- **WHEN** 系统生成 `create-project` payload 和后续单元计划
- **THEN** `project_payload.name` SHALL 使用用户提供的 `name`
- **AND** `unit_plan.name` SHALL 使用用户提供的 `unit_name`
- **AND** 系统 SHALL NOT 用默认命名覆盖任一显式名称

