#!/usr/bin/env bash
# DeerFlow Hot-Reload 部署辅助脚本
# 使用方法:
#   ./scripts/deploy-hotreload.sh up        # 启动服务
#   ./scripts/deploy-hotreload.sh build     # 重新构建镜像
#   ./scripts/deploy-hotreload.sh restart   # 重启服务（代码更新后）
#   ./scripts/deploy-hotreload.sh down      # 停止并移除容器
#   ./scripts/deploy-hotreload.sh logs      # 查看日志
#   ./scripts/deploy-hotreload.sh status    # 查看服务状态

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/docker"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose-hotreload.yaml"
MIRRORS_FILE="$COMPOSE_DIR/.env.mirrors"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 检查必要文件
check_prerequisites() {
  local missing=0

  if [ ! -f "$PROJECT_ROOT/config.yaml" ]; then
    warn "config.yaml 不存在，从示例创建..."
    cp "$PROJECT_ROOT/config.example.yaml" "$PROJECT_ROOT/config.yaml"
  fi

  if [ ! -f "$PROJECT_ROOT/extensions_config.json" ]; then
    warn "extensions_config.json 不存在，从示例创建..."
    cp "$PROJECT_ROOT/extensions_config.example.json" "$PROJECT_ROOT/extensions_config.json"
  fi

  if [ ! -f "$PROJECT_ROOT/frontend/.env" ]; then
    warn "frontend/.env 不存在，从示例创建..."
    cp "$PROJECT_ROOT/frontend/.env.example" "$PROJECT_ROOT/frontend/.env"
  fi

  mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/backend/.deer-flow"
}

# 设置镜像源
setup_env() {
  if [ -f "$MIRRORS_FILE" ]; then
    export $(grep -v '^#' "$MIRRORS_FILE" | grep '=' | xargs) 2>/dev/null || true
    info "已加载镜像源配置: $MIRRORS_FILE"
  fi
}

# Docker compose 命令
compose() {
  docker compose -f "$COMPOSE_FILE" --env-file "$PROJECT_ROOT/.env" "$@"
}

case "${1:-help}" in
  up)
    check_prerequisites
    setup_env
    info "启动 DeerFlow (hot-reload 模式)..."
    compose up -d --build
    info "服务已启动，访问: http://localhost:${PORT:-2026}"
    ;;

  build)
    check_prerequisites
    setup_env
    info "重新构建镜像..."
    compose build --no-cache
    info "构建完成"
    ;;

  restart)
    info "重启服务..."
    compose restart
    info "服务已重启"
    ;;

  down)
    info "停止并移除容器..."
    compose down
    info "服务已停止"
    ;;

  logs)
    compose logs -f "${2:-}"
    ;;

  status)
    compose ps
    ;;

  help|*)
    echo "DeerFlow Hot-Reload 部署辅助脚本"
    echo ""
    echo "用法: $0 {up|build|restart|down|logs|status|help}"
    echo ""
    echo "命令:"
    echo "  up        启动服务（首次运行或镜像更新）"
    echo "  build     重新构建镜像（不使用缓存）"
    echo "  restart   重启服务（代码更新后使用）"
    echo "  down      停止并移除容器"
    echo "  logs      查看日志 [service_name]"
    echo "  status    查看服务状态"
    echo ""
    echo "镜像源配置: $MIRRORS_FILE"
    ;;
esac
