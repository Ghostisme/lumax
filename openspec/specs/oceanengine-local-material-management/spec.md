# oceanengine-local-material-management Specification

## Purpose
TBD - created by archiving change add-oceanengine-local-material-skill. Update Purpose after archive.
## Requirements
### Requirement: 素材管理 Skill 必须覆盖官方模块接口

`oceanengine-local-material` SHALL 作为独立标准业务 Skill 覆盖巨量引擎开放平台“本地推素材管理”的 8 个接口，并保持接口范围与官方模块页子文档一致。

#### Scenario: 维护人员检查能力索引

- **GIVEN** 维护人员打开 `skills/custom/oceanengine-local-material/references/index.md`
- **WHEN** 查看接口列表
- **THEN** 索引 SHALL 包含异步上传本地推视频、查询异步上传本地推视频结果、上传视频、获取素材库视频、获取抖音主页视频、获取图文素材、上传图片素材、获取视频素材评估标签
- **AND** 每个接口 SHALL 标明官方 path、`doc_id`、reference、rule、endpoint script 和 capability

#### Scenario: 规则索引完整

- **GIVEN** `skills/custom/oceanengine-local-material/rules/index.json` 已存在
- **WHEN** 执行规则配置自检
- **THEN** `rules/index.json` SHALL 为 8 个接口分别提供唯一 capability
- **AND** 每个 capability SHALL 指向存在的 reference、rule 和 endpoint script

### Requirement: 素材管理必须复用标准业务 Skill 结构

`oceanengine-local-material` SHALL 复用标准业务 Skill 的渐进式文件结构，使 `SKILL.md` 只承担导航和执行约束，接口事实和机器可执行规则分别落在 `references/` 与 `rules/`。

#### Scenario: Agent 处理单个素材管理能力

- **GIVEN** 用户请求命中素材管理的某个具体能力
- **WHEN** Agent 按 `SKILL.md` 读取上下文
- **THEN** Agent SHALL 先读取 `references/index.md` 定位 capability
- **AND** Agent SHALL 只读取该 capability 对应的 reference 与 rule
- **AND** Agent SHALL NOT 一次性加载无关接口的全部 reference 或规则配置

#### Scenario: 维护人员查看 Skill 主文件

- **GIVEN** 维护人员打开 `skills/custom/oceanengine-local-material/SKILL.md`
- **WHEN** 查看文件内容
- **THEN** `SKILL.md` SHALL 包含使用流程、原生业务工具入口、接口导航、上传安全边界和 MCP 安全约束
- **AND** 详细字段、枚举、示例和约束 SHALL 放在 `references/` 或 `rules/` 中

### Requirement: 素材管理必须通过原生业务工具执行

`oceanengine-local-material` 的全部 capability SHALL 在 DeerFlow 运行时通过 `oceanengine_local_material` 原生业务工具执行，并使用 `capability`、`payload_json` 和可选 `dry_run` 作为调用入口。`oceanengine_local_material` 的主实现 SHALL 位于仓库根目录 `tools/oceanengine_local_material.py`，其运行时依赖 SHALL 位于 `tools/` 同域模块内；系统 SHALL NOT 保留 `deerflow.tools.oceanengine_local_material` 兼容导入路径。

#### Scenario: 主 Agent 调用素材管理能力

- **GIVEN** 用户请求命中 `oceanengine-local-material` 中任一 capability
- **WHEN** 主 Agent 需要执行该业务能力
- **THEN** 主 Agent SHALL 调用 `oceanengine_local_material` 原生业务工具
- **AND** 调用参数 SHALL 包含 `capability`、`payload_json` 和可选 `dry_run`
- **AND** 主 Agent SHALL NOT 直接调用 `nacos-mcp-router_use_tool`、底层素材管理 MCP 工具、curl、HTTP API、SDK 或子代理来替代该业务工具

#### Scenario: 原生业务工具按 capability 路由

- **GIVEN** `rules/index.json` 中存在目标 capability 条目
- **WHEN** `oceanengine_local_material` 收到该 capability
- **THEN** 业务工具 SHALL 加载条目声明的 `rules/*.json`
- **AND** 业务工具 SHALL 复用 `tools/` 同域公共 endpoint runner 执行参数校验、文件参数校验、字段映射、MCP payload 构造和必要的上传确认
- **AND** 返回结果 SHALL 包含 `execution_source=deerflow-native-tool`、`business_tool_name=oceanengine_local_material`、`mcp_server_name` 和 `mcp_tool_name`

#### Scenario: 素材管理 native tool 不依赖 skill scripts 路径

- **GIVEN** 调用方从干净 `sys.path` 环境导入 `tools.oceanengine_local_material`
- **AND** `sys.path` 中不包含 `skills/custom/oceanengine-local-material/scripts` 或 `skills/custom/oceanengine-local-project/scripts`
- **WHEN** 调用 `run_oceanengine_local_material` 执行任一 capability 的 dry-run、mock MCP 路径或 MCP 缺失诊断路径
- **THEN** 调用 SHALL 使用 `tools/` 同域运行时完成规则加载和 endpoint 执行
- **AND** 调用完成后 `sys.path` SHALL NOT 新增上述 skill scripts 路径
- **AND** `tools/oceanengine_local_material.py` SHALL NOT 导入 `common.rule_loader`、`common.endpoint_runner` 或其它来自 `skills/custom/**/scripts` 的运行时模块

#### Scenario: 后端 harness 不保留素材管理 wrapper

- **GIVEN** 维护人员检查 `backend/packages/harness/deerflow/tools/`
- **WHEN** 查找素材管理原生业务工具实现
- **THEN** `backend/packages/harness/deerflow/tools/oceanengine_local_material.py` SHALL 不存在
- **AND** 生产代码和测试 SHALL NOT 依赖 `deerflow.tools.oceanengine_local_material`

