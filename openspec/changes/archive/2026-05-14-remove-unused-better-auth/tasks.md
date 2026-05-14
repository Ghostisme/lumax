# 任务清单

## 1. 定位与影响

- [x] 1.1 确认当前 `better-auth` 引用范围。
- [x] 1.2 确认现有主认证链路仍通过 `frontend/src/core/auth/api.ts` 访问 `/api/auth/...`。
- [x] 1.3 对将要删除的源码入口完成影响评估，并记录风险。

## 2. 实现

- [x] 2.1 删除 `frontend/src/server/better-auth/**`。
- [x] 2.2 删除未启用的 `frontend/src/app/api/auth/[...all]/route.ts`。
- [x] 2.3 清理前端文档中的 `better-auth`、`BETTER_AUTH_SECRET` 和 `BETTER_AUTH_URL` 说明。
- [x] 2.4 清理启动和部署脚本中专为 `better-auth` 生成或持久化 secret 的逻辑。

## 3. 验证

- [x] 3.1 搜索确认没有残留 `better-auth` import 或 `@/server/better-auth` 引用。
- [x] 3.2 运行 `cd frontend && pnpm check`。
- [x] 3.3 如脚本清理影响启动路径，执行必要的静态检查或说明未执行原因。
