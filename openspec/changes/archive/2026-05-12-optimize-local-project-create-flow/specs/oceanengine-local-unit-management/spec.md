## ADDED Requirements

### Requirement: 创建项目后单元名称必须按业务默认生成

当创建项目流程需要继续创建或配置单元时，`oceanengine-local-unit` SHALL 支持使用业务默认规则生成单元名称。默认名称 SHALL 使用执行日期、地域、定向类型、年龄和投手姓名首字母大写组成，品牌另有要求时才由用户明确覆盖。

#### Scenario: 生成默认单元名称

- **GIVEN** 项目已通过 `oceanengine_local_project` 创建成功
- **AND** 流程态包含地域、定向类型、年龄和投手姓名
- **AND** 用户没有提供品牌自定义单元名称规则
- **WHEN** 系统准备调用 `oceanengine_local_unit` 创建单元
- **THEN** 单元名称 SHALL 使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 投手姓名首字母大写
- **AND** `yyyyMMdd` SHALL 使用实际执行日期，例如 2026-05-12 对应 `20260512`
- **AND** 系统 SHALL NOT 把用户示例中的 `20250507` 当作当前日期

#### Scenario: 品牌自定义名称覆盖默认规则

- **GIVEN** 用户明确提供品牌单元命名要求
- **WHEN** 系统生成单元名称
- **THEN** 系统 SHALL 优先使用用户明确提供的品牌规则
- **AND** 生成后的名称仍 SHALL 满足单元 `name` 长度和格式校验
- **AND** 非法名称 SHALL 由 `oceanengine_local_unit` 本地校验返回中文错误

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

