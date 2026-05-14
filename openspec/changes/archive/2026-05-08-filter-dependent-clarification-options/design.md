# Design

## Context

当前结构化补齐链路分两步：

1. `validate_payload()` 基于 `rules/*.json` 产生错误列表。
2. `_build_parameter_clarification()` 读取首个缺参错误对应字段的规则，把 `enum` 或 `item_enum` 直接转换为 `choice_cards.options`。

这个流程可以稳定展示字段的完整静态枚举，但没有把当前 payload 中已选择的依赖参数代入规则。结果是：后续选项可能包含当前组合下必然非法的枚举值；用户已经选中非法组合时，校验器还可能继续追问后续字段。

## Definitions

固定枚举稳定性只适用于规则文件声明的静态枚举：

- `fields.*.enum`
- `fields.*.item_enum`
- `batch_item.fields.*.enum`
- `batch_item.fields.*.item_enum`

不纳入固定稳定测试的候选：

- 平台实时查询返回的商品、门店、抖音号、人群包、营销页、组件等业务候选。
- MCP 或平台响应内容里的业务数据。
- LLM 最终自然语言表述中的自由文本。

动态平台候选只验证结构、链路和用户可见清洗，不要求真实候选集合固定。

## Recommended Approach

采用规则仿真式过滤：

1. 结构化补齐仍从命中 capability 的 `rules/*.json` 读取枚举候选。
2. 对待追问的静态枚举字段，按规则中的原始枚举顺序遍历候选值。
3. 对每个候选构造 `candidate_payload = current_payload + {field: candidate_value}`。
4. 只评估与当前候选字段相关的依赖禁止规则，过滤会触发 `forbidden_when` 或互斥禁止语义的候选。
5. 保留未被过滤的候选，`value` 使用原始枚举值，`label` 使用 `enum_labels`。

这个方案不依赖模型、不依赖前端状态、不依赖平台实时数据，能够保证同一规则文件和同一 payload 下返回完全一致的静态枚举选项。

## Alternatives

### 方案 A：在规则文件给每个字段增加手写 `visible_when`

优点是表达直观。缺点是会把同一依赖关系在 `forbidden_when` 和 `visible_when` 中重复维护，容易漂移，也要求同步改大量规则文件。

### 方案 B：让主 Agent 根据中文规则自行决定展示选项

成本低，但不稳定。模型可能混入其它接口枚举、重排候选、漏掉依赖条件，不满足固定枚举稳定性要求。

### 方案 C：基于现有规则做确定性仿真过滤

复用现有规则事实，改动集中在共享运行时，候选来源、顺序和过滤结果都可测试。推荐采用。

## Error Priority

当 payload 已经包含非法组合时，应优先返回当前组合错误。例如：

- `marketing_goal=VIDEO_IMAGE`、`local_delivery_scene=CONTENT_HEAT`、`ad_type=SEARCHING`
- `local_delivery_scene=EXTERNAL`、`ad_type=SEARCHING`
- `marketing_goal=VIDEO_IMAGE`、`local_delivery_scene=POI_RECOMMEND`、`delivery_goal=PRODUCT`

这些场景不得继续追问 `schedule_type`、`product_id` 或其它被非法组合触发的后续字段。校验结果应先暴露组合错误，使用户能修正已选参数。

## Test Boundary

测试不走 LLM、不走浏览器、不依赖真实平台数据。测试直接调用：

- `oceanengine_local_project`
- `oceanengine_local_unit`
- `oceanengine_local_material`

并使用 `dry_run=True`。需要验证动态候选结构时，mock MCP 只读候选响应。

完整测试覆盖：

- 三类 `rules/*.json` 全部扫描，收集静态枚举字段。
- 无上下文时完整枚举展示。
- 有上游上下文时过滤被依赖规则禁止的枚举值。
- 已选非法组合时优先返回组合错误。
- 条件未触发时不追问条件字段。
- 条件触发时展示正确字段和正确候选。
- `batch_item` 枚举缺参保留单问题和 `item_index`。
- `user_visible_text` 与 `data.clarification.input_control.options` 不矛盾。
- 动态候选如 `product_id` 只验证结构与链路，不断言真实平台候选集合固定。

