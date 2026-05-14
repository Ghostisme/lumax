# structured-parameter-clarification Specification

## Purpose
TBD - created by archiving change add-structured-parameter-clarification. Update Purpose after archive.
## Requirements
### Requirement: 后端必须返回结构化参数补齐信息

OceanEngine 本地推原生业务工具在本地参数校验失败且失败原因属于缺少普通必填或条件必填参数时，SHALL 在 Agent 可见结果的 `data.clarification` 中返回结构化参数补齐信息。该结构 SHALL 与现有 `data.user_visible_text` 兼容，并 SHALL NOT 要求前端在本次变更中实现新的渲染组件。

#### Scenario: 缺少填写型参数

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 本地参数校验发现首个可见错误是缺少填写型字段，例如 `name`、`local_account_id`、`project_id`、`keyword` 或 `video_file_path`
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** 返回结果 SHALL 包含 `success=false`
- **AND** `data.user_visible_text` SHALL 保留首个中文追问
- **AND** `data.clarification.version` SHALL 为 `v1`
- **AND** `data.clarification.field` SHALL 等于首个可见 `errors[0].field`
- **AND** `data.clarification.field_label` SHALL 使用规则中的中文字段标签
- **AND** `data.clarification.question` SHALL 与当前首个中文追问一致
- **AND** `data.clarification.input_control.type` SHALL 为 `text_input`
- **AND** `data.clarification.input_control.value_type` SHALL 表达规则字段类型
- **AND** `data.clarification.input_control.placeholder` SHALL 使用中文提示用户填写该字段

#### Scenario: 缺少枚举型参数

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 本地参数校验发现首个可见错误是缺少字段
- **AND** 该字段规则包含 `enum` 或 `item_enum`
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** 当字段规则包含 `enum` 时，`data.clarification.input_control.selection_mode` SHALL 为 `single`
- **AND** 当字段规则包含 `item_enum` 时，`data.clarification.input_control.selection_mode` SHALL 为 `multiple`
- **AND** `data.clarification.input_control.options` SHALL 按规则声明顺序列出候选项
- **AND** 每个候选项 SHALL 包含原始枚举 `value`
- **AND** 每个候选项 SHALL 优先使用 `enum_labels` 中的中文 `label`
- **AND** 缺少中文标签时 SHALL 回退为原始枚举值，不得臆造官方未声明含义

#### Scenario: 多个缺参仍只暴露首个结构化追问

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 本地参数校验发现多个缺少普通必填或条件必填参数
- **WHEN** 业务工具生成 Agent 可见失败结果
- **THEN** `errors` SHALL 只保留首个可见错误
- **AND** `data.user_visible_text` SHALL 只包含首个中文追问
- **AND** `data.clarification.field` SHALL 只指向该首个可见错误字段
- **AND** `data.error_count` SHALL 保留本次校验发现的总错误数量
- **AND** `data.omitted_error_count` SHALL 表示未展示的错误数量
- **AND** 返回结果 SHALL NOT 同时生成多个 `clarification` 项

#### Scenario: 非参数补齐类失败不生成输入控件

- **GIVEN** OceanEngine 本地推原生业务工具已经通过本地参数校验
- **WHEN** 失败原因是 MCP 工具缺失、MCP 调用失败、平台业务失败、后置确认失败、响应展示异常或认证环境问题
- **THEN** 返回结果 SHALL 保留现有中文失败诊断
- **AND** 返回结果 SHALL NOT 生成 `data.clarification.input_control`
- **AND** 系统 SHALL NOT 将该失败误导为需要用户补充官方请求参数

### Requirement: 结构化补齐信息必须由后端规则元数据生成

`data.clarification` SHALL 由后端基于本次命中 capability 的 `rules/*.json` 和首个可见校验错误生成。系统 SHALL NOT 依赖前端解析自然语言文案来推断字段类型、枚举候选或输入控件类型。

#### Scenario: 枚举候选来自规则文件

- **GIVEN** 当前字段规则声明了 `enum` 或 `item_enum`
- **AND** 当前字段规则声明了 `enum_labels`
- **WHEN** 后端生成 `choice_cards` 候选项
- **THEN** 候选项 `value` SHALL 来自 `enum` 或 `item_enum`
- **AND** 候选项 `label` SHALL 来自 `enum_labels`
- **AND** 候选项顺序 SHALL 与规则文件中的枚举顺序一致
- **AND** 后端 SHALL NOT 从模型回复、前端状态或 MCP schema 泄漏字段中推断其它候选项

#### Scenario: 旧展示路径保持可用

