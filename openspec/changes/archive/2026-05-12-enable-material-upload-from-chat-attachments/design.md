# 设计说明

## 问题分层

本次失败不是普通附件上传失败。真实浏览器路径已经完成前端选文件和 Gateway `/api/threads/{thread_id}/uploads` 保存，Agent 也拿到了 `/mnt/user-data/uploads/视频 2.mp4`。失败发生在后续素材库上传阶段：`localFileVideoUpload` 所在的 `platform-agent-biz` 服务端无法读取该 sandbox 路径。

因此设计上需要把文件生命周期分成两段：

1. 浏览器附件上传：用户把本地文件交给当前 DeerFlow thread。
2. 素材库上传：`oceanengine_local_material` 把已授权附件转换为目标 MCP 服务可读取的文件引用，并调用 `localFileVideoUpload`。

只有第二段成功，才算“上传到本地推素材库”成功。

## 文件引用契约

Apply 阶段不得继续把 `/mnt/user-data/uploads/...` 直接视为平台服务端可读路径。实现必须在调用 MCP 前完成以下判断：

- 来源是否来自当前任务中用户明确上传或授权的附件。
- 附件是否仍存在于当前 thread uploads 中，文件名、大小和扩展名是否与规则一致。
- 将要传给 `localFileVideoUpload` 的 `videoFilePath` 是否对目标上传服务实际可读，或是否已经转换成目标服务支持的等价文件引用。

如果目标服务不可读取该文件引用，`oceanengine_local_material` 应返回中文诊断，说明“附件已收到，但素材库上传服务无法读取该文件”，并给出运维或实现层需要修复的文件传递方式；不得把该失败伪装成参数缺失或上传成功。

## 可选实现方向

Apply 阶段应先通过 `platform-agent-biz` MCP schema、Java 服务实现或运行日志确认它接受的文件输入语义，再选择最小可行方案：

- 如果 `platform-agent-biz` 与 Gateway 运行在共享文件系统或容器挂载下，优先把 thread upload 的 host path 映射为目标服务可见路径，并在调用前验证映射存在。
- 如果目标服务只接受自身服务器本地路径，需由 Gateway 或业务工具提供受控的临时文件投递机制，保证路径只指向当前授权附件。
- 如果目标服务支持 URL 或对象存储引用，应优先使用已有安全上传/临时 URL 能力，并在规则或适配层中明确与 `videoFilePath` 的关系。
- 如果当前平台能力无法支持从聊天附件入库，系统必须返回稳定中文失败诊断，不得建议用户改用脚本、curl、SDK 或直接 MCP。

## 安全边界

- 只能使用用户在当前任务明确上传或授权的文件；不得扫描下载目录、最近文件、浏览器记录、剪贴板或任意目录。
- 不得在最终用户可见回复中暴露 host 绝对路径、容器挂载路径、内部 trace、MCP payload JSON 或平台请求日志 ID。
- 失败诊断面向用户时应区分“附件上传失败”“附件已上传但素材库服务不可读”“MCP 调用失败”“平台业务失败”。
- 测试和日志可记录内部路径用于排查，但不得把这些内部标识复制回浏览器自然语言输入中降低验收难度。

## 重复内容处理

`platform-agent-biz` 当前上传实现会读取 `videoFilePath` 对应文件并计算 `video_signature`，再把 `filename`、`local_account_id`、`video_file` 和 `video_signature` 作为 `multipart/form-data` 传给巨量上传接口。实测同一视频内容即使更换附件文件名，平台仍返回同一个 `materialId` / `videoId`，素材中心不会新增记录，说明平台按内容签名做去重或幂等命中。

Apply 阶段需要把这类结果从“新增上传成功”中区分出来。判重只基于 `localFileVideoUpload` 这次 MCP 调用的返回信息：当 MCP 返回已有素材的 `materialId` / `videoId`，或返回信息中明确表达重复、已存在、已上传、幂等命中等语义时，用户可见回复应明确写“素材已上传”，并展示已有 `materialId` / `videoId`。不得让用户误以为素材中心会出现一个以新文件名命名的新视频。

本变更不引入上传前 / 上传后素材列表查询作为判重依据。如果 MCP 返回信息只表示成功但没有重复或已存在语义，系统不得臆造“素材已上传”状态；应仅描述为“上传接口返回成功”，并展示 MCP 返回的视频 ID、素材 ID 等字段。

如果 `localFileVideoUpload` 的 MCP 返回信息没有给出可确认的素材结果字段，例如缺少 `materialId`、`videoId`、明确上传状态或重复命中语义，用户可见回复不得编造上传结果，也不得自行生成素材 ID、视频 ID 或“素材已上传”状态。此时应说明上传接口未返回可确认的素材结果，并提示需要通过素材中心或后续查询确认。

测试和验收可以使用素材中心数量作为外部判定证据，但该证据只用于验收记录，不作为用户可见业务结果的编造来源。新增素材验收时，应在真实浏览器流程前后查看素材中心视频数量：数量增长才能计为“新增素材成功”；数量不增长但 MCP 返回明确重复语义时，计为“素材已上传 / 重复命中”；数量不增长且 MCP 返回缺少可确认信息时，不得计为上传成功。

## 验收证据

本变更完成后，验收必须保留四类证据：

- 浏览器截图、日志或 network 证据证明用户通过附件控件上传视频。
- Gateway 日志证明 `/api/threads/{thread_id}/uploads` 保存了对应文件。
- Langfuse 或后端 trace 证明 Agent 读取素材管理 skill/rule，并调用 `oceanengine_local_material` 的 `upload-video`。
- MCP 调用或工具结果证明 `localFileVideoUpload` 成功返回素材库视频结果；若失败，必须按失败分层记录，不得计为通过。
