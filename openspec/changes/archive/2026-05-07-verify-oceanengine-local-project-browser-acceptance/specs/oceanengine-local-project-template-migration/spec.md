# oceanengine-local-project-template-migration Specification

## ADDED Requirements

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
