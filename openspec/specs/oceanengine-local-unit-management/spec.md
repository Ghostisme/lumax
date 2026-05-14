# oceanengine-local-unit-management Specification

## Purpose
约束 `oceanengine-local-unit` 作为独立标准业务 Skill 覆盖巨量引擎本地推单元管理模块，确保单元创建、更新、查询、状态变更、门店商品查询和审核建议查询均通过原生业务工具、规则配置、本地校验、受保护 MCP 调用和中文结构化输出完成。
## Requirements
### Requirement: 单元管理 Skill 必须覆盖官方模块接口

`oceanengine-local-unit` SHALL 作为独立标准业务 Skill 覆盖巨量引擎开放平台“单元管理模块”的 7 个接口，并保持接口范围与官方模块页子文档一致。每个接口的 reference 和 rule SHALL 能追溯到对应官方 `doc_id`，并在参数校准后通过重复核对证明与官方参数表一致。

#### Scenario: 维护人员检查官方参数校准结果

- **GIVEN** 维护人员打开 `skills/custom/oceanengine-local-unit/references/index.md`
- **WHEN** 查看 7 个 capability 对应的官方 `doc_id`
- **THEN** 每个 capability SHALL 指向当前官方子文档
- **AND** 对应 `references/*.md` SHALL 摘要说明官方普通必填、条件必填、枚举、数组限制和默认语义
- **AND** 对应 `rules/*.json` SHALL 用机器可执行规则表达这些参数要求

#### Scenario: 完成后执行五轮重复核对

- **GIVEN** 实现人员完成单元管理官方参数校准
- **WHEN** 准备结束任务
- **THEN** 实现人员 SHALL 完成 5 轮重复检查
- **AND** 每轮 SHALL 分别覆盖官方参数表与 reference、官方参数表与 rules、rules 与测试、rules 与 MCP payload 构造、旧错误口径残留搜索
- **AND** 任一轮发现差异时 SHALL 修复后从对应核对点重新检查

### Requirement: 单元管理必须复用标准业务 Skill 结构

`oceanengine-local-unit` SHALL 复用标准业务 Skill 的渐进式文件结构，使 `SKILL.md` 只承担导航和执行约束，接口事实和机器可执行规则分别落在 `references/` 与 `rules/`。

#### Scenario: Agent 处理单个单元管理能力

- **GIVEN** 用户请求命中单元管理的某个具体能力
- **WHEN** Agent 按 `SKILL.md` 读取上下文
- **THEN** Agent SHALL 先读取 `references/index.md` 定位 capability
- **AND** Agent SHALL 只读取该 capability 对应的 reference 和 rule
- **AND** Agent SHALL NOT 一次性加载无关接口的全部 reference 或规则配置

#### Scenario: 维护人员查看 Skill 主文件

- **GIVEN** 维护人员打开 `skills/custom/oceanengine-local-unit/SKILL.md`
- **WHEN** 查看文件内容
- **THEN** `SKILL.md` SHALL 包含使用流程、原生业务工具入口、接口导航和 MCP 安全约束
- **AND** 详细字段、枚举、示例和约束 SHALL 放在 `references/` 或 `rules/` 中

### Requirement: 单元管理必须通过原生业务工具执行

`oceanengine-local-unit` 的全部 capability SHALL 在 DeerFlow 运行时通过 `oceanengine_local_unit` 原生业务工具执行，并使用 `capability`、`payload_json` 和可选 `dry_run` 作为调用入口。`oceanengine_local_unit` 的主实现 SHALL 位于仓库根目录 `tools/oceanengine_local_unit.py`，其运行时依赖 SHALL 位于 `tools/` 同域模块内；系统 SHALL NOT 保留 `deerflow.tools.oceanengine_local_unit` 兼容导入路径。

#### Scenario: 主 Agent 调用单元管理能力

- **GIVEN** 用户请求命中 `oceanengine-local-unit` 中任一 capability
- **WHEN** 主 Agent 需要执行该业务能力
- **THEN** 主 Agent SHALL 调用 `oceanengine_local_unit` 原生业务工具
- **AND** 调用参数 SHALL 包含 `capability`、`payload_json` 和可选 `dry_run`
- **AND** 主 Agent SHALL NOT 直接调用 `nacos-mcp-router_use_tool`、底层 `localUnit*` MCP 工具、curl、HTTP API、SDK 或子代理来替代该业务工具

#### Scenario: 原生业务工具按 capability 路由

- **GIVEN** `rules/index.json` 中存在目标 capability 条目
- **WHEN** `oceanengine_local_unit` 收到该 capability
- **THEN** 业务工具 SHALL 加载条目声明的 `rules/*.json`
- **AND** 业务工具 SHALL 复用 `tools/` 同域运行时执行参数校验、字段映射、MCP payload 构造和必要的后置确认
- **AND** 返回结果 SHALL 包含 `execution_source=deerflow-native-tool`、`business_tool_name=oceanengine_local_unit`、`mcp_server_name` 和 `mcp_tool_name`