- **GIVEN** 后端已经生成 `data.clarification`
- **WHEN** 当前前端或主 Agent 未消费该结构化字段
- **THEN** `data.user_visible_text` SHALL 仍可直接作为中文追问展示
- **AND** `reply_guidance` SHALL 继续要求主 Agent 只追问当前一个问题
- **AND** 现有 Markdown 展示路径 SHALL NOT 因新增结构化字段而失效

### Requirement: 本变更不得修改前端代码

结构化参数补齐的后端契约 SHALL 由原生业务工具基于 `rules/*.json` 和真实只读业务查询生成。本 change 的 Apply 阶段 SHALL 只修改后端接口契约、后端测试、OpenSpec 文档和必要的后端辅助类型或函数。前端控件展示由后续同事对接，本 change SHALL NOT 修改 `frontend/` 下任何源码、样式、测试或生成组件。

#### Scenario: 实施人员检查改动范围

- **GIVEN** Apply 阶段准备提交通用结构化补齐后端契约变更
- **WHEN** 实施人员检查 `git diff --stat` 或等价改动清单
- **THEN** 改动文件 SHALL NOT 位于 `frontend/`
- **AND** 若发现 `frontend/` 改动，实施人员 SHALL 移除该改动或另建后续 OpenSpec change 处理前端渲染
- **AND** 后端 SHALL NOT 依赖前端解析 `data.user_visible_text` 来构造候选项

### Requirement: OceanEngine 运行时守卫必须位于项目扩展点

OceanEngine 本地推业务的运行时守卫、响应清洗和工具链路约束 SHALL 位于 `tools/`、Gateway 注入层或其它显式 `extension-point`。这些逻辑 SHALL NOT 依赖 `backend/packages/harness/deerflow/**` 中的业务专用模块。

#### Scenario: 项目管理缺参尝试直接 clarification

- **GIVEN** 当前消息历史已经成功读取 `oceanengine-local-project/SKILL.md`
- **AND** 项目级 OceanEngine middleware 已通过扩展点注入
- **WHEN** 主 Agent 尝试调用 `ask_clarification` 追问项目管理业务参数
- **THEN** 扩展点 middleware SHALL 阻断该 `ask_clarification` 工具调用
- **AND** 阻断信息 SHALL 要求调用 `oceanengine_local_project`
- **AND** 系统 SHALL NOT 依赖 harness 内置 OceanEngine middleware 完成该阻断

#### Scenario: 单元管理缺参尝试直接 clarification

- **GIVEN** 当前消息历史已经成功读取 `oceanengine-local-unit/SKILL.md`
- **AND** 项目级 OceanEngine middleware 已通过扩展点注入
- **WHEN** 主 Agent 尝试调用 `ask_clarification` 追问单元管理业务参数
- **THEN** 扩展点 middleware SHALL 阻断该 `ask_clarification` 工具调用
- **AND** 阻断信息 SHALL 要求调用 `oceanengine_local_unit`
- **AND** 系统 SHALL NOT 依赖 harness 内置 OceanEngine middleware 完成该阻断

#### Scenario: 素材管理缺参尝试直接 clarification

- **GIVEN** 当前消息历史已经成功读取 `oceanengine-local-material/SKILL.md`
- **AND** 项目级 OceanEngine middleware 已通过扩展点注入
- **WHEN** 主 Agent 尝试调用 `ask_clarification` 追问素材管理业务参数
- **THEN** 扩展点 middleware SHALL 阻断该 `ask_clarification` 工具调用
- **AND** 阻断信息 SHALL 要求调用 `oceanengine_local_material`
- **AND** 系统 SHALL NOT 依赖 harness 内置 OceanEngine middleware 完成该阻断

### Requirement: 迁出后 OceanEngine 原生工具链路行为必须等价

迁出 OceanEngine 运行时守卫后，系统 SHALL 保持与迁出前等价的原生工具链路约束和结构化参数补齐契约。

#### Scenario: 缺参仍由原生业务工具生成结构化补齐

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 本地参数校验发现缺少普通必填、条件必填、枚举或批量项字段
- **WHEN** 原生业务工具返回失败结果
- **THEN** 返回结果 SHALL 保留 `success=false`
- **AND** `data.user_visible_text` SHALL 只包含首个中文追问
- **AND** `data.clarification` SHALL 由后端基于当前 capability 的 `rules/*.json` 生成
- **AND** 本地参数校验失败时 SHALL NOT 调用 MCP

#### Scenario: 受保护 MCP 直连仍被阻断

- **GIVEN** 当前请求属于 OceanEngine 本地推项目、单元或素材管理
- **WHEN** 主 Agent 尝试直接调用 MCP Router 管理工具或受保护底层 MCP tool
- **THEN** 系统 SHALL 阻断该调用
- **AND** 阻断信息 SHALL 引导使用对应原生业务工具
- **AND** 系统 SHALL NOT 将底层 MCP 直连结果作为业务执行成功返回

