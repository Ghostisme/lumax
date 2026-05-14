# 修复根路径新建对话重定向

## 背景

前端 middleware 已将站点根路径 `/` 重定向到 `/workspace/chats/new`，但在经过 Nginx 反向代理后，根路径访问未稳定落到新建对话页。当前 Nginx 配置没有根路径兜底跳转，只是将 `/` 代理给前端，导致该行为完全依赖 Next.js middleware。

## 目标

- 在 Nginx 配置中为根路径 `/` 增加显式跳转到 `/workspace/chats/new`。
- 覆盖宿主机域名配置与容器内入口配置，避免不同入口行为不一致。
- 保持 `/api/`、`/health`、`/.well-known/acme-challenge/` 和其他前端路由现有代理行为不变。

## 非目标

- 不调整前端 middleware 逻辑。
- 不改变聊天页路由结构或会话创建逻辑。
- 不调整 API、SSE 或静态资源代理策略。

## 影响范围

- Nginx 容器入口配置：`docker/nginx/nginx.conf`、`docker/nginx/nginx.local.conf`。
- 宿主机域名反向代理配置：`docker/nginx/dev-lumax.conf`、`docker/nginx/dev-lumax-ssl.conf`、`docker/nginx/lumaxai.conf`、`docker/nginx/lumaxai-ssl.conf`。

## 风险与约束

- 仅对精确根路径 `/` 生效，不能影响 `/workspace/...` 或其他页面的 Next.js 路由。
- HTTP 到 HTTPS 的 server 仍需要保留 ACME challenge 行为，避免证书续期路径被根路径跳转影响。