#### Scenario: 未知 capability 被本地拦截

- **GIVEN** 主 Agent 或调用方传入不在 `rules/index.json` 中的 capability
- **WHEN** `oceanengine_local_material` 解析能力索引
- **THEN** 业务工具 SHALL 返回失败或抛出可转为失败响应的中文诊断
- **AND** 诊断 SHALL 列出当前支持的 capability
- **AND** 业务工具 SHALL NOT 发起 MCP 调用

### Requirement: 素材管理参数校验必须统一经过 Pydantic

`oceanengine-local-material` 的所有 endpoint SHALL 只通过共享 Pydantic v2 校验边界执行参数校验。该边界 SHALL 从对应 `rules/*.json` 读取规则，并覆盖普通必填、条件必填、类型、枚举、长度、范围、格式、数组项、分页、排序、时间范围和文件参数等规则。endpoint SHALL NOT 使用绕过 Pydantic 的独立手写分支得出最终通过或失败结论，且 SHALL NOT 提供任何非 Pydantic 参数校验降级策略。

#### Scenario: 缺少普通必填字段

- **GIVEN** 用户请求查询、上传或批量查询素材任务
- **AND** 用户缺少规则配置声明的普通必填字段
- **WHEN** endpoint 执行本地校验
- **THEN** endpoint SHALL 返回 `success=false` 和中文 `errors`
- **AND** 错误 SHALL 用中文询问缺失字段是什么值
- **AND** endpoint SHALL NOT 调用 MCP

#### Scenario: 缺少条件必填字段

- **GIVEN** 用户输入触发官方文档声明的条件必填规则
- **AND** 用户缺少对应字段
- **WHEN** endpoint 执行本地校验
- **THEN** endpoint SHALL 返回中文结构化错误
- **AND** 错误 SHALL 说明触发条件和缺失字段中文名
- **AND** endpoint SHALL NOT 自动填充默认值或调用 MCP

#### Scenario: 数组或分页输入非法

- **GIVEN** 用户提交 `task_ids`、`carousel_ids`、`material_ids`、分页或 `page_size` 参数
- **AND** 输入违反官方数量、范围或 `page * page_size` 限制
- **WHEN** endpoint 执行本地校验
- **THEN** 错误结果 SHALL 标明具体字段和限制
- **AND** endpoint SHALL NOT 调用 MCP

#### Scenario: 文件上传参数经过 Pydantic 边界

- **GIVEN** 用户请求上传视频或上传图片
- **AND** 规则配置声明文件路径、文件名、MD5、格式、大小或视频宽高比例限制
- **WHEN** endpoint 执行上传前校验
- **THEN** Pydantic 校验边界 SHALL 执行这些文件参数规则
- **AND** 校验失败 SHALL 返回中文结构化错误
- **AND** endpoint SHALL NOT 上传文件或调用 MCP

#### Scenario: Pydantic 不可用时不得降级

- **GIVEN** `oceanengine-local-material` 的 endpoint 已加载目标 `rules/*.json`
- **AND** 当前运行环境无法导入 Pydantic 或 Pydantic 校验边界无法覆盖已声明规则类型
- **WHEN** endpoint 准备执行参数校验
- **THEN** endpoint SHALL 返回中文失败诊断
- **AND** endpoint SHALL NOT 使用手写备用校验器、自然语言判断或跳过校验
- **AND** endpoint SHALL NOT 调用 MCP

### Requirement: 上传类接口必须显式处理文件和 URL 安全边界

上传视频、上传图片和异步上传本地推视频 SHALL 只使用用户明确提供或明确授权的本地文件路径、文件 URL 和上传参数；系统 SHALL NOT 读取本地历史、最近文件、浏览器记录、剪贴板或目录扫描结果来猜测素材文件。

#### Scenario: 上传文件参数缺失

- **GIVEN** 用户请求上传视频或上传图片
- **AND** 用户没有提供当前任务明确授权的文件路径、文件内容引用或官方支持的 URL 参数
- **WHEN** endpoint 执行上传前校验
- **THEN** endpoint SHALL 返回中文追问，要求用户提供具体文件或 URL
- **AND** 系统 SHALL NOT 从本地最近文件、下载目录、剪贴板或浏览器历史中推断上传对象
- **AND** endpoint SHALL NOT 调用 MCP

#### Scenario: 上传文件格式或大小不合规

- **GIVEN** 用户提供了上传文件路径或文件元数据
- **AND** 文件格式、大小、MD5 签名、文件名或视频宽高比例不满足官方文档或 MCP schema 声明的限制
- **WHEN** endpoint 执行上传前校验
- **THEN** endpoint SHALL 返回中文结构化错误
- **AND** 错误 SHALL 说明具体不合规项
- **AND** endpoint SHALL NOT 上传文件或调用 MCP

#### Scenario: 异步上传视频 URL 不符合官方限制

- **GIVEN** 用户请求异步上传本地推视频
- **AND** `video_url` 不是用户明确提供的连山云素材服务 tos 链接或无法确认来源
- **WHEN** endpoint 执行上传前校验
- **THEN** endpoint SHALL 返回中文错误或追问
- **AND** 错误 SHALL 说明该接口只支持官方文档声明的连山云素材服务 tos 链接
- **AND** endpoint SHALL NOT 调用 MCP

### Requirement: 素材管理 MCP payload 必须按规则映射

`oceanengine-local-material` SHALL 使用规则配置将用户侧字段和值映射为 MCP schema 需要的字段名、包装结构、请求方法和枚举值。

#### Scenario: 调用需要 request 包装的 MCP 工具