#### Scenario: 单元管理工具主实现位于根目录 tools

- **GIVEN** 运行时配置需要解析 `oceanengine_local_unit`
- **WHEN** 读取 `config.yaml` 或 `config.example.yaml` 中的工具注册
- **THEN** 注册路径 SHALL 使用 `tools.oceanengine_local_unit:oceanengine_local_unit_tool`
- **AND** `backend/packages/harness/deerflow/tools/oceanengine_local_unit.py` SHALL 不存在
- **AND** 生产代码和测试 SHALL NOT 依赖 `deerflow.tools.oceanengine_local_unit`

#### Scenario: 单元管理 native tool 不依赖 skill scripts 路径

- **GIVEN** 调用方从干净 `sys.path` 环境导入 `tools.oceanengine_local_unit`
- **AND** `sys.path` 中不包含 `skills/custom/oceanengine-local-unit/scripts` 或 `skills/custom/oceanengine-local-project/scripts`
- **WHEN** 调用 `run_oceanengine_local_unit` 执行任一 capability 的 dry-run 或 mock MCP 路径
- **THEN** 调用 SHALL 使用 `tools/` 同域运行时完成规则加载和 endpoint 执行
- **AND** 调用完成后 `sys.path` SHALL NOT 新增上述 skill scripts 路径
- **AND** `tools/oceanengine_local_unit.py` SHALL NOT 导入 `common.rule_loader`、`common.endpoint_runner` 或其它来自 `skills/custom/**/scripts` 的运行时模块

#### Scenario: 未知 capability 被本地拦截

- **GIVEN** 主 Agent 或调用方传入不在 `rules/index.json` 中的 capability
- **WHEN** `oceanengine_local_unit` 解析能力索引
- **THEN** 业务工具 SHALL 返回失败或抛出可转为失败响应的中文诊断
- **AND** 诊断 SHALL 列出当前支持的 capability
- **AND** 业务工具 SHALL NOT 发起 MCP 调用

### Requirement: 单元管理参数校验必须本地硬校验

`oceanengine-local-unit` 的所有 endpoint SHALL 在调用 MCP 前完成本地规则参数校验，覆盖普通必填、条件必填、条件禁止、互斥、至少一个、类型、枚举、长度、范围、格式、数组项和批量项递归等规则。单元管理字段的中文说明、普通必填、条件必填、条件禁止、枚举候选、数组长度、默认值和适用场景 SHALL 与官方入口页 `1808003978921193` 下对应子文档的请求参数表保持一致。

#### Scenario: 创建单元按官方必填口径校验

- **GIVEN** 用户请求 `create-unit`
- **WHEN** endpoint 校验普通必填字段
- **THEN** 普通必填 SHALL 只包含官方普通必填字段 `local_account_id`、`project_id`、`name`
- **AND** `aweme_id`、`enable_graphic_delivery`、`live_material_type`、`customer_material_list`、`procedural_material`、`promotion_card_info` SHALL 按官方条件必填或条件禁止规则校验
- **AND** `video_hp_visibility` SHALL 作为可选字段处理，并保留官方默认语义

#### Scenario: 更新单元按官方必填口径校验

- **GIVEN** 用户请求 `update-unit`
- **WHEN** endpoint 校验普通必填字段
- **THEN** 普通必填 SHALL 只包含 `local_account_id`、`promotion_id`
- **AND** `aweme_id` SHALL 按官方条件字段处理
- **AND** 可选素材、图文、卡片和主页可见性字段 SHALL NOT 被误设为普通必填

#### Scenario: 批量状态更新递归校验批量项

- **GIVEN** 用户请求 `batch-update-unit-status`
- **WHEN** endpoint 校验 `data`
- **THEN** `data` SHALL 是长度 `1-50` 的数组
- **AND** 每个 `data[]` 项 SHALL 校验必填 `promotion_id` 和 `opt_status`
- **AND** `opt_status` SHALL 只允许 `ENABLE` 或 `PAUSED`
- **AND** 错误 SHALL 标明具体项序号或业务标识

#### Scenario: 门店商品查询不强制传入可选营销目的

- **GIVEN** 用户请求 `list-products-by-poi-ids`
- **AND** 用户已提供 `local_account_id` 和 `poi_ids`
- **AND** 用户未提供 `local_delivery_scene`
- **WHEN** endpoint 执行本地校验
- **THEN** endpoint SHALL NOT 因缺少 `local_delivery_scene` 判定校验失败
- **AND** reference SHALL 说明官方默认语义为交易广告，即 `CONTENT_HEAT`、`POI_RECOMMEND`、`PRODUCT_PAY`

