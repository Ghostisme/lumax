from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _find_repo_root_from_file() -> Path | None:
    current = Path(__file__).resolve()
    for path in [current.parent, *current.parents]:
        if (path / "config.yaml").exists() and (path / "skills").exists():
            return path
    configured = os.getenv("DEER_FLOW_PROJECT_ROOT")
    if configured:
        return Path(configured).resolve()
    return None


_REPO_ROOT = _find_repo_root_from_file()
if _REPO_ROOT is not None and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from tools.oceanengine_local_project_runtime import mcp_client as _runtime_mcp_client
except Exception as _import_exc:  # pragma: no cover - depends on script execution environment
    _RUNTIME_IMPORT_ERROR: Exception | None = _import_exc

    class McpToolError(RuntimeError):
        pass

else:
    _RUNTIME_IMPORT_ERROR = None
    McpToolError = _runtime_mcp_client.McpToolError


def _runtime():
    if _RUNTIME_IMPORT_ERROR is not None:
        raise McpToolError(
            "无法加载项目共享 MCP runtime，项目管理脚本不能执行真实 MCP 调用。"
            "请在项目根目录运行脚本，或设置 DEER_FLOW_PROJECT_ROOT 指向包含 config.yaml 和 tools/ 的项目根目录。"
        ) from _RUNTIME_IMPORT_ERROR
    return _runtime_mcp_client


def __getattr__(name: str) -> Any:
    return getattr(_runtime(), name)


def find_repo_root(start: Path | None = None) -> Path:
    return _runtime().find_repo_root(start)


def load_config(repo_root: Path | None = None) -> dict[str, Any]:
    return _runtime().load_config(repo_root)


def expected_server_name(config: dict[str, Any]) -> str:
    return _runtime().expected_server_name(config)


def build_mcp_payload(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return _runtime().build_mcp_payload(spec, payload)


def invoke_endpoint_via_nacos(spec: dict[str, Any], payload: dict[str, Any], server_name: str | None = None) -> dict[str, Any]:
    return _runtime().invoke_endpoint_via_nacos(spec, payload, server_name)


def invoke_endpoint(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return _runtime().invoke_endpoint(spec, payload)


def _router_url() -> str:
    value = os.getenv("OCEANENGINE_MCP_ROUTER_URL") or os.getenv("NACOS_MCP_ROUTER_URL")
    if not value:
        raise McpToolError("项目管理脚本不再提供本机固定 Router 默认地址；请通过 Nacos 解析目标 MCP endpoint。")
    if not value.endswith("/"):
        value += "/"
    return value


def invoke_endpoint_via_router(spec: dict[str, Any], payload: dict[str, Any], server_name: str | None = None) -> dict[str, Any]:
    raise McpToolError("项目管理脚本不再支持通过固定 Router 地址作为业务兜底；请通过 Nacos 解析目标 MCP endpoint。")


def _call_router_tool(tool_name: str, arguments: dict[str, Any], *, request_id: int) -> Any:
    raise McpToolError("项目管理脚本不再支持直接调用 Router 管理工具作为业务兜底。")