#### Scenario: 用户可见响应仍保持清洁

- **GIVEN** OceanEngine 原生业务工具或平台链路返回结果
- **WHEN** 系统生成用户可见回复
- **THEN** 用户可见回复 SHALL 优先展示真实业务 ID、名称、状态、分页和失败原因
- **AND** 用户可见回复 SHALL NOT 展示平台请求日志 ID、内部 trace 或原始 JSON 包装
- **AND** 该清洗行为 SHALL 由扩展点 middleware 或原生业务工具结果格式保证

### Requirement: 结构化补齐必须支持动态候选选项卡

当 OceanEngine 本地推原生业务工具能够根据当前已知业务参数查询候选值时，`data.clarification.input_control` SHALL 支持动态 `choice_cards`。动态候选 SHALL 来自真实只读业务查询结果，而不是来自模型臆测、前端状态推断或静态规则枚举。

#### Scenario: 动态候选生成选项卡

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 本地参数校验发现首个可行动缺参适合用动态候选补齐
- **AND** 当前 payload 已包含执行候选查询所需的前置参数
- **WHEN** 原生业务工具生成参数补齐结果
- **THEN** 返回结果 SHALL 包含 `success=false`
- **AND** `data.clarification.reason` SHALL 表示参数补齐
- **AND** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** `data.clarification.input_control.options` SHALL 来自真实只读业务查询结果
- **AND** 每个候选项 SHALL 包含用于回填目标字段的 `value`
- **AND** 每个候选项 SHALL 包含用户可读的 `label`
- **AND** 系统 SHALL NOT 因本地校验失败而执行目标 mutation MCP 调用

#### Scenario: 动态候选查询前置参数不足

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 本地参数校验发现首个可行动缺参理论上可使用动态候选补齐
- **AND** 当前 payload 缺少候选查询所需的前置参数
- **WHEN** 原生业务工具生成参数补齐结果
- **THEN** 系统 SHALL NOT 发起候选查询 MCP 调用
- **AND** 返回结果 SHALL 继续只追问首个缺失的前置参数
- **AND** 返回结果 SHALL NOT 生成空的或臆造的 `choice_cards.options`

#### Scenario: 动态候选查询失败或为空

- **GIVEN** 原生业务工具已经发起只读候选查询
- **WHEN** MCP 工具缺失、MCP 调用失败、平台业务失败或返回空候选
- **THEN** 返回结果 SHALL 说明候选查询失败或暂无可选项
- **AND** 返回结果 SHALL NOT 生成虚假候选卡片
- **AND** 返回结果 MAY 引导用户更换关键词、营销目的或手动提供目标字段值
- **AND** 用户可见结果 SHALL NOT 展示内部 trace、平台请求日志 ID 或原始 JSON 包装

### Requirement: 动态候选必须兼容现有文本展示路径

当动态候选以 `data.clarification.input_control.type=choice_cards` 返回时，后端用户可见出口 SHALL 同步生成现有消息展示路径可直接展示的 `data.user_visible_text`。本 change SHALL NOT 依赖前端改动来展示动态候选。

#### Scenario: 用户可见文本展示单选候选

- **GIVEN** 工具结果包含 `data.clarification.input_control.type=choice_cards`
- **AND** `selection_mode=single`
- **WHEN** 后端构造用户可见工具结果
- **THEN** `data.user_visible_text` SHALL 包含原始单问题追问
- **AND** `data.user_visible_text` SHALL 展示候选项 `label` 和 `value`
- **AND** 当候选项存在 `description` 时，`data.user_visible_text` SHOULD 展示该业务摘要
- **AND** `data.user_visible_text` SHALL 提示用户回复候选 ID 或名称
- **AND** 用户可见文本 SHALL NOT 展示内部 trace、平台请求日志 ID、原始 JSON 包装或底层 MCP tool 名

#### Scenario: 保留旧文本展示路径

- **GIVEN** 工具结果没有结构化 `data.clarification`
- **OR** `input_control.type=text_input`
- **WHEN** 后端构造用户可见工具结果
- **THEN** 后端 SHALL 保留现有 Markdown 或文本追问展示路径
- **AND** 本变更 SHALL NOT 破坏既有 `ask_clarification` 和普通文本消息展示

### Requirement: 分页 MCP 接口必须沿用第一页二十条

OceanEngine 本地推原生业务工具执行分页 MCP 接口时，如果能力字段包含 `page` 和 `page_size` 且用户未指定分页参数，系统 SHALL 默认使用 `page=1`、`page_size=20`。该规则 SHALL 统一适用于 `oceanengine_local_project`、`oceanengine_local_unit`、`oceanengine_local_material` 及后续同域 OceanEngine 原生业务工具。规则文件显式声明其它默认值时，规则默认值优先。