#### Scenario: 审核建议批量查询限制单元 ID 数量

- **GIVEN** 用户请求 `batch-get-unit-reject-reasons`
- **WHEN** endpoint 校验 `promotion_ids`
- **THEN** `promotion_ids` SHALL 是长度 `1-10` 的数组
- **AND** 超过 10 个单元 ID 时 SHALL 返回中文结构化错误
- **AND** endpoint SHALL NOT 调用 MCP

### Requirement: 单元管理 MCP payload 必须按规则映射

`oceanengine-local-unit` SHALL 使用规则配置将用户侧 snake_case 字段和值映射为 MCP schema 需要的字段名、包装结构和枚举值。官方参数表和当前 MCP schema 存在字段名或枚举口径差异时，规则 SHALL 显式声明映射或返回中文诊断，不得保留无说明的错误枚举值。

#### Scenario: 素材枚举按官方口径接收

- **GIVEN** 用户请求 `create-unit` 或 `update-unit`
- **AND** 用户填写 `customer_material_list[].image_mode` 或 `procedural_material.video_material_list[].image_mode`
- **WHEN** endpoint 执行本地校验
- **THEN** 用户侧规则 SHALL 接收官方枚举 `IMAGE_MODE_VIDEO` 和 `IMAGE_MODE_VIDEO_VERTICAL`
- **AND** 如 MCP schema 需要不同 wire 值，payload 构造 SHALL 通过规则映射显式转换
- **AND** 本地 reference 和错误提示 SHALL 使用官方中文说明“横版视频”“竖版视频”

#### Scenario: 单元列表状态枚举按官方口径接收

- **GIVEN** 用户请求 `list-units`
- **WHEN** endpoint 校验 `filtering.promotion_status_first`
- **THEN** 规则 SHALL 接收官方枚举 `PROMOTION_STATUS_ALL`、`PROMOTION_STATUS_DELETED`、`PROMOTION_STATUS_DISABLE`、`PROMOTION_STATUS_DONE`、`PROMOTION_STATUS_ENABLE`、`PROMOTION_STATUS_FROZEN`、`PROMOTION_STATUS_NOT_DELETE`
- **AND** 如 MCP schema 需要不同 wire 值，payload 构造 SHALL 通过规则映射显式转换
- **AND** 用户可见文案 SHALL 使用官方术语“单元一级状态”

#### Scenario: 列表二级状态按官方条件处理

- **GIVEN** 用户请求 `list-units`
- **WHEN** `filtering.promotion_status_first=PROMOTION_STATUS_DISABLE`
- **THEN** `filtering.promotion_status_second` SHALL 按官方文档作为条件必填字段校验
- **AND** 当 `filtering.promotion_status_first` 不是 `PROMOTION_STATUS_DISABLE` 时，`filtering.promotion_status_second` SHALL 按官方文档作为无效传入处理或返回中文诊断

### Requirement: 单元管理变更操作必须后置确认

`oceanengine-local-unit` 的创建、更新和批量状态变更能力 SHALL 在 MCP 调用成功后执行后置查询或等价确认，确认失败不得声称业务已完成。后置确认 SHALL 将详情查询或列表查询中的非零业务 `code`、业务错误文本、无法解析目标详情、目标资源不存在或目标状态不一致识别为确认失败。

#### Scenario: 创建单元成功后确认

- **GIVEN** 创建单元 MCP 调用返回成功
- **WHEN** endpoint 执行后置确认
- **THEN** endpoint SHALL 查询或识别新单元的可确认状态
- **AND** 只有确认到目标单元存在或目标状态一致时才返回业务成功

#### Scenario: 创建单元详情确认返回业务失败

- **GIVEN** 创建单元 MCP 调用返回成功并包含 `promotionId`
- **AND** 后置 `localUnitDetail` 查询返回非零业务 `code`、业务错误文本或无法解析目标单元详情
- **WHEN** endpoint 汇总后置确认结果
- **THEN** endpoint SHALL 返回 `success=false`
- **AND** 错误摘要 SHALL 包含后置确认失败原因
- **AND** endpoint SHALL NOT 声称单元创建已完成

#### Scenario: 更新单元成功后确认

- **GIVEN** 更新单元 MCP 调用返回成功
- **WHEN** endpoint 执行后置确认
- **THEN** endpoint SHALL 查询目标 `promotion_id` 的详情或列表摘要
- **AND** 只有确认关键字段与预期一致时才返回业务成功

#### Scenario: 批量更新单元状态部分失败

- **GIVEN** 批量更新单元状态 MCP 调用返回成功
- **WHEN** endpoint 执行逐项后置确认
- **THEN** endpoint SHALL 对每个 `promotion_id` 返回确认结果
- **AND** 任一项确认失败时 SHALL 返回失败或部分失败摘要

