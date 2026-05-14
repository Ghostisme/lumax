---
name: oceanengine-local-material
description: 通过 DeerFlow 原生业务工具执行巨量引擎本地推素材管理，包括视频上传、上传任务查询、素材库视频、抖音主页视频、图文素材、图片上传和视频素材评估标签查询。
---

# 巨量本地推素材管理

通过 DeerFlow 原生业务工具 `oceanengine_local_material` 调用巨量引擎本地推素材管理模块接口。主文件只负责导航和执行流程；接口字段、枚举和示例按需读取 `references/`，机器可执行规则按需读取 `rules/`。

## 使用时机

- 用户要上传本地推视频、图片或异步创建视频上传任务。
- 用户要查询视频上传任务结果、素材库视频、抖音主页视频或图文素材。
- 用户要查询视频素材评估标签。

## ReAct 流程

1. 明确用户意图并选择 `rules/index.json` 中的 `capability`。
2. 如参数、枚举或口径不明确，读取对应 `references/*.md` 和 `rules/*.json`。
3. 将用户输入整理成 JSON，字段名使用 snake_case。
4. 即使用户缺少必填参数，也不得直接调用 `ask_clarification` 自行汇总多个缺失项；必须先调用 DeerFlow 原生业务工具 `oceanengine_local_material`，传入 `capability`、`payload_json` 和可选 `dry_run`。
5. 工具返回参数校验失败时，直接按 `data.user_visible_text` 或首条中文错误向用户追问；不得追加其它未展示缺失项，也不要绕过本地校验直调 MCP。
6. 工具返回 MCP 缺失或 MCP 失败时，保留 `request_id`、`mcp_tool_name` 和错误摘要，方便排查。

## Capability

| capability | 用途 | MCP 工具 |
| --- | --- | --- |
| `async-upload-local-video` | 异步上传本地推视频 | `localFileUploadTaskCreate` |
| `list-local-video-upload-tasks` | 查询异步上传本地推视频结果 | `localFileVideoUploadTaskList` |
| `upload-video` | 上传视频 | `localFileVideoUpload` |
| `get-library-videos` | 获取素材库视频 | `localFileVideoGet` |
| `get-aweme-videos` | 获取抖音主页视频 | `localFileVideoAwemeGet` |
| `list-carousel-materials` | 获取图文素材 | `localFileCarouselList` |
| `upload-image` | 上传图片素材 | `localImageUpload` |
| `list-video-material-attributes` | 获取视频素材评估标签 | 当前 MCP 工具缺失 |

## 必填项

- 本地推 v3.0 素材能力通常需要 `local_account_id`。
- 异步上传视频需要 `filename` 和 `video_url`。
- 查询上传任务需要 `task_ids`，单次最多 100 个。
- 上传视频需要 `filename` 和 `video_file_path`；当前 MCP schema 由服务端读取文件并计算 `video_signature`。
- 上传图片需要 `image_file_path`、`image_signature`、`is_aigc` 和 `upload_type=UPLOAD_BY_FILE`。
- 视频素材评估标签接口使用 `account_id`、`account_type`、`page` 和 `page_size`，但当前 MCP 工具缺失。

## 约束

- 主 Agent 必须调用 `oceanengine_local_material`，不得直接调用 `nacos-mcp-router_use_tool` 执行上述 MCP 工具。
- 不得使用 `task` 或任何子代理执行、诊断或替代执行本 skill；必须由主 Agent 直接调用 `oceanengine_local_material` 或返回业务工具不可用。
- 本地校验失败时不得调用 MCP。
- 上传文件必须来自用户当前任务中明确提供或明确授权的路径；不得扫描最近文件、下载目录、浏览器记录、剪贴板或任意目录来猜测素材。
- `video_url` 仅用于异步上传视频，并按官方限制只接受连山云素材服务生成的 tos 链接。
