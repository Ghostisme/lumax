# 移除未启用的 better-auth 前端残留

## 背景

前端当前主登录链路通过 `frontend/src/core/auth/api.ts` 调用后端或外部认证服务的 `/api/auth/...` 接口。

仓库中同时残留了一套 `better-auth` 预留实现：

- `frontend/src/app/api/auth/[...all]/route.ts`
- `frontend/src/server/better-auth/`
- 文档和启动脚本中的 `BETTER_AUTH_SECRET` / `BETTER_AUTH_URL` 说明与生成逻辑

但 `frontend/package.json` 与 `frontend/pnpm-lock.yaml` 当前没有声明 `better-auth` 依赖，导致 `pnpm check` 在 TypeScript 阶段报 `Cannot find module 'better-auth...'`。

## 问题

这套 `better-auth` 代码没有接入现有产品认证链路，却会造成前端类型检查失败，并增加部署脚本和配置文档中的无效认证配置负担。

## 目标

- 删除未启用的 `better-auth` 前端源码入口。
- 清理 `BETTER_AUTH_SECRET` / `BETTER_AUTH_URL` 相关文档说明。
- 清理本地启动和生产部署脚本中专为 `better-auth` 生成 secret 的逻辑。
- 保持现有 `/api/auth/...` 外部/后端认证链路不变。
- 让 `frontend pnpm check` 不再因为缺失 `better-auth` 依赖失败。

## 非目标

- 不引入新的认证方案。
- 不改造登录、登出、验证码、OAuth token 或租户选择业务逻辑。
- 不调整后端 Gateway 鉴权、权限模型或 Redis token 解析逻辑。
- 不新增 `better-auth` 依赖。

## 影响范围

- 前端未启用认证预留代码：`frontend/src/server/better-auth/**`
- 前端 Next API 路由：`frontend/src/app/api/auth/[...all]/route.ts`
- 前端文档：`frontend/README.md`、`frontend/CLAUDE.md`、`frontend/src/content/**/application/configuration.mdx`
- 启动和部署脚本：`scripts/serve.sh`、`scripts/serve.py`、`scripts/deploy.sh`

## 风险与约束

- 如果未来重新启用 `better-auth`，需要重新创建独立 OpenSpec change 并补齐依赖、配置、路由和产品接入设计。
- 本次只删除未启用残留，不改变当前用户可见登录链路。
- 删除前后需要搜索确认没有业务代码依赖 `@/server/better-auth` 或 `better-auth/*`。