- **GIVEN** 目标 MCP tool schema 要求顶层 `request` 对象
- **WHEN** endpoint 构造 MCP payload
- **THEN** payload SHALL 使用 `{"request": {...}}` 包装
- **AND** 内部字段 SHALL 从用户侧字段映射为 MCP schema 需要的 camelCase 或实际字段名

#### Scenario: 调用扁平入参 MCP 工具

- **GIVEN** 目标 MCP tool schema 使用扁平入参
- **WHEN** endpoint 构造 MCP payload
- **THEN** payload SHALL 按 MCP schema 直接传入对应字段
- **AND** endpoint SHALL NOT 强行添加 `request` 包装

#### Scenario: MCP 工具缺失

- **GIVEN** 官方接口已在素材管理模块中列出
- **AND** Apply 阶段无法在 `platform-agent-biz` 中确认对应 MCP tool
- **WHEN** 用户触发该 capability
- **THEN** 业务工具 SHALL 返回中文失败诊断，说明当前 MCP 工具缺失
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用 HTTP API、curl 或 SDK 直连

### Requirement: 素材管理受管理 MCP 工具必须被 guard 保护

`platform-agent-biz` 中归属 `oceanengine-local-material` 的素材管理 MCP 工具 SHALL 只能在 `oceanengine_local_material` 业务工具允许的上下文中调用。

#### Scenario: 主 Agent 直接调用素材管理 MCP 工具

- **GIVEN** 某调用路径准备直接调用 `nacos-mcp-router_use_tool`
- **AND** 参数中的 `mcp_server_name=platform-agent-biz`
- **AND** 参数中的 `mcp_tool_name` 属于 `oceanengine-local-material` 管理的素材管理工具
- **WHEN** 当前上下文不是 `oceanengine_local_material` 业务工具内部调用
- **THEN** 系统 SHALL 阻断该调用
- **AND** 错误 SHALL 提示必须调用 `oceanengine_local_material`
- **AND** 系统 SHALL NOT 将该调用发送到 Nacos MCP Router

#### Scenario: 业务工具内部调用素材管理 MCP 工具

- **GIVEN** 用户输入已通过本地规则校验
- **AND** `oceanengine_local_material` 已进入允许受管理 MCP 调用的上下文
- **WHEN** 公共 endpoint runner 调用对应素材管理 MCP 工具
- **THEN** guard SHALL 允许该调用继续
- **AND** 调用失败时系统 SHALL 返回该目标的失败诊断
- **AND** 系统 SHALL NOT 自动切换到其它 MCP server、其它 MCP tool、curl、HTTP API 或 SDK

### Requirement: 素材管理输出必须面向用户中文展示

`oceanengine-local-material` SHALL 返回统一结构化结果，并为主 Agent 提供可直接展示给用户的中文 `user_visible_text` 或等价字段。`oceanengine_local_material` LangChain tool 返回给 Agent 的默认结果 SHALL 隐藏原始 `data.result`，不得让主 Agent 默认遍历英文 API 字段名、英文枚举值、上传参数或原始 MCP 响应。

#### Scenario: 查询接口返回成功

- **GIVEN** 用户请求获取素材库视频、获取抖音主页视频、获取图文素材、查询异步上传任务结果或获取视频素材评估标签
- **WHEN** MCP 调用成功并返回数据
- **THEN** 业务工具 SHALL 返回 `success=true`、中文 `message` 和业务 `data`
- **AND** `data` SHALL 包含面向用户的中文字段名和中文值
- **AND** Agent 最终回复 SHALL NOT 展示英文 API 字段名、英文枚举值或原始响应

#### Scenario: 上传接口返回成功

- **GIVEN** 用户请求上传视频、上传图片或异步上传本地推视频
- **WHEN** MCP 调用成功并返回素材 ID、任务 ID、预览 URL 或关键元数据
- **THEN** 业务工具 SHALL 返回中文上传结果摘要
- **AND** 关键 ID 可保留原始数值，但字段标签必须为中文
- **AND** Agent 最终回复 SHALL NOT 直接遍历原始响应

#### Scenario: Agent 可见结果隐藏原始响应

- **GIVEN** `oceanengine_local_material_tool` 收到底层成功结果
- **AND** 底层结果包含 `data.result`、英文 API 字段名、英文枚举值、上传 URL 或原始 MCP 响应
- **WHEN** tool wrapper 生成返回给主 Agent 的 JSON 字符串
- **THEN** 返回结果 SHALL 移除或隐藏 `data.result`
- **AND** 返回结果 SHALL 提供中文 `data.user_visible_text` 或等价中文摘要
- **AND** 返回结果 SHALL NOT 包含默认展示不需要的英文枚举码、上传原始链接或原始 MCP 响应正文

#### Scenario: 校验失败返回中文追问

- **GIVEN** endpoint 本地校验失败
- **WHEN** 业务工具返回失败结果
- **THEN** 返回结果 SHALL 包含 `success=false`、中文 `message` 和结构化 `errors`
- **AND** Agent 面向用户的最终回复 SHALL 展示这些 `errors` 对应的中文文字
- **AND** Agent SHALL NOT 只输出内部字段名、英文枚举码或原始 JSON

### Requirement: 页面验收必须证明素材管理业务工具可用

实现完成后，`oceanengine-local-material` SHALL 通过 DeerFlow 前端页面或等价对话入口验证用户对话可以调用 `oceanengine_local_material` 原生业务工具，并保留可追踪证据。

#### Scenario: 页面请求调用素材管理业务工具