#### Scenario: 未指定分页参数

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 当前 capability 对应的 MCP 接口支持 `page` 和 `page_size`
- **AND** 用户没有指定页码和每页数量
- **WHEN** 原生业务工具构造 MCP payload
- **THEN** payload SHALL 包含 `page=1`
- **AND** payload SHALL 包含 `page_size=20`
- **AND** 响应分页后置校验 SHALL 使用该默认请求值

#### Scenario: 项目单元素材分页接口统一默认

- **GIVEN** 用户请求分别命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 对应 capability 是分页 MCP 读取接口
- **AND** 用户没有指定页码和每页数量
- **WHEN** 原生业务工具构造 MCP payload
- **THEN** 三类业务工具 SHALL 使用同一默认分页规则
- **AND** payload SHALL 包含 `page=1`
- **AND** payload SHALL 包含 `page_size=20`

#### Scenario: 测试覆盖所有分页 MCP capability

- **GIVEN** Apply 阶段准备验证分页默认值
- **WHEN** 测试人员检查 `oceanengine-local-project`、`oceanengine-local-unit`、`oceanengine-local-material` 的 `rules/*.json`
- **THEN** 测试人员 SHALL 列出所有同时声明 `page` 与 `page_size` 的 capability
- **AND** 每个 capability SHALL 至少有一个未指定分页的测试，证明 payload 使用 `page=1`、`page_size=20`
- **AND** 每个 capability SHALL 至少有一个显式分页测试，证明系统不覆盖用户输入
- **AND** 测试范围 SHALL NOT 只覆盖动态商品候选接口

#### Scenario: 用户显式指定分页参数

- **GIVEN** 用户请求命中 OceanEngine 本地推分页 MCP 接口
- **AND** 用户明确指定 `page` 或 `page_size`
- **WHEN** 原生业务工具构造 MCP payload
- **THEN** 系统 SHALL 保留用户显式指定的分页值
- **AND** 系统 SHALL NOT 用默认值覆盖用户输入

### Requirement: 静态枚举选项必须按依赖规则确定性过滤

OceanEngine 本地推原生业务工具为静态枚举缺参生成 `data.clarification.input_control.type=choice_cards` 时，候选项 SHALL 由当前 capability 的 `rules/*.json` 和当前 payload 确定性计算。系统 SHALL NOT 展示当前已选参数组合下会被依赖规则禁止的静态枚举候选。

#### Scenario: 静态枚举候选来源稳定

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 本地参数校验发现首个可见错误是缺少静态枚举字段
- **AND** 该字段规则包含 `enum`、`item_enum`、`batch_item.fields.*.enum` 或 `batch_item.fields.*.item_enum`
- **WHEN** 原生业务工具生成 `choice_cards`
- **THEN** `data.clarification.input_control.options[].value` SHALL 只来自规则声明的静态枚举值
- **AND** `options[].label` SHALL 只来自对应 `enum_labels` 或原始枚举值回退
- **AND** `options` 的相对顺序 SHALL 与规则文件中的枚举顺序一致
- **AND** 系统 SHALL NOT 从模型回复、其它接口 MCP schema、前端状态或平台响应中混入候选

#### Scenario: 已选上游参数过滤后续候选

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 当前 payload 已经包含影响后续枚举字段可选范围的上游参数
- **AND** 后续缺失字段规则包含静态枚举候选
- **WHEN** 原生业务工具生成 `choice_cards`
- **THEN** 系统 SHALL 对每个候选按当前 payload 做依赖规则仿真
- **AND** 会触发当前字段相关 `forbidden_when` 或互斥禁止语义的候选 SHALL NOT 出现在 `options` 中
- **AND** 未被禁止的候选 SHALL 保持规则声明顺序
- **AND** 相同规则文件和相同 payload 每次 SHALL 返回完全一致的 `options`

#### Scenario: 无依赖上下文时保留完整枚举

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 当前 payload 没有提供足以收窄目标枚举字段的上游参数
- **AND** 目标字段规则包含静态 `enum` 或 `item_enum`
- **WHEN** 原生业务工具生成 `choice_cards`
- **THEN** 系统 SHALL 保留该字段规则声明的完整枚举候选
- **AND** 系统 SHALL NOT 因缺少上下文而臆测删除候选

#### Scenario: 批量项枚举按依赖规则过滤

- **GIVEN** 用户请求命中批量接口
- **AND** 缺失字段位于 `batch_item.fields`
- **AND** 批量项内或顶层 payload 已经包含影响该枚举字段可选范围的参数
- **WHEN** 原生业务工具生成 `choice_cards`
- **THEN** 系统 SHALL 对该批量项对应的静态枚举候选做依赖过滤
- **AND** `data.clarification.field` SHALL 指向缺失的批量项字段
- **AND** 对应错误 SHALL 保留 `item_index`
- **AND** 本轮仍 SHALL 只暴露一个结构化追问

