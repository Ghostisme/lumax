## ADDED Requirements

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

