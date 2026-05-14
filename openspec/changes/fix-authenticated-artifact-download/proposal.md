# 修复认证 Artifact 下载

## 背景

用户在浏览器直接访问 `GET /api/threads/{thread_id}/artifacts/{path}?download=true` 时收到 `{"detail":"请先登录"}`，目标是让已登录用户能够正常下载 agent 生成的文件。后续验证发现，点击“分享/在新窗口打开”时访问不带 `download=true` 的同类 artifact URL 也会返回 `{"detail":"请先登录"}`。

后端 artifact 路由受 Gateway 认证保护；前端预览内容已通过 `fetchWithAuth` 读取，但下载入口和新窗口打开入口使用 `<a href>` 或 `window.open` 直接打开后端 URL。由于认证信息保存在前端会话中并通过请求头发送，浏览器直接打开 URL 不会自动携带 `Authorization`、`Business-Code` 和 `TENANT-ID`，因此被后端认证中间件拒绝。

## 目标

- 已登录用户点击 artifact 下载时，前端必须通过已有认证请求链路发起下载请求。
- 已登录用户点击 artifact 分享/在新窗口打开时，前端必须通过已有认证请求链路读取文件内容，再打开可访问的浏览器 Blob URL。
- 下载请求必须复用 `fetchWithAuth` 注入认证头，并保留后端返回的真实文件内容与文件名。
- 下载失败或登录失效时，沿用现有认证失败处理与用户提示机制。

## 非目标

- 不放宽后端 artifact 路由认证。
- 不把 token 放入下载 URL、查询参数或可分享链接。
- 不改变 artifact 存储路径、线程权限校验或后端文件响应语义。
- 不处理匿名用户下载；未登录用户仍应被要求登录。
- 不把受保护 artifact URL 变成可公开访问的长期分享链接。

## 影响范围

- 前端 artifact 下载交互：文件列表下载按钮、详情面板下载按钮。
- 前端 artifact 新窗口打开交互：详情面板“在新窗口打开”按钮，以及消息内 `/mnt/...` artifact 链接。
- 前端 artifact 工具函数：新增或调整认证下载 Blob 并触发浏览器保存的逻辑。
- 前端测试：覆盖认证下载使用 `fetchWithAuth`、文件名解析和 Blob URL 清理。

## 风险与约束

- 大文件下载会先进入浏览器内存 Blob；本次只修复现有下载失败，不引入流式保存能力。
- 新窗口打开预览若仍直接访问受保护 URL，可能继续受浏览器请求头限制；本次验收目标聚焦“文件能正常下载”。
- 由于 GitNexus MCP 工具未在当前 Cursor MCP 列表中暴露，实施阶段如无法运行 GitNexus impact analysis，需要在交付说明中明确该约束。