### Requirement: 已选非法依赖组合必须优先返回组合错误

当用户已经提供的 payload 触发 `forbidden_when`、`mutually_exclusive` 或等价依赖禁止规则时，OceanEngine 原生业务工具 SHALL 优先提示当前组合无效。系统 SHALL NOT 继续追问由该非法组合触发或位于其后的缺失参数。

#### Scenario: 已选非法组合不继续追问后续参数

- **GIVEN** 用户请求命中 OceanEngine 本地推原生业务工具
- **AND** 当前 payload 已经触发依赖禁止规则
- **AND** 同一 payload 还缺少后续普通必填或条件必填字段
- **WHEN** 原生业务工具返回本地参数校验失败
- **THEN** `errors[0]` SHALL 指向当前非法组合涉及的字段或字段组
- **AND** `data.user_visible_text` SHALL 提示当前组合无效
- **AND** 返回结果 SHALL NOT 继续追问后续缺失字段
- **AND** 本地参数校验失败时 SHALL NOT 调用 MCP

#### Scenario: 短视频线上互动不展示搜索单元

- **GIVEN** 用户创建或更新本地推项目
- **AND** 当前 payload 已选择 `marketing_goal=VIDEO_IMAGE`
- **AND** 当前 payload 已选择 `local_delivery_scene=CONTENT_HEAT`
- **AND** 当前 payload 缺少 `ad_type`
- **WHEN** 原生业务工具生成 `ad_type` 的 `choice_cards`
- **THEN** `options` SHALL 包含 `GENERAL`
- **AND** `options` SHALL NOT 包含 `SEARCHING`

#### Scenario: 获取线索不展示搜索单元

- **GIVEN** 用户创建或更新本地推项目
- **AND** 当前 payload 已选择 `local_delivery_scene=EXTERNAL`
- **AND** 当前 payload 缺少 `ad_type`
- **WHEN** 原生业务工具生成 `ad_type` 的 `choice_cards`
- **THEN** `options` SHALL 包含 `GENERAL`
- **AND** `options` SHALL NOT 包含 `SEARCHING`

#### Scenario: 线下到店不展示商品投放内容

- **GIVEN** 用户创建或更新本地推项目
- **AND** 当前 payload 已选择 `marketing_goal=VIDEO_IMAGE`
- **AND** 当前 payload 已选择 `local_delivery_scene=POI_RECOMMEND`
- **AND** 当前 payload 缺少 `delivery_goal`
- **WHEN** 原生业务工具生成 `delivery_goal` 的 `choice_cards`
- **THEN** `options` SHALL 包含 `POI`
- **AND** `options` SHALL NOT 包含 `PRODUCT`

### Requirement: 固定枚举测试必须覆盖项目单元素材全部规则

Apply 阶段 SHALL 先写完整测试用例，覆盖 `oceanengine-local-project`、`oceanengine-local-unit`、`oceanengine-local-material` 三类规则目录中的静态枚举字段和依赖规则。测试 SHALL 直接调用原生业务工具 dry-run 或共享校验边界，不依赖 LLM、浏览器或真实平台候选数据。

#### Scenario: 扫描三类规则目录

- **GIVEN** Apply 阶段准备验证静态枚举补齐稳定性
- **WHEN** 测试加载规则文件
- **THEN** 测试 SHALL 扫描 `skills/custom/oceanengine-local-project/rules/*.json`
- **AND** 测试 SHALL 扫描 `skills/custom/oceanengine-local-unit/rules/*.json`
- **AND** 测试 SHALL 扫描 `skills/custom/oceanengine-local-material/rules/*.json`
- **AND** 测试 SHALL 识别 `fields.*.enum`、`fields.*.item_enum`、`batch_item.fields.*.enum` 和 `batch_item.fields.*.item_enum`

#### Scenario: 测试覆盖依赖规则类型

- **GIVEN** 某规则文件声明 `forbidden_when`、`conditional_required`、`mutually_exclusive` 或 `at_least_one`
- **WHEN** 测试构造本地 dry-run payload
- **THEN** 测试 SHALL 覆盖候选过滤
- **AND** 测试 SHALL 覆盖已选非法组合优先报错
- **AND** 测试 SHALL 覆盖条件未触发时不追问条件字段
- **AND** 测试 SHALL 覆盖条件触发时只追问正确字段
- **AND** 测试 SHALL 覆盖用户可见文本只展示一个问题或一个明确错误