### Requirement: 单元管理受管理 MCP 工具必须被 guard 保护

`platform-agent-biz` 中归属 `oceanengine-local-unit` 的 7 个 MCP 工具 SHALL 只能在 `oceanengine_local_unit` 业务工具允许的上下文中调用。`tools/managed_mcp_guard.py` SHALL 作为唯一主实现和唯一导入路径登记项目管理与单元管理的受保护 MCP tool；系统 SHALL NOT 保留或使用 `deerflow.tools.managed_mcp_guard` 模块路径。

#### Scenario: 主 Agent 直接调用单元管理 MCP 工具

- **GIVEN** 某调用路径准备直接调用 `nacos-mcp-router_use_tool`
- **AND** 参数中的 `mcp_server_name=platform-agent-biz`
- **AND** 参数中的 `mcp_tool_name` 属于 `oceanengine-local-unit` 管理的单元管理工具
- **WHEN** 当前上下文不是 `oceanengine_local_unit` 业务工具内部调用
- **THEN** 系统 SHALL 阻断该调用
- **AND** 错误 SHALL 提示必须调用 `oceanengine_local_unit`
- **AND** 系统 SHALL NOT 将该调用发送到 Nacos MCP Router

#### Scenario: 业务工具内部调用单元管理 MCP 工具

- **GIVEN** 用户输入已通过本地规则校验
- **AND** `oceanengine_local_unit` 已进入允许受管理 MCP 调用的上下文
- **WHEN** 公共 endpoint runner 调用对应单元管理 MCP 工具
- **THEN** guard SHALL 允许该调用继续
- **AND** 调用失败时系统 SHALL 返回该目标的失败诊断
- **AND** 系统 SHALL NOT 自动切换到其它 MCP server、其它 MCP tool、curl、HTTP API 或 SDK

#### Scenario: 系统不保留 deerflow guard 模块路径

- **GIVEN** 维护人员检查仓库代码
- **WHEN** 搜索 `deerflow.tools.managed_mcp_guard`
- **THEN** 生产代码 SHALL NOT 引用该模块路径
- **AND** `backend/packages/harness/deerflow/tools/managed_mcp_guard.py` SHALL 不存在
- **AND** 业务工具和 MCP 工具加载器 SHALL 直接导入 `tools.managed_mcp_guard`

#### Scenario: 根目录 guard 登记单元管理 MCP 工具

- **GIVEN** 维护人员打开 `tools/managed_mcp_guard.py`
- **WHEN** 查看受管理 MCP tool 注册表
- **THEN** 注册表 SHALL 包含 `localUnitCreate`、`localUnitUpdate`、`localUnitList`、`localUnitDetail`、`localUnitStatusBatchUpdate`、`localProductGetByPoiIds`、`localPromotionRejectReasonBatchGet`
- **AND** 这些 tool 的 owner SHALL 为 `oceanengine_local_unit`
- **AND** guard 允许上下文 SHALL 只由 `tools.managed_mcp_guard` 中的单一 `ContextVar` 管理

### Requirement: 单元管理输出必须面向用户中文展示

`oceanengine-local-unit` SHALL 返回统一结构化结果，并为主 Agent 提供可直接展示给用户的中文 `user_visible_text` 或等价字段。`oceanengine_local_unit` LangChain tool 返回给 Agent 的默认结果 SHALL 隐藏原始 `data.result`，不得让主 Agent 默认遍历英文 API 字段名、英文枚举值或原始 MCP 响应。

#### Scenario: 查询接口返回成功

- **GIVEN** 用户请求获取单元列表、单元详情、门店商品或审核建议
- **WHEN** MCP 调用成功并返回数据
- **THEN** 业务工具 SHALL 返回 `success=true`、中文 `message` 和业务 `data`
- **AND** `data` SHALL 包含面向用户的中文字段名和中文值
- **AND** Agent 最终回复 SHALL NOT 展示英文 API 字段名、英文枚举值或原始响应

#### Scenario: Agent 可见结果隐藏原始响应

- **GIVEN** `oceanengine_local_unit_tool` 收到底层成功结果
- **AND** 底层结果包含 `data.result`、英文 API 字段名或英文枚举值
- **WHEN** tool wrapper 生成返回给主 Agent 的 JSON 字符串
- **THEN** 返回结果 SHALL 移除或隐藏 `data.result`
- **AND** 返回结果 SHALL 提供中文 `data.user_visible_text` 或等价中文摘要
- **AND** 返回结果 SHALL NOT 包含默认展示不需要的英文枚举码或原始 MCP 响应正文

#### Scenario: 校验失败返回中文追问

