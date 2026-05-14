# 智能体能力权限管控

## 背景

当前 Lumax 仅基于登录态控制可用性，尚未在前端消费登录后单独返回的智能体能力权限。用户要求：

- 登录完成后请求 `/user/availableAgents` 获取智能体权限。
- 若无 AI 智能对话权限，页面不允许交互，输入区上锁并提示“暂无权限”。
- 若无 AI 智能投流权限，输入框不展示“智能投流”按钮。
- 若无 AI 内容工厂权限，输入框不展示“内容工厂”按钮。

已确认能力映射为：

- `1001` = AI智能对话
- `1002` = AI智能投流
- `1003` = AI内容工厂

并且仅当条目 `selected === 1` 时视为该能力可用。

## 目标

- 在前端登录态建立后，拉取并缓存 `/user/availableAgents` 权限数据。
- 将后端响应归一为三类能力布尔值，供页面统一消费。
- 按能力控制 chat 页面交互与输入区入口显隐，满足三条业务规则。
- 对权限加载中和加载失败给出可理解提示，避免误交互。

## 非目标

- 不改造后端接口与网关鉴权逻辑。
- 不新增新的权限能力类型（仅三类）。
- 不实现内容工厂或智能投流的新业务行为，仅做权限显隐与交互门禁。

## 影响范围

- 认证/会话层：`frontend/src/core/auth/session.ts`、`frontend/src/core/auth/index.ts`。
- 新增权限拉取与归一模块：`frontend/src/core/auth/agent-permissions.ts`。
- 登录后权限初始化：`frontend/src/components/workspace/workspace-sidebar.tsx`。
- 输入区按钮显隐与提交门禁：`frontend/src/components/workspace/input-box.tsx`。
- chat 页面上锁提示：`frontend/src/app/workspace/chats/[thread_id]/page.tsx`。
- i18n 文案：`frontend/src/core/i18n/locales/zh-CN.ts` 与 `frontend/src/core/i18n/locales/en-US.ts` 及类型定义。

## 风险与约束

- 当前 Cursor MCP 列表未暴露 GitNexus 工具；实施阶段将记录工具约束，并基于静态调用边界控制影响范围。
- `/user/availableAgents` 响应中能力可能缺失或 `selected` 为 `0`，前端应采用保守策略，避免放开未授权操作。
- 权限请求失败时应默认禁止对话交互并提示重试，不应误判为有权限。