#### Scenario: 动态候选不纳入固定枚举断言

- **GIVEN** 缺失字段的候选来自平台实时查询，例如商品、门店、抖音号、人群包、营销页或组件
- **WHEN** 测试验证动态候选行为
- **THEN** 测试 MAY 使用 mock MCP 响应断言 `choice_cards` 结构
- **AND** 测试 SHALL NOT 要求真实平台候选集合固定
- **AND** 测试 SHALL NOT 把动态平台候选写入静态规则枚举

### Requirement: 后端接口必须通用返回结构化参数补齐控件数据

当原生业务工具返回 `data.clarification.input_control` 时，后端 SHALL 通过通用 history、stream 或约定线程消息接口返回结构化补齐控件数据。该能力 SHALL 适用于所有返回同一契约的 OceanEngine 本地推原生业务工具，不得只针对某个接口、字段或 capability 实现。前端控件渲染不属于本 change 范围。

#### Scenario: 静态枚举缺参通过接口返回选项数据

- **GIVEN** 用户请求命中 `oceanengine_local_project`、`oceanengine_local_unit` 或 `oceanengine_local_material`
- **AND** 原生业务工具返回 `success=false`
- **AND** 返回结果包含 `data.clarification.input_control.type=choice_cards`
- **AND** `data.clarification.input_control.options` 来自当前 capability 的规则文件
- **WHEN** 客户端通过 history、stream 或约定线程消息接口读取本轮结果
- **THEN** 接口结果 SHALL 包含结构化澄清数据
- **AND** 结构化澄清数据 SHALL 包含 `input_control.type=choice_cards`
- **AND** 候选项 SHALL 保留后端返回的 `options[].label`
- **AND** 候选值 SHALL 保留后端返回的 `options[].value`
- **AND** 候选项顺序 SHALL 与后端返回顺序一致
- **AND** 后端 SHALL NOT 从 `data.user_visible_text` 解析或推断候选项

#### Scenario: 动态候选通过接口返回选项数据

- **GIVEN** 原生业务工具返回动态候选 `data.clarification.input_control.type=choice_cards`
- **AND** 候选项包含 `value`、`label`、`description` 或 `metadata`
- **WHEN** 客户端通过接口读取结构化澄清数据
- **THEN** 接口结果 SHALL 保留用户可读的 `label`
- **AND** 接口结果 SHALL 保留用于后续补齐的 `value`
- **AND** 接口结果 SHALL 保留安全的 `description`
- **AND** 接口结果 SHALL 保留后续交互所需的候选 `metadata`
- **AND** 后端 SHALL NOT 臆造、重排或合并动态候选

#### Scenario: 填写型缺参通过接口返回输入提示

- **GIVEN** 原生业务工具返回 `data.clarification.input_control.type=text_input`
- **WHEN** 客户端通过接口读取结构化澄清数据
- **THEN** 接口结果 SHALL 包含 `data.clarification.question`
- **AND** 接口结果 SHALL 包含后端返回的 `placeholder` 或字段中文标签
- **AND** 接口结果 SHALL NOT 包含内部字段映射、payload JSON 或工具调用细节

#### Scenario: 旧文本展示路径仍可兜底

- **GIVEN** 原生业务工具返回 `data.clarification`
- **WHEN** 后端构造用户可见接口结果
- **THEN** 接口结果 SHALL 继续包含 `data.user_visible_text` 或等价兜底文本
- **AND** 接口结果 SHALL NOT 返回空候选控件
- **AND** 后端 SHALL NOT 为缺失结构臆造候选项

### Requirement: 结构化补齐用户可见出口必须清洗内部信息

系统将原生业务工具返回的结构化补齐信息转成用户可见接口结果时，SHALL 只保留前端对接所需的安全字段。原始工具调用、底层 MCP 信息和内部调试信息 SHALL 继续隐藏。

#### Scenario: 用户可见结构不泄漏内部工具信息

- **GIVEN** 原生业务工具返回 `data.clarification.input_control`
- **WHEN** Gateway / runtime 构造 history 或 stream 用户可见消息
- **THEN** 用户可见接口结果 SHALL 包含 `version`、`reason`、`field`、`field_label`、`question`、`input_control` 和 `user_visible_text`
- **AND** 用户可见接口结果 SHALL NOT 包含 `business_tool_name`
- **AND** 用户可见接口结果 SHALL NOT 包含 `mcp_server_name`
- **AND** 用户可见接口结果 SHALL NOT 包含 `mcp_tool_name`
- **AND** 用户可见接口结果 SHALL NOT 包含原始 `payload_json`、内部 trace、平台请求日志 ID 或原始 JSON 包装

#### Scenario: 通用实现不绑定具体接口