- **GIVEN** 本地 DeerFlow 前端、Gateway 和 agent runtime 已启动
- **AND** `oceanengine_local_material` 已注册为可用工具
- **WHEN** 测试人员在前端对话页面提交素材查询或上传 dry-run 请求
- **THEN** 页面 SHALL 返回来自业务工具结构化结果的中文反馈
- **AND** 后端日志、trace 或响应诊断 SHALL 显示调用路径经过 `oceanengine_local_material`
- **AND** 证据 SHALL 显示主 Agent 没有直接调用受保护的 `nacos-mcp-router_use_tool`

#### Scenario: 页面验收发现调用路径异常

- **GIVEN** 页面请求已提交
- **WHEN** 证据显示业务工具未被选择、参数校验未按规则执行、页面结果展示异常或请求绕过业务工具直连 MCP
- **THEN** 实现人员 SHALL 修复工具注册、skill 导航、调用保护、参数整理或结果展示问题
- **AND** 修复后 SHALL 重新执行同类页面验收

### Requirement: 素材管理浏览器验收必须覆盖全部接口

`oceanengine-local-material` SHALL 在浏览器对话入口完成全接口自然语言验收，覆盖 `rules/index.json` 中声明的 8 个 capability，并在测试前先形成可追踪的测试用例矩阵。

#### Scenario: 验收前建立全接口测试矩阵

- **GIVEN** Apply 阶段准备测试 `oceanengine-local-material`
- **WHEN** 测试人员开始浏览器验收前
- **THEN** 测试矩阵 SHALL 包含 `async-upload-local-video`、`list-local-video-upload-tasks`、`upload-video`、`get-library-videos`、`get-aweme-videos`、`list-carousel-materials`、`upload-image` 和 `list-video-material-attributes`
- **AND** 每个 capability SHALL 至少列出正向、负向、边界或条件依赖类用例
- **AND** 测试人员 SHALL 先完成用例矩阵登记，再执行浏览器提交

#### Scenario: 已映射 MCP 工具的接口完成正向与负向覆盖

- **GIVEN** 某素材管理 capability 已映射到 `platform-agent-biz` MCP tool
- **WHEN** 测试人员通过浏览器对话页面验收该 capability
- **THEN** 该 capability SHALL 至少完成 5 条参数组合不重复的正向计数用例
- **AND** 该 capability SHALL 覆盖缺必填、类型或格式错误、枚举或数组边界、分页或条件依赖中的至少 4 类负向或边界用例
- **AND** 正向计数用例、负向校验用例和环境失败用例 SHALL 分开记录

#### Scenario: MCP 缺失接口完成缺失诊断验收

- **GIVEN** `list-video-material-attributes` 当前未在 `platform-agent-biz` 暴露对应 MCP tool
- **WHEN** 测试人员通过浏览器对话页面提交视频素材评估标签相关请求
- **THEN** 页面 SHALL 返回中文 MCP 工具缺失诊断
- **AND** 诊断 SHALL 说明当前无法执行该官方接口
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用 curl、HTTP API、SDK 或直接 MCP 调用绕过缺失状态

### Requirement: 素材管理浏览器测试输入必须模拟真实用户表达

浏览器验收 SHALL 使用自然语言业务请求触发素材管理能力。测试输入 SHALL NOT 显式指定 skill、业务工具、capability、底层 MCP tool、脚本路径或 JSON tool payload 来降低路由难度。

#### Scenario: 浏览器输入禁止点名工具或 Skill

- **GIVEN** 测试人员准备在浏览器对话框提交素材管理请求
- **WHEN** 编写浏览器输入内容
- **THEN** 输入 SHALL NOT 包含 `oceanengine-local-material`
- **AND** 输入 SHALL NOT 包含 `oceanengine_local_material`
- **AND** 输入 SHALL NOT 包含 `capability`、`payload_json` 或 `dry_run`
- **AND** 输入 SHALL NOT 包含底层 MCP tool 名，例如 `localFileVideoGet`、`localFileVideoUpload`、`localImageUpload`
- **AND** 输入 SHALL NOT 要求 Agent “直接调用某工具”或“使用某 skill”

#### Scenario: 浏览器输入保留业务参数

- **GIVEN** 某用例需要账号、任务 ID、素材 ID、分页、排序、时间、文件路径、URL、签名或文件元数据
- **WHEN** 测试人员编写自然语言输入
- **THEN** 输入 MAY 包含本轮明确提供或授权的业务参数
- **AND** 输入 SHALL 以用户业务意图描述目标接口
- **AND** 输入 SHALL NOT 直接粘贴 `oceanengine_local_material` 的 JSON tool payload 作为验收输入

#### Scenario: 证据记录允许出现内部标识

- **GIVEN** 浏览器输入已经按自然语言提交
- **WHEN** 测试人员记录日志、trace、线程历史或工具调用证据
- **THEN** 证据 MAY 包含 `oceanengine_local_material`、capability 和 MCP tool 名
- **AND** 这些内部标识 SHALL 只用于证明真实调用路径
- **AND** 证据 SHALL NOT 被反向复制到后续浏览器输入中降低测试难度

### Requirement: 素材管理浏览器验收参数必须多样化

测试矩阵 SHALL 明确每条用例的参数差异点，并通过不同账号、文件名、URL、文件路径、分页、排序、枚举、数组、时间范围和布尔值组合提高覆盖率，避免使用同一组参数反复提交。

#### Scenario: 查询类接口参数多样化

- **GIVEN** 测试人员验收素材查询类 capability
- **WHEN** 编写和执行查询类测试用例
- **THEN** 用例 SHALL 覆盖不同分页或游标
- **AND** 用例 SHALL 覆盖不同排序字段或排序方向
- **AND** 用例 SHALL 覆盖至少一种数组筛选或枚举筛选
- **AND** 多条正向用例 SHALL NOT 使用完全相同的参数组合

