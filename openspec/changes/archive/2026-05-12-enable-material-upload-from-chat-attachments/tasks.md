# 任务清单

## 1. 调研与影响分析

- [x] 1.1 使用 GitNexus 确认 `platform-agent-biz` 的 `localFileVideoUpload` 对 `videoFilePath` 的真实语义；记录 `LocalFileAssetController.localFileVideoUpload`、`LocalFileAssetServiceImpl.uploadLocalVideo`、`resolveRequiredFile`、`FileDigestUtil.md5Hex` 的调用链证据。
- [x] 1.2 使用 GitNexus 梳理浏览器附件上传到 Gateway thread uploads、前端 `additional_kwargs.files`、`UploadsMiddleware`、Agent uploaded files 上下文、`oceanengine_local_material` payload 的现有链路。
- [x] 1.3 对 Apply 阶段计划修改的 `upload_files`、`UploadsMiddleware.before_agent`、`run_oceanengine_local_material`、`run_endpoint`、`build_mcp_payload`、`invoke_endpoint` 或新增辅助函数运行 GitNexus upstream impact analysis，并记录直接调用方、受影响流程和风险级别。
- [x] 1.4 若 GitNexus 索引提示 stale，先运行 `npx gitnexus analyze` 后再继续影响分析；跨仓库涉及 `platform-biz` 时也必须刷新对应仓库索引。
- [x] 1.5 明确实现边界：不得在 `build_mcp_payload` 等通用 MCP 字段映射层硬编码素材上传特例；优先在 `tools/oceanengine_local_material.py` 或根目录 `tools/` 同域辅助模块处理素材文件来源解析。
- [x] 1.6 明确受保护源码边界：不得为本需求修改 `backend/packages/harness/deerflow/**` 中通用 DeerFlow 中间件，除非后续单独获得用户批准并满足 OpenSpec / Superpowers 约束。

## 2. 设计与实现

- [x] 2.1 设计当前 thread 附件到素材上传文件引用的最小转换方案，明确目标服务可读性的判断方式。
- [x] 2.2 在素材上传链路中只接受当前任务明确上传或授权的文件来源，不扫描本地目录、最近文件、浏览器记录或剪贴板。
- [x] 2.3 在调用 `localFileVideoUpload` 前校验附件存在、格式合规、大小元数据一致，并确认传给 MCP 的文件引用对目标上传服务可读。
- [x] 2.4 当目标服务不可读取附件时，返回中文可行动诊断，区分附件已上传但素材库上传未完成。
- [x] 2.5 保持 `oceanengine_local_material` 原生业务工具入口、MCP guard、Pmydantic 校验、payload 字段映射和用户可见清洗边界不被绕过。
- [x] 2.6 验证业务工具能否通过 `ToolRuntime`、运行时 `context.thread_id`、`RunnableConfig.configurable.thread_id` 或其它现有上下文拿到当前 `thread_id`；若无法稳定获取，返回中文诊断或补齐受控上下文传递，不得让 Agent 猜测 thread。
- [x] 2.7 将 `/mnt/user-data/uploads/<filename>` 解析为当前 thread uploads 中的授权文件时，必须校验 `filename`、大小、扩展名和当前用户隔离目录；不得接受目录穿越或跨 thread 引用。
- [x] 2.8 如果 `platform-agent-biz` 与 DeerFlow 不共享文件系统，必须明确采用受控文件投递、共享挂载或平台侧可读路径方案；方案不可用时返回“附件已收到但素材库上传服务不可读取”的中文诊断。
- [x] 2.9 Apply 阶段涉及设计或代码变更时先使用 Superpowers，并遵守受保护源码包边界。
- [x] 2.10 处理重复视频内容上传：仅依据 `localFileVideoUpload` 的 MCP 返回信息判断重复；当返回信息明确表示重复、已存在、已上传、幂等命中，或返回已有 `materialId` / `videoId` 并带有重复语义时，用户可见结果必须提示“素材已上传”，不得误报为新增素材。
- [x] 2.11 处理 MCP 返回缺少可确认素材结果的情况：缺少 `materialId`、`videoId`、明确上传状态和重复命中语义时，不得编造素材 ID、视频 ID、上传成功或“素材已上传”状态。

## 3. 测试

- [x] 3.1 增加或更新 Gateway 上传链路测试，覆盖附件元数据、虚拟路径和 host 保存路径关系。
- [x] 3.2 增加素材管理上传视频测试，覆盖当前 thread 附件可解析为上传来源的正向路径。
- [x] 3.3 增加目标服务不可读文件引用的负向测试，断言不会调用或不会继续声称素材库上传成功。
- [x] 3.4 增加安全边界测试，确认未授权路径、非当前 thread 附件、目录穿越和不支持格式被中文拒绝。
- [x] 3.5 增加用户可见结果测试，确认最终回复不泄漏 host 路径、MCP payload、trace 或平台请求日志 ID。
- [x] 3.6 增加 MCP payload 测试，确认 `video_file_path` 只有在转换为目标服务可读引用后才映射为 `videoFilePath`，且不影响非素材上传 capability。
- [x] 3.7 增加 `platform-biz` 侧或集成层验证：`localFileVideoUpload` 读取的路径必须存在于 Java 服务运行环境，否则按预期返回文件不可读诊断。
- [x] 3.8 增加重复内容上传测试：模拟 `localFileVideoUpload` MCP 返回重复 / 已存在 / 已上传语义时，断言系统返回“素材已上传”并保留已有 `materialId` / `videoId`，不展示“新增成功”类误导文案。
- [x] 3.9 增加 MCP 空结果 / 弱结果测试：当 MCP 返回缺少可确认素材字段和重复语义时，断言系统不会编造上传结果，并返回“上传接口未返回可确认的素材结果”类中文提示。

