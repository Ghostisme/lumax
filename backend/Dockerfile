# Backend Dockerfile — multi-stage build
# Stage 1 (builder): compiles native Python extensions with build-essential
# Stage 2 (dev):     retains toolchain for dev containers (uv sync at startup)
# Stage 3 (runtime): clean image without compiler toolchain for production

# UV source image (override for restricted networks that cannot reach ghcr.io)
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.7.20
FROM ${UV_IMAGE} AS uv-source

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

ARG APT_MIRROR
ARG NODE_VERSION=22.16.0
ARG UV_INDEX_URL
# Optional extras to install (e.g. "postgres" for PostgreSQL support)
# Usage: docker build --build-arg UV_EXTRAS=postgres ...
ARG UV_EXTRAS

# Configure APT sources — use Chinese mirrors (deb.debian.org is unreachable from Aliyun ECS)
RUN set -ex; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    MIRROR="${APT_MIRROR:-mirrors.cloud.aliyuncs.com}"; \
    echo "deb http://${MIRROR}/debian bookworm main" > /etc/apt/sources.list; \
    echo "deb http://${MIRROR}/debian bookworm-updates main" >> /etc/apt/sources.list; \
    echo "deb http://${MIRROR}/debian-security bookworm-security main" >> /etc/apt/sources.list; \
    cat /etc/apt/sources.list; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        curl build-essential gnupg ca-certificates xz-utils \
    || { \
      echo "==> Primary mirror failed, trying mirrors.ustc.edu.cn"; \
      echo "deb http://mirrors.ustc.edu.cn/debian bookworm main" > /etc/apt/sources.list; \
      echo "deb http://mirrors.ustc.edu.cn/debian bookworm-updates main" >> /etc/apt/sources.list; \
      echo "deb http://mirrors.ustc.edu.cn/debian-security bookworm-security main" >> /etc/apt/sources.list; \
      apt-get clean; rm -rf /var/lib/apt/lists/*; \
      apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential gnupg ca-certificates xz-utils; \
    }

# Install Node.js from npmmirror CDN (NodeSource mirror is broken in China)
RUN ARCH="$(dpkg --print-architecture)" \
    && if [ "$ARCH" = "amd64" ]; then ARCH="x64"; elif [ "$ARCH" = "arm64" ]; then ARCH="arm64"; fi \
    && curl -fsSL "https://cdn.npmmirror.com/binaries/node/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" \
       -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && node --version && npm --version

# Install uv (source image overridable via UV_IMAGE build arg)
COPY --from=uv-source /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency manifests first (changes less often → better layer caching)
COPY backend/pyproject.toml backend/uv.lock ./backend/
COPY backend/packages/harness/pyproject.toml ./backend/packages/harness/
COPY backend/packages/harness/deerflow/__init__.py ./backend/packages/harness/deerflow/

# Install dependencies with cache mount (layer is cached when manifests are unchanged)
RUN --mount=type=cache,target=/root/.cache/uv \
    sh -c "cd backend && UV_INDEX_URL=${UV_INDEX_URL:-http://mirrors.cloud.aliyuncs.com/pypi/simple} UV_HTTP_TIMEOUT=300 uv sync ${UV_EXTRAS:+--extra $UV_EXTRAS}"

# Copy remaining backend source code
COPY backend ./backend

# ── Stage 2: Dev ──────────────────────────────────────────────────────────────
# Retains compiler toolchain from builder so startup-time `uv sync` can build
# source distributions in development containers.
FROM builder AS dev

# Install Docker CLI (for DooD: allows starting sandbox containers via host Docker socket)
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

EXPOSE 8001 2024

CMD ["sh", "-c", "cd backend && PYTHONPATH=. uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001"]

# ── Stage 3: Runtime ──────────────────────────────────────────────────────────
# Clean image without build-essential — reduces size (~200 MB) and attack surface.
FROM python:3.12-slim-bookworm

# Copy Node.js runtime from builder (provides npx for MCP servers)
COPY --from=builder /usr/local/bin/node /usr/local/bin/node
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Install Docker CLI (for DooD: allows starting sandbox containers via host Docker socket)
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Install uv (source image overridable via UV_IMAGE build arg)
COPY --from=uv-source /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy backend with pre-built virtualenv from builder
COPY --from=builder /app/backend ./backend
COPY tools ./tools

# Expose ports (gateway: 8001, langgraph: 2024)
EXPOSE 8001 2024

# Default command (can be overridden in docker-compose)
CMD ["sh", "-c", "cd backend && PYTHONPATH=. uv run --no-sync uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001"]
