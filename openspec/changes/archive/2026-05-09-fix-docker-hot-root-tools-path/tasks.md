# 任务清单

## 1. 实现

- [x] 1.1 将 `docker/Dockerfile.backend.hot` 默认 CMD 中的 `PYTHONPATH=.` 改为 `PYTHONPATH=/app:/app/backend`。
- [x] 1.2 在 `docker/Dockerfile.backend.hot` 中复制根目录 `tools/` 到镜像 `/app/tools`。

## 2. 验证

- [x] 2.1 运行 `openspec validate fix-docker-hot-root-tools-path --strict`。
- [x] 2.2 静态确认 `docker/Dockerfile.backend.hot` 中 hot 后端启动命令包含 `/app` 和 `/app/backend`。
- [x] 2.3 静态确认 `docker/Dockerfile.backend.hot` 中包含 `COPY tools ./tools`。
