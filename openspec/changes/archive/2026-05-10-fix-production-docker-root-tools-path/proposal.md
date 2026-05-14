# 修复生产 Docker 根目录工具导入路径

## 背景

生产部署使用 `docker/docker-compose.yaml` 启动 `deer-flow-gateway`，其构建来源是 `backend/Dockerfile`。当前生产 runtime stage 只复制 `/app/backend`，没有复制仓库根目录 `tools/`；compose 中 Gateway 启动命令也只设置 `PYTHONPATH=.`，因此容器内无法导入 `tools.oceanengine_local_project`。

服务器验证结果显示 `/app/tools` 不存在，导致 `Could not import module tools.oceanengine_local_project`。这不是缺少第三方依赖，而是生产镜像和启动路径未包含根目录本地业务工具包。

## 目标

- 生产 Gateway 镜像必须包含 `/app/tools`。
- 生产 Gateway 启动时 `PYTHONPATH` 必须包含 `/app` 和 `/app/backend`。
- 生产 Gateway 容器内必须能以 `/app` 作为项目根目录读取 `config.yaml` 和 `skills/`。
- 保持 `config.yaml` 中 `tools.oceanengine_local_*` 注册路径不变。
- 不改动 OceanEngine 业务工具实现。

## 非目标

- 不新增第三方 `tools` 依赖。
- 不修改 hot reload Dockerfile 或 dev compose。
- 不调整 MCP、Nacos、平台接口逻辑。
- 不迁移或重构业务工具代码。

## 影响范围

- `backend/Dockerfile`：生产 runtime stage 复制 `tools/`。
- `docker/docker-compose.yaml`：生产 Gateway command 使用 `PYTHONPATH=/app:/app/backend`，并把 `config.yaml` 暴露到 `/app/config.yaml`，设置 `DEER_FLOW_PROJECT_ROOT=/app`。
- 生产部署重新 build 后，`tools.oceanengine_local_*` 能在容器内导入。

## 风险与约束

- 需要重新 build 生产 Gateway 镜像才能让 `COPY tools ./tools` 生效。
- 若实际部署使用其它 compose 或覆盖 command，也必须同步设置等价 `PYTHONPATH`。
