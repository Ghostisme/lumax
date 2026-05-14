#!/usr/bin/env bash
#
# jenkins-deploy.sh - Jenkins CI/CD 部署脚本（在目标服务器上执行）
#
# 用法:
#   jenkins-deploy.sh deploy              — 智能构建并启动（仅依赖变化时重建镜像）
#   jenkins-deploy.sh deploy --force      — 强制全量重建所有镜像
#   jenkins-deploy.sh restart             — 重启已有容器（不重新构建）
#   jenkins-deploy.sh stop                — 停止并移除容器
#   jenkins-deploy.sh health              — 健康检查
#

set -e

CMD="${1:-deploy}"
FORCE_BUILD="${2:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 支持通过 PORT 环境变量覆盖默认端口
export PORT="${PORT:-2026}"

DOCKER_DIR="$REPO_ROOT/docker"
COMPOSE_CMD=(docker compose -p deer-flow -f "$DOCKER_DIR/docker-compose.yaml")
CHECKSUM_DIR="$REPO_ROOT/backend/.deer-flow/.deploy-checksums"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 初始化环境变量 ────────────────────────────────────────────────────────

init_env() {
    export DEER_FLOW_HOME="${DEER_FLOW_HOME:-$REPO_ROOT/backend/.deer-flow}"
    export DEER_FLOW_REPO_ROOT="$REPO_ROOT"
    export DEER_FLOW_DOCKER_SOCKET="${DEER_FLOW_DOCKER_SOCKET:-/var/run/docker.sock}"

    mkdir -p "$DEER_FLOW_HOME" "$CHECKSUM_DIR"

    # config.yaml
    if [ -z "$DEER_FLOW_CONFIG_PATH" ]; then
        export DEER_FLOW_CONFIG_PATH="$REPO_ROOT/config.yaml"
    fi
    if [ ! -f "$DEER_FLOW_CONFIG_PATH" ]; then
        if [ -f "$REPO_ROOT/config.example.yaml" ]; then
            cp "$REPO_ROOT/config.example.yaml" "$DEER_FLOW_CONFIG_PATH"
            log_warn "config.yaml 不存在，已从 config.example.yaml 创建，请检查配置是否正确"
        else
            log_error "config.yaml 未找到，且无模板文件"
            exit 1
        fi
    fi
    log_ok "config.yaml: $DEER_FLOW_CONFIG_PATH"

    # extensions_config.json
    if [ -z "$DEER_FLOW_EXTENSIONS_CONFIG_PATH" ]; then
        export DEER_FLOW_EXTENSIONS_CONFIG_PATH="$REPO_ROOT/extensions_config.json"
    fi
    if [ ! -f "$DEER_FLOW_EXTENSIONS_CONFIG_PATH" ]; then
        echo '{"mcpServers":{},"skills":{}}' > "$DEER_FLOW_EXTENSIONS_CONFIG_PATH"
        log_warn "extensions_config.json 不存在，已创建空配置"
    fi

    # frontend/.env
    if [ ! -f "$REPO_ROOT/frontend/.env" ]; then
        if [ -f "$REPO_ROOT/frontend/.env.example" ]; then
            cp "$REPO_ROOT/frontend/.env.example" "$REPO_ROOT/frontend/.env"
            log_warn "frontend/.env 不存在，已从 .env.example 创建"
        else
            touch "$REPO_ROOT/frontend/.env"
            log_warn "frontend/.env 不存在，已创建空文件"
        fi
    fi

    # BETTER_AUTH_SECRET
    local secret_file="$DEER_FLOW_HOME/.better-auth-secret"
    if [ -z "$BETTER_AUTH_SECRET" ]; then
        if [ -f "$secret_file" ]; then
            export BETTER_AUTH_SECRET
            BETTER_AUTH_SECRET="$(cat "$secret_file")"
        else
            export BETTER_AUTH_SECRET
            BETTER_AUTH_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || openssl rand -hex 32)"
            echo "$BETTER_AUTH_SECRET" > "$secret_file"
            chmod 600 "$secret_file"
            log_ok "BETTER_AUTH_SECRET 已生成"
        fi
    fi

    # HOME (docker-compose volume mounts need it)
    export HOME="${HOME:-/root}"
    mkdir -p "$HOME/.claude" "$HOME/.codex"

    # skills directory (mounted by gateway container)
    mkdir -p "$REPO_ROOT/skills"
}

# ── 依赖变化检测 ─────────────────────────────────────────────────────────
#
# 通过对依赖清单文件计算 sha256 来判断依赖是否发生变化。
# 如果 checksum 与上次部署相同，则跳过该服务的镜像构建。
#
# 监控文件:
#   backend  → pyproject.toml, uv.lock, packages/harness/pyproject.toml, Dockerfile
#   frontend → package.json, pnpm-lock.yaml, Dockerfile

