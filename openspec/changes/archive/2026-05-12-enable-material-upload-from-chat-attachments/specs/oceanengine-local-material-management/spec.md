## ADDED Requirements

### Requirement: 聊天附件必须可作为素材库上传的视频来源

`oceanengine-local-material` SHALL allow a video file uploaded through the current browser chat attachment flow to be used as the source file for `upload-video`, while preserving the existing requirement that the user must explicitly upload or authorize the file in the current task.

#### Scenario: 使用当前对话附件上传视频素材

- **GIVEN** 用户在真实浏览器中通过附件控件上传了视频文件
- **AND** Gateway 已在当前 thread uploads 中保存该文件
- **AND** 用户自然语言请求把该视频上传到本地推素材库
- **WHEN** Agent 调用 `oceanengine_local_material` 的 `upload-video`
- **THEN** 业务工具 SHALL 将该附件识别为当前任务授权的视频来源
- **AND** 业务工具 SHALL 保留 `filename`、文件大小、扩展名和当前 thread 归属信息用于上传前校验
- **AND** 业务工具 SHALL NOT 要求用户再次提供本地绝对路径来替代已上传附件

#### Scenario: 附件来源必须属于当前任务

- **GIVEN** 用户请求上传本地推视频素材
- **AND** payload 中的文件引用不属于当前 thread uploads，也不是本轮用户明确授权的文件路径或 URL
- **WHEN** `oceanengine_local_material` 执行上传前校验
- **THEN** 业务工具 SHALL 返回中文失败或追问，要求用户上传或授权具体视频文件
- **AND** 系统 SHALL NOT 扫描下载目录、最近文件、浏览器记录、剪贴板或任意目录来猜测素材
- **AND** 业务工具 SHALL NOT 调用 `localFileVideoUpload`

### Requirement: 素材库上传前必须确认目标服务可读取文件引用

`oceanengine-local-material` SHALL verify that the file reference passed to `localFileVideoUpload` is readable by the target upload service or has been converted to an equivalent supported reference before calling the MCP tool. A DeerFlow sandbox path such as `/mnt/user-data/uploads/...` SHALL NOT be treated as target-service-readable by default.

#### Scenario: 附件路径已转换为目标服务可读引用

- **GIVEN** 当前 thread 附件已通过格式、大小和授权校验
- **AND** 系统已将附件转换为 `platform-agent-biz` 可读取的文件引用
- **WHEN** 业务工具构造 `localFileVideoUpload` payload
- **THEN** payload SHALL 使用目标服务可读取的 `videoFilePath` 或目标服务明确支持的等价字段
- **AND** payload SHALL 继续包含正确的 `localAccountId` 与 `filename`
- **AND** 业务工具 SHALL 通过受管理 MCP guard 调用 `localFileVideoUpload`

#### Scenario: 目标服务无法读取附件

- **GIVEN** 当前 thread 附件存在且用户已授权
- **AND** 系统无法把附件解析为 `platform-agent-biz` 可读取的文件引用
- **WHEN** 用户请求上传到本地推素材库
- **THEN** 业务工具 SHALL 返回中文诊断，说明附件已收到但素材库上传服务无法读取该文件
- **AND** 诊断 SHALL 区分该问题与缺少附件、参数校验失败、敏感词拦截和平台业务失败
- **AND** 业务工具 SHALL NOT 声称素材已上传成功

#### Scenario: 不可见 sandbox 路径不得直接透传

- **GIVEN** 用户上传附件后，Agent 上下文中的文件路径为 `/mnt/user-data/uploads/<filename>`
- **AND** 目标 MCP 服务端不共享该 sandbox 路径
- **WHEN** 业务工具准备调用 `localFileVideoUpload`
- **THEN** 业务工具 SHALL NOT 仅把 `/mnt/user-data/uploads/<filename>` 作为 `videoFilePath` 透传给 MCP
- **AND** 系统 SHALL 先完成服务端可读引用转换或返回中文失败诊断
- **AND** 失败结果 SHALL NOT 被计为素材库上传成功

### Requirement: 素材库上传成功标准必须来自真实上传接口结果

浏览器验收和用户可见结果 SHALL distinguish chat attachment upload success from local material library upload success. The operation SHALL be considered successful only when `localFileVideoUpload` completes successfully and returns usable material data.

#### Scenario: 附件上传成功但素材库上传未完成

- **GIVEN** 浏览器附件上传接口返回成功
- **AND** `localFileVideoUpload` 未被调用、调用失败或返回文件不可读错误
- **WHEN** 系统向用户展示结果或记录验收状态
- **THEN** 用户可见结果 SHALL 说明附件已上传到对话，但本地推素材库上传未完成
- **AND** 验收记录 SHALL NOT 将该轮标记为素材库上传成功
- **AND** 系统 SHALL 保留中文失败原因用于下一步修复

#### Scenario: 素材库上传成功展示中文摘要

