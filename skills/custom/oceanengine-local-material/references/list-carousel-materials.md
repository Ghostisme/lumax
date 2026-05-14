# 获取图文素材

- 官方 `doc_id`：`1849312906748032`
- 官方 path：`/open_api/v3.0/local/file/carousel/list/`
- 方法：`GET`
- capability：`list-carousel-materials`
- MCP 工具：`localFileCarouselList`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `keyword` | 否 | 图文素材标题关键词，映射到当前 MCP schema 的 `itemTitle` |
| `carousel_ids` | 否 | 图文素材 ID 列表，最多 10 个，映射到 `itemIds` |
| `start_time` | 否 | 官方字段，创建时间筛选开始时间；当前 MCP schema 暂未暴露，不进入实际调用参数 |
| `end_time` | 否 | 官方字段，创建时间筛选结束时间；当前 MCP schema 暂未暴露，不进入实际调用参数 |
| `page` | 否 | 页码，最小 1 |
| `page_size` | 否 | 每页数量，最大 100 |
| `order.order_by` | 否 | 排序字段 |
| `order.order_type` | 否 | 排序方向 |
| `cursor` | 否 | 当前 MCP schema 暴露字段，官方文档未列出 |
| `material_source` | 否 | 当前 MCP schema 暴露字段，官方文档未列出 |

## 差异记录

- 官方和 Java SDK 字段为 `keyword`、`carousel_ids`、`start_time`、`end_time`、`order`、`page`、`page_size`。
- 当前 `platform-agent-biz` MCP schema 暴露 `itemTitle`、`itemIds`，并额外暴露 `cursor`、`materialSource`。
- 本地规则保留 `keyword` 到 `itemTitle`、`carousel_ids` 到 `itemIds` 的映射；`start_time`、`end_time` 只在参考文档记录，等 MCP schema 对齐后再进入可执行参数。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.carousel_list[]` | `object[]` | 账户下图文id列表 |
| `data.carousel_list[].carousel_id` | `number` | 图文素材id |
| `data.carousel_list[].title` | `string` | 图文标题 |
| `data.carousel_list[].image_list[]` | `object[]` | 图文图片信息 |
| `data.carousel_list[].image_list[].uri` | `string` | 图片uri |
| `data.carousel_list[].image_list[].url` | `string` | 图片预览url |
| `data.carousel_list[].image_list[].height` | `number` | 高度 |
| `data.carousel_list[].image_list[].width` | `number` | 宽度 |
| `data.carousel_list[].music` | `object` | 图文内音频信息列表 |
| `data.carousel_list[].music.music_id` | `number` | 音频id |
| `data.carousel_list[].music.music_vid` | `string` | 音频vid |
| `data.carousel_list[].music.music_url` | `string` | 音频播放url |
| `data.carousel_list[].create_time` | `string` | 图文素材创建时间 |
| `data.page_info` | `object` | 分页信息 |
| `data.page_info.page` | `number` | 页码 |
| `data.page_info.page_size` | `number` | 页面大小 |
| `data.page_info.total_number` | `number` | 总数 |
| `data.page_info.total_page` | `number` | 总页数 |
| `request_id` | `string` | 请求日志id |