## 4. 本地环境启动

- [x] 4.1 启动 public 环境 Java 服务，至少包含本轮素材上传依赖的 `auth`、`upms`、`gateway`、`agent` / `platform-agent-biz` 相关服务，并确认 Nacos 注册和 `platform-agent-biz` MCP endpoint 可解析。
- [x] 4.2 启动 DeerFlow 本地前端、Gateway 和 Agent runtime，确保 DeerFlow 请求指向本地 Gateway 服务，而不是 `dev.lumaxai.cn` 或其它远端 Gateway。
- [x] 4.3 检查 `config.yaml`、环境变量和运行日志，确认 `oceanengine_local_material` 注册可用，`platform-agent-biz` 通过 public 环境 Nacos 解析到真实 MCP endpoint。
- [x] 4.4 如果 Chrome 登录显示成功但仍反复弹出登录框，检查 Redis 会话 / token 相关库；按本轮约定切换并核验 Redis `db=3` 后再重试登录。
- [x] 4.5 环境启动完成后，先用健康检查、Nacos 注册、Gateway 登录态和 MCP tools/list 证据确认链路可用；不得用这些检查替代最终浏览器验收，也不得用跳过 MCP 的 HTTP、SDK、curl、脚本或本地文件检查路径替代验收。

## 5. 浏览器验收

- [x] 5.1 使用 Chrome 真实登录测试账号；测试凭证只使用本轮用户提供的账号密码，不写入文档、日志摘要或提交信息。
- [x] 5.2 使用 Chrome 真实附件控件上传用户明确授权的视频文件，不用脚本、curl、SDK、直接 MCP、跳过 MCP 的 Java Controller HTTP / 开放平台 API 调用，或浏览器 DevTools 构造请求代替上传。
- [x] 5.3 用自然语言请求上传到本地推素材库，输入必须模拟真实用户表达，不得包含 `oceanengine-local-material`、`oceanengine_local_material`、`capability`、`payload_json`、`dry_run`、底层 MCP tool 名、脚本路径或“直接调用某工具”。
- [x] 5.4 使用本地推账号 `1854708763953159` 执行素材库上传验收，并确认结果属于本地推素材库视频上传，而不是仅完成聊天附件上传。
- [x] 5.5 结合 Gateway 日志、Langfuse trace、Java `platform-agent-biz` 日志和工具结果记录证据：附件上传成功、进入 `oceanengine_local_material`、通过 MCP 调用 `localFileVideoUpload`、Java 服务读取到文件、素材库上传成功或明确失败分层；验收证据必须能证明没有跳过 MCP。
- [x] 5.6 如果因敏感词拦截、登录态、Redis 会话、Nacos、MCP endpoint、Java 服务、文件可见性或平台业务返回失败，记录为对应失败类型，不计为素材库上传成功。
- [x] 5.7 如果 Chrome 验收发现问题，必须结合 Langfuse trace、本地 Gateway / Agent runtime 日志、Java `platform-agent-biz` 日志、Nacos / MCP 日志和浏览器可见结果定位根因；不得只凭页面文案猜测原因。
- [x] 5.8 对定位到的代码、配置或环境问题完成修复后，必须重新启动受影响服务并重跑同一 Chrome 真实用户用例；重试仍必须经过 MCP 调用链路，未重试通过前不得标记该验收项完成。
- [x] 5.9 稳定性验收固定使用本轮用户明确授权的视频 `/Users/shanqijie/Downloads/视频 2.mp4`，通过 Chrome 真实附件控件和自然语言请求连续执行 10 次素材库上传；每次都必须重新走附件上传、Agent、`oceanengine_local_material`、MCP `localFileVideoUpload` 和 Java 服务读取文件链路。
- [x] 5.10 10 次稳定性验收必须逐次记录 Chrome 线程 ID、Langfuse trace ID、Java 日志时间窗、MCP 调用证据、素材库返回的视频 ID / 素材 ID / 视频地址摘要和通过或失败结论；任一次失败都必须按 5.7 定位并按 5.8 修复后重试，不得把失败轮次计入 10 次成功。
- [x] 5.11 验收成功后汇总 10 次稳定性结果；不得记录密码、Cookie、token、host 绝对路径或平台请求日志 ID 到用户可见结果。
- [x] 5.12 重复内容验收：使用同一视频内容但不同附件文件名执行至少 2 次 Chrome 真实上传；当第二次及后续的 `localFileVideoUpload` MCP 返回信息表达重复、已存在、已上传或幂等命中时，用户可见结果必须提示“素材已上传”，素材中心未新增记录也不得计为失败。
- [x] 5.13 新增素材验收：如需验证素材中心新增记录，必须使用内容签名不同的视频变体，仍通过 Chrome 真实附件控件和自然语言请求上传；不得仅改文件名来规避去重判断。
- [x] 5.14 新增素材验收必须记录素材中心上传前后视频数量；数量增长才计为新增素材成功，数量不增长且 MCP 返回重复语义时计为重复命中，数量不增长且 MCP 缺少可确认信息时不得计为成功。

## 6. 校验与交付

- [x] 6.1 运行定向后端测试和素材管理相关测试。
- [x] 6.2 运行前端上传相关检查或定向测试。
- [x] 6.3 运行 `openspec validate enable-material-upload-from-chat-attachments --strict`。
- [x] 6.4 运行 GitNexus detect changes 或等价范围检查，确认改动只影响预期链路。
- [x] 6.5 汇总修改文件、测试结果、本地 public 环境启动证据、Chrome 浏览器验收线程或 trace、剩余风险和是否需要平台侧配合。
