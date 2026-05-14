# 巨量本地推素材管理接口索引

来源入口：`https://open.oceanengine.com/labels/37/docs/1810502232483907?origin=left_nav`

| 接口 | doc_id | path | capability | reference | rule | endpoint script | MCP 工具 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 异步上传本地推视频 | `1810070109238283` | `/open_api/v3.0/local/file/upload_task/create/` | `async-upload-local-video` | `references/async-upload-local-video.md` | `rules/async-upload-local-video.json` | `scripts/endpoints/async_upload_local_video.py` | `localFileUploadTaskCreate` |
| 查询异步上传本地推视频结果 | `1810070318501988` | `/open_api/v3.0/local/file/video/upload_task/list/` | `list-local-video-upload-tasks` | `references/list-local-video-upload-tasks.md` | `rules/list-local-video-upload-tasks.json` | `scripts/endpoints/list_local_video_upload_tasks.py` | `localFileVideoUploadTaskList` |
| 上传视频 | `1808003989738499` | `/open_api/v3.0/local/file/video/upload/` | `upload-video` | `references/upload-video.md` | `rules/upload-video.json` | `scripts/endpoints/upload_video.py` | `localFileVideoUpload` |
| 获取素材库视频 | `1808613640441882` | `/open_api/v3.0/local/file/video/get/` | `get-library-videos` | `references/get-library-videos.md` | `rules/get-library-videos.json` | `scripts/endpoints/get_library_videos.py` | `localFileVideoGet` |
| 获取抖音主页视频 | `1808004088768608` | `/open_api/v3.0/local/file/video/aweme/get/` | `get-aweme-videos` | `references/get-aweme-videos.md` | `rules/get-aweme-videos.json` | `scripts/endpoints/get_aweme_videos.py` | `localFileVideoAwemeGet` |
| 获取图文素材 | `1849312906748032` | `/open_api/v3.0/local/file/carousel/list/` | `list-carousel-materials` | `references/list-carousel-materials.md` | `rules/list-carousel-materials.json` | `scripts/endpoints/list_carousel_materials.py` | `localFileCarouselList` |
| 上传图片素材 | `1851654919296067` | `/open_api/v3.0/local/image/upload/` | `upload-image` | `references/upload-image.md` | `rules/upload-image.json` | `scripts/endpoints/upload_image.py` | `localImageUpload` |
| 获取视频素材评估标签 | `1848486485420108` | `/open_api/2/file/material_attributes/list/` | `list-video-material-attributes` | `references/list-video-material-attributes.md` | `rules/list-video-material-attributes.json` | `scripts/endpoints/list_video_material_attributes.py` | 当前 MCP 工具缺失 |

中文字段说明按官方文档；MCP tool 名、英文字段包装、上传文件表达方式和 required 差异按当前 `platform-agent-biz` MCP schema 执行。当前 `platform-agent-biz` 未暴露视频素材评估标签工具，该 capability 只能返回缺失诊断。