- **GIVEN** endpoint 本地校验失败
- **WHEN** 业务工具返回失败结果
- **THEN** 返回结果 SHALL 包含 `success=false`、中文 `message` 和结构化 `errors`
- **AND** Agent 面向用户的最终回复 SHALL 展示这些 `errors` 对应的中文文字
- **AND** Agent SHALL NOT 只输出内部字段名、英文枚举码或原始 JSON

### Requirement: 页面验收必须证明单元管理业务工具可用

实现完成后，`oceanengine-local-unit` SHALL 通过 DeerFlow 前端页面验证用户对话可以调用 `oceanengine_local_unit` 原生业务工具，并保留可追踪证据。

#### Scenario: 页面请求调用单元管理业务工具

- **GIVEN** 本地 DeerFlow 前端、Gateway 和 agent runtime 已启动
- **AND** `oceanengine_local_unit` 已注册为可用工具
- **WHEN** 测试人员在前端对话页面提交单元列表或单元详情查询请求
- **THEN** 页面 SHALL 返回来自业务工具结构化结果的中文反馈
- **AND** 后端日志、trace 或响应诊断 SHALL 显示调用路径经过 `oceanengine_local_unit`
- **AND** 证据 SHALL 显示主 Agent 没有直接调用受保护的 `nacos-mcp-router_use_tool`

#### Scenario: 页面验收发现调用路径异常

- **GIVEN** 页面请求已提交
- **WHEN** 证据显示业务工具未被选择、参数校验未按规则执行、页面结果展示异常或请求绕过业务工具直连 MCP
- **THEN** 实现人员 SHALL 修复工具注册、skill 导航、调用保护、参数整理或结果展示问题
- **AND** 修复后 SHALL 重新执行同类页面验收

### Requirement: 单元管理响应字段必须与官方应答表同步

`oceanengine-local-unit` 的每个 capability SHALL 在 reference 文档和 rule 配置中记录官方子文档“应答字段”表。`rules/*.json` SHALL 使用 `output.response_fields` 记录响应字段路径、当前层字段名、中文标签、类型、官方描述和默认展示策略。响应字段同步 SHALL NOT 改变 MCP 调用、请求 payload 构造或请求参数校验。

#### Scenario: 创建和更新单元记录官方应答字段

- **GIVEN** 维护人员检查 `create-unit` 和 `update-unit`
- **WHEN** 查看对应 `references/*.md` 和 `rules/*.json`
- **THEN** `create-unit` SHALL 记录 `code`、`message`、`data`、`data.promotion_id`、`request_id`
- **AND** `data.promotion_id` SHALL 作为默认展示字段
- **AND** `update-unit` SHALL 记录 `code`、`message`、`data`、`request_id`
- **AND** `update-unit` SHALL NOT 臆造官方未声明的业务响应字段

#### Scenario: 单元列表记录官方列表和分页应答字段

- **GIVEN** 维护人员检查 `list-units`
- **WHEN** 查看 `output.response_fields`
- **THEN** 字段 SHALL 覆盖 `data.promotion_list[]` 及其官方子字段 `project_id`、`local_account_id`、`ad_type`、`promotion_id`、`promotion_name`、`promotion_create_time`、`promotion_modify_time`、`promotion_status_first`、`promotion_status_second`、`learning_phase`、`aweme_id`、`aweme_name`
- **AND** 字段 SHALL 覆盖分页字段 `data.page_info.page`、`data.page_info.page_size`、`data.page_info.total_number`、`data.page_info.total_page`
- **AND** 用户可见标签 SHALL 使用官方术语“单元类型”

#### Scenario: 单元详情记录官方素材、图文和卡片应答字段

- **GIVEN** 维护人员检查 `get-unit-detail`
- **WHEN** 查看 `output.response_fields`
- **THEN** 字段 SHALL 覆盖官方基础字段 `data.promotion_id`、`data.enable_graphic_delivery`、`data.aweme_id`、`data.video_hp_visibility`、`data.live_material_type`
- **AND** 字段 SHALL 覆盖 `data.customer_material_list[]` 下的标题和视频素材字段
- **AND** 字段 SHALL 覆盖 `data.procedural_material.title_material_list[]`、`video_material_list[]`、`carousel_material_list[]` 及其图片、音乐字段
- **AND** 字段 SHALL 覆盖 `data.promotion_card_info` 下的卡片标题、配图、卖点、行动号召和智能生成开关字段

#### Scenario: 批量状态、门店商品和审核建议记录官方应答字段

- **GIVEN** 维护人员检查批量状态、门店商品和审核建议 capability
- **WHEN** 查看对应 `output.response_fields`
- **THEN** `batch-update-unit-status` SHALL 记录 `data.promotion_ids`、`data.errors[]`、`data.errors[].promotion_id`、`data.errors[].error_message`
- **AND** `list-products-by-poi-ids` SHALL 记录 `data.product_ids`
- **AND** `batch-get-unit-reject-reasons` SHALL 记录 `data.list[]`、`data.list[].promotion_id`、`data.list[].material_reject[]`、审核来源、审核素材类型、拒绝内容、视频素材、图片素材、拒绝理由和审核建议字段

