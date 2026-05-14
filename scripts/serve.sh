#!/usr/bin/env bash
#
# serve.sh — Unified DeerFlow service launcher
#
# Usage:
#   ./scripts/serve.sh [--dev|--prod] [--daemon] [--fe-only] [--stop|--restart]
#
# Modes:
#   --dev       Development mode with hot-reload (default)
#   --prod      Production mode, pre-built frontend, no hot-reload
#   --daemon    Run all services in background (nohup), exit after startup
#   --fe-only   Start only Nginx + Frontend (assumes Gateway/LangGraph
#               are already running externally, e.g. inside an IDE debugger).
#               In stop/restart actions, only Nginx + Frontend are touched —
#               Gateway (8001) and LangGraph (2024) are NOT killed.
#
# Actions:
#   --skip-install  Skip dependency installation (faster restart)
#   --stop      Stop running services and exit
#   --restart   Stop services, then start with the given mode flags
#
# Examples:
#   ./scripts/serve.sh --dev                 # Full stack dev, hot reload
#   ./scripts/serve.sh --prod                # Full stack prod
#   ./scripts/serve.sh --dev --daemon        # Full stack dev, background
#   ./scripts/serve.sh --dev --fe-only       # Nginx + Frontend only (FE dev)
#   ./scripts/serve.sh --fe-only --stop      # Stop only Nginx + Frontend
#   ./scripts/serve.sh --stop                # Stop all services
#   ./scripts/serve.sh --restart --dev       # Restart dev services
#
# Must be run from the repo root directory.

set -e

REPO_ROOT="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
cd "$REPO_ROOT"
BACKEND_PYTHONPATH="$(cd "$REPO_ROOT/backend" && (pwd -W 2>/dev/null || pwd -P))"

# ── Windows: add nginx to PATH if not found ──────────────────────────────────
if ! command -v nginx >/dev/null 2>&1; then
    NGINX_WIN="/c/Users/EDY/tools/deer-prereqs/nginx/nginx-1.29.8"
    [ -f "$NGINX_WIN/nginx.exe" ] && export PATH="$NGINX_WIN:$PATH"
fi

# ── Load .env ────────────────────────────────────────────────────────────────

if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    source "$REPO_ROOT/.env"
    set +a
fi

# ── Argument parsing ─────────────────────────────────────────────────────────

DEV_MODE=true
DAEMON_MODE=false
SKIP_INSTALL=false
FRONTEND_ONLY=false
ACTION="start"   # start | stop | restart

for arg in "$@"; do
    case "$arg" in
        --dev)     DEV_MODE=true ;;
        --prod)    DEV_MODE=false ;;
        --daemon)  DAEMON_MODE=true ;;
        --skip-install) SKIP_INSTALL=true ;;
        --fe-only) FRONTEND_ONLY=true ;;
        --stop)    ACTION="stop" ;;
        --restart) ACTION="restart" ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--dev|--prod] [--daemon] [--fe-only] [--skip-install] [--stop|--restart]"
            exit 1
            ;;
    esac
done

# ── Stop helper ──────────────────────────────────────────────────────────────

_kill_port() {
    local port=$1
    local pid
    pid=$(lsof -ti :"$port" 2>/dev/null) || true
    if [ -n "$pid" ]; then
        kill -9 $pid 2>/dev/null || true
    fi
}

stop_all() {
    echo "Stopping all services..."
    pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
    sleep 1
    pkill -9 nginx 2>/dev/null || true
    # Force-kill any survivors still holding the service ports
    _kill_port 8001
    _kill_port 3000
    ./scripts/cleanup-containers.sh deer-flow-sandbox 2>/dev/null || true
    echo "✓ All services stopped"
}

# Stop ONLY Nginx + Frontend.
# Used by --fe-only mode so Gateway (8001) and LangGraph (2024) keep running.
stop_frontend_stack() {
    echo "Stopping Nginx + Frontend (Gateway/LangGraph left untouched)..."
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
    sleep 1
    pkill -9 nginx 2>/dev/null || true
    _kill_port 3000
    _kill_port 2026
    echo "✓ Nginx + Frontend stopped"
}

# ── Action routing ───────────────────────────────────────────────────────────

if [ "$ACTION" = "stop" ]; then
    if $FRONTEND_ONLY; then
        stop_frontend_stack
    else
        stop_all
    fi
    exit 0
fi

ALREADY_STOPPED=false
if [ "$ACTION" = "restart" ]; then
    if $FRONTEND_ONLY; then
        stop_frontend_stack
    else
        stop_all
    fi
    sleep 1
    ALREADY_STOPPED=true
