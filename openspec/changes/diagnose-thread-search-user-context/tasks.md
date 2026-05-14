# Tasks

- [ ] 在 `AuthMiddleware` 认证成功路径添加安全诊断日志，不记录 token 或原始 claims。
- [ ] 在 `/api/threads/search` 查询前添加当前用户上下文诊断日志。
- [ ] 在 `/api/threads/search` 查询后添加返回条数诊断日志。
- [ ] 添加或更新定向测试，验证日志不影响接口行为，且 search 仍按当前用户隔离。
- [ ] 运行后端定向测试。
- [ ] 根据日志输出判断历史会话查不到的实际断点。