compute_checksum() {
    local files=("$@")
    local combined=""
    for f in "${files[@]}"; do
        if [ -f "$f" ]; then
            combined+="$(sha256sum "$f")"
        fi
    done
    echo -n "$combined" | sha256sum | awk '{print $1}'
}

BACKEND_DEP_FILES=(
    "$REPO_ROOT/backend/pyproject.toml"
    "$REPO_ROOT/backend/uv.lock"
    "$REPO_ROOT/backend/packages/harness/pyproject.toml"
    "$REPO_ROOT/backend/Dockerfile"
)

FRONTEND_DEP_FILES=(
    "$REPO_ROOT/frontend/package.json"
    "$REPO_ROOT/frontend/pnpm-lock.yaml"
    "$REPO_ROOT/frontend/Dockerfile"
)

INFRA_DEP_FILES=(
    "$REPO_ROOT/docker/docker-compose.yaml"
    "$REPO_ROOT/docker/nginx/nginx.conf"
)

check_deps_changed() {
    local service="$1"
    local checksum_file="$CHECKSUM_DIR/${service}.sha256"
    local current_checksum=""

    case "$service" in
        gateway)
            current_checksum="$(compute_checksum "${BACKEND_DEP_FILES[@]}")"
            ;;
        frontend)
            current_checksum="$(compute_checksum "${FRONTEND_DEP_FILES[@]}")"
            ;;
        nginx)
            current_checksum="$(compute_checksum "${INFRA_DEP_FILES[@]}")"
            ;;
        *)
            return 0
            ;;
    esac

    if [ -f "$checksum_file" ]; then
        local stored_checksum
        stored_checksum="$(cat "$checksum_file")"
        if [ "$current_checksum" = "$stored_checksum" ]; then
            return 1
        fi
    fi

    return 0
}

save_checksum() {
    local service="$1"
    local checksum_file="$CHECKSUM_DIR/${service}.sha256"
    local current_checksum=""

    case "$service" in
        gateway)
            current_checksum="$(compute_checksum "${BACKEND_DEP_FILES[@]}")"
            ;;
        frontend)
            current_checksum="$(compute_checksum "${FRONTEND_DEP_FILES[@]}")"
            ;;
        nginx)
            current_checksum="$(compute_checksum "${INFRA_DEP_FILES[@]}")"
            ;;
    esac

    echo "$current_checksum" > "$checksum_file"
}

# ── 沙箱模式检测 ─────────────────────────────────────────────────────────

