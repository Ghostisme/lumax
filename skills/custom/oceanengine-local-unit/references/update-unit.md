# 更新单元

- path: `/open_api/v3.0/local/promotion/update/`
- MCP: `platform-agent-biz/localUnitUpdate`
- capability: `update-unit`

## 请求字段摘要

普通必填字段：`local_account_id`、`promotion_id`。

可更新字段与创建单元同源，但除 `local_account_id`、`promotion_id` 外均不是普通必填，包括 `name`、`aweme_id`、`customer_material_list`、`procedural_material`、`promotion_card_info`、`video_hp_visibility`。

官方条件和限制：
- `aweme_id`：仅当存在素材库视频或本地上传视频时有意义；原项目未选择抖音号 ID 时支持传入，若项目已选择则不支持更新修改；交易场景支持传入，`local_delivery_scene=EXTERNAL` 时不支持传入。
- `customer_material_list`：视频素材信息，全量更新；传入空数组会清空单元原来选择的视频，传空或不传则不会更新。
- 直播间且 `live_material_type=LIVE` 时，`customer_material_list` 不生效且不支持传入。
- `procedural_material`：线索单元素材列表，仅 `local_delivery_scene=EXTERNAL` 支持传入。
- `procedural_material.carousel_material_list`：图文素材列表，长度 1-10，包含 `carousel_id`。
- `promotion_card_info`：投放卡片素材，仅 `local_delivery_scene=EXTERNAL` 支持传入。
- `video_hp_visibility`：可选，仅针对素材库和本地上传视频生效。

常用枚举：
- `customer_material_list[].image_mode`: `IMAGE_MODE_VIDEO`、`IMAGE_MODE_VIDEO_VERTICAL`
- `procedural_material.video_material_list[].image_mode`: `IMAGE_MODE_VIDEO`、`IMAGE_MODE_VIDEO_VERTICAL`
- `video_hp_visibility` / `is_ff_see_setting`: `ALWAYS_VISIBLE`、`HIDE_VIDEO_ON_HP`

素材与卡片限制沿用官方创建/更新文档：标题、卡片标题、配图、卖点、行动号召和图文素材均按对应长度或数组数量限制校验。

本地工具会将 snake_case 字段转换为 MCP schema 使用的 camelCase，并按 `request` 包装调用。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `request_id` | `string` | 请求日志id |
