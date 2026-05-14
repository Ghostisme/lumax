# 查询异步上传本地推视频结果

- 官方 `doc_id`：`1810070318501988`
- 官方 path：`/open_api/v3.0/local/file/video/upload_task/list/`
- 方法：`GET`
- capability：`list-local-video-upload-tasks`
- MCP 工具：`localFileVideoUploadTaskList`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `task_ids` | 是 | 上传任务 ID 列表，单次最多 100 个 |

## 响应重点

- 任务状态包含处理中、成功、失败。
- 成功任务返回视频素材信息；失败任务返回失败原因。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.list[]` | `object[]` | 任务列表 |
| `data.list[].status` | `string` | 任务处理状态 可选值: PROCESS 处理中 SUCCESS 成功 FAILED 失败 |
| `data.list[].error_msg` | `string` | 当任务失败后，会返回失败信息 |
| `data.list[].create_time` | `string` | 任务创建时间 |
| `data.list[].task_id` | `number` | 任务id |
| `data.list[].video_info` | `object` | 视频信息 |
| `data.list[].video_info.video_id` | `string` | 视频id |
| `data.list[].video_info.material_id` | `number` | 素材id |
| `data.list[].video_info.size` | `number` | 视频大小 |
| `data.list[].video_info.video_signature` | `string` | 视频md5 |
| `data.list[].video_info.width` | `number` | 视频宽 |
| `data.list[].video_info.height` | `number` | 视频高 |
| `data.list[].video_info.video_url` | `string` | 视频预览链接 |
| `data.list[].video_info.duration` | `double` | 视频时长 |
| `request_id` | `string` | 请求日志id |
