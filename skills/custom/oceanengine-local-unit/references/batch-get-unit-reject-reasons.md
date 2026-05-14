# 批量获取广告审核建议

- path: `/open_api/v3.0/local/promotion/reject_reason/get/`
- MCP: `platform-agent-biz/localPromotionRejectReasonBatchGet`
- capability: `batch-get-unit-reject-reasons`

## 请求字段摘要

必填字段：`local_account_id`、`promotion_ids`。

`promotion_ids` 为单元 ID 列表，长度限制 `1-10`。

返回内容用于展示每个单元的审核建议、拒审原因和相关素材定位信息。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.list[]` | `object[]` | 单元审核建议列表 |
| `data.list[].promotion_id` | `number` | 单元id |
| `data.list[].material_reject[]` | `object[]` | 素材维度审核建议列表 |
| `data.list[].material_reject[].audit_platform` | `string` | 审核建议来源类型；审核建议来源类型，可选值：AD 广告审核；CONTENT 内容审核 |
| `data.list[].material_reject[].type` | `string` | 审核建议素材类型 |
| `data.list[].material_reject[].content` | `string` | 审核拒绝的具体内容 |
| `data.list[].material_reject[].video_material` | `object` | 审核拒绝视频素材 |
| `data.list[].material_reject[].video_material.video_id` | `string` | 审核拒绝视频素材id |
| `data.list[].material_reject[].video_material.video_url` | `string` | 审核拒绝视频素材url |
| `data.list[].material_reject[].image_material[]` | `object[]` | 审核拒绝图片素材 |
| `data.list[].material_reject[].image_material[].web_url` | `string` | 审核拒绝图片url |
| `data.list[].material_reject[].image_material[].web_uri` | `string` | 审核拒绝图片uri |
| `data.list[].material_reject[].image_material[].height` | `number` | 审核拒绝图片高度 |
| `data.list[].material_reject[].image_material[].width` | `number` | 审核拒绝图片宽度 |
| `data.list[].material_reject[].reject_reason[]` | `string[]` | 拒绝理由 |
| `data.list[].material_reject[].suggestion[]` | `string[]` | 审核建议 |
| `request_id` | `string` | 请求日志id |
