# 修复 hot reload Docker 根目录工具导入路径

## 背景

`docker/Dockerfile.backend.hot` 的默认启动命令在 `/app/backend` 下执行，并设置 `PYTHONPATH=.`。这只暴露后端目录，无法稳定导入仓库根目录的 `tools.*` 原生业务工具。

当前 `config.yaml` 中 OceanEngine 本地推原生业务工具使用根目录路径，例如 `tools.oceanengine_local_project:oceanengine_local_project_tool`。服务器使用 hot reload Dockerfile 部署时，若 `/app` 未进入 Python import path，会出现 `Could not import module tools.oceanengine_local_project`。

## 目标

- hot reload Docker 后端启动时必须能导入 `/app/tools`。
- hot reload Docker 镜像即使未挂载完整项目根目录，也必须包含 `tools/` 本地业务扩展包。
- 保持 `config.yaml` 中 `tools.oceanengine_local_*` 注册路径不变。
- 只做 Dockerfile 级别的最小修改，不改业务代码。

## 非目标

- 不修改 OceanEngine 原生业务工具实现。
- 不调整生产 `backend/Dockerfile` 或其它 compose 文件。
- 不新增第三方 `tools` 依赖。
- 不处理与本次导入路径无关的 MCP、Nacos 或平台接口问题。

## 影响范围

- `docker/Dockerfile.backend.hot`：复制根目录 `tools/` 并调整默认 CMD 的 `PYTHONPATH`。
- hot reload Docker 部署：后端进程将同时看到 `/app` 和 `/app/backend`。

## 风险与约束

- 该变更只影响使用 `docker/Dockerfile.backend.hot` 默认 CMD 的部署方式。
- `PYTHONPATH` 增加 `/app` 后，根目录同名包会进入解析范围；当前目标正是解析根目录 `tools` 包。