fi

# Mode label for banner
if $DEV_MODE; then
    MODE_LABEL="DEV (Gateway runtime, hot-reload enabled)"
else
    MODE_LABEL="PROD (Gateway runtime, optimized)"
fi

if $FRONTEND_ONLY; then
    MODE_LABEL="$MODE_LABEL [fe-only]"
fi

if $DAEMON_MODE; then
    MODE_LABEL="$MODE_LABEL [daemon]"
fi

# Resolve pnpm command for Git Bash on Windows:
# prefer direct pnpm; fall back to Corepack-managed pnpm.
if command -v pnpm >/dev/null 2>&1; then
    PNPM_CMD="pnpm"
elif command -v corepack >/dev/null 2>&1; then
    PNPM_CMD="corepack pnpm"
else
    echo "pnpm not found in this shell. Install pnpm or enable Corepack (corepack enable)."
    exit 1
fi

# Frontend command
if $DEV_MODE; then
    FRONTEND_CMD="$PNPM_CMD run dev"
else
    FRONTEND_CMD="$PNPM_CMD run preview"
fi

# Extra flags for uvicorn
if $DEV_MODE && ! $DAEMON_MODE; then
    GATEWAY_EXTRA_FLAGS="--reload --reload-include='*.yaml' --reload-include='.env' --reload-exclude='*.pyc' --reload-exclude='__pycache__' --reload-exclude='sandbox/' --reload-exclude='.deer-flow/'"
else
    GATEWAY_EXTRA_FLAGS=""
fi

# ── Stop existing services (skip if restart already did it) ──────────────────

if ! $ALREADY_STOPPED; then
    if $FRONTEND_ONLY; then
        stop_frontend_stack
    else
        stop_all
    fi
    sleep 1
fi

# ── Config check ─────────────────────────────────────────────────────────────

if ! { \
        [ -n "$DEER_FLOW_CONFIG_PATH" ] && [ -f "$DEER_FLOW_CONFIG_PATH" ] || \
        [ -f backend/config.yaml ] || \
        [ -f config.yaml ]; \
    }; then
    echo "✗ No DeerFlow config file found."
    echo "  Run 'make setup' (recommended) or 'make config' to generate config.yaml."
    exit 1
fi

"$REPO_ROOT/scripts/config-upgrade.sh"

# ── Install dependencies ────────────────────────────────────────────────────

if ! $SKIP_INSTALL; then
    echo "Syncing dependencies..."
    if $FRONTEND_ONLY; then
        (cd frontend && $PNPM_CMD install --silent) || { echo "✗ Frontend dependency install failed"; exit 1; }
    else
        (cd backend && uv sync --quiet --extra postgres) || { echo "✗ Backend dependency install failed"; exit 1; }
        (cd frontend && $PNPM_CMD install --silent) || { echo "✗ Frontend dependency install failed"; exit 1; }
    fi
    echo "✓ Dependencies synced"
else
    echo "⏩ Skipping dependency install (--skip-install)"
fi

# ── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  Starting DeerFlow"
echo "=========================================="
echo ""
echo "  Mode: $MODE_LABEL"
echo ""
echo "  Services:"
if $FRONTEND_ONLY; then
    echo "    Gateway     → localhost:8001  (assumed already running, NOT started)"
    echo "    LangGraph   → localhost:2024  (assumed already running, NOT started)"
else
    echo "    Gateway     → localhost:8001  (REST API + agent runtime)"
fi
echo "    Frontend    → localhost:3000  (Next.js)"
echo "    Nginx       → localhost:2026  (reverse proxy)"
echo ""

# ── Cleanup handler ──────────────────────────────────────────────────────────

cleanup() {
    trap - INT TERM
    echo ""
    if $FRONTEND_ONLY; then
        stop_frontend_stack
    else
        stop_all
    fi
    exit 0
}

trap cleanup INT TERM

# ── Helper: start a service ──────────────────────────────────────────────────

# run_service NAME COMMAND PORT TIMEOUT
# In daemon mode, wraps with nohup. Waits for port to be ready.
run_service() {
    local name="$1" cmd="$2" port="$3" timeout="$4"

    echo "Starting $name..."
    if $DAEMON_MODE; then
        nohup sh -c "$cmd" > /dev/null 2>&1 &
    else
        sh -c "$cmd" &
    fi

    ./scripts/wait-for-port.sh "$port" "$timeout" "$name" || {
        local logfile="logs/$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-').log"
        echo "✗ $name failed to start."
        [ -f "$logfile" ] && tail -20 "$logfile"
        cleanup
    }
    echo "✓ $name started on localhost:$port"
}

