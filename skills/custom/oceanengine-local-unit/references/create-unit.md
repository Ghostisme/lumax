# 创建单元

- path: `/open_api/v3.0/local/promotion/create/`
- MCP: `platform-agent-biz/localUnitCreate`
- capability: `create-unit`

## 请求字段摘要

普通必填字段：`local_account_id`、`project_id`、`name`。

条件字段：
- `enable_graphic_delivery`：仅当项目 `marketing_goal=VIDEO_IMAGE` 且 `local_delivery_scene=PRODUCT_PAY` / `POI_RECOMMEND` 时有效且必传。
- `aweme_id`：短视频场景且选择素材库或上传视频投放时必填；`local_delivery_scene=EXTERNAL` 时需与项目中的 `consult_aweme_uid` 保持一致。
- `live_material_type`：项目营销场景为直播间时有效且必传；`LIVE` 时不支持传入 `customer_material_list` 和 `procedural_material`。
- `customer_material_list`：视频素材列表；按官方场景在直播短视频、短视频/图文交易场景下条件必填；`local_delivery_scene=EXTERNAL` 或 `live_material_type=LIVE` 时不支持传入。
- `procedural_material`：线索素材列表，仅 `local_delivery_scene=EXTERNAL` 支持传入，并按直播/短视频场景条件必填。
- `promotion_card_info`：投放卡片设置，仅 `local_delivery_scene=EXTERNAL` 支持传入。
- `video_hp_visibility`：可选，默认 `HIDE_VIDEO_ON_HP`，仅针对素材库和上传视频生效。

常用枚举：
- `live_material_type`: `LIVE`、`VIDEO`
- `video_hp_visibility`: `ALWAYS_VISIBLE`、`HIDE_VIDEO_ON_HP`
- `customer_material_list[].image_mode`: `IMAGE_MODE_VIDEO`、`IMAGE_MODE_VIDEO_VERTICAL`
- `procedural_material.video_material_list[].image_mode`: `IMAGE_MODE_VIDEO`、`IMAGE_MODE_VIDEO_VERTICAL`
- `procedural_material.video_material_list[].is_ff_see_setting`: `ALWAYS_VISIBLE`、`HIDE_VIDEO_ON_HP`

素材与卡片限制：
- `name` 长度 1-50 个字。
- `title_material.title` 长度 5-55 个字。
- `procedural_material.title_material_list` 长度 1-30。
- `procedural_material.carousel_material_list` 长度 1-10，包含 `carousel_id`。
- `promotion_card_info.product_name` 长度 1-20 个字。
- `promotion_card_info.product_images`、`product_selling_points`、`call_to_actions` 长度均为 1-10。
- `selling_point` 长度 4-10 个字，`action` 长度 2-4 个字。

本地工具会将 snake_case 字段转换为 MCP schema 使用的 camelCase，并按 `request` 包装调用。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.promotion_id` | `number` | 单元ID |
| `request_id` | `string` | 请求日志id |