#### Scenario: 上传类接口参数多样化

- **GIVEN** 测试人员验收上传视频、上传图片或异步上传视频 capability
- **WHEN** 编写和执行上传类测试用例
- **THEN** 用例 SHALL 覆盖不同文件名、文件路径、URL、签名、文件大小或 `is_aigc` 参数
- **AND** 用例 SHALL 覆盖授权素材、缺素材、格式不合规和边界大小
- **AND** 上传文件、URL、签名和元数据 SHALL 来自本轮用户明确提供或授权的测试数据
- **AND** 系统 SHALL NOT 扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录来猜测素材

#### Scenario: 重复参数不能充当覆盖率

- **GIVEN** 同一 capability 已存在正向计数用例
- **WHEN** 新用例只重复相同账号、相同筛选、相同分页、相同素材路径或相同 URL
- **THEN** 新用例 SHALL NOT 作为新的正向覆盖计数
- **AND** 测试人员 SHALL 调整至少一个实质业务参数后再记录为新覆盖

### Requirement: 素材管理浏览器验收状态必须逐用例维护

浏览器验收 SHALL 以单条用例作为最小完成单元。任务状态、验收记录和能力级汇总 SHALL 反映真实执行进度，不得在未逐条完成证据记录时批量标记完成。

#### Scenario: 单条用例完成后才允许勾选

- **GIVEN** `tasks.md` 中存在某个浏览器验收用例 checkbox
- **WHEN** 测试人员完成该用例的浏览器提交
- **AND** 验收记录已经保存线程 ID 或 trace ID、工具调用证据、用户可见结果摘要和通过或失败结论
- **THEN** 该用例 checkbox MAY 标记为完成
- **AND** 未执行或缺少证据的用例 SHALL 保持未完成

#### Scenario: 能力级完成依赖所有子用例

- **GIVEN** 某素材管理 capability 下仍有未完成用例
- **WHEN** 测试人员汇总该 capability 的验收状态
- **THEN** 该 capability SHALL NOT 标记为整体完成
- **AND** 汇总 SHALL 列出剩余未完成用例 ID
- **AND** 汇总 SHALL 区分正向成功、负向校验通过、环境失败和待重测状态

#### Scenario: 修复后重测按用例重置状态

- **GIVEN** 某用例失败后实施人员完成修复
- **WHEN** 该修复影响同一 capability 的多条用例
- **THEN** 受影响用例 SHALL 标记为待重测
- **AND** 这些用例 SHALL 在重新通过浏览器提交并记录证据后才可再次标记完成
- **AND** 受影响 capability 的正向计数 SHALL 按重测后的结果重新计算

### Requirement: 素材管理浏览器验收发现问题后必须修复并重测

浏览器验收发现工具未被选择、校验绕过、MCP guard 绕过、结果展示异常、认证失败、环境缺失或接口调用失败时，实施人员 SHALL 先定位根因并修复，再重新执行受影响用例组。

#### Scenario: 调用路径异常后修复重测

- **GIVEN** 浏览器用例已经提交
- **WHEN** 证据显示主 Agent 未经过 `oceanengine_local_material`、直接调用受保护素材 MCP tool、或未按规则执行本地校验
- **THEN** 实施人员 SHALL 定位并修复工具注册、skill 导航、调用保护或参数整理问题
- **AND** 修复后 SHALL 重新执行受影响 capability 的浏览器用例组
- **AND** 受影响 capability 的正向连续成功计数 SHALL 从 0 重新开始

#### Scenario: 展示或输出异常后修复重测

- **GIVEN** 业务工具已返回结构化结果
- **WHEN** 页面最终回复只展示英文 API 字段名、英文枚举值、原始 JSON、上传原始链接或未翻译错误
- **THEN** 实施人员 SHALL 修复结果压缩、中文摘要或前端展示问题
- **AND** 修复后 SHALL 重新执行同类浏览器用例
- **AND** 验收记录 SHALL 保存修复前失败摘要和修复后中文展示证据

#### Scenario: 环境阻断不能算接口失败

- **GIVEN** 浏览器验收因登录、前端、Gateway、agent runtime、MCP server 或 Java 依赖不可用而失败
- **WHEN** 根因确认属于环境阻断
- **THEN** 该轮 SHALL 记录为环境失败
- **AND** 该轮 SHALL NOT 计入 capability 正向成功或负向校验覆盖
- **AND** 环境恢复后 SHALL 重新执行受影响用例

### Requirement: 素材管理参数校验失败一次只追问一个问题

`oceanengine_local_material` SHALL 在参数校验失败时只向 Agent 和用户暴露首个可行动中文问题。内部校验 MAY 继续收集完整错误列表用于计数、日志和测试，但面向 Agent 的结构化结果 SHALL NOT 同时暴露多个缺参问题，避免最终回复一次追问多个参数。

#### Scenario: 多个普通必填缺失时只展示首个问题

