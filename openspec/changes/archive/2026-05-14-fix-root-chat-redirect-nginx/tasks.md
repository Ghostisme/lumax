# 任务清单

## 1. 定位与影响

- [x] 1.1 确认前端根路径 middleware 的目标路径为 `/workspace/chats/new`。
- [x] 1.2 盘点宿主机与容器内 Nginx 配置中根路径代理行为。

## 2. 实现

- [x] 2.1 在容器内 Nginx 配置中为精确根路径 `/` 增加新建对话页跳转。
- [x] 2.2 在宿主机 dev/prod HTTP 与 HTTPS 配置中同步根路径跳转。
- [x] 2.3 确认 ACME challenge、API、健康检查与其他前端路由代理不受影响。

## 3. 验证

- [x] 3.1 运行可用的 Nginx 配置语法检查或记录无法运行原因。
- [x] 3.2 检查改动 diff，确认仅新增根路径跳转相关配置。

验证记录：`nginx -t -c docker/nginx/nginx.local.conf` 通过；`docker/nginx/nginx.conf` 在本机直接检查时因未处于 Docker 网络而无法解析 `gateway:8001`，当前 shell 也未提供 `docker` 命令用于容器内复验。
