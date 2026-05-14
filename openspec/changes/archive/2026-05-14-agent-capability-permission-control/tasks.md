# 任务清单

## 1. 定位与影响

- [x] 1.1 确认 `/user/availableAgents` 请求入口与鉴权头复用 `fetchWithAuth`。
- [x] 1.2 在可用工具范围内完成影响分析并记录 GitNexus 工具不可用约束。

## 2. 权限数据层

- [x] 2.1 新增 `agent-permissions` 模块，定义响应类型与能力常量（1001/1002/1003）。
- [x] 2.2 实现 `/user/availableAgents` 拉取与 `selected === 1` 过滤。
- [x] 2.3 归一化输出三类权限布尔值：`aiChat`、`smartDistribution`、`contentFactory`。
- [x] 2.4 将权限结果写入 `AuthSession` 并提供读取工具函数。

## 3. 登录后接线

- [x] 3.1 在登录成功后触发权限拉取并更新会话。
- [x] 3.2 在已有登录态但缺少权限缓存时补拉取一次，防止刷新后丢失。
- [x] 3.3 处理权限加载失败状态并提供可复用错误标记。

## 4. 页面与组件门禁

- [x] 4.1 在 chat 页面无 `aiChat` 权限时锁定交互并显示“暂无权限”提示。
- [x] 4.2 在 `InputBox` 中无 `smartDistribution` 权限时隐藏“智能投流”按钮。
- [x] 4.3 在 `InputBox` 中无 `contentFactory` 权限时隐藏“内容工厂”按钮。
- [x] 4.4 在提交链路增加 `aiChat` 权限校验，避免仅靠 UI 状态绕过。

## 5. 文案与验证

- [x] 5.1 新增/更新中英文权限提示文案与 locale 类型。
- [x] 5.2 补充单测（权限归一化、会话更新、按钮显隐、无权限门禁）。
- [x] 5.3 运行前端 `pnpm check` 与定向测试，记录结果（`pnpm check` 因项目既有 `better-auth` 依赖缺失失败，已通过定向 eslint 与单测完成本次变更验证）。
