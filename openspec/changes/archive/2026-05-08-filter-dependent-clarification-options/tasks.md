# Tasks

## 1. OpenSpec

- [x] 1.1 明确静态枚举稳定性边界：只覆盖 `rules/*.json` 中的 `enum`、`item_enum`、`batch_item.fields.*.enum`、`batch_item.fields.*.item_enum`。
- [x] 1.2 明确动态平台候选边界：商品、门店、抖音号、人群包、营销页、组件等实时查询候选不要求固定集合。
- [x] 1.3 为 `structured-parameter-clarification` 增加依赖选项过滤、非法组合优先报错和全接口测试要求。

## 2. 测试先行

- [x] 2.1 新增高覆盖测试文件，优先覆盖三类规则目录：
  - `skills/custom/oceanengine-local-project/rules/*.json`
  - `skills/custom/oceanengine-local-unit/rules/*.json`
  - `skills/custom/oceanengine-local-material/rules/*.json`
- [x] 2.2 对所有静态枚举字段做数据驱动扫描，确认 `choice_cards.options` 的 `value`、`label` 和顺序只来自规则文件。
- [x] 2.3 对无依赖上下文的静态枚举缺参场景，确认完整枚举候选仍按规则顺序展示。
- [x] 2.4 对声明 `forbidden_when` 且目标字段为静态枚举的接口，覆盖候选过滤：当前 payload 加候选值会触发禁止规则时，该候选不出现在 `choice_cards.options`。
- [x] 2.5 对已选非法组合，覆盖错误优先级：返回当前组合错误，不继续追问 `schedule_type`、`product_id` 或其它后续条件字段。
- [x] 2.6 对 `conditional_required` 覆盖条件触发边界：条件满足时才追问条件字段，条件不满足时不追问。
- [x] 2.7 对 `mutually_exclusive` 覆盖互斥边界：当前三类规则扫描确认未声明 `mutually_exclusive`；新增测试已加保护，后续新增该规则时会失败提示补充互斥行为用例。
- [x] 2.8 对 `at_least_one` 覆盖至少一个边界：只在条件满足且候选字段都缺失时触发，不提前展示无关后续参数。
- [x] 2.9 对批量接口的 `batch_item` 静态枚举缺参覆盖单问题 `choice_cards`，并保留 `item_index`。
- [x] 2.10 对 `data.user_visible_text` 覆盖用户可见文本：只展示一个问题或一个明确组合错误，不追加其它缺参。
- [x] 2.11 对动态候选字段覆盖结构边界：mock 平台候选响应，只验证动态 `choice_cards` 结构和链路，不把平台候选内容纳入固定稳定性断言。
- [x] 2.12 先运行新增测试，确认失败原因是缺少依赖过滤或错误优先级，而不是测试自身语法或夹具错误。

## 3. 实现

- [x] 3.1 修改任一函数、类或方法前，按仓库 GitNexus 规则对目标符号执行 upstream impact analysis，并记录影响面。
- [x] 3.2 在共享规则校验或结构化补齐层实现确定性静态枚举候选过滤，不依赖 LLM 生成或排序。
- [x] 3.3 调整非法依赖组合的错误优先级，确保当前组合错误先于后续缺参追问返回。
- [x] 3.4 保持动态平台候选逻辑不被静态枚举过滤影响。
- [x] 3.5 不修改 `frontend/`，不新增受保护 MCP 直连路径，不修改 `backend/packages/harness/deerflow/**` 受保护源码包。

## 4. 验证

- [x] 4.1 运行新增聚焦测试，确认依赖选项过滤和非法组合优先报错通过。
- [x] 4.2 运行既有结构化追问与动态候选测试，确认回归不破坏。
- [x] 4.3 运行 `npx openspec validate filter-dependent-clarification-options --strict`。
- [x] 4.4 提交前运行 `gitnexus_detect_changes()` 或等价 GitNexus change detection，确认影响范围符合预期。
