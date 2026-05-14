#!/usr/bin/env bash
set -e

REPO_ROOT="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
cd "$REPO_ROOT"

echo "Cleaning up..."
rm -rf backend/.deer-flow 2>/dev/null || true
rm -rf backend/.langgraph_api 2>/dev/null || true
rm -f logs/*.log 2>/dev/null || true
echo "[OK] Cleanup complete"
