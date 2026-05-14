# 获取素材库视频

- 官方 `doc_id`：`1808613640441882`
- 官方 path：`/open_api/v3.0/local/file/video/get/`
- 方法：`GET`
- capability：`get-library-videos`
- MCP 工具：`localFileVideoGet`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `filtering` | 是 | 过滤条件，可为空对象 |
| `filtering.search_key_word` | 否 | 搜索关键词 |
| `filtering.image_mode` | 否 | 视频类型数组；当前 MCP schema 使用 `VIDEO`、`VIDEO_VERTICAL`，分别对应官方 `IMAGE_MODE_VIDEO`、`IMAGE_MODE_VIDEO_VERTICAL` |
| `filtering.material_source` | 否 | 素材来源数组，支持 `BP_PLATFORM`、`CREATIVE_AIGC`、`LOCAL_ADS_UPLOAD`、`STAR`、`MAPI` |
| `filtering.analysis_type` | 否 | 分析类型数组，支持 `FIRST_PUBLISH`、`FIRST_PUBLISH_AND_HIGH_QUALITY`、`HIGH_QUALITY` |
| `filtering.start_time` | 否 | 创建时间筛选开始时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `filtering.end_time` | 否 | 创建时间筛选结束时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `filtering.is_filter_unqualified` | 否 | 是否过滤不合格素材，官方默认 `true` |
| `order_field` | 否 | 排序字段，支持 `CONVERSION_COST`、`CONVERSION_RATE`、`CREATE_TIME`、`CTR`、`DURATION`、`STAT_COST` |
| `order_type` | 否 | 排序方向，支持 `ASC`、`DESC` |
| `page` | 否 | 页码，最小 1 |
| `page_size` | 否 | 每页数量，最大 100 |

## 校验说明

- `filtering.material_source` 和 `filtering.analysis_type` 逐项按官方枚举校验。
- `filtering.image_mode` 以当前 MCP schema 可执行值为准，同时在说明中标注官方序列化值。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.video_list[]` | `object[]` | 素材库视频列表 |
| `data.video_list[].video_id` | `string` | 视频ID |
| `data.video_list[].material_id` | `number` | 素材id |
| `data.video_list[].signature` | `string` | 视频md5 |
| `data.video_list[].video_name` | `string` | 视频名称 |
| `data.video_list[].video_url` | `string` | 视频地址，链接有效期：1小时 |
| `data.video_list[].poster_url` | `string` | 视频首帧截图 |
| `data.video_list[].material_properties[]` | `string[]` | 素材标签，枚举值：COPY 搬运风险 FIRST_PUBLISH 首发 HIGH_QUALITY 优质 LOW_QUALITY 低质 SIMILAR 同质化风险 |
| `data.video_list[].image_mode` | `string` | 视频类型，枚举值：IMAGE_MODE_VIDEO 横版视频 IMAGE_MODE_VIDEO_VERTICAL 竖版视频 |
| `data.video_list[].duration` | `double` | 视频时长 |
| `data.video_list[].source` | `string` | 视频来源，枚举值：BP_PLATFORM 巨量引擎工作平台共享视频 CREATIVE_AIGC 即创 LOCAL_ADS_UPLOAD 本地上传 STAR 星图平台 MAPI MAPI接口上传 |
| `data.video_list[].create_time` | `string` | 素材的上传时间，格式：yyyy-mm-dd HH:mm:ss |
| `data.page_info` | `object` | 分页信息 |
| `data.page_info.page` | `number` | 页码 |
| `data.page_info.page_size` | `number` | 页面大小 |
| `data.page_info.total_page` | `number` | 总页数 |
| `data.page_info.total_number` | `number` | 总数 |
| `request_id` | `string` | 请求日志id |
