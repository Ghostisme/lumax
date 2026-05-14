# 依赖参数下的静态枚举选项稳定过滤

## Why

OceanEngine 本地推原生业务工具已经能在缺少枚举参数时返回 `data.clarification.input_control.type=choice_cards`。但当前结构化补齐只按字段自身的 `enum` 或 `item_enum` 直接生成完整候选，没有把当前 payload 中已经选择的上游参数代入 `forbidden_when`、`conditional_required`、`mutually_exclusive`、`at_least_one` 等依赖规则。

因此用户选择某个上游选项后，后续参数可能仍展示当前组合下不应出现的枚举值。例如短视频/图文项目选择“线上互动”后，单元类型仍可能展示“搜索”；选择“线下到店”后，投放内容仍可能展示“商品”。用户一旦选中这类不合法组合，校验器还可能先追问后续缺参，而不是优先提示当前组合无效。

这会破坏结构化追问的确定性：同一个静态枚举字段虽然能稳定返回同一组候选，但候选集合没有随已选参数稳定收窄，导致用户看见不应该选择的选项。

## What Changes

- 对 `oceanengine-local-project`、`oceanengine-local-unit`、`oceanengine-local-material` 三类原生业务工具的静态枚举补齐统一增加依赖规则过滤。
- 静态枚举候选只来自 `rules/*.json` 中的 `enum` / `item_enum` 和 `enum_labels`，候选顺序保持规则声明顺序。
- 生成 `choice_cards.options` 时，把当前 payload 与候选值做确定性规则仿真，过滤掉会触发当前字段相关 `forbidden_when` 或互斥类禁止规则的候选。
- 当用户已经提供了非法依赖组合时，优先返回当前组合错误，不继续追问由该非法组合触发的后续缺参。
- 明确测试边界：固定稳定性只适用于规则文件声明的静态枚举；平台实时查询返回的动态候选不要求固定候选集合。
- Apply 阶段先写完整测试用例并确认 RED，再做最小实现修复；设计或代码变更必须使用 Superpowers 和 TDD。

## Out of Scope

- 不修改前端展示组件，不要求前端实现新的交互控件。
- 不要求固定平台实时查询候选，例如商品、门店、抖音号、人群包、营销页或组件候选。
- 不改变 MCP payload 的官方字段映射，不新增直接 MCP、HTTP API、curl 或 SDK 绕过路径。
- 不把动态候选静态写入 `rules/*.json`。

## Impact

- 主要影响共享规则校验和结构化补齐生成链路：`tools/oceanengine_local_project_runtime/validators.py` 与 `tools/oceanengine_local_project_runtime/endpoint_runner.py`。
- 三类 OceanEngine 原生业务工具都会继承该行为，因此测试必须扫描项目、单元、素材全部 `rules/*.json`。
- 现有动态商品候选 `product_id` 逻辑应保持实时查询候选，只验证结构和链路，不验证真实平台候选集合固定。