- **GIVEN** 用户请求命中 `oceanengine_local_material`
- **AND** 本地参数校验发现多个普通必填字段缺失
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.user_visible_text` SHALL 只包含规则顺序中的第一个缺失字段中文问题
- **AND** `errors` SHALL 只保留该第一个可见错误
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量

#### Scenario: 上传参数缺失时只展示当前首个问题

- **GIVEN** 用户请求上传视频、异步上传视频或上传图片
- **AND** 用户缺少多个文件、URL、签名或文件元数据参数
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** 用户可见结果 SHALL 只展示校验顺序中的首个可行动中文问题
- **AND** 系统 SHALL NOT 在同一轮要求用户同时补充多个素材参数
- **AND** 后续问题 SHALL 等用户补充首个问题后在下一轮重新校验时继续追问

#### Scenario: Skill 入口不得直接汇总多个缺失项

- **GIVEN** 用户通过自然语言请求上传、查询或评估本地推素材
- **AND** 用户缺少多个官方请求参数
- **WHEN** 主 Agent 已识别请求属于 `oceanengine-local-material`
- **THEN** 主 Agent SHALL 先调用 `oceanengine_local_material` 原生业务工具执行本地校验
- **AND** 主 Agent SHALL NOT 直接调用 `ask_clarification` 自行汇总多个缺失项
- **AND** 最终用户可见结果 SHALL 只展示一个中文补充问题

#### Scenario: MCP 缺失诊断不被单问题追问掩盖

- **GIVEN** `oceanengine_local_material` 的本地参数校验已经通过
- **AND** 目标官方接口当前未在 `platform-agent-biz` 暴露对应 MCP tool
- **WHEN** 业务工具生成失败结果
- **THEN** 用户可见结果 SHALL 保留 MCP 缺失中文诊断
- **AND** 系统 SHALL NOT 将 MCP 缺失诊断改写为素材参数追问
- **AND** 系统 SHALL NOT 建议或尝试 curl、HTTP API、SDK 或其它绕路方式

### Requirement: 素材管理 MCP 调用必须通过 Nacos 解析真实服务端点

`oceanengine-local-material` 在通过原生业务工具调用 `platform-agent-biz` 素材管理 MCP tool 前，SHALL 以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源解析目标 MCP server 的实际地址、端口和路径。业务工具 SHALL NOT 将 `127.0.0.1:18000` 或其它本机固定 Router 地址作为默认业务兜底端点。

#### Scenario: Nacos 解析到素材管理 MCP 服务端点

- **GIVEN** 用户请求命中 `oceanengine-local-material` 中任一需要 MCP 调用的 capability
- **AND** 本地参数校验已通过
- **AND** Nacos 中存在 `platform-agent-biz` 并能解析出实际 MCP endpoint
- **WHEN** 原生业务工具调用目标素材管理 MCP tool
- **THEN** 调用 SHALL 发送到 Nacos 解析出的实际 MCP endpoint
- **AND** payload SHALL 继续按素材管理 rule 中的 MCP 字段映射构造
- **AND** 系统 SHALL NOT 使用 `http://127.0.0.1:18000/mcp/` 作为默认业务兜底地址

#### Scenario: Nacos 未注册素材管理目标 MCP server

- **GIVEN** 用户请求命中素材管理 capability
- **AND** 本地参数校验已通过
- **WHEN** 系统无法从 Nacos 或 DeerFlow Nacos MCP 配置解析到 `platform-agent-biz`
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明 Nacos 中未找到目标 MCP server 或配置不可用
- **AND** 系统 SHALL NOT 继续请求本机固定 Router 地址
- **AND** 系统 SHALL NOT 改用 curl、SDK、HTTP API、mock 或其它 MCP server

#### Scenario: 素材管理目标 MCP endpoint 不可达

- **GIVEN** Nacos 已返回 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 本地参数校验已通过
- **WHEN** 系统连接该 endpoint 失败、超时或返回不可用错误
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明解析到的 MCP 服务不可达
- **AND** 失败结果 SHALL NOT 声称素材管理操作已完成
- **AND** 系统 SHALL NOT 自动切换到本机固定 Router、curl、SDK、HTTP API 或 mock

#### Scenario: 素材管理目标 MCP tool 缺失

- **GIVEN** Nacos 已解析到 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 目标素材管理 capability 声明了 `mcp_tool_name`
- **WHEN** 解析到的 MCP 服务未暴露该 tool
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明目标 MCP tool 未注册或不可用
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用其它 tool 或其它调用协议

### Requirement: 聊天附件必须可作为素材库上传的视频来源

`oceanengine-local-material` SHALL allow a video file uploaded through the current browser chat attachment flow to be used as the source file for `upload-video`, while preserving the existing requirement that the user must explicitly upload or authorize the file in the current task.

#### Scenario: 使用当前对话附件上传视频素材

- **GIVEN** 用户在真实浏览器中通过附件控件上传了视频文件
- **AND** Gateway 已在当前 thread uploads 中保存该文件
- **AND** 用户自然语言请求把该视频上传到本地推素材库
- **WHEN** Agent 调用 `oceanengine_local_material` 的 `upload-video`
- **THEN** 业务工具 SHALL 将该附件识别为当前任务授权的视频来源
- **AND** 业务工具 SHALL 保留 `filename`、文件大小、扩展名和当前 thread 归属信息用于上传前校验
- **AND** 业务工具 SHALL NOT 要求用户再次提供本地绝对路径来替代已上传附件

#### Scenario: 附件来源必须属于当前任务

- **GIVEN** 用户请求上传本地推视频素材
- **AND** payload 中的文件引用不属于当前 thread uploads，也不是本轮用户明确授权的文件路径或 URL
- **WHEN** `oceanengine_local_material` 执行上传前校验
- **THEN** 业务工具 SHALL 返回中文失败或追问，要求用户上传或授权具体视频文件
- **AND** 系统 SHALL NOT 扫描下载目录、最近文件、浏览器记录、剪贴板或任意目录来猜测素材
- **AND** 业务工具 SHALL NOT 调用 `localFileVideoUpload`

### Requirement: 素材库上传前必须确认目标服务可读取文件引用

`oceanengine-local-material` SHALL verify that the file reference passed to `localFileVideoUpload` is readable by the target upload service or has been converted to an equivalent supported reference before calling the MCP tool. A DeerFlow sandbox path such as `/mnt/user-data/uploads/...` SHALL NOT be treated as target-service-readable by default.

