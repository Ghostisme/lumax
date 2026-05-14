## ADDED Requirements

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
