# 优化本地推创建项目流程设计

## 背景与现状

`skills/custom/oceanengine-local-project/rules/create-project.json` 当前维护了 `create-project` 的 65 个官方字段，普通必填包括 `local_account_id`、`name`、`marketing_goal`、`local_delivery_scene`、`ad_type`、`schedule_type`、`bid_type`、`budget_mode` 和 `budget`。规则还包含 `delivery_goal`、`product_id`、`promotion_poi_ids`、`external_action`、`audience.*`、`aigc_dynamic_creative_switch`、`local_asset_type`、`tool_pack_id`、`market_page_ids` 等条件字段。

素材上传和素材库查询已经由 `oceanengine-local-material` 管理，视频素材相关能力包括 `upload-video`、`async-upload-local-video`、`list-local-video-upload-tasks`、`get-library-videos` 和 `get-aweme-videos`。创建或更新单元的素材、标题、投放卡片、封面字段位于 `oceanengine-local-unit`，包括 `customer_material_list`、`procedural_material`、`promotion_card_info` 和封面 URI 字段。

因此，本次不是把所有字段塞进 `localProjectCreate`，而是定义“创建项目业务流程”的跨工具编排边界。

## 方案

推荐在 Apply 阶段实现一个项目创建业务编排层，落在根目录 `tools/`、Gateway 接入层或其它明确项目扩展点。该编排层负责把用户自然语言转成流程状态和官方 payload，但真实业务执行仍通过现有三个原生业务工具完成：

1. `oceanengine_local_project`：校验并执行 `create-project`，创建项目并做后置确认。
2. `oceanengine_local_material`：上传用户明确授权的视频，查询素材库，返回可选视频候选。
3. `oceanengine_local_unit`：项目创建成功后创建或更新单元，写入单元名称、视频素材、标题、封面和投放卡片。

编排层只能保存流程态字段，例如 `operator_name`、视频选择数量要求、品牌命名偏好、AI 生成意图和用户已确认候选。它不得把非官方字段透传给 `localProjectCreate`、`localFile*` 或 `localUnit*` MCP tool。

## 字段边界

投手是业务流程必填项，但当前项目创建官方规则没有 `operator_name` 字段。Apply 阶段应把它用于项目/单元名称生成、验收记录和用户可见上下文；除非后续官方规则或 Java 模型明确提供对应字段，否则不得加入 MCP payload。

用户定向默认项中，能映射到当前规则的字段应进入官方 payload，例如：

- 地域类型：`audience.region.location_type=HOME`。
- 性别：`audience.gender=NONE`。
- 年龄：`audience.age` 表达 18 到 55 岁。
- 人群包不限：不传 `audience.retargeting_tags` 和 `audience.retargeting_tags_exclude`，除非用户明确指定定向或排除人群包。
- 过滤已转化用户：`audience.hide_if_converted=CUSTOMER`。
- 过滤时间：`audience.converted_time_duration=THREE_MONTH`。
- 获取线索行为兴趣不限：`audience.customized_interest_action=INTERESTACTION_OFF`。
- 获取线索过滤高活跃用户：`audience.filter_aweme_abnormal_active=FILTER_AWEME_ABNORMAL_ACTIVE_TYPE_ON`。
- 获取线索过滤高关注用户：`audience.filter_aweme_fans_count=FILTER_AWEME_FANS_COUNT_TYPE_OVER1000`。

当前 `create-project` 规则未暴露的业务项，例如 `智能定向拓展` 和 `搜索出价系数`，实现阶段必须先确认是否属于其它接口或平台默认；未确认前只记录为流程决策，不得自造字段。

## 场景化默认

默认排期和预算：

- 投放日期默认为 `schedule_type=FROM_NOW_ON`，表达“从今天起长期投放”；由于当前日期是 2026-05-12，文档示例不得把 `20250507` 当成当前日期，只能把它作为 `yyyyMMdd` 格式示例。
- 投放时段默认不传 `schedule_time`，表示不限。
- 预算模式默认 `budget_mode=BUDGET_MODE_DAY`。
- 高峰日预算默认关闭；如果当前场景要求传 `is_set_peak_budget`，应传 `false`。

默认出价：

- 线下到店使用 `bid_type=SMART`，不得让用户选择 `MANUAL`。
- 获取线索使用 `bid_type=MAX_CONVERSION`。
- 其它场景可按用户给定或现有规则校验；若用户显式指定非法组合，必须原样交给本地校验拦截。

获取线索场景：

- 优化目标从 `external_action` 的获取线索相关枚举中选择：`CLUE_ACQUISITION`、`PRIVATE_MESSAGE`、`CLUE_CONFIRM`、`CLUE_HIGH_INTENTION`。
- 引导页面使用 `local_asset_type` 表达：营销页、门店页、私信页等必须按当前枚举映射。
- `tool_pack_id`、`market_page_ids`、`consult_aweme_uid` 应按现有动态候选能力和规则条件补齐。
- `aigc_dynamic_creative_switch` 默认关闭，即 `AIGC_DYNAMIC_CREATIVE_SWITCH_OFF`。

## 素材与单元联动

视频上传必须由用户明确提供或授权 `video_file_path`、`video_url`、签名和元数据。系统不得扫描本地目录猜测素材。视频上传或素材库查询成功后，候选视频应以 `choice_cards` 返回，并保留 `video_id`、`material_id`、标题、时长、封面、可投状态等安全业务摘要。

项目创建成功后，系统才能创建或更新单元：

- 团购成交默认要求选择 10 条视频。
- 其它投放目标默认要求选择 3 到 5 条视频。
- 单元名称默认使用 `yyyyMMdd` + 地域 + 定向类型 + 年龄 + 投手姓名首字母大写。
- 线上互动时，投放类型默认“自选素材”，但必须映射到当前单元规则真实字段，不能自造项目字段。
- 获取线索时，标题和投放卡片可以由 AI 基于用户授权素材和业务上下文生成；如果无法访问素材内容或缺少必要信息，必须返回中文说明或继续追问，不能编造分析结果。
- AI 优化封面默认不启用；如当前规则没有对应字段，应只记录为流程决策或使用已有封面 URI 字段，不得自造 `localProjectCreate` 字段。

## 校验与验收

所有缺参和非法组合仍必须进入原生业务工具本地校验，保持首个可行动问题原则。动态候选继续使用 `data.clarification.input_control.type=choice_cards`，并由 Gateway 保留 `structured_clarifications`。

验证应覆盖：

- 项目 payload 默认项和禁止自造字段。
- 获取线索、线下到店、团购成交、线上互动的出价和素材差异。
- 素材上传安全边界。
- 视频数量要求。
- 单元名称生成。
- 浏览器自然语言真实验收。

## 取舍

不推荐把本流程做成一个新的公共 skill，也不推荐让主 Agent 串行直调底层 MCP tool。保留三个原生业务工具的边界，可以复用既有本地校验、Nacos MCP endpoint 解析、响应清洗、动态候选和后置确认能力，同时避免把创建项目接口扩展成不符合官方字段的“大而全 payload”。