## Test Case Matrix

以下测试用例用于 Apply 阶段先行落地到 `backend/tests/test_oceanengine_dependent_clarification_options.py`。固定选项断言只针对 `rules/*.json` 中声明的静态枚举值；平台实时查询返回的数据只使用 mocked MCP 响应验证结构和链路。

| 编号 | 覆盖接口 / 范围 | 输入或前置条件 | 期望结果 |
| --- | --- | --- | --- |
| TC-01 | `oceanengine-local-project`、`oceanengine-local-unit`、`oceanengine-local-material` 全部 `rules/*.json` | 扫描三类规则目录，跳过 `index.json`，收集 `fields.*.enum`、`fields.*.item_enum`、`batch_item.fields.*.enum`、`batch_item.fields.*.item_enum` | 至少覆盖项目、单元、素材三类规则；包含 `batch_item` 枚举；静态枚举用例数量不低于当前规则规模；新增静态枚举字段会自动进入测试 |
| TC-02 | 结构化追问生成层 `_build_parameter_clarification()` | 对 TC-01 收集到的每个静态枚举字段构造缺参错误，连续调用两次结构化追问生成 | 两次结果完全一致；`input_control.type=choice_cards`；`selection_mode` 与 `enum` / `item_enum` 类型一致；`options.value`、`options.label` 和顺序完全来自规则文件 |
| TC-03 | `oceanengine_local_project` / `create-project` | payload 包含 `marketing_goal=VIDEO_IMAGE`、`local_delivery_scene=CONTENT_HEAT`，缺少 `ad_type` | 只追问 `ad_type`；`choice_cards.options.value=["GENERAL"]`；不得展示 `SEARCHING`；`user_visible_text` 不得包含“搜索” |
| TC-04 | `oceanengine_local_project` / `create-project` | payload 包含 `marketing_goal=VIDEO_IMAGE`、`local_delivery_scene=EXTERNAL`，缺少 `ad_type` | 只追问 `ad_type`；`choice_cards.options.value=["GENERAL"]`；不得展示 `SEARCHING`；`user_visible_text` 不得包含“搜索” |
| TC-05 | `oceanengine_local_project` / `create-project` | payload 包含 `local_delivery_scene=POI_RECOMMEND`，缺少 `delivery_goal` | 只追问 `delivery_goal`；`choice_cards.options.value=["POI"]`；不得展示 `PRODUCT`；`user_visible_text` 不得包含“商品” |
| TC-06 | `oceanengine_local_project` / `create-project` | payload 已选择 `local_delivery_scene=CONTENT_HEAT`、`ad_type=SEARCHING`，同时缺少后续字段 | 优先返回 `ad_type` 非法组合错误，错误包含“不支持搜索单元”；不得继续追问 `schedule_type`；不得返回 `data.clarification` |
| TC-07 | `oceanengine_local_project` / `create-project` | payload 已选择 `local_delivery_scene=EXTERNAL`、`ad_type=SEARCHING`，同时缺少后续字段 | 优先返回 `ad_type` 非法组合错误，错误包含“不支持搜索单元”；不得继续追问 `schedule_type`；不得返回 `data.clarification` |
| TC-08 | `oceanengine_local_project` / `create-project` | payload 已选择 `local_delivery_scene=POI_RECOMMEND`、`delivery_goal=PRODUCT`，同时缺少 `product_id` | 优先返回 `delivery_goal` 非法组合错误，错误包含“线下到店仅支持投放门店”；不得继续追问 `product_id`；不得返回 `data.clarification` |
| TC-09 | `oceanengine_local_unit` / `list-units` | `filtering.promotion_status_first=PROMOTION_STATUS_DISABLE` 且缺少 `filtering.promotion_status_second` | 触发 `filtering.promotion_status_second` 条件必填错误 |
| TC-10 | `oceanengine_local_unit` / `list-units` | `filtering.promotion_status_first=PROMOTION_STATUS_ENABLE` 且缺少 `filtering.promotion_status_second` | 不触发 `filtering.promotion_status_second` 缺参错误，避免展示不该追问的后续参数 |
| TC-11 | `oceanengine_local_unit` / `list-units` | `filtering.promotion_status_first=PROMOTION_STATUS_ENABLE` 且传入 `filtering.promotion_status_second=PROMOTION_STATUS_AUDIT` | 返回 `filtering.promotion_status_second` 禁止传入错误，证明已选非法组合优先暴露 |
| TC-12 | `oceanengine_local_material` / `get-aweme-videos` | `anchor_types=["POI_ANCHOR"]`，缺少 `filtering.anchor_info.poi_ids` | 只触发门店锚点对应的 `poi_ids` 条件必填边界 |
| TC-13 | `oceanengine_local_material` / `get-aweme-videos` | `anchor_types=["PRODUCT_ANCHOR"]`，缺少 `filtering.anchor_info.product_ids` | 只触发商品锚点对应的 `product_ids` 条件必填边界 |
| TC-14 | `oceanengine_local_material` / `get-aweme-videos` | `anchor_types=["ALL_ANCHOR"]`，缺少 `filtering.aweme_ids` | 只触发全部锚点对应的 `aweme_ids` 条件必填边界 |
| TC-15 | `oceanengine_local_project` / `create-project` | `audience.customized_interest_action` 未选择自定义行为兴趣 | 不触发“行为和兴趣至少需要传入一个”错误 |
| TC-16 | `oceanengine_local_project` / `create-project` | `audience.customized_interest_action=INTERESTACTION_CUSTOM`，且行为与兴趣字段都缺失 | 触发“行为和兴趣至少需要传入一个”错误 |
| TC-17 | 三类规则文件的 `constraints` | 扫描当前 `rules/*.json` 中的 `mutually_exclusive` 规则 | 当前期望为空；后续新增互斥规则时测试失败，提示必须补充互斥依赖过滤用例 |
| TC-18 | `oceanengine_local_unit` / `batch-update-unit-status` | payload 的 `data[0]` 只包含 `promotion_id`，缺少 `opt_status` | 返回单个问题；错误保留 `item_index=0`；`choice_cards.options` 为 `ENABLE`、`PAUSED`，并保持规则标签和顺序 |
| TC-19 | `oceanengine_local_material` / `upload-image` | payload 包含图片路径、签名和 `is_aigc`，缺少静态枚举字段 `upload_type` | 返回 `upload_type` 单问题；`choice_cards.options.value=["UPLOAD_BY_FILE"]`；`user_visible_text` 只展示“本地文件上传” |
| TC-20 | `oceanengine_local_project` / `create-project` | `delivery_goal=PRODUCT` 且缺少 `product_id`，mock MCP 返回两个商品候选 | 追问 `product_id`；`choice_cards.options` 来自 mocked 平台响应并保留 `metadata`；规则文件中 `product_id` 不得声明 `enum` 或 `item_enum` |
| TC-21 | `oceanengine_local_material` / `upload-image` | patch MCP 调用入口后触发缺少 `upload_type` 的静态枚举追问 | MCP 调用入口不得被调用；证明静态枚举不会伪装成动态候选查询 |

真实接口测试不是静态依赖过滤的必要前置条件。静态枚举稳定性由规则文件和本地确定性过滤保证，真实平台接口只适合做端到端验收或动态候选链路抽样，不应作为固定枚举集合的断言来源。

## Implementation Notes

- Apply 阶段必须使用 Superpowers 和 TDD。
- 先写完整测试并确认 RED，再修改实现代码。
- 修改任何符号前必须按 GitNexus 规则执行 upstream impact analysis。
- 实现应位于根目录 `tools/` 同域运行时或其它项目扩展点。
- 不修改 `frontend/`。
- 不新增或恢复 `backend/packages/harness/deerflow/tools/oceanengine_local_*` wrapper。
