# 获取单元详情

- path: `/open_api/v3.0/local/promotion/detail/`
- MCP: `platform-agent-biz/localUnitDetail`
- capability: `get-unit-detail`

## 请求字段摘要

必填字段：`local_account_id`、`promotion_id`。

返回内容包含单元基础信息、项目关联、投放状态、素材、卡片和审核信息。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | 返回数据 |
| `data.promotion_id` | `number` | 单元ID |
| `data.enable_graphic_delivery` | `bool` | 是否开启团购卡 |
| `data.aweme_id` | `string` | 抖音号 |
| `data.video_hp_visibility` | `string` | 抖音主页可见性；抖音主页可见性，枚举值：ALWAYS_VISIBLE 抖音主页可见；HIDE_VIDEO_ON_HP 抖音主页单次可见 |
| `data.live_material_type` | `string` | 直播素材类型；直播素材类型，枚举值：LIVE 直播素材；VIDEO 单元素材 |
| `data.customer_material_list[]` | `object[]` | 自定义素材组合 |
| `data.customer_material_list[].image_mode` | `string` | 素材类型；素材类型，枚举值：IMAGE_MODE_VIDEO 横版视频；IMAGE_MODE_VIDEO_VERTICAL 竖版视频 |
| `data.customer_material_list[].title_material` | `object` | 标题 |
| `data.customer_material_list[].title_material.title` | `string` | 标题内容 |
| `data.customer_material_list[].title_material.lego_material_id` | `number` | 标题素材库id |
| `data.customer_material_list[].title_material.material_id` | `number` | 标题素材id |
| `data.customer_material_list[].video_material` | `object` | 视频 |
| `data.customer_material_list[].video_material.video_id` | `string` | 视频id |
| `data.customer_material_list[].video_material.lego_material_id` | `number` | 视频素材库id |
| `data.customer_material_list[].video_material.material_id` | `number` | 视频素材id |
| `data.customer_material_list[].video_material.aweme_item_id` | `number` | 抖音主页视频ID |
| `data.customer_material_list[].video_material.image_mode` | `string` | 素材类型；素材类型，枚举值：IMAGE_MODE_VIDEO 横版视频；IMAGE_MODE_VIDEO_VERTICAL 竖版视频 |
| `data.customer_material_list[].video_material.video_duration` | `number` | 视频长度 |
| `data.customer_material_list[].video_material.video_height` | `number` | 视频高度 |
| `data.customer_material_list[].video_material.video_width` | `number` | 视频宽度 |
| `data.customer_material_list[].video_material.video_play_url` | `string` | 视频播放链接 |
| `data.customer_material_list[].video_material.cover_image_height` | `number` | 封面图片高度 |
| `data.customer_material_list[].video_material.cover_image_width` | `number` | 封面图片宽度 |
| `data.customer_material_list[].video_material.cover_web_uri` | `string` | 封面图片uri |
| `data.customer_material_list[].video_material.cover_web_url` | `string` | 封面图片链接 |
| `data.procedural_material` | `object` | 线索单元-素材列表 |
| `data.procedural_material.title_material_list[]` | `object[]` | 标题素材列表 |
| `data.procedural_material.title_material_list[].title` | `string` | 标题内容 |
| `data.procedural_material.title_material_list[].lego_material_id` | `number` | 标题素材库id |
| `data.procedural_material.title_material_list[].material_id` | `number` | 标题素材id |
| `data.procedural_material.video_material_list[]` | `object[]` | 视频素材 |
| `data.procedural_material.video_material_list[].image_mode` | `string` | 素材类型；素材类型，可选值：IMAGE_MODE_VIDEO 横版视频；IMAGE_MODE_VIDEO_VERTICAL 竖版视频 |
| `data.procedural_material.video_material_list[].video_id` | `string` | 视频id |
| `data.procedural_material.video_material_list[].lego_material_id` | `number` | 标题素材库id |
| `data.procedural_material.video_material_list[].material_id` | `number` | 标题素材id |
| `data.procedural_material.video_material_list[].video_duration` | `number` | 视频长度 |
| `data.procedural_material.video_material_list[].video_height` | `number` | 视频高度 |
| `data.procedural_material.video_material_list[].video_width` | `number` | 视频宽度 |
| `data.procedural_material.video_material_list[].video_play_url` | `string` | 视频播放链接 |
| `data.procedural_material.video_material_list[].cover_image_height` | `number` | 封面图片高度 |
| `data.procedural_material.video_material_list[].cover_image_width` | `number` | 封面图片宽度 |
| `data.procedural_material.video_material_list[].cover_web_uri` | `string` | 封面图片uri |
| `data.procedural_material.video_material_list[].cover_web_url` | `string` | 封面图片链接 |
| `data.procedural_material.video_material_list[].is_ff_see_setting` | `string` | 视频主页可见性；视频主页可见性，可选值：ALWAYS_VISIBLE 抖音主页可见；HIDE_VIDEO_ON_HP 抖音主页单次可见；UNKNOWN 未设置 |
| `data.procedural_material.carousel_material_list[]` | `object[]` | 图文素材 |
| `data.procedural_material.carousel_material_list[].carousel_id` | `number` | 图文素材id |
| `data.procedural_material.carousel_material_list[].image_list[]` | `object[]` | 图文图片信息 |
| `data.procedural_material.carousel_material_list[].image_list[].uri` | `string` | 图文uri |
| `data.procedural_material.carousel_material_list[].image_list[].url` | `string` | 图文url |
| `data.procedural_material.carousel_material_list[].image_list[].height` | `number` | 图片高度 |
| `data.procedural_material.carousel_material_list[].image_list[].width` | `number` | 图片宽度 |
| `data.procedural_material.carousel_material_list[].music` | `object` | 音乐素材 |
| `data.procedural_material.carousel_material_list[].music.music_id` | `string` | 音乐id |
| `data.procedural_material.carousel_material_list[].music.music_vid` | `string` | 音乐id |
| `data.procedural_material.carousel_material_list[].music.music_url` | `string` | 音乐播放url |
| `data.promotion_card_info` | `object` | 线索单元-投放卡片素材 |
| `data.promotion_card_info.product_name` | `string` | 卡片标题 |
| `data.promotion_card_info.product_images[]` | `object[]` | 卡片配图 |
| `data.promotion_card_info.product_images[].image_uri` | `string` | 图片uri |
| `data.promotion_card_info.product_images[].image_url` | `string` | 图片预览url |
| `data.promotion_card_info.product_images[].height` | `number` | 图片高度 |
| `data.promotion_card_info.product_images[].width` | `number` | 图片宽度 |
| `data.promotion_card_info.product_selling_points[]` | `object[]` | 投放卖点 |
| `data.promotion_card_info.product_selling_points[].selling_point` | `string` | 卖点描述 |
| `data.promotion_card_info.call_to_actions[]` | `object[]` | 行动号召 |
| `data.promotion_card_info.call_to_actions[].action` | `string` | 号召描述 |
| `data.promotion_card_info.enable_personal_call_to_action` | `bool` | 行动号召是否开启智能生成 |
| `request_id` | `string` | 请求日志id |
