# 获取抖音主页视频

- 官方 `doc_id`：`1808004088768608`
- 官方 path：`/open_api/v3.0/local/file/video/aweme/get/`
- 方法：`GET`
- capability：`get-aweme-videos`
- MCP 工具：`localFileVideoAwemeGet`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `cursor` | 是 | 分页游标，首次通常传 `0` |
| `filtering.anchor_info.anchor_types` | 是 | 挂载类型，支持 `ALL_ANCHOR`、`POI_ANCHOR`、`PRODUCT_ANCHOR` |
| `filtering.anchor_info.poi_ids` | 条件 | 门店 ID 列表；`anchor_types` 包含 `POI_ANCHOR` 时必填 |
| `filtering.anchor_info.product_ids` | 条件 | 商品 ID 列表；`anchor_types` 包含 `PRODUCT_ANCHOR` 时必填 |
| `filtering.aweme_ids` | 条件 | 抖音号 ID 列表；`anchor_types` 包含 `ALL_ANCHOR` 时必填 |
| `filtering.item_ids` | 否 | 视频 `item_id` 列表，单次最多 10 个 |
| `filtering.item_status` | 否 | 素材状态，支持 `ALL`、`VALID`，官方默认 `VALID` |
| `filtering.start_time` | 否 | 发布时间筛选开始时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `filtering.end_time` | 否 | 发布时间筛选结束时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `order_field` | 否 | 当前 MCP schema 字段；官方请求字段名为 `order_filed`，支持 `ARRIVE_SHOP`、`ESTIMATE`、`LIKE_CNT`、`PAY_ORDER_CNT`、`PUBLISH_TIME` |
| `external_action` | 否 | 优化目标，仅在按 `ESTIMATE` 排序时生效；支持 `OTO_PAY`（团购购买）、`POI_RECOMMEND`（门店引流） |
| `page_size` | 否 | 当前 MCP schema 使用 `pageSize` 表达每页数量；官方请求字段名为 `count`，范围 1 到 100 |

## 条件约束

- `anchor_types` 包含 `POI_ANCHOR` 时需要 `filtering.anchor_info.poi_ids`。
- `anchor_types` 包含 `PRODUCT_ANCHOR` 时需要 `filtering.anchor_info.product_ids`。
- `anchor_types` 包含 `ALL_ANCHOR` 时需要 `filtering.aweme_ids`。
- `filtering.item_ids` 单次最多 10 个。

## 官方与 MCP 差异

- 官方字段名存在历史拼写 `order_filed`；当前 MCP schema 暴露为 `orderField`，本地规则用 `order_field` 映射。
- 官方分页数量字段为 `count`；当前 MCP schema 暴露为 `pageSize`，本地规则用 `page_size` 映射。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.video_list[]` | `object[]` | 视频列表 |
| `data.video_list[].item_id` | `string` | 抖音视频ID |
| `data.video_list[].title` | `string` | 视频标题 |
| `data.video_list[].video_id` | `string` | 视频ID |
| `data.video_list[].aweme_id` | `string` | 抖音号id |
| `data.video_list[].aweme_name` | `string` | 抖音号名称 |
| `data.video_list[].image_mode` | `string` | 视频格式 可选值: IMAGE_MODE_LOCAL_ADGRAPHIC 团购卡 IMAGE_MODE_VIDEO 横版视频 IMAGE_MODE_VIDEO_VERTICAL 竖版视频 |
| `data.video_list[].duration` | `string` | 时长 |
| `data.video_list[].cover_image_url` | `string` | 视频封面图片地址 |
| `data.video_list[].aweme_video_url` | `string` | 视频播放地址 |
| `data.video_list[].not_delivery_reason[]` | `string[]` | 不可投放原因 |
| `data.video_list[].can_delivery` | `bool` | 视频是否可投放 true 可投放 false 不可投放 |
| `data.video_list[].lego_material_id` | `number` | 素材id |
| `data.video_list[].video_width` | `number` | 视频宽度 |
| `data.video_list[].video_heigh` | `number` | 视频高度 |
| `data.page_info` | `object` | 分页信息 |
| `data.page_info.cursor` | `string` | 页码游标值 |
| `data.page_info.has_more` | `bool` | 是否有下一页 |
| `request_id` | `string` | 请求日志id |
