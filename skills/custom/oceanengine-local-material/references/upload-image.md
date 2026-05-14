# 上传图片素材

- 官方 `doc_id`：`1851654919296067`
- 官方 path：`/open_api/v3.0/local/image/upload/`
- 方法：`POST`
- capability：`upload-image`
- MCP 工具：`localImageUpload`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `image_file_path` | 是 | 当前 MCP schema 使用的本地图片文件绝对路径 |
| `image_signature` | 是 | 图片 MD5 签名，当前 MCP schema 标记为 required |
| `is_aigc` | 是 | 是否 AIGC 图片，当前 MCP schema 标记为 required |
| `upload_type` | 是 | 当前只允许 `UPLOAD_BY_FILE` |

## 执行约束

- 文件路径必须由用户明确提供或授权。
- dry-run 只校验路径形态、扩展名和 MD5 格式，不读取文件内容。
- 支持扩展名：`jpg`、`jpeg`、`png`、`bmp`、`gif`。
- 官方图片大小上限为 1.5M；如用户提供 `image_file_size_bytes`，规则会按该上限校验。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.id` | `string` | 图片ID |
| `data.size` | `number` | 图片大小 |
| `data.width` | `number` | 图片宽度 |
| `data.height` | `number` | 图片高度 |
| `data.url` | `string` | 图片预览地址 |
| `data.format` | `string` | 图片格式 |
| `data.signature` | `string` | 图片md5 |
| `data.material_id` | `number` | 素材id，即多合一报表中的素材id，一个素材唯一对应一个素材id |
| `request_id` | `string` | 请求日志id |