#### Scenario: 附件路径已转换为目标服务可读引用

- **GIVEN** 当前 thread 附件已通过格式、大小和授权校验
- **AND** 系统已将附件转换为 `platform-agent-biz` 可读取的文件引用
- **WHEN** 业务工具构造 `localFileVideoUpload` payload
- **THEN** payload SHALL 使用目标服务可读取的 `videoFilePath` 或目标服务明确支持的等价字段
- **AND** payload SHALL 继续包含正确的 `localAccountId` 与 `filename`
- **AND** 业务工具 SHALL 通过受管理 MCP guard 调用 `localFileVideoUpload`

#### Scenario: 目标服务无法读取附件

- **GIVEN** 当前 thread 附件存在且用户已授权
- **AND** 系统无法把附件解析为 `platform-agent-biz` 可读取的文件引用
- **WHEN** 用户请求上传到本地推素材库
- **THEN** 业务工具 SHALL 返回中文诊断，说明附件已收到但素材库上传服务无法读取该文件
- **AND** 诊断 SHALL 区分该问题与缺少附件、参数校验失败、敏感词拦截和平台业务失败
- **AND** 业务工具 SHALL NOT 声称素材已上传成功

#### Scenario: 不可见 sandbox 路径不得直接透传

- **GIVEN** 用户上传附件后，Agent 上下文中的文件路径为 `/mnt/user-data/uploads/<filename>`
- **AND** 目标 MCP 服务端不共享该 sandbox 路径
- **WHEN** 业务工具准备调用 `localFileVideoUpload`
- **THEN** 业务工具 SHALL NOT 仅把 `/mnt/user-data/uploads/<filename>` 作为 `videoFilePath` 透传给 MCP
- **AND** 系统 SHALL 先完成服务端可读引用转换或返回中文失败诊断
- **AND** 失败结果 SHALL NOT 被计为素材库上传成功

### Requirement: 素材库上传成功标准必须来自真实上传接口结果

浏览器验收和用户可见结果 SHALL distinguish chat attachment upload success from local material library upload success. The operation SHALL be considered successful only when `localFileVideoUpload` completes successfully and returns usable material data.

#### Scenario: 附件上传成功但素材库上传未完成

- **GIVEN** 浏览器附件上传接口返回成功
- **AND** `localFileVideoUpload` 未被调用、调用失败或返回文件不可读错误
- **WHEN** 系统向用户展示结果或记录验收状态
- **THEN** 用户可见结果 SHALL 说明附件已上传到对话，但本地推素材库上传未完成
- **AND** 验收记录 SHALL NOT 将该轮标记为素材库上传成功
- **AND** 系统 SHALL 保留中文失败原因用于下一步修复

#### Scenario: 素材库上传成功展示中文摘要

- **GIVEN** `oceanengine_local_material` 已通过真实 MCP 调用执行 `localFileVideoUpload`
- **AND** MCP 返回视频 ID、素材 ID、视频地址、视频大小或其它素材库结果字段
- **WHEN** Agent 生成最终回复
- **THEN** 回复 SHALL 用中文说明视频已上传到本地推素材库
- **AND** 回复 SHALL 展示可用的视频 ID、素材 ID 或视频地址
- **AND** 回复 SHALL NOT 展示 host 绝对路径、sandbox 路径、MCP payload JSON、内部 trace 或平台请求日志 ID

#### Scenario: MCP 返回缺少可确认素材结果

- **GIVEN** `oceanengine_local_material` 已通过真实 MCP 调用执行 `localFileVideoUpload`
- **AND** MCP 返回信息缺少可确认的素材 ID、视频 ID、明确上传状态和重复命中语义
- **WHEN** Agent 生成最终回复或验收记录
- **THEN** 用户可见结果 SHALL NOT 编造素材 ID、视频 ID、上传成功状态或“素材已上传”状态
- **AND** 用户可见结果 SHALL 说明上传接口未返回可确认的素材结果
- **AND** 该轮验收 SHALL NOT 仅凭泛化成功文案计为素材库上传成功

#### Scenario: 重复视频内容命中已有素材

- **GIVEN** 用户通过当前对话附件上传了一个视频文件
- **AND** 该视频内容的 `video_signature` 已经对应本地推素材库中的已有视频素材
- **WHEN** `localFileVideoUpload` 的 MCP 返回信息表明命中已有素材，或返回已有素材的视频 ID / 素材 ID 且带有重复、已存在、已上传、幂等命中等语义
- **THEN** 用户可见结果 SHALL 明确提示“素材已上传”
- **AND** 用户可见结果 SHALL 展示已有的视频 ID 或素材 ID
- **AND** 用户可见结果 SHALL NOT 声称素材中心会新增一个以本轮附件文件名命名的新视频
- **AND** 浏览器验收 SHALL 将该轮记录为重复内容幂等命中，而不是新增素材成功

### Requirement: 附件上传到素材库必须通过真实浏览器验收

`oceanengine-local-material` attachment-based video upload SHALL be validated through the real browser chat flow. Scripts, curl, SDK calls, direct MCP invocations, dry-run, mock results, or tool-name prompts SHALL NOT substitute for acceptance success.

#### Scenario: 真实浏览器附件上传验收

- **GIVEN** 本地前端、Gateway、Agent runtime 和必要的 MCP 服务已启动
- **AND** 测试人员已通过真实浏览器登录测试账号
- **WHEN** 测试人员通过附件控件上传视频，并用自然语言要求上传到本地推素材库
- **THEN** 验收证据 SHALL 显示 Gateway 保存附件成功
- **AND** Langfuse、后端日志或 trace SHALL 显示调用路径经过 `oceanengine_local_material`
- **AND** 证据 SHALL 显示真实调用 `localFileVideoUpload` 或返回明确的目标服务不可读诊断
- **AND** 输入 SHALL NOT 包含 `oceanengine-local-material`、`oceanengine_local_material`、`capability`、`payload_json`、`dry_run` 或底层 MCP tool 名