- **GIVEN** `oceanengine_local_material` 已通过真实 MCP 调用执行 `localFileVideoUpload`
- **AND** MCP 返回视频 ID、素材 ID、视频地址、视频大小或其它素材库结果字段
- **WHEN** Agent 生成最终回复
- **THEN** 回复 SHALL 用中文说明视频已上传到本地推素材库
- **AND** 回复 SHALL 展示可用的视频 ID、素材 ID 或视频地址
- **AND** 回复 SHALL NOT 展示 host 绝对路径、sandbox 路径、MCP payload JSON、内部 trace 或平台请求日志 ID

#### Scenario: MCP 返回缺少可确认素材结果

- **GIVEN** `oceanengine_local_material` 已通过真实 MCP 调用执行 `localFileVideoUpload`
- **AND** MCP 返回信息缺少可确认的素材 ID、视频 ID、明确上传状态和重复命中语义
- **WHEN** Agent 生成最终回复或验收记录
- **THEN** 用户可见结果 SHALL NOT 编造素材 ID、视频 ID、上传成功状态或“素材已上传”状态
- **AND** 用户可见结果 SHALL 说明上传接口未返回可确认的素材结果
- **AND** 该轮验收 SHALL NOT 仅凭泛化成功文案计为素材库上传成功

#### Scenario: 重复视频内容命中已有素材

- **GIVEN** 用户通过当前对话附件上传了一个视频文件
- **AND** 该视频内容的 `video_signature` 已经对应本地推素材库中的已有视频素材
- **WHEN** `localFileVideoUpload` 的 MCP 返回信息表明命中已有素材，或返回已有素材的视频 ID / 素材 ID 且带有重复、已存在、已上传、幂等命中等语义
- **THEN** 用户可见结果 SHALL 明确提示“素材已上传”
- **AND** 用户可见结果 SHALL 展示已有的视频 ID 或素材 ID
- **AND** 用户可见结果 SHALL NOT 声称素材中心会新增一个以本轮附件文件名命名的新视频
- **AND** 浏览器验收 SHALL 将该轮记录为重复内容幂等命中，而不是新增素材成功

### Requirement: 附件上传到素材库必须通过真实浏览器验收

`oceanengine-local-material` attachment-based video upload SHALL be validated through the real browser chat flow. Scripts, curl, SDK calls, direct MCP invocations, dry-run, mock results, or tool-name prompts SHALL NOT substitute for acceptance success.

#### Scenario: 真实浏览器附件上传验收

- **GIVEN** 本地前端、Gateway、Agent runtime 和必要的 MCP 服务已启动
- **AND** 测试人员已通过真实浏览器登录测试账号
- **WHEN** 测试人员通过附件控件上传视频，并用自然语言要求上传到本地推素材库
- **THEN** 验收证据 SHALL 显示 Gateway 保存附件成功
- **AND** Langfuse、后端日志或 trace SHALL 显示调用路径经过 `oceanengine_local_material`
- **AND** 证据 SHALL 显示真实调用 `localFileVideoUpload` 或返回明确的目标服务不可读诊断
- **AND** 输入 SHALL NOT 包含 `oceanengine-local-material`、`oceanengine_local_material`、`capability`、`payload_json`、`dry_run` 或底层 MCP tool 名

#### Scenario: 绕过真实用户路径不得计为通过

- **GIVEN** 某次验证通过脚本、curl、SDK、直接 MCP、mock、dry-run 或手工构造 tool payload 完成
- **WHEN** 汇总附件上传到素材库的浏览器验收状态
- **THEN** 该验证 MAY 作为定位证据
- **AND** 该验证 SHALL NOT 作为真实浏览器验收成功
- **AND** 仍必须通过浏览器附件控件和自然语言对话重新执行

#### Scenario: 素材中心数量用于新增成功验收判定

- **GIVEN** 测试人员需要确认一轮真实浏览器上传是否新增了素材库视频
- **AND** 测试人员可以在同一本地推账号的素材中心查看上传前后视频数量
- **WHEN** 上传后素材中心视频数量相比上传前增长
- **THEN** 该轮 MAY 计为新增素材成功
- **AND** 验收记录 SHALL 记录上传前数量、上传后数量和对应 Chrome 线程 ID
- **AND** 用户可见业务回复 SHALL 仍只展示 MCP 返回或后续真实查询可确认的素材字段

#### Scenario: 数量未增长时不得误判新增成功

- **GIVEN** 真实浏览器上传完成后素材中心视频数量没有增长
- **WHEN** `localFileVideoUpload` MCP 返回信息明确表达重复、已存在、已上传或幂等命中
- **THEN** 该轮 SHALL 计为“素材已上传 / 重复命中”
- **AND** 用户可见结果 SHALL 使用“素材已上传”而不是“新增成功”
- **WHEN** MCP 返回信息也缺少可确认素材结果和重复语义
- **THEN** 该轮 SHALL NOT 计为素材库上传成功