#### Scenario: 响应字段基线参与展示和漂移诊断

- **GIVEN** MCP 返回成功响应
- **WHEN** endpoint runner 生成用户可见展示和诊断信息
- **THEN** 已配置为 `display=default` 的响应字段 SHALL 可用于成功摘要展示
- **AND** `display=diagnostic` 字段 SHALL 作为已知官方字段参与未映射字段排除
- **AND** 官方未记录但 MCP 返回的额外字段 SHALL 继续进入 `diagnostics.unmapped_response_fields`

### Requirement: 单元管理必须完成浏览器自然语言连续验收

`oceanengine-local-unit` SHALL 在归档前完成 Chrome 浏览器自然语言验收，证明前端页面、Gateway、Agent runtime、`oceanengine_local_unit` 原生业务工具、受保护 MCP 调用和测试环境 Java 服务的端到端链路可用。

#### Scenario: 验收覆盖全部单元管理能力

- **GIVEN** 本地前端、Gateway、Agent runtime、MCP router 和 Java 测试环境依赖已启动
- **AND** `oceanengine_local_unit` 已注册为主 Agent 可用的原生业务工具
- **WHEN** 验收人员在 Chrome 页面以自然语言提交本地推单元管理请求
- **THEN** 验收 SHALL 覆盖 `create-unit`、`update-unit`、`list-units`、`get-unit-detail`、`batch-update-unit-status`、`list-products-by-poi-ids` 和 `batch-get-unit-reject-reasons`
- **AND** 每个 capability SHALL 连续成功 5 次后才进入下一个 capability
- **AND** 每次成功计数用例 SHALL 使用不同参数、不同单元、不同筛选条件或不同批量组合，以提升覆盖率

#### Scenario: 自然语言提示不得降低真实调用难度

- **GIVEN** 验收人员正在浏览器页面提交测试请求
- **WHEN** 编写自然语言测试提示
- **THEN** 提示 SHALL NOT 指定底层 MCP 工具名、受保护 MCP 接口名、`nacos-mcp-router_use_tool` 或固定返回字段
- **AND** 提示 SHALL 以用户业务意图描述要创建、更新、查询、暂停或获取审核建议的目标
- **AND** 如果提示导致 Agent 要求澄清、调用错误能力、跳过 `oceanengine_local_unit` 或直接暴露底层 MCP 细节，则该轮 SHALL 不计入连续成功

#### Scenario: 失败后清零并重新累计

- **GIVEN** 某个 capability 正在累计连续成功次数
- **WHEN** 发生业务工具未调用、调用路径错误、参数整理错误、页面提交未生成 run、run 被取消、run 卡住、业务校验失败、后置确认失败或测试环境限制导致不可达成的成功路径
- **THEN** 当前 capability 的连续成功次数 SHALL 清零
- **AND** 验收人员 SHALL 记录失败摘要、根因层级和修复或规避方式
- **AND** 修复或调整测试路径后 SHALL 从 0 开始重新累计，直到重新达到连续 5 次成功

#### Scenario: 验收证据必须可追踪且不泄露敏感信息

- **GIVEN** 浏览器验收已经执行
- **WHEN** 维护人员查看验收记录
- **THEN** 记录 SHALL 包含 capability、轮次、自然语言输入摘要、线程或 run 标识、业务工具调用证据、用户可见结果摘要和连续成功计数
- **AND** 记录 SHALL NOT 保存登录密码、Cookie、token、浏览器本地存储值或未授权素材路径
- **AND** 上传素材只允许使用用户在当前任务中明确提供或授权的素材文件、签名和元数据

### Requirement: 单元管理参数校验失败一次只追问一个问题

`oceanengine_local_unit` SHALL 在参数校验失败时只向 Agent 和用户暴露首个可行动中文问题。内部校验 MAY 继续收集完整错误列表用于计数、日志和测试，但面向 Agent 的结构化结果 SHALL NOT 同时暴露多个缺参问题，避免最终回复一次追问多个参数。

#### Scenario: 多个普通必填缺失时只展示首个问题

