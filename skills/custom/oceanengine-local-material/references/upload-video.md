# 上传视频

- 官方 `doc_id`：`1808003989738499`
- 官方 path：`/open_api/v3.0/local/file/video/upload/`
- 方法：`POST`
- capability：`upload-video`
- MCP 工具：`localFileVideoUpload`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `filename` | 是 | 视频文件名，官方长度上限 255 个字符 |
| `video_file_path` | 是 | 当前 MCP schema 使用的本地视频文件绝对路径 |
| `video_file_size_bytes` | 否 | 本地前置校验使用的文件大小，最大 1000M |

## 官方与 MCP 差异

- 官方文档是 `multipart/form-data`，包含 `video_file` 和 `video_signature`。
- 当前 `platform-agent-biz` MCP schema 要求 `videoFilePath`，并说明服务端读取文件后计算 MD5 作为 `video_signature`。
- 因此规则使用 `video_file_path`，不要求主 Agent 传 `video_signature`。

## 执行约束

- 文件路径必须由用户明确提供或授权。
- dry-run 只校验路径形态和扩展名，不读取文件内容。
- 支持扩展名：`mp4`、`mpeg`、`3gp`、`avi`。
- 官方横版视频宽度范围 1280 到 2560、高度范围 720 到 1440、宽高比范围 1.775 到 1.784。
- 官方竖版视频宽度范围 720 到 1440、高度范围 1280 到 2560、宽高比范围 0.555 到 0.564。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.video_id` | `string` | 视频ID |
| `data.size` | `number` | 视频大小 |
| `data.width` | `number` | 视频宽度 |
| `data.height` | `number` | 视频高度 |
| `data.video_url` | `string` | 视频地址 |
| `data.duration` | `double` | 视频时长 |
| `data.material_id` | `number` | 素材id，即多合一报表中的素材id，一个素材唯一对应一个素材id |
| `data.video_signature` | `string` | 视频md5值 |
| `request_id` | `string` | 请求日志id |
