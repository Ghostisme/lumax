"""Windows-native DeerFlow service launcher.

The Unix launcher is scripts/serve.sh. This file intentionally mirrors its
user-facing behavior for Windows environments where Git Bash cannot start.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
UV_CACHE_DIR = ROOT / "backend" / ".uv-cache-local"
UV_TOOL_DIR = ROOT / "backend" / ".uv-tools-local"
TEMP_DIRS = [
    ROOT / "temp" / "client_body_temp",
    ROOT / "temp" / "proxy_temp",
    ROOT / "temp" / "fastcgi_temp",
    ROOT / "temp" / "uwsgi_temp",
    ROOT / "temp" / "scgi_temp",
]
SERVICE_PORTS = (8001, 8002, 3000, 2026)


def _load_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def _find_executable(name: str) -> str:
    if name == "nginx" and os.name == "nt":
        bundled = Path.home() / "tools" / "deer-prereqs" / "nginx" / "nginx-1.29.8" / "nginx.exe"
        if bundled.is_file():
            return str(bundled)

    exe = shutil.which(name)
    if exe:
        return exe

    if name == "nginx":
        bundled = Path.home() / "tools" / "deer-prereqs" / "nginx" / "nginx-1.29.8" / "nginx.exe"
        if bundled.is_file():
            return str(bundled)

    raise SystemExit(f"{name} not found in PATH.")


def _ensure_dirs() -> None:
    LOGS.mkdir(exist_ok=True)
    for temp_dir in TEMP_DIRS:
        temp_dir.mkdir(parents=True, exist_ok=True)
    UV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    UV_TOOL_DIR.mkdir(parents=True, exist_ok=True)


def _apply_local_uv_env(env: dict[str, str]) -> dict[str, str]:
    """Force uv to use workspace-local cache/tool dirs to avoid global ACL issues."""
    merged = dict(env)
    merged["UV_CACHE_DIR"] = str(UV_CACHE_DIR)
    merged["UV_TOOL_DIR"] = str(UV_TOOL_DIR)
    return merged


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port: int, timeout: int, name: str) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if _port_is_open(port):
            print("\r" + " " * 60 + "\r", end="", flush=True)
            return True
        elapsed = int(time.monotonic() - start)
        print(f"\r  Waiting for {name} on port {port}... {elapsed}s", end="", flush=True)
        time.sleep(1)
    print()
    print(f"ERROR {name} failed to start on port {port} after {timeout}s")
    return False


def _pids_for_port(port: int) -> set[int]:
    result = subprocess.run(
        ["netstat", "-ano"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        capture_output=True,
        check=False,
    )
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address, state, pid = parts[1], parts[3].upper(), parts[-1]
        if state == "LISTENING" and local_address.endswith(f":{port}") and pid.isdigit():
            pids.add(int(pid))
    return pids


def _kill_port(port: int) -> None:
    for pid in _pids_for_port(port):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def stop_all() -> None:
    print("Stopping all services...")
    nginx = shutil.which("nginx")
    if nginx:
        subprocess.run(
            [
                nginx,
                "-c",
                str(ROOT / "docker" / "nginx" / "nginx.local.conf"),
                "-p",
                str(ROOT),
                "-s",
                "quit",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    time.sleep(1)
    for port in SERVICE_PORTS:
        _kill_port(port)
    print("OK All services stopped")


def _config_exists() -> bool:
    env_path = os.environ.get("DEER_FLOW_CONFIG_PATH")
    return bool(
        (env_path and Path(env_path).is_file())
        or (ROOT / "backend" / "config.yaml").is_file()
        or (ROOT / "config.yaml").is_file()
    )


def _run_checked(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(args, cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _sync_dependencies(pnpm: str, env: dict[str, str]) -> None:
    print("Syncing dependencies...")
    _run_checked(["uv", "sync", "--quiet"], ROOT / "backend", env=env)
    _run_checked([pnpm, "install", "--silent"], ROOT / "frontend", env=env)
    print("OK Dependencies synced")


def _start_process(name: str, args: list[str], cwd: Path, log_file: Path, env: dict[str, str]) -> subprocess.Popen:
    log_handle = log_file.open("ab")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        return subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception:
        log_handle.close()
        raise


def _tail_log(log_file: Path, lines: int = 20) -> None:
    if not log_file.is_file():
        return
    content = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in content[-lines:]:
        print(line)


def _run_service(
    name: str,
    args: list[str],
    cwd: Path,
    port: int,
    timeout: int,
    env: dict[str, str],
    processes: list[subprocess.Popen],
) -> None:
    print(f"Starting {name}...")
    log_file = LOGS / f"{name.lower().replace(' ', '-')}.log"
    process = _start_process(name, args, cwd, log_file, env)
    processes.append(process)

    if not _wait_for_port(port, timeout, name):
        print(f"ERROR {name} failed to start.")
        _tail_log(log_file)
        stop_all()
        raise SystemExit(1)

    print(f"OK {name} started on localhost:{port}")


def _gateway_args(dev_mode: bool, daemon_mode: bool) -> list[str]:
    args = [
        "uv",
        "run",
        "--extra",
        "postgres",
        "--no-sync",
        "python",
        "-m",
        "deerflow.runtime.cli",
        "uvicorn",
        "app.gateway.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8001",
    ]
    if dev_mode and not daemon_mode:
        args.extend(
            [
                "--reload",
                "--reload-include=*.yaml",
                "--reload-include=.env",
                "--reload-exclude=*.pyc",
                "--reload-exclude=__pycache__",
                "--reload-exclude=sandbox/",
                "--reload-exclude=.deer-flow/",
            ]
        )
    return args


def _frontend_args(dev_mode: bool, pnpm: str, env: dict[str, str]) -> list[str]:
    if dev_mode:
        return [pnpm, "run", "dev"]
    return [pnpm, "run", "preview"]


def _nginx_args(nginx: str) -> list[str]:
    return [
        nginx,
        "-g",
        "daemon off;",
        "-c",
        str(ROOT / "docker" / "nginx" / "nginx.local.conf"),
        "-p",
        str(ROOT),
    ]


def _print_banner(mode_label: str) -> None:
    print()
    print("==========================================")
    print("  Starting DeerFlow")
    print("==========================================")
    print()
    print(f"  Mode: {mode_label}")
    print()
    print("  Services:")
    print("    Gateway     -> localhost:8001  (REST API + agent runtime)")
    print("    Frontend    -> localhost:3000  (Next.js)")
    print("    Nginx       -> localhost:2026  (reverse proxy)")
    print()


def _print_ready(mode_label: str, daemon_mode: bool) -> None:
    print()
    print("==========================================")
    print(f"  OK DeerFlow is running!  [{mode_label}]")
    print("==========================================")
    print()
    print("  URL: http://localhost:2026")
    print()
    print("  Routing: Frontend -> Nginx -> Gateway")
    print("  API:     /api/langgraph/*  -> Gateway agent runtime")
    print("           /api/*              -> Gateway REST API (8001)")
    print()
    print("  Logs: logs/{gateway,frontend,nginx}.log")
    print()
    if daemon_mode:
        print("  Stop: make stop")
    else:
        print("  Press Ctrl+C to stop all services")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--prod", action="store_true")
    # Compatibility flag: Windows launcher always runs Gateway runtime.
    parser.add_argument("--gateway", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--restart", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_file()

    if args.stop:
        stop_all()
        return 0

    dev_mode = not args.prod
    mode_label = "DEV (Gateway runtime, hot-reload enabled)" if dev_mode else "PROD (Gateway runtime, optimized)"
    if args.daemon:
        mode_label = f"{mode_label} [daemon]"

    if args.restart:
        stop_all()
        time.sleep(1)
    else:
        stop_all()
        time.sleep(1)

    if not _config_exists():
        print("ERROR No DeerFlow config file found.")
        print("  Run 'make setup' (recommended) or 'make config' to generate config.yaml.")
        return 1

    _run_checked([sys.executable, str(ROOT / "scripts" / "config_upgrade.py")], ROOT)

    pnpm = _find_executable("pnpm")
    nginx = _find_executable("nginx")

    _ensure_dirs()
    _print_banner(mode_label)

    base_env = _apply_local_uv_env(os.environ.copy())
    backend_env = base_env.copy()
    backend_env["PYTHONPATH"] = str(ROOT / "backend")

    frontend_env = base_env.copy()
    nginx_env = base_env.copy()

    if not args.skip_install:
        _sync_dependencies(pnpm, base_env)
    else:
        print("INFO Skipping dependency install (--skip-install)")

    processes: list[subprocess.Popen] = []
    try:
        _run_service(
            "Gateway",
            _gateway_args(dev_mode, args.daemon),
            ROOT / "backend",
            8001,
            60,
            backend_env,
            processes,
        )
        _run_service(
            "Frontend",
            _frontend_args(dev_mode, pnpm, frontend_env),
            ROOT / "frontend",
            3000,
            120,
            frontend_env,
            processes,
        )
        _run_service(
            "Nginx",
            _nginx_args(nginx),
            ROOT,
            2026,
            10,
            nginx_env,
            processes,
        )
        _print_ready(mode_label, args.daemon)

        if args.daemon:
            return 0

        while True:
            exited = [process for process in processes if process.poll() is not None]
            if exited:
                print("A service exited unexpectedly.")
                stop_all()
                return exited[0].returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        stop_all()
        return 0


if __name__ == "__main__":
    if os.name != "nt":
        print("scripts/serve.py is intended for Windows. Use scripts/serve.sh on Unix.")
    raise SystemExit(main())