detect_sandbox_mode() {
    local sandbox_use=""
    local provisioner_url=""

    [ -f "$DEER_FLOW_CONFIG_PATH" ] || { echo "local"; return; }

    sandbox_use=$(awk '
        /^[[:space:]]*sandbox:[[:space:]]*$/ { in_sandbox=1; next }
        in_sandbox && /^[^[:space:]#]/ { in_sandbox=0 }
        in_sandbox && /^[[:space:]]*use:[[:space:]]*/ {
            line=$0; sub(/^[[:space:]]*use:[[:space:]]*/, "", line); print line; exit
        }
    ' "$DEER_FLOW_CONFIG_PATH")

    provisioner_url=$(awk '
        /^[[:space:]]*sandbox:[[:space:]]*$/ { in_sandbox=1; next }
        in_sandbox && /^[^[:space:]#]/ { in_sandbox=0 }
        in_sandbox && /^[[:space:]]*provisioner_url:[[:space:]]*/ {
            line=$0; sub(/^[[:space:]]*provisioner_url:[[:space:]]*/, "", line); print line; exit
        }
    ' "$DEER_FLOW_CONFIG_PATH")

    if [[ "$sandbox_use" == *"deerflow.community.aio_sandbox:AioSandboxProvider"* ]]; then
        if [ -n "$provisioner_url" ]; then
            echo "provisioner"
        else
            echo "aio"
        fi
    else
        echo "local"
    fi
}

# ── 构建服务列表 ─────────────────────────────────────────────────────────

get_services() {
    local sandbox_mode
    sandbox_mode="$(detect_sandbox_mode)"
    log_info "沙箱模式: $sandbox_mode" >&2

    local services="frontend gateway nginx"
    if [ "$sandbox_mode" = "provisioner" ]; then
        services="$services provisioner"
    fi
    echo "$services"
}

# ── deploy: 智能构建并启动 ───────────────────────────────────────────────

do_deploy() {
    log_info "=========================================="
    log_info "  DeerFlow Jenkins 部署 - 智能构建"
    log_info "=========================================="

    init_env

    local services
    services="$(get_services)"

    local build_services=""
    local skip_services=""
    local is_force=false

    if [ "$FORCE_BUILD" = "--force" ]; then
        is_force=true
        log_warn "强制构建模式：跳过依赖检测，全量重建所有镜像"
    fi

    # 逐服务检测依赖变化
    for svc in $services; do
        if [ "$svc" = "nginx" ]; then
            # nginx 使用上游镜像，无需 build，只检测配置变化决定是否重启
            continue
        fi

        if $is_force; then
            build_services="$build_services $svc"
            continue
        fi

        if check_deps_changed "$svc"; then
            build_services="$build_services $svc"
        else
            skip_services="$skip_services $svc"
        fi
    done

    # 打印检测结果
    echo ""
    log_info "┌─────────────────────────────────────────┐"
    log_info "│         依赖变化检测结果                 │"
    log_info "├─────────────────────────────────────────┤"

    for svc in $services; do
        if [ "$svc" = "nginx" ]; then
            log_info "│  nginx     : 使用上游镜像，无需构建     │"
        elif echo "$build_services" | grep -qwF "$svc"; then
            case "$svc" in
                gateway)
                    log_warn "│  gateway   : 依赖已变更 → 重新构建镜像  │"
                    log_info "│    监控: pyproject.toml, uv.lock         │"
                    ;;
                frontend)
                    log_warn "│  frontend  : 依赖已变更 → 重新构建镜像  │"
                    log_info "│    监控: package.json, pnpm-lock.yaml    │"
                    ;;
                *)
                    log_warn "│  $svc : 需要构建                        │"
                    ;;
            esac
        else
            case "$svc" in
                gateway)
                    log_ok "│  gateway   : 依赖未变更 → 跳过构建      │"
                    ;;
                frontend)
                    log_ok "│  frontend  : 依赖未变更 → 跳过构建      │"
                    ;;
            esac
        fi
    done
    log_info "└─────────────────────────────────────────┘"
    echo ""

    # 构建前清理悬空镜像和构建缓存，防止磁盘空间不足
    if [ -n "$build_services" ]; then
        log_info "清理 Docker 悬空镜像和构建缓存..."
        docker image prune -f 2>/dev/null || true
        docker builder prune -f --filter "until=72h" 2>/dev/null || true
    fi

    # 构建发生变化的服务
    if [ -n "$build_services" ]; then
        log_info "正在构建镜像:$build_services ..."
        # shellcheck disable=SC2086
        "${COMPOSE_CMD[@]}" build $build_services
    else
        log_ok "所有服务依赖均未变化，跳过镜像构建"
    fi

    # 启动所有服务（包括跳过构建的，用现有镜像启动）
    log_info "启动所有服务: $services"
    # shellcheck disable=SC2086
    "${COMPOSE_CMD[@]}" up -d --remove-orphans $services

    # 构建成功后保存 checksums
    for svc in $services; do
        save_checksum "$svc"
    done

    echo ""
    log_ok "=========================================="
    log_ok "  DeerFlow 部署完成!"
    log_ok "=========================================="
    log_ok "  应用地址: http://localhost:${PORT:-2026}"
    log_ok "  API 网关: http://localhost:${PORT:-2026}/api/*"

    if [ -n "$build_services" ]; then
        log_info "  已重建:$build_services"
    fi
    if [ -n "$skip_services" ]; then
        log_info "  已跳过:$skip_services (依赖无变化)"
    fi
}

# ── restart: 重启容器 ────────────────────────────────────────────────────

do_restart() {
    log_info "重启 DeerFlow 服务..."

    init_env

    local services
    services="$(get_services)"

    # shellcheck disable=SC2086
    "${COMPOSE_CMD[@]}" up -d --remove-orphans $services

    log_ok "DeerFlow 服务已重启"
}

# ── stop: 停止服务 ───────────────────────────────────────────────────────

do_stop() {
    log_info "停止 DeerFlow 服务..."

    init_env

    "${COMPOSE_CMD[@]}" down

    log_ok "DeerFlow 服务已停止"
}

# ── health: 健康检查 ─────────────────────────────────────────────────────

do_health() {
    log_info "执行健康检查..."

    local max_retries=60
    local retry_interval=10
    local url="http://localhost:${PORT:-2026}/health"

    for i in $(seq 1 $max_retries); do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_ok "健康检查通过 (尝试 $i/$max_retries)"
            log_ok "服务运行正常: http://localhost:${PORT:-2026}"

            log_info "容器状态:"
            "${COMPOSE_CMD[@]}" ps 2>/dev/null || docker ps --filter "label=com.docker.compose.project=deer-flow" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

            return 0
        fi
        log_warn "等待服务启动... ($i/$max_retries)"
        sleep "$retry_interval"
    done

    log_error "健康检查失败（超时 $((max_retries * retry_interval)) 秒）"
    log_error "容器日志:"
    "${COMPOSE_CMD[@]}" logs --tail=50 2>/dev/null || true
    exit 1
}

# ── 主入口 ────────────────────────────────────────────────────────────────

case "$CMD" in
    deploy)
        do_deploy
        ;;
    restart)
        do_restart
        ;;
    stop)
        do_stop
        ;;
    health)
        init_env
        do_health
        ;;
    *)
        echo "用法: $0 {deploy|restart|stop|health} [--force]"
        exit 1
        ;;
esac
