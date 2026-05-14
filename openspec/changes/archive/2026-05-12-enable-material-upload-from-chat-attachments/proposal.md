# 支持通过聊天附件上传本地推素材库视频

## Why

真实浏览器验收中，用户以普通上传控件选择 `/Users/shanqijie/Downloads/视频 2.mp4`，本地 Gateway 已将附件保存到当前 thread 的 uploads 目录，并在对话上下文中暴露为 `/mnt/user-data/uploads/视频 2.mp4`。随后 Agent 正确识别用户意图为“上传到本地推素材库”，读取 `oceanengine-local-material` 规则，并调用 `oceanengine_local_material` 的 `upload-video` capability。

Langfuse 证据显示本轮 payload 包含：

- `local_account_id=1854708763953159`
- `filename="视频 2.mp4"`
- `video_file_path="/mnt/user-data/uploads/视频 2.mp4"`

但 `platform-agent-biz` 的 `localFileVideoUpload` 返回 `videoFilePath 对应文件不存在`。现有 `skills/custom/oceanengine-local-material/references/upload-video.md` 已说明：官方接口是 `multipart/form-data`，但当前 MCP schema 要求 `videoFilePath`，并由服务端读取文件计算 `video_signature`。因此，聊天附件上传成功并不等于素材库上传成功；`/mnt/user-data/uploads/...` 是 DeerFlow 对话 sandbox 路径，目标 MCP 服务端未必可见。

本变更要补齐“聊天附件作为素材来源”到“本地推素材库上传服务可读取文件”的契约，避免把对话 sandbox 路径直接透传到 MCP 后才失败。

## What Changes

- 用户通过浏览器真实附件上传视频后，Agent 可以把该附件作为 `oceanengine-local-material` 的上传素材来源。
- `oceanengine_local_material` 在调用 `localFileVideoUpload` 前，必须确认传给目标服务的文件引用对目标上传链路可读。
- 当附件只存在于 DeerFlow thread uploads 中而目标 MCP 服务不可读时，系统必须返回中文可行动诊断，说明附件已收到但尚未完成素材库上传。
- 上传成功标准必须是素材库上传接口返回成功，并展示视频 ID、素材 ID、视频地址等可用结果；附件上传成功不得被当成素材库上传成功。
- 浏览器验收必须使用真实用户附件上传和自然语言请求，并结合 Langfuse、后端日志或 trace 证明进入 `oceanengine_local_material` 与 `localFileVideoUpload` 链路。

## Non-Goals

- 提案阶段不修改功能代码、运行时配置、skill 文件或测试实现。
- 不改变 `oceanengine-local-material` 的 capability 范围、官方字段语义或响应字段同步规则。
- 不绕过 `oceanengine_local_material` 原生业务工具。
- 不使用 curl、SDK、HTTP API、脚本、直接 MCP 调用或 mock 成功替代浏览器真实上传验收。
- 不把聊天附件保存路径、浏览器本地路径、临时 host 路径或内部 trace 默认展示给最终用户。
- 不处理敏感词拦截本身；敏感词只作为前序验收失败背景，不属于本变更修复范围。

## Impact

- Gateway 上传链路：`/api/threads/{thread_id}/uploads` 返回和保存的附件元数据。
- Agent 附件上下文：对话中可见的 uploaded files 信息和 `/mnt/user-data/uploads/...` 虚拟路径。
- `oceanengine_local_material` 上传视频能力：`upload-video` 的文件来源解析、上传前可读性诊断、MCP payload 构造和用户可见结果。
- 公共 OceanEngine endpoint runner / MCP client：若 Apply 阶段选择在公共运行时处理文件引用，需保证项目、单元、素材其它能力不受无关影响。
- 浏览器验收和 Langfuse 证据记录：需要证明附件上传、工具选择、真实 MCP 调用和最终素材库结果。

## Risks and Constraints

- 当前 MCP schema 由 `platform-agent-biz` 服务端读取 `videoFilePath`，这意味着本地 Agent 可读路径不一定是 MCP 服务可读路径。Apply 阶段必须先确认 `platform-agent-biz` 支持的文件传递方式，不能凭空假设共享文件系统。
- 如果只能通过可公开访问 URL、对象存储临时地址或服务端可读 host path 传递文件，必须保留用户授权来源和文件安全边界。
- 修改任何函数、类或方法前必须按 GitNexus 规则执行 upstream impact analysis；高风险或关键调用链必须先向用户说明。
- Apply 阶段涉及设计或代码变更时必须使用 Superpowers。
- 验收输入不得点名 `oceanengine-local-material`、`oceanengine_local_material`、`capability`、`payload_json`、`dry_run`、底层 MCP tool 名或“直接调用某工具”。