#### Scenario: 绕过真实用户路径不得计为通过

- **GIVEN** 某次验证通过脚本、curl、SDK、直接 MCP、mock、dry-run 或手工构造 tool payload 完成
- **WHEN** 汇总附件上传到素材库的浏览器验收状态
- **THEN** 该验证 MAY 作为定位证据
- **AND** 该验证 SHALL NOT 作为真实浏览器验收成功
- **AND** 仍必须通过浏览器附件控件和自然语言对话重新执行

#### Scenario: 素材中心数量用于新增成功验收判定

- **GIVEN** 测试人员需要确认一轮真实浏览器上传是否新增了素材库视频
- **AND** 测试人员可以在同一本地推账号的素材中心查看上传前后视频数量
- **WHEN** 上传后素材中心视频数量相比上传前增长
- **THEN** 该轮 MAY 计为新增素材成功
- **AND** 验收记录 SHALL 记录上传前数量、上传后数量和对应 Chrome 线程 ID
- **AND** 用户可见业务回复 SHALL 仍只展示 MCP 返回或后续真实查询可确认的素材字段

#### Scenario: 数量未增长时不得误判新增成功

- **GIVEN** 真实浏览器上传完成后素材中心视频数量没有增长
- **WHEN** `localFileVideoUpload` MCP 返回信息明确表达重复、已存在、已上传或幂等命中
- **THEN** 该轮 SHALL 计为“素材已上传 / 重复命中”
- **AND** 用户可见结果 SHALL 使用“素材已上传”而不是“新增成功”
- **WHEN** MCP 返回信息也缺少可确认素材结果和重复语义
- **THEN** 该轮 SHALL NOT 计为素材库上传成功

### Requirement: 创建项目流程中的视频必须通过素材管理上传或选择

创建项目业务流程需要视频素材时，系统 SHALL 通过 `oceanengine_local_material` 上传用户明确授权的视频或查询素材库候选。系统 SHALL NOT 扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录来猜测素材。

#### Scenario: 用户提供本地视频文件

- **GIVEN** 用户在创建项目流程中要求添加视频
- **AND** 用户明确提供或授权了 `video_file_path`
- **WHEN** 系统需要把视频加入素材库
- **THEN** 系统 SHALL 调用 `oceanengine_local_material` 的上传视频能力
- **AND** 上传前 SHALL 执行素材管理本地文件参数校验
- **AND** 校验失败时 SHALL 只追问当前一个视频参数问题
- **AND** 系统 SHALL NOT 直接调用 `localFileVideoUpload` MCP tool

#### Scenario: 用户要求从素材库选择视频

- **GIVEN** 用户在创建项目流程中要求从素材库选择视频
- **WHEN** 系统需要展示可选视频
- **THEN** 系统 SHALL 调用 `oceanengine_local_material` 的素材库视频查询能力
- **AND** 候选结果 SHALL 以 `data.clarification.input_control.type=choice_cards` 或等价结构返回
- **AND** 每个候选 SHALL 保留用于回填的 `value`、用户可读 `label`、安全业务摘要 `metadata` 和原始顺序
- **AND** 用户可见文本 SHALL 不展示内部 MCP tool 名、平台请求日志 ID 或原始 JSON 包装

#### Scenario: 视频来源未被用户授权

- **GIVEN** 创建项目流程需要视频
- **AND** 用户没有提供或授权视频文件、视频 URL、签名或素材库候选
- **WHEN** 系统准备获取视频
- **THEN** 系统 SHALL 返回中文单问题追问
- **AND** 系统 SHALL NOT 从本机目录、最近文件、浏览器记录、剪贴板或历史会话中推断视频来源
- **AND** 系统 SHALL NOT 生成虚假的素材候选

### Requirement: 创建项目流程必须按投放目标校验视频数量

创建项目流程选择视频时，系统 SHALL 按投放目标维护默认视频数量要求：团购成交需要 10 条视频，其它投放目标需要 3 到 5 条视频。数量不足或过多时，系统 SHALL 返回中文提示或候选补齐，不得静默裁剪用户选择。

#### Scenario: 团购成交视频数量要求

- **GIVEN** 创建项目流程的投放目标为团购成交
- **WHEN** 用户选择的视频数量少于 10 条
- **THEN** 系统 SHALL 返回中文提示说明团购成交需要 10 条视频
- **AND** 系统 SHALL 可继续通过素材库候选 `choice_cards` 引导用户补齐
- **AND** 系统 SHALL NOT 静默使用不足 10 条视频继续创建单元素材

#### Scenario: 其它目标视频数量要求

- **GIVEN** 创建项目流程的投放目标不是团购成交
- **WHEN** 用户选择的视频数量少于 3 条或超过 5 条
- **THEN** 系统 SHALL 返回中文提示说明当前目标需要 3 到 5 条视频
- **AND** 用户明确坚持边界外数量时 SHALL 由后续单元或素材规则校验处理
- **AND** 系统 SHALL NOT 自行截断、抽样或删除用户选择的视频

#### Scenario: 素材候选为空或查询失败

- **GIVEN** 系统已调用素材管理查询候选视频
- **WHEN** MCP 工具缺失、MCP 调用失败、平台业务失败或返回空候选
- **THEN** 系统 SHALL 返回中文失败或暂无候选说明
- **AND** 系统 SHALL NOT 生成空的或臆造的 `choice_cards.options`
- **AND** 该结果 SHALL NOT 被当作创建项目流程成功