# ── Start services ───────────────────────────────────────────────────────────

mkdir -p logs
mkdir -p temp/client_body_temp temp/proxy_temp temp/fastcgi_temp temp/uwsgi_temp temp/scgi_temp

# 1. LangGraph + Gateway — only when NOT in fe-only mode.
# In --fe-only we assume both are already running externally
# (e.g. started via VSCode debugger or another terminal).
if ! $FRONTEND_ONLY; then
    # 1a. LangGraph (skip in gateway mode)
    if ! ${GATEWAY_MODE:-false}; then
        CONFIG_LOG_LEVEL=$(grep -m1 '^log_level:' config.yaml 2>/dev/null | awk '{print $2}' | tr -d ' ')
        LANGGRAPH_LOG_LEVEL="${LANGGRAPH_LOG_LEVEL:-${CONFIG_LOG_LEVEL:-info}}"
        LANGGRAPH_JOBS_PER_WORKER="${LANGGRAPH_JOBS_PER_WORKER:-10}"
        LANGGRAPH_ALLOW_BLOCKING="${LANGGRAPH_ALLOW_BLOCKING:-0}"
        LANGGRAPH_ALLOW_BLOCKING_FLAG=""
        if [ "$LANGGRAPH_ALLOW_BLOCKING" = "1" ]; then
            LANGGRAPH_ALLOW_BLOCKING_FLAG="--allow-blocking"
        fi
        run_service "LangGraph" \
            "cd backend && PYTHONPATH=\"$BACKEND_PYTHONPATH\" NO_COLOR=1 CLICOLOR=0 CLICOLOR_FORCE=0 PY_COLORS=0 TERM=dumb uv run python -m deerflow.runtime.cli langgraph dev --no-browser $LANGGRAPH_ALLOW_BLOCKING_FLAG --n-jobs-per-worker $LANGGRAPH_JOBS_PER_WORKER --server-log-level $LANGGRAPH_LOG_LEVEL $LANGGRAPH_EXTRA_FLAGS 2>&1 | LC_ALL=C LC_CTYPE=C LANG=C perl -pe 's/\e\[[0-9;]*[[:alpha:]]//g' > ../logs/langgraph.log" \
            2024 120
    else
        echo "⏩ Skipping LangGraph (Gateway mode — runtime embedded in Gateway)"
    fi

    # 1b. Gateway API
    run_service "Gateway" \
        "cd backend && PYTHONPATH=\"$BACKEND_PYTHONPATH\" uv run --extra postgres python -m deerflow.runtime.cli uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001 $GATEWAY_EXTRA_FLAGS > ../logs/gateway.log 2>&1" \
        8001 60
else
    echo "⏩ Skipping LangGraph + Gateway (--fe-only). Make sure both are already running on :2024 / :8001."
fi

# 2. Frontend
run_service "Frontend" \
    "cd frontend && $FRONTEND_CMD > ../logs/frontend.log 2>&1" \
    3000 120

# 3. Nginx
run_service "Nginx" \
    "nginx -g 'daemon off;' -c '$REPO_ROOT/docker/nginx/nginx.local.conf' -p '$REPO_ROOT' > logs/nginx.log 2>&1" \
    2026 10

# ── Ready ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  ✓ DeerFlow is running!  [$MODE_LABEL]"
echo "=========================================="
echo ""
echo "  🌐 http://localhost:2026"
echo ""
echo "  Routing: Frontend → Nginx → Gateway"
echo "  API:     /api/langgraph/*  →  Gateway agent runtime"
echo "           /api/*              →  Gateway REST API (8001)"
echo ""
if $FRONTEND_ONLY; then
    echo "  📋 Logs: logs/{frontend,nginx}.log"
else
    echo "  📋 Logs: logs/{gateway,frontend,nginx}.log"
fi
echo ""

if $DAEMON_MODE; then
    if $FRONTEND_ONLY; then
        echo "  🛑 Stop: make stop-fe"
    else
        echo "  🛑 Stop: make stop"
    fi
    # Detach — trap is no longer needed
    trap - INT TERM
else
    if $FRONTEND_ONLY; then
        echo "  Press Ctrl+C to stop Nginx + Frontend (Gateway/LangGraph stay up)"
    else
        echo "  Press Ctrl+C to stop all services"
    fi
    wait
fi
