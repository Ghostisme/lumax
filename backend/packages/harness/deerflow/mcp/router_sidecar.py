"""Windows fallback sidecar launcher for nacos-mcp-router."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROUTER_NAME = "nacos-mcp-router"
_DEFAULT_PORT = int(os.getenv("DEER_FLOW_NACOS_MCP_ROUTER_PORT", "18000"))
_DEFAULT_READY_TIMEOUT_SECONDS = float(os.getenv("DEER_FLOW_NACOS_MCP_ROUTER_READY_TIMEOUT_SECONDS", "12"))
_DEFAULT_STARTUP_TIMEOUT_SECONDS = float(os.getenv("DEER_FLOW_NACOS_MCP_ROUTER_STARTUP_TIMEOUT_SECONDS", "120"))
_LOCK = threading.Lock()
_ROUTER_PROCESS: subprocess.Popen[str] | None = None
_ROUTER_PATCH_MARKER = "# deer-flow patch: initialize MCP session before list/call"
_NACOS_LIST_PATCH_MARKER = "# deer-flow patch: keep search=blur for nacos mcp list"
_NACOS_LIST_FALLBACK_PATCH_MARKER = "# deer-flow patch: fallback to DEER_FLOW_NACOS_MCP_NAMES when list api fails"
_ROUTER_PERF_PATCH_MARKER = "# deer-flow patch: reduce nacos-mcp-router runtime overhead"
_SSL_CERT_FILE_ENV_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")
_SSL_CERT_DIR_ENV_VARS = ("SSL_CERT_DIR",)


def _is_http_endpoint_reachable(url: str, timeout: float = 1.0) -> bool:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(getattr(resp, "status", 0)) < 500
    except urllib.error.HTTPError as exc:
        code = int(getattr(exc, "code", 0))
        return code != 404 and 400 <= code < 500
    except Exception:
        return False


def _wait_router_ready(base_url: str, timeout_seconds: float | None = None) -> str | None:
    timeout = timeout_seconds if timeout_seconds is not None else _DEFAULT_READY_TIMEOUT_SECONDS
    deadline = time.time() + timeout
    while time.time() < deadline:
        for path in ("/mcp", "/sse"):
            url = f"{base_url}{path}"
            if _is_http_endpoint_reachable(url):
                return url
        time.sleep(0.5)
    return None


def _router_http_base_url(port: int | None = None) -> str:
    return f"http://127.0.0.1:{port if port is not None else _DEFAULT_PORT}"


def _discover_local_nacos_mcp_server_names(env: Mapping[str, str]) -> str | None:
    raw_names = str(env.get("DEER_FLOW_NACOS_MCP_NAMES") or "").strip()
    if raw_names:
        return raw_names

    namespace = str(env.get("NACOS_NAMESPACE") or "public").strip() or "public"
    candidate_roots: list[Path] = []

    nacos_home = str(env.get("NACOS_HOME") or "").strip()
    if nacos_home:
        candidate_roots.append(Path(nacos_home) / "data" / "tenant-config-data")

    deer_flow_root = Path(__file__).resolve().parents[5]
    candidate_roots.append(deer_flow_root / "tools" / "nacos-3.2.0" / "data" / "tenant-config-data")
    candidate_roots.append(deer_flow_root.parent / "tools" / "nacos-3.2.0" / "data" / "tenant-config-data")

    discovered: set[str] = set()
    for data_root in candidate_roots:
        version_dir = data_root / namespace / "mcp-server-versions"
        if not version_dir.exists():
            continue

        for version_file in version_dir.glob("*-mcp-versions.json"):
            try:
                payload = json.loads(version_file.read_text(encoding="utf-8"))
            except Exception:
                logger.debug("skip invalid local nacos mcp cache file: %s", version_file, exc_info=True)
                continue

            name = str(payload.get("name") or "").strip()
            if name:
                discovered.add(name)

        if discovered:
            break

    if not discovered:
        return None
    return ",".join(sorted(discovered))


def _patch_router_streamable_transport(runtime_root: Path) -> int:
    """Patch streamable HTTP transport to initialize session before list/call."""
    uv_archive_root = runtime_root / "uv-cache" / "archive-v0"
    if not uv_archive_root.exists():
        return 0

    patched_count = 0
    for transport_file in uv_archive_root.rglob("nacos_mcp_router/streamable_http_transport.py"):
        try:
            content = transport_file.read_text(encoding="utf-8")
        except Exception:
            logger.debug("skip unreadable transport file: %s", transport_file, exc_info=True)
            continue

        if _ROUTER_PATCH_MARKER in content:
            continue

        updated = content.replace(
            "            async with ClientSession(read, write) as session:\n                return await session.call_tool(name=name, arguments=args)",
            "            async with ClientSession(read, write) as session:\n                await session.initialize()\n                "
            + _ROUTER_PATCH_MARKER
            + "\n                return await session.call_tool(name=name, arguments=args)",
        )
        updated = updated.replace(
            "            async with ClientSession(read, write) as session:\n                return await session.list_tools()",
            "            async with ClientSession(read, write) as session:\n                await session.initialize()\n                "
            + _ROUTER_PATCH_MARKER
            + "\n                return await session.list_tools()",
        )

        if updated == content:
            continue

        try:
            transport_file.write_text(updated, encoding="utf-8")
            patched_count += 1
            logger.info("patched streamable transport file: %s", transport_file)
        except Exception:
            logger.warning("failed to patch streamable transport file: %s", transport_file, exc_info=True)

    return patched_count


def _patch_router_nacos_list_api(runtime_root: Path) -> int:
    """Patch list API handling and add name-based fallback when list API is broken."""
    uv_archive_root = runtime_root / "uv-cache" / "archive-v0"
    if not uv_archive_root.exists():
        return 0

    patched_count = 0
    for client_file in uv_archive_root.rglob("nacos_mcp_router/nacos_http_client.py"):
        try:
            content = client_file.read_text(encoding="utf-8")
        except Exception:
            logger.debug("skip unreadable nacos client file: %s", client_file, exc_info=True)
            continue

        has_complete_fallback_patch = (
            _NACOS_LIST_FALLBACK_PATCH_MARKER in content
            and "async def _deer_flow_fallback_by_env_names" in content
            and "params['search'] = \"blur\"" in content
            and "params['content'] = \"blur\"" in content
        )
        if has_complete_fallback_patch:
            continue

        updated = content
        if "import os\n" not in updated:
            updated = updated.replace("import json\n", "import json\nimport os\n")

        # Keep both parameter names: nacos-mcp-router versions use search, while
        # local Nacos 3.x builds may validate content as required.
        updated = updated.replace(
            "        # " + _NACOS_LIST_PATCH_MARKER + "\n        params['content'] = \"blur\"",
            "        # " + _NACOS_LIST_PATCH_MARKER + "\n        params['search'] = \"blur\"\n        params['content'] = \"blur\"",
        )
        updated = updated.replace(
            "        params['content'] = \"blur\"",
            "        params['search'] = \"blur\"\n        params['content'] = \"blur\"",
        )
        if "        params['search'] = \"blur\"" in updated and "        params['content'] = \"blur\"" not in updated:
            updated = updated.replace(
                "        params['search'] = \"blur\"",
                "        params['search'] = \"blur\"\n        params['content'] = \"blur\"",
                1,
            )

        old_failure = (
            "        if not success:\n"
            "            logger.warning(\"failed to get mcp server list response\")\n"
            "            return 0, mcp_servers"
        )
        new_failure = (
            "        if not success:\n"
            "            logger.warning(\"failed to get mcp server list response\")\n"
            "            # "
            + _NACOS_LIST_FALLBACK_PATCH_MARKER
            + "\n"
            "            fallback_total, fallback_servers = await self._deer_flow_fallback_by_env_names()\n"
            "            if fallback_total > 0:\n"
            "                return fallback_total, fallback_servers\n"
            "            return 0, mcp_servers"
        )
        updated = updated.replace(old_failure, new_failure)

        helper_anchor = "\ndef _parse_tool_params(data, mcp_name, tools) -> dict[str, str]:"
        if helper_anchor in updated and "async def _deer_flow_fallback_by_env_names" not in updated:
            helper_block = (
                "\n    async def _deer_flow_fallback_by_env_names(self) -> tuple[int, list[McpServer]]:\n"
                "        # "
                + _NACOS_LIST_FALLBACK_PATCH_MARKER
                + "\n"
                "        raw_names = os.getenv(\"DEER_FLOW_NACOS_MCP_NAMES\", \"\")\n"
                "        names = [name.strip() for name in raw_names.split(\",\") if name.strip()]\n"
                "        if not names:\n"
                "            return 0, []\n"
                "\n"
                "        mcp_servers = list[McpServer]()\n"
                "        for name in names:\n"
                "            try:\n"
                "                server = await self.get_mcp_server(\"\", name)\n"
                "            except Exception as exc:\n"
                "                logger.warning(\"failed to get mcp server in fallback mode, name %s\", name, exc_info=exc)\n"
                "                continue\n"
                "            if getattr(server, \"description\", \"\"):\n"
                "                mcp_servers.append(server)\n"
                "\n"
                "        logger.info(\"fallback loaded mcp server list by DEER_FLOW_NACOS_MCP_NAMES, size: %d\", len(mcp_servers))\n"
                "        return len(mcp_servers), mcp_servers\n"
            )
            updated = updated.replace(helper_anchor, helper_block + helper_anchor)

        if updated == content:
            continue

        try:
            client_file.write_text(updated, encoding="utf-8")
            patched_count += 1
            logger.info("patched nacos list client file: %s", client_file)
        except Exception:
            logger.warning("failed to patch nacos list client file: %s", client_file, exc_info=True)

    return patched_count


def _patch_router_runtime_behavior(runtime_root: Path) -> int:
    """Patch runtime behavior to reduce needless overhead on Windows."""
    uv_archive_root = runtime_root / "uv-cache" / "archive-v0"
    if not uv_archive_root.exists():
        return 0

    patched_count = 0
    for router_file in uv_archive_root.rglob("nacos_mcp_router/router.py"):
        try:
            content = router_file.read_text(encoding="utf-8")
        except Exception:
            logger.debug("skip unreadable router file: %s", router_file, exc_info=True)
            continue

        if _ROUTER_PERF_PATCH_MARKER in content:
            continue

        old_tool_sync = (
            "        if nacos_http_client is not None:\n"
            "            await nacos_http_client.update_mcp_tools(mcp_server_name, tools, mcp_version,\n"
            "                                                     mcp_server.id if mcp_server.id else \"\")"
        )
        new_tool_sync = (
            "        # "
            + _ROUTER_PERF_PATCH_MARKER
            + "\n"
            + "        if auto_register_tools and nacos_http_client is not None:\n"
            "            await nacos_http_client.update_mcp_tools(mcp_server_name, tools, mcp_version,\n"
            "                                                     mcp_server.id if mcp_server.id else \"\")"
        )
        updated = content.replace(old_tool_sync, new_tool_sync)

        old_vector_init = (
            "            chroma_db_service = ChromaDb()\n"
            "            mcp_updater =  McpUpdater.create(nacos_client=nacos_http_client, chroma_db=chroma_db_service, "
            "update_interval=update_interval, enable_vector_db=True, mode=mode, proxy_mcp_name=proxied_mcp_name, "
            "enable_auto_refresh=True)"
        )
        new_vector_init = (
            "            chroma_db_service = None\n"
            "            # "
            + _ROUTER_PERF_PATCH_MARKER
            + " (disable vector db path to avoid extra startup cost)\n"
            "            mcp_updater =  McpUpdater.create(nacos_client=nacos_http_client, chroma_db=chroma_db_service, "
            "update_interval=update_interval, enable_vector_db=False, mode=mode, proxy_mcp_name=proxied_mcp_name, "
            "enable_auto_refresh=False)"
        )
        updated = updated.replace(old_vector_init, new_vector_init)
        if updated == content:
            continue

        try:
            router_file.write_text(updated, encoding="utf-8")
            patched_count += 1
            logger.info("patched router runtime file: %s", router_file)
        except Exception:
            logger.warning("failed to patch router runtime file: %s", router_file, exc_info=True)

    return patched_count


def _build_start_env(env_from_server: Mapping[str, Any] | None, port: int) -> dict[str, str]:
    env = dict(os.environ)
    if env_from_server:
        for key, value in env_from_server.items():
            if value is not None:
                env[str(key)] = str(value)
    env["TRANSPORT_TYPE"] = "streamable_http"
    env["PORT"] = str(port)
    env.setdefault("AUTO_REGISTER_TOOLS", "false")
    if "DEER_FLOW_NACOS_MCP_NAMES" not in env:
        discovered_names = _discover_local_nacos_mcp_server_names(env)
        if discovered_names:
            env["DEER_FLOW_NACOS_MCP_NAMES"] = discovered_names
            logger.info("loaded DEER_FLOW_NACOS_MCP_NAMES automatically: %s", discovered_names)

    runtime_root = Path(__file__).resolve().parents[4] / ".deer-flow"
    runtime_root.mkdir(parents=True, exist_ok=True)
    uv_cache_dir = runtime_root / "uv-cache"
    uv_tool_dir = runtime_root / "uv-tools"
    uv_cache_dir.mkdir(parents=True, exist_ok=True)
    uv_tool_dir.mkdir(parents=True, exist_ok=True)

    patched_count = 0
    patched_count += _patch_router_streamable_transport(runtime_root)
    patched_count += _patch_router_nacos_list_api(runtime_root)
    patched_count += _patch_router_runtime_behavior(runtime_root)
    if patched_count > 0:
        logger.info("applied nacos-mcp-router compatibility patches: %d files", patched_count)

    env["UV_CACHE_DIR"] = str(uv_cache_dir)
    env["UV_TOOL_DIR"] = str(uv_tool_dir)
    env["HOME"] = str(runtime_root)
    if os.name == "nt":
        env["USERPROFILE"] = str(runtime_root)
        drive, tail = os.path.splitdrive(str(runtime_root))
        if drive:
            env["HOMEDRIVE"] = drive
        env["HOMEPATH"] = tail or "\\"
    _sanitize_ssl_env(env)
    return env


def _sanitize_ssl_env(env: dict[str, str]) -> None:
    """Drop invalid SSL cert env vars that can break ssl.create_default_context()."""

    for key in _SSL_CERT_FILE_ENV_VARS:
        _drop_invalid_env_path(env, key, expect_dir=False)
    for key in _SSL_CERT_DIR_ENV_VARS:
        _drop_invalid_env_path(env, key, expect_dir=True)


def _drop_invalid_env_path(env: dict[str, str], key: str, *, expect_dir: bool) -> None:
    raw_value = env.get(key)
    if raw_value is None:
        return

    value = str(raw_value).strip()
    if not value:
        env.pop(key, None)
        logger.warning("drop empty SSL env var for nacos-mcp-router: %s", key)
        return

    path = Path(value).expanduser()
    exists = path.is_dir() if expect_dir else path.is_file()
    if exists:
        return

    env.pop(key, None)
    logger.warning("drop invalid SSL env var for nacos-mcp-router: %s=%s", key, value)


def _start_router_process(command: str, args: list[str], env: dict[str, str]) -> tuple[subprocess.Popen[str], Path]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

    log_dir = Path(__file__).resolve().parents[4] / ".deer-flow" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "nacos-mcp-router-sidecar.log"
    log_fh = log_file.open("a", encoding="utf-8")

    process = subprocess.Popen(
        [command, *args],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
        text=True,
    )
    log_fh.close()
    return process, log_file


def ensure_nacos_router_http_url(
    router_params: Mapping[str, Any],
    router_name: str = _DEFAULT_ROUTER_NAME,
    port: int | None = None,
) -> str | None:
    """Ensure sidecar is reachable and return streamable HTTP URL."""
    global _ROUTER_PROCESS

    command = str(router_params.get("command") or "").strip()
    args = [str(arg) for arg in (router_params.get("args") or [])]
    if not command:
        logger.error("HTTP fallback failed: MCP service %s missing command", router_name)
        return None

    effective_port = int(port) if port is not None else _DEFAULT_PORT
    base_url = _router_http_base_url(effective_port)

    with _LOCK:
        if _is_http_endpoint_reachable(f"{base_url}/mcp"):
            logger.info("detected existing nacos-mcp-router endpoint: %s/mcp", base_url)
            return f"{base_url}/mcp"

        if _ROUTER_PROCESS is not None and _ROUTER_PROCESS.poll() is None:
            ready_url = _wait_router_ready(base_url, timeout_seconds=_DEFAULT_READY_TIMEOUT_SECONDS)
            if ready_url is not None:
                logger.info("reusing running nacos-mcp-router sidecar: %s", ready_url)
                return ready_url

        start_env = _build_start_env(router_params.get("env"), effective_port)
        logger.info("starting nacos-mcp-router sidecar: command=%s args=%s port=%s", command, args, effective_port)
        try:
            process, log_file = _start_router_process(command, args, start_env)
            _ROUTER_PROCESS = process
            logger.info("nacos-mcp-router sidecar started: pid=%s log=%s", process.pid, log_file)
        except Exception:
            logger.exception("failed to start nacos-mcp-router sidecar")
            _ROUTER_PROCESS = None
            return None

    startup_timeout = float(router_params.get("startup_timeout") or _DEFAULT_STARTUP_TIMEOUT_SECONDS)
    ready_url = _wait_router_ready(base_url, timeout_seconds=startup_timeout)
    if ready_url is not None:
        logger.info("nacos-mcp-router sidecar is ready: %s", ready_url)
        return ready_url

    with _LOCK:
        returncode = _ROUTER_PROCESS.poll() if _ROUTER_PROCESS is not None else None
        if _ROUTER_PROCESS is not None and _ROUTER_PROCESS.poll() is None:
            _ROUTER_PROCESS.terminate()
        _ROUTER_PROCESS = None

    logger.error("nacos-mcp-router sidecar startup timeout (returncode=%s)", returncode)
    return None


def build_windows_stdio_fallback_servers_config(servers_config: Mapping[str, dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
    """Convert nacos stdio config to HTTP sidecar fallback config on Windows."""
    router_params = servers_config.get(_DEFAULT_ROUTER_NAME)
    if not isinstance(router_params, Mapping):
        return None
    if str(router_params.get("transport") or "").lower() != "stdio":
        return None

    router_url = ensure_nacos_router_http_url(router_params)
    if not router_url:
        return None

    fallback: dict[str, dict[str, Any]] = {}
    for name, params in servers_config.items():
        transport = str(params.get("transport") or "").lower()
        if name == _DEFAULT_ROUTER_NAME:
            fallback[name] = {"transport": "http", "url": router_url}
            continue
        if transport in ("http", "sse"):
            fallback[name] = dict(params)
            continue
        logger.warning("skip MCP server in Windows fallback mode: transport=%s name=%s", transport or "<unknown>", name)
    return fallback