- **GIVEN** 一个 OceanEngine 原生业务工具返回符合 `data.clarification.input_control` 契约的结果
- **WHEN** 系统构造结构化补齐接口结果
- **THEN** 后端提取逻辑 SHALL 基于结构化契约识别补齐信息
- **AND** 实现 SHALL NOT 写死 `create-project`、`marketing_goal`、`local_delivery_scene`、`opt_status`、`upload_type` 或其它具体接口字段作为展示条件

### Requirement: 动态 MCP 候选必须按卡片契约返回

当 OceanEngine 原生业务工具通过只读 MCP 查询获得参数候选时，系统 SHALL 将可用于用户补齐的候选按 `data.clarification.input_control.type=choice_cards` 返回。该契约 SHALL 与静态枚举缺参的卡片候选保持字段兼容，并 SHALL NOT 要求本次变更修改 `frontend/**`。

#### Scenario: 单选动态候选返回卡片结构

- **GIVEN** 用户请求命中 OceanEngine 原生业务工具
- **AND** 本地参数校验发现首个可行动缺参适合通过只读 MCP 查询生成候选
- **AND** 该缺参字段业务语义为单选
- **WHEN** MCP 查询返回可用候选
- **THEN** 返回结果 SHALL 包含 `success=false`
- **AND** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** `data.clarification.input_control.selection_mode` SHALL 为 `single`
- **AND** `data.clarification.input_control.options[]` SHALL 来自 MCP 查询结果
- **AND** 每个候选项 SHALL 包含用于回填字段的 `value`
- **AND** 每个候选项 SHALL 包含用户可读的 `label`
- **AND** 系统 SHALL NOT 因本地校验失败而调用目标 mutation MCP 工具

#### Scenario: 多选动态候选返回卡片结构

- **GIVEN** 用户请求命中 OceanEngine 原生业务工具
- **AND** 本地参数校验发现首个可行动缺参适合通过只读 MCP 查询生成候选
- **AND** 该缺参字段业务语义为多选
- **WHEN** MCP 查询返回可用候选
- **THEN** `data.clarification.input_control.type` SHALL 为 `choice_cards`
- **AND** `data.clarification.input_control.selection_mode` SHALL 为 `multiple`
- **AND** `data.clarification.input_control.options[]` SHALL 来自 MCP 查询结果
- **AND** 候选项 SHALL 保留 MCP 查询结果中的安全展示顺序
- **AND** 系统 SHALL NOT 把动态候选写入 `rules/*.json` 的静态 `enum` 或 `item_enum`

#### Scenario: 动态候选保留安全业务摘要

- **GIVEN** MCP 查询候选包含业务摘要、绑定对象、分页或其它展示辅助字段
- **WHEN** 原生业务工具构造 `choice_cards`
- **THEN** 候选项 MAY 包含安全的 `description`
- **AND** 候选项 MAY 包含后续补齐需要的安全 `metadata`
- **AND** `input_control` MAY 包含安全的 `page_info`
- **AND** 输出 SHALL NOT 包含内部 MCP tool name、平台请求日志 ID、trace 或原始 payload JSON

### Requirement: 动态候选必须提供不依赖前端改动的文本兜底

当动态 MCP 候选以 `choice_cards` 返回时，后端 SHALL 同步生成用户可读的 `data.user_visible_text`，使当前前端不修改代码时用户仍可理解候选并继续回复。

#### Scenario: 单选候选文本兜底

- **GIVEN** `data.clarification.input_control.selection_mode` 为 `single`
- **AND** `options[]` 包含一个或多个候选
- **WHEN** 后端构造用户可见结果
- **THEN** `data.user_visible_text` SHALL 包含原始单问题追问
- **AND** `data.user_visible_text` SHALL 展示每个候选的 `label` 和 `value`
- **AND** 当候选项存在 `description` 时，`data.user_visible_text` SHOULD 展示该业务摘要
- **AND** `data.user_visible_text` SHALL 提示用户回复一个候选 ID 或名称

#### Scenario: 多选候选文本兜底

- **GIVEN** `data.clarification.input_control.selection_mode` 为 `multiple`
- **AND** `options[]` 包含一个或多个候选
- **WHEN** 后端构造用户可见结果
- **THEN** `data.user_visible_text` SHALL 包含原始单问题追问
- **AND** `data.user_visible_text` SHALL 展示每个候选的 `label` 和 `value`
- **AND** `data.user_visible_text` SHALL 提示用户可回复多个候选 ID 或名称
- **AND** 用户可见文本 SHALL NOT 暴露内部 tool name、MCP tool name、payload JSON、trace 或平台请求日志 ID

#### Scenario: 当前变更不修改前端

