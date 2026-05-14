# 异步上传本地推视频

- 官方 `doc_id`：`1810070109238283`
- 官方 path：`/open_api/v3.0/local/file/upload_task/create/`
- 方法：`POST`
- capability：`async-upload-local-video`
- MCP 工具：`localFileUploadTaskCreate`

## 请求字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `local_account_id` | 是 | 本地推账号 ID |
| `filename` | 是 | 视频文件名 |
| `video_url` | 是 | 视频 URL。官方限制为连山云素材服务上传生成的 tos 链接，不支持其他三方链接地址，文件大小最大 1000M |

## 执行约束

- 该接口只创建异步上传任务，成功后返回 `task_id`。
- `video_url` 必须由用户明确提供，不能从历史、剪贴板或目录扫描推断。
- 本地规则会先校验 tos 链接形态，失败时不会调用 MCP。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.task_id` | `number` | 任务id |
| `request_id` | `string` | 请求日志id |