- **GIVEN** 用户请求命中 `oceanengine_local_unit`
- **AND** 本地参数校验发现多个普通必填字段缺失
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.user_visible_text` SHALL 只包含规则顺序中的第一个缺失字段中文问题
- **AND** `errors` SHALL 只保留该第一个可见错误
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量

#### Scenario: 条件必填缺失时只展示当前首个问题

- **GIVEN** 用户输入触发单元管理条件必填规则
- **AND** 本地参数校验发现多个条件必填或批量项错误
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** 用户可见结果 SHALL 只展示校验顺序中的首个可行动中文问题
- **AND** 后续问题 SHALL 等用户补充首个问题后在下一轮重新校验时继续追问

#### Scenario: Skill 入口不得直接汇总多个缺失项

- **GIVEN** 用户通过自然语言请求创建、更新、查询或批量处理本地推单元
- **AND** 用户缺少多个官方请求参数
- **WHEN** 主 Agent 已识别请求属于 `oceanengine-local-unit`
- **THEN** 主 Agent SHALL 先调用 `oceanengine_local_unit` 原生业务工具执行本地校验
- **AND** 主 Agent SHALL NOT 直接调用 `ask_clarification` 自行汇总多个缺失项
- **AND** 最终用户可见结果 SHALL 只展示一个中文补充问题

#### Scenario: 非参数补齐类失败不被改写为追问

- **GIVEN** `oceanengine_local_unit` 已通过本地参数校验
- **WHEN** 失败原因是 MCP 工具缺失、MCP 调用失败、平台业务失败、后置确认失败或响应展示异常
- **THEN** 业务工具 SHALL 按现有中文诊断展示失败原因
- **AND** 系统 SHALL NOT 将这些失败裁剪成单个参数追问

### Requirement: 单元管理 MCP 调用必须通过 Nacos 解析真实服务端点

`oceanengine-local-unit` 在通过原生业务工具调用 `platform-agent-biz` 单元管理 MCP tool 前，SHALL 以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源解析目标 MCP server 的实际地址、端口和路径。业务工具 SHALL NOT 将 `127.0.0.1:18000` 或其它本机固定 Router 地址作为默认业务兜底端点。

#### Scenario: Nacos 解析到单元管理 MCP 服务端点

- **GIVEN** 用户请求命中 `oceanengine-local-unit` 中任一需要 MCP 调用的 capability
- **AND** 本地参数校验已通过
- **AND** Nacos 中存在 `platform-agent-biz` 并能解析出实际 MCP endpoint
- **WHEN** 原生业务工具调用目标单元管理 MCP tool
- **THEN** 调用 SHALL 发送到 Nacos 解析出的实际 MCP endpoint
- **AND** payload SHALL 继续按单元管理 rule 中的 MCP 字段映射构造
- **AND** 系统 SHALL NOT 使用 `http://127.0.0.1:18000/mcp/` 作为默认业务兜底地址

#### Scenario: Nacos 未注册单元管理目标 MCP server

- **GIVEN** 用户请求命中单元管理 capability
- **AND** 本地参数校验已通过
- **WHEN** 系统无法从 Nacos 或 DeerFlow Nacos MCP 配置解析到 `platform-agent-biz`
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明 Nacos 中未找到目标 MCP server 或配置不可用
- **AND** 系统 SHALL NOT 继续请求本机固定 Router 地址
- **AND** 系统 SHALL NOT 改用 curl、SDK、HTTP API、mock 或其它 MCP server

#### Scenario: 单元管理目标 MCP endpoint 不可达

- **GIVEN** Nacos 已返回 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 本地参数校验已通过
- **WHEN** 系统连接该 endpoint 失败、超时或返回不可用错误
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明解析到的 MCP 服务不可达
- **AND** 失败结果 SHALL NOT 声称单元管理操作已完成
- **AND** 系统 SHALL NOT 自动切换到本机固定 Router、curl、SDK、HTTP API 或 mock

#### Scenario: 单元管理目标 MCP tool 缺失

- **GIVEN** Nacos 已解析到 `platform-agent-biz` 的实际 MCP endpoint
- **AND** 目标单元管理 capability 声明了 `mcp_tool_name`
- **WHEN** 解析到的 MCP 服务未暴露该 tool
- **THEN** 原生业务工具 SHALL 返回中文失败诊断，说明目标 MCP tool 未注册或不可用
- **AND** 系统 SHALL NOT 臆造 MCP tool 名
- **AND** 系统 SHALL NOT 改用其它 tool 或其它调用协议

### Requirement: 创建项目后单元名称必须按业务默认生成

当创建项目流程需要继续创建或配置单元时，`oceanengine-local-unit` SHALL 支持使用业务默认规则生成单元名称。默认名称 SHALL 使用执行日期、地域、定向类型和年龄组成；当流程态包含非空投手姓名时，默认名称 SHALL 在末尾追加投手姓名首字母大写。默认项目名和默认单元名 SHALL 使用同一套命名规则，且在用户未显式覆盖时保持一致。品牌另有要求时才由用户明确覆盖。

#### Scenario: 生成包含投手后缀的默认单元名称

- **GIVEN** 创建项目流程已收集到项目创建所需业务信息
- **AND** 流程态包含地域、定向类型、年龄和非空投手姓名
- **AND** 用户没有提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 投手姓名首字母大写
- **AND** 系统 SHALL NOT 把投手姓名作为自造字段写入 `localProjectCreate` payload