- **GIVEN** 实施人员执行本 change
- **WHEN** 检查 git diff
- **THEN** 改动 SHALL NOT 包含 `frontend/**` 下的文件
- **AND** 若现有前端无法交互式展示 `selection_mode=multiple`，该限制 SHALL 记录为当前 UI 能力边界
- **AND** 后端文本兜底 SHALL 仍允许用户通过自然语言回复继续补齐参数

### Requirement: 浏览器验收必须使用真实用户路径

动态 MCP 候选卡片契约完成后，验收 SHALL 通过真实浏览器和真实用户自然语言输入验证，不得用指定工具、脚本直连或 MCP 直连替代用户路径。

#### Scenario: 浏览器自然语言触发动态候选

- **GIVEN** 验收人员已经登录本地页面
- **AND** 测试参数包含本地提账号 `1854708763953159`
- **WHEN** 验收人员在浏览器对话框中输入本地推参数补齐相关自然语言请求
- **THEN** 输入内容 SHALL NOT 包含 `oceanengine-local-project`、`oceanengine_local_project`、`capability`、`payload_json`、底层 MCP tool 名、脚本路径或“直接调用某工具”等提示
- **AND** 验收 SHALL 证明真实 Agent 被触发
- **AND** 验收 SHALL 证明 OceanEngine 原生业务工具被触发
- **AND** 验收 SHALL 证明只读 MCP 候选查询链路被触发
- **AND** 验收 SHALL NOT 以 dry-run、mock 成功、curl、脚本直连或 MCP 直连结果替代浏览器结果

#### Scenario: 验收失败先结合本地日志排查

- **GIVEN** 浏览器验收失败或链路证据不清晰
- **WHEN** 验收人员排查原因
- **THEN** 验收人员 SHALL 先结合本地 Gateway、backend、frontend 和 MCP 相关日志定位问题
- **AND** 本地日志证据 SHALL 用于诊断失败原因或链路缺口
- **AND** 本地日志 SHALL NOT 替代最终浏览器自然语言验收

#### Scenario: 本地日志不足时使用 Langfuse sessionId 辅助

- **GIVEN** 浏览器验收失败或链路证据不清晰
- **AND** 本地日志仍不足以定位问题
- **WHEN** 本轮请求存在可用于追踪的 `sessionId`
- **THEN** 验收人员 MAY 使用该 `sessionId` 查询 Langfuse 日志
- **AND** Langfuse 日志 SHALL 仅作为问题定位和链路证明辅助
- **AND** Langfuse 日志 SHALL NOT 替代最终浏览器自然语言验收

#### Scenario: 问题排除后重新浏览器验收

- **GIVEN** 验收失败问题已经通过本地日志、Langfuse 或代码分析排除
- **WHEN** 验收人员验证修复结果
- **THEN** 验收人员 SHALL 重新使用浏览器自然语言输入测试
- **AND** 重新测试 SHALL 遵守禁止指定工具名、`capability`、`payload_json` 和底层 MCP tool 名的规则
- **AND** 只有重新浏览器验收通过，才可将该验收项标记为完成

### Requirement: 动态候选异常路径不得生成虚假卡片

当动态 MCP 候选查询无法得到可用候选时，系统 SHALL 返回清晰的中文失败或继续追问结果，并 SHALL NOT 生成空的、臆造的或与当前参数上下文不匹配的 `choice_cards.options`。

#### Scenario: 前置参数不足时不查询候选

- **GIVEN** 首个可行动缺参理论上可通过动态 MCP 候选补齐
- **AND** 当前 payload 缺少候选查询所需的前置参数
- **WHEN** 原生业务工具生成参数补齐结果
- **THEN** 系统 SHALL NOT 发起候选查询 MCP 调用
- **AND** 返回结果 SHALL 继续只追问首个缺失的前置参数
- **AND** 返回结果 SHALL NOT 生成 `choice_cards.options`

#### Scenario: 候选查询失败时不生成卡片

- **GIVEN** 原生业务工具已经发起只读 MCP 候选查询
- **WHEN** MCP 工具缺失、MCP 调用失败或平台业务失败
- **THEN** 返回结果 SHALL 说明候选查询失败
- **AND** 返回结果 SHALL NOT 生成虚假候选卡片
- **AND** 用户可见结果 SHALL NOT 展示内部 trace、平台请求日志 ID 或底层 MCP tool name

#### Scenario: 候选为空时不生成空卡片

- **GIVEN** 原生业务工具已经发起只读 MCP 候选查询
- **WHEN** MCP 查询成功但候选列表为空
- **THEN** 返回结果 SHALL 说明暂无可选候选
- **AND** 返回结果 SHALL NOT 生成空的 `choice_cards.options`
- **AND** 返回结果 MAY 引导用户更换关键词、前置参数或手动提供目标字段值

