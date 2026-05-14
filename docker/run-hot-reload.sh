#!/bin/bash
# DeerFlow Hot Reload Runner
# Usage:
#   ./run-hot-reload.sh start     # Start services
#   ./run-hot-reload.sh stop      # Stop services
#   ./run-hot-reload.sh restart   # Restart (code hot reload)
#   ./run-hot-reload.sh logs      # View logs
#   ./run-hot-reload.sh logs-f    # Follow logs
#   ./run-hot-reload.sh clean     # Clean up containers
#
# Mirror switching:
#   MIRROR=cn ./run-hot-reload.sh start   # Use China mirrors
#   MIRROR=official ./run-hot-reload.sh start  # Use official sources

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-hot-reload.yaml"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MIRROR=${MIRROR:-}

setup_mirrors() {
    case "$MIRROR" in
        cn)
            echo ">>> Using China mirrors..."
            export APT_MIRROR="https://mirrors.aliyun.com/debian"
            export UV_IMAGE="registry.cn-beijing.aliyuncs.com/astral-sh/uv:0.7.20"
            export UV_INDEX_URL="http://mirrors.cloud.aliyuncs.com/pypi/simple"
            export NPM_REGISTRY="https://registry.npmmirror.com"
            ;;
        official)
            echo ">>> Using official sources..."
            unset APT_MIRROR
            export UV_IMAGE="ghcr.io/astral-sh/uv:0.7.20"
            export UV_INDEX_URL="http://mirrors.cloud.aliyuncs.com/pypi/simple"
            unset NPM_REGISTRY
            ;;
        *)
            echo ">>> Using current environment settings..."
            ;;
    esac
}

cd "$PROJECT_DIR"

case "${1:-start}" in
    start)
        setup_mirrors
        docker-compose -f "$COMPOSE_FILE" up -d
        echo ""
        echo ">>> Services started!"
        echo "   Frontend: http://localhost:2026"
        echo "   Frontend Dev: http://localhost:3000"
        echo "   Backend API: http://localhost:8001"
        echo ""
        echo ">>> Restart after code changes: $0 restart"
        ;;
    stop)
        docker-compose -f "$COMPOSE_FILE" down
        echo ">>> Services stopped"
        ;;
    restart)
        docker-compose -f "$COMPOSE_FILE" restart
        echo ">>> Services restarted (code changes applied)"
        ;;
    logs)
        docker-compose -f "$COMPOSE_FILE" logs
        ;;
    logs-f)
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    clean)
        docker-compose -f "$COMPOSE_FILE" down -v
        echo ">>> Containers and volumes cleaned"
        ;;
    build)
        setup_mirrors
        docker-compose -f "$COMPOSE_FILE" build --no-cache
        echo ">>> Images rebuilt"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|logs-f|clean|build}"
        exit 1
        ;;
esac