# 任务清单

## 1. 实现

- [x] 1.1 在 `backend/Dockerfile` production runtime stage 中从 build context 复制根目录 `tools/` 到镜像 `/app/tools`。
- [x] 1.2 将 `docker/docker-compose.yaml` Gateway command 的 `PYTHONPATH=.` 改为 `PYTHONPATH=/app:/app/backend`。
- [x] 1.3 在 `docker/docker-compose.yaml` 中把 `config.yaml` 同时挂载到 `/app/config.yaml`，并设置 `DEER_FLOW_PROJECT_ROOT=/app`。

## 2. 验证

- [x] 2.1 运行 `openspec validate fix-production-docker-root-tools-path --strict`。
- [x] 2.2 静态确认 `backend/Dockerfile` 包含 `COPY tools ./tools`。
- [x] 2.3 静态确认 `docker/docker-compose.yaml` Gateway command 包含 `PYTHONPATH=/app:/app/backend`。
- [x] 2.4 静态确认 `docker/docker-compose.yaml` 同时提供 `/app/config.yaml`、`/app/skills` 和 `DEER_FLOW_PROJECT_ROOT=/app`。
