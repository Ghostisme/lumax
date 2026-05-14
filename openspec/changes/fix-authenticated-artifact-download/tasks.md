# 任务清单

## 1. 定位与设计

- [x] 1.1 确认 artifact 后端下载接口受 Gateway 认证保护。
- [x] 1.2 确认前端当前下载入口使用直接 URL 打开，无法携带 `Authorization` 请求头。
- [x] 1.3 确认 GitNexus impact analysis 可用性；当前 Cursor MCP 列表未暴露 GitNexus 工具，仓库 `.claude/skills/gitnexus` 也不存在，已改用静态调用关系记录低风险影响范围。

## 2. 实现

- [x] 2.1 新增或调整前端 artifact 下载工具，使用 `fetchWithAuth` 请求 `?download=true` 文件内容。
- [x] 2.2 从 `Content-Disposition` 或 artifact 路径解析下载文件名，并通过 Blob URL 触发浏览器保存。
- [x] 2.3 将文件列表下载按钮改为认证下载，不再直接 `<a href>` 打开受保护 URL。
- [x] 2.4 将详情面板下载按钮改为认证下载，并保留现有 loading/error 体验。
- [x] 2.5 新增认证打开 artifact 工具，使用 `fetchWithAuth` 读取文件内容并在新窗口打开 Blob URL。
- [x] 2.6 将详情面板“在新窗口打开”按钮改为认证打开，不再直接 `window.open` 受保护 URL。
- [x] 2.7 将消息内 `/mnt/...` artifact 链接改为认证打开，避免点击后新窗口返回“请先登录”。

## 3. 验证

- [x] 3.1 添加前端单元测试，覆盖认证下载、文件名解析和 Blob URL 清理。
- [x] 3.2 运行相关前端测试和本次修改文件 ESLint；完整 `pnpm check` 受既有 `feedback.ts` import/order 与 `better-auth` 类型依赖缺失阻断，`pnpm typecheck` 仍受既有 `better-auth` 类型依赖缺失阻断。
- [ ] 3.3 如可访问目标环境，验证已登录状态下 artifact 文件可正常下载。
- [x] 3.4 添加前端单元测试，覆盖认证打开 artifact 使用 `fetchWithAuth` 和 Blob URL。
- [ ] 3.5 如可访问目标环境，验证已登录状态下点击分享/在新窗口打开 artifact 不再返回“请先登录”。