#### Scenario: 拿不到投手姓名时省略投手后缀

- **GIVEN** 创建项目流程需要生成默认单元名称
- **AND** 流程态包含地域、定向类型和年龄
- **AND** 系统拿不到非空投手姓名
- **AND** 用户没有提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄
- **AND** 单元名称 SHALL NOT 追加 `X`、`--`、`未知`、`None`、`null` 或其它投手占位符
- **AND** 系统 SHALL NOT 把缺失投手姓名写入 `localProjectCreate` payload

#### Scenario: 未提供单元名称时默认复用项目名

- **GIVEN** 创建项目流程已生成项目名
- **AND** 用户没有显式提供品牌自定义单元名称规则
- **WHEN** 系统生成单元名称
- **THEN** 单元名称 SHALL 默认复用项目名
- **AND** 单元名称 SHALL NOT 再按另一套规则生成不同名称
- **AND** 如果项目名是默认生成的名称，项目名和单元名 SHALL 完全一致

#### Scenario: 品牌自定义名称覆盖默认规则

- **GIVEN** 用户明确提供品牌自定义单元名称
- **WHEN** 系统生成单元名称
- **THEN** 系统 SHALL 使用用户提供的名称
- **AND** 系统 SHALL NOT 再追加执行日期、地域、定向类型、年龄或投手首字母后缀

### Requirement: 创建项目后素材配置必须落到单元管理链路

视频素材、标题、投放卡片和封面配置属于单元素材链路。创建项目流程 SHALL 在项目创建成功后通过 `oceanengine_local_unit` 写入这些字段，不得把它们作为 `localProjectCreate` 字段透传。

#### Scenario: 自选素材配置到单元

- **GIVEN** 创建项目流程已创建项目
- **AND** 投放目标为线上互动
- **WHEN** 用户需要使用自选素材
- **THEN** 系统 SHALL 在单元管理链路中表达自选素材配置
- **AND** 素材字段 SHALL 使用 `customer_material_list`、`procedural_material` 或当前单元规则声明的字段
- **AND** 系统 SHALL NOT 自造 `localProjectCreate` 字段表达自选素材

#### Scenario: AI 优化封面默认不启用

- **GIVEN** 创建项目流程已选择视频素材
- **AND** 用户没有明确要求启用 AI 优化封面
- **WHEN** 系统构造单元素材 payload
- **THEN** AI 优化封面 SHALL 默认不启用
- **AND** 如果当前单元规则没有独立开关字段，系统 SHALL 仅使用已选素材的封面 URI 或保持字段缺省
- **AND** 系统 SHALL NOT 自造项目或单元 payload 字段表达该开关

#### Scenario: 获取线索标题和投放卡片由授权素材生成

- **GIVEN** 投放目标为获取线索
- **AND** 用户已授权可用于分析的视频素材或素材元数据
- **WHEN** 系统生成单元标题和投放卡片
- **THEN** 标题 SHALL 写入 `procedural_material.title_material_list[].title` 或当前单元规则声明的标题字段
- **AND** 投放卡片 SHALL 写入 `promotion_card_info` 及其子字段
- **AND** 生成内容 SHALL 满足标题、卖点、行动号召、图片数量和长度限制
- **AND** 如果素材内容不可分析或缺少必要业务信息，系统 SHALL 返回中文说明或单问题追问，不得编造视频分析结论

### Requirement: 创建项目联动单元时必须保持原生工具边界

创建项目流程联动单元管理时，系统 SHALL 只通过 `oceanengine_local_unit` 原生业务工具执行单元创建或更新。系统 SHALL NOT 直接调用受保护的 `localUnit*` MCP tool，也不得让项目管理工具代替单元管理工具写入单元素材。

#### Scenario: 项目创建成功后创建单元

- **GIVEN** `oceanengine_local_project` 已返回创建成功并确认项目存在
- **AND** 流程需要配置视频素材、标题或卡片
- **WHEN** 系统继续创建或配置单元
- **THEN** 系统 SHALL 调用 `oceanengine_local_unit`
- **AND** `project_id` SHALL 来自刚创建并确认的项目
- **AND** 单元本地校验失败时 SHALL 只展示当前首个中文问题
- **AND** 系统 SHALL NOT 直接调用 `localUnitCreate` 或其它受保护 MCP tool

#### Scenario: 单元配置失败不伪造成项目创建完全成功

- **GIVEN** 项目已创建成功
- **AND** 后续单元素材配置失败
- **WHEN** 系统生成最终用户可见结果
- **THEN** 系统 SHALL 区分项目创建成功与单元配置失败
- **AND** 用户可见结果 SHALL 给出中文失败原因和可继续补齐的问题
- **AND** 系统 SHALL NOT 声称完整创建项目流程已经完成

