from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class McpToolError(RuntimeError):
    pass


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / "config.yaml").exists() and (path / "skills").exists():
            return path
    configured = os.getenv("DEER_FLOW_PROJECT_ROOT")
    if configured:
        return Path(configured).resolve()
    raise McpToolError("未找到项目根目录，无法读取 config.yaml。请在项目根目录运行脚本，或设置 DEER_FLOW_PROJECT_ROOT。")


def load_config(repo_root: Path | None = None) -> dict[str, Any]:
    explicit_config_path = os.getenv("DEER_FLOW_CONFIG_PATH")
    if explicit_config_path:
        config_path = Path(explicit_config_path).expanduser().resolve()
    else:
        root = repo_root or find_repo_root()
        config_path = root / "config.yaml"
    if not config_path.exists():
        raise McpToolError(f"未找到 config.yaml：{config_path}")
    try:
        import yaml
    except ModuleNotFoundError:
        return _load_minimal_yaml(config_path)
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_minimal_yaml(config_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#") or ":" not in raw_line:
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        key, value = raw_line.strip().split(":", 1)
        value = value.strip().strip("'\"")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent, child))
        else:
            if value.lower() in {"true", "false"}:
                current[key] = value.lower() == "true"
            else:
                current[key] = value
    return result


def expected_server_name(config: dict[str, Any]) -> str:
    return os.getenv("OCEANENGINE_MCP_SERVER_NAME") or "platform-agent-biz"


def _spec_server_name(spec: dict[str, Any], fallback: str | None = None) -> str:
    return (
        spec.get("mcp_server_name")
        or spec.get("mcp", {}).get("server")
        or os.getenv("OCEANENGINE_MCP_SERVER_NAME")
        or fallback
        or "platform-agent-biz"
    )


def _ensure_backend_import_path(repo_root: Path) -> None:
    harness_path = repo_root / "backend" / "packages" / "harness"
    app_path = repo_root / "backend"
    for path in (harness_path, app_path):
        value = str(path)
        if value not in sys.path and path.exists():
            sys.path.insert(0, value)


async def _load_mcp_tools(repo_root: Path) -> list[Any]:
    _ensure_backend_import_path(repo_root)
    try:
        from deerflow.mcp.cache import initialize_mcp_tools
    except Exception as exc:  # pragma: no cover
        raise McpToolError(f"当前环境无法加载 DeerFlow MCP 工具：{exc}") from exc
    return await initialize_mcp_tools()


def _nacos_base_url(config: dict[str, Any]) -> str:
    value = os.getenv("NACOS_ADDR") or str(config.get("nacos", {}).get("server-addr") or config.get("nacos", {}).get("server_addr") or "")
    if not value:
        raise McpToolError("未配置 Nacos 地址，无法解析 MCP 服务。")
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    if not value.endswith("/"):
        value += "/"
    return value


def _nacos_namespace(config: dict[str, Any]) -> str:
    return os.getenv("NACOS_NAMESPACE") or str(config.get("nacos", {}).get("namespace") or "public")


def _nacos_get_json(config: dict[str, Any], path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = urllib.parse.urljoin(_nacos_base_url(config), path)
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    if query:
        url = f"{url}?{query}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise McpToolError(f"访问 Nacos 失败，无法解析 MCP 服务地址：{exc}") from exc


def _nacos_response_data(response: dict[str, Any], *, action: str) -> Any:
    if response.get("code") not in (0, "0", None):
        raise McpToolError(f"Nacos {action}失败：{response.get('message') or response}")
    return response.get("data")


def _server_endpoint_from_value(value: Any, export_path: str | None = None) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if not isinstance(value, dict):
        return None

    for key in ("endpoint", "url", "mcpEndpoint", "mcp_endpoint", "serverUrl", "server_url"):
        endpoint = _server_endpoint_from_value(value.get(key), export_path)
        if endpoint:
            return endpoint

    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        for key in ("endpoint", "url", "mcpEndpoint", "mcp_endpoint", "serverUrl", "server_url", "path"):
            endpoint = _server_endpoint_from_value(metadata.get(key), export_path)
            if endpoint:
                return endpoint

    host = value.get("address") or value.get("ip") or value.get("host") or value.get("hostname")
    port = value.get("port")
    if host and port:
        path = value.get("path") or value.get("exportPath") or export_path or "/mcp"
        if not str(path).startswith("/"):
            path = f"/{path}"
        scheme = value.get("scheme") or "http"
        return f"{scheme}://{host}:{port}{path}"
    return None


def _iter_endpoint_candidates(value: Any, export_path: str | None = None):
    if isinstance(value, dict):
        endpoint = _server_endpoint_from_value(value, export_path)
        if endpoint:
            yield endpoint
        for item in value.values():
            yield from _iter_endpoint_candidates(item, export_path)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_endpoint_candidates(item, export_path)


def _resolve_nacos_mcp_endpoint(config: dict[str, Any], server_name: str) -> str:
    detail = _nacos_response_data(
        _nacos_get_json(config, "nacos/v3/admin/ai/mcp", {"mcpName": server_name, "namespaceId": _nacos_namespace(config)}),
        action=f"查询 MCP server {server_name}",
    )
    if not isinstance(detail, dict) or detail.get("name") != server_name:
        raise McpToolError(f"Nacos 中不存在 MCP server {server_name}，请先确认 Nacos 配置和 Java 服务注册状态。")

    remote_config = detail.get("remoteServerConfig") if isinstance(detail.get("remoteServerConfig"), dict) else {}
    export_path = remote_config.get("exportPath") or detail.get("exportPath") or "/mcp"
    for endpoint in _iter_endpoint_candidates(
        [detail.get("backendEndpoints"), detail.get("frontendEndpoints"), remote_config.get("endpoint"), remote_config.get("endpoints")],
        export_path,
    ):
        return endpoint

    service_ref = remote_config.get("serviceRef") if isinstance(remote_config.get("serviceRef"), dict) else {}
    service_name = service_ref.get("serviceName")
    if not service_name:
        raise McpToolError(f"Nacos MCP server {server_name} 未配置可用的 serviceRef 或 endpoint。")

    instances = _nacos_response_data(
        _nacos_get_json(
            config,
            "nacos/v3/client/ns/instance/list",
            {
                "serviceName": service_name,
                "groupName": service_ref.get("groupName") or "DEFAULT_GROUP",
                "namespaceId": service_ref.get("namespaceId") or _nacos_namespace(config),
            },
        ),
        action=f"查询 MCP server {server_name} 实例",
    )
    for endpoint in _iter_endpoint_candidates(instances, export_path):
        return endpoint

    raise McpToolError(f"Nacos 已注册 MCP server {server_name}，但未解析到可用的实例地址、端口和路径。")


def _decode_streamable_http(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line.removeprefix("data:").strip())
    if text.strip():
        return json.loads(text)
    return {}


def _read_response_text(response: Any) -> str:
    return response.read().decode("utf-8")


def _mcp_outbound_identity_headers() -> dict[str, str]:
    """与 Gateway AuthMiddleware / LangChain MCP 一致的出站身份头（X-User-Id 等）。

    合并版通过 urllib 直连 MCP 时不经过 httpx.Auth，必须在此显式合并 ContextVar，
    否则 Java MCP 侧无法从 Header 还原当前用户。
    """
    try:
        root = find_repo_root()
        _ensure_backend_import_path(root)
        from deerflow.mcp.context import build_request_headers

        return build_request_headers()
    except Exception:
        return {}


def _jsonrpc_request(endpoint: str, method: str, params: dict[str, Any] | None = None, *, request_id: int | None = 1, session_id: str | None = None):
    body: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if request_id is not None:
        body["id"] = request_id
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    for key, value in _mcp_outbound_identity_headers().items():
        headers.setdefault(key, value)
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )


def _initialize_mcp_session(endpoint: str) -> str:
    request = _jsonrpc_request(
        endpoint,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "deerflow-oceanengine-native-tool", "version": "1.0.0"},
        },
        request_id=1,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            _decode_streamable_http(_read_response_text(response))
            session_id = response.headers.get("Mcp-Session-Id")
    except Exception as exc:  # pragma: no cover
        raise McpToolError(f"MCP 服务端点初始化失败：{endpoint}，错误：{exc}") from exc
    if not session_id:
        raise McpToolError(f"MCP 服务端点初始化失败：{endpoint} 未返回 Mcp-Session-Id。")
    try:
        with urllib.request.urlopen(
            _jsonrpc_request(endpoint, "notifications/initialized", {}, request_id=None, session_id=session_id),
            timeout=60,
        ) as response:
            _read_response_text(response)
    except Exception as exc:  # pragma: no cover
        raise McpToolError(f"MCP 服务端点初始化完成通知失败：{endpoint}，错误：{exc}") from exc
    return session_id


def _call_jsonrpc(
    endpoint: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
    session_id: str | None = None,
) -> dict[str, Any]:
    request = _jsonrpc_request(endpoint, method, params, request_id=request_id, session_id=session_id)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return _decode_streamable_http(_read_response_text(response))
    except Exception as exc:  # pragma: no cover
        raise McpToolError(f"MCP 服务端点不可达或调用失败：{endpoint}，错误：{exc}") from exc


def _call_mcp_tool_endpoint(endpoint: str, tool_name: str, arguments: dict[str, Any], *, request_id: int) -> Any:
    session_id = _initialize_mcp_session(endpoint)
    response = _call_jsonrpc(endpoint, "tools/call", {"name": tool_name, "arguments": arguments}, request_id=request_id, session_id=session_id)
    if "error" in response:
        raise McpToolError(str(response["error"]))
    result = response.get("result", {})
    return result.get("content", result)


def _iter_mcp_text(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "message", "msg", "error"} and isinstance(item, str):
                yield item
            yield from _iter_mcp_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mcp_text(item)
    elif isinstance(value, str):
        yield value


def _is_server_not_found_result(value: Any) -> bool:
    markers = (
        "mcp server not found",
        "server not found",
        "is not found",
        "not found, use search_mcp_server",
    )
    return any(any(marker in text.lower() for marker in markers) for text in _iter_mcp_text(value))


def _lookup_nacos_mcp_server(server_name: str) -> dict[str, Any]:
    try:
        config = load_config(find_repo_root())
        endpoint = _resolve_nacos_mcp_endpoint(config, server_name)
    except Exception as exc:  # pragma: no cover - best-effort diagnostic only
        return {"found": None, "error": str(exc)}
    return {"found": True, "endpoint": endpoint}


def _raise_server_not_found(server_name: str) -> None:
    lookup = _lookup_nacos_mcp_server(server_name)
    if lookup.get("found") is False:
        raise McpToolError(f"Nacos 中不存在 MCP server {server_name}，请先确认 Nacos 配置和 Java 服务注册状态。")
    if lookup.get("found") is True:
        raise McpToolError(
            f"Nacos 中存在 MCP server {server_name}，但未解析到可用的 MCP 服务端点，请检查 Java 服务实例注册和 exportPath。"
        )
    raise McpToolError(
        f"MCP server {server_name} 未被 router 找到，且无法确认 Nacos 注册状态：{lookup.get('error') or '未知原因'}。"
    )


def _ensure_mcp_tool_result_usable(result: Any, server_name: str) -> None:
    if _is_server_not_found_result(result):
        _raise_server_not_found(server_name)


def invoke_endpoint_via_nacos(spec: dict[str, Any], payload: dict[str, Any], server_name: str | None = None) -> dict[str, Any]:
    mcp_tool_name = spec.get("mcp_tool_name")
    if not mcp_tool_name:
        raise McpToolError(f"接口 {spec['path']} 未配置 MCP 工具名，无法通过 Nacos MCP 服务调用。")

    resolved_server_name = _spec_server_name(spec, server_name)
    mcp_payload = build_mcp_payload(spec, payload)
    config = load_config(find_repo_root())
    endpoint = _resolve_nacos_mcp_endpoint(config, resolved_server_name)
    result = _call_mcp_tool_endpoint(endpoint, mcp_tool_name, mcp_payload, request_id=2)
    _ensure_mcp_tool_result_usable(result, resolved_server_name)
    return {"tool_name": f"{resolved_server_name}:{mcp_tool_name}", "raw": result, "request_id": None}


def _tool_text(tool: Any) -> str:
    name = str(getattr(tool, "name", ""))
    description = str(getattr(tool, "description", ""))
    return f"{name}\n{description}".lower()


def _score_tool(tool: Any, spec: dict[str, Any], server_name: str) -> int:
    text = _tool_text(tool)
    score = 0
    if server_name.lower() in text:
        score += 100
    compact_path = spec["path"].strip("/").lower()
    path_fragments = [compact_path, compact_path.replace("/", "_"), compact_path.replace("/", "-")]
    if any(fragment in text for fragment in path_fragments):
        score += 60
    for token in spec.get("match_tokens", []):
        if str(token).lower() in text:
            score += 10
    if spec.get("title", "").lower() in text:
        score += 20
    return score


def select_tool(tools: list[Any], spec: dict[str, Any], server_name: str) -> Any | None:
    scored = [(tool, _score_tool(tool, spec, server_name)) for tool in tools]
    scored = [item for item in scored if item[1] > 0]
    if not scored:
        return None
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[0][0]


def _tool_by_name(tools: list[Any], name: str) -> Any | None:
    for tool in tools:
        if getattr(tool, "name", None) == name:
            return tool
    return None


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _map_value(value: Any, value_maps: dict[str, Any] | None = None, field_path: str = "") -> Any:
    if isinstance(value, dict):
        mapped: dict[str, Any] = {}
        for key, item in value.items():
            mcp_key = _snake_to_camel(str(key))
            child_path = f"{field_path}.{mcp_key}" if field_path else mcp_key
            mapped[mcp_key] = _map_value(item, value_maps, child_path)
        return mapped
    if isinstance(value, list):
        return [_map_value(item, value_maps, field_path) for item in value]
    if value_maps is not None and field_path:
        return _replace_mapped_value(field_path, value, value_maps)
    return value


def _replace_mapped_value(field_path: str, value: Any, value_maps: dict[str, Any]) -> Any:
    replacements = value_maps.get(field_path)
    if isinstance(replacements, dict) and value in replacements:
        return replacements[value]
    return value


def _get_path(value: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _set_path(value: dict[str, Any], path: str, item: Any) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = item


def _delete_path(value: dict[str, Any], path: str) -> None:
    parts = path.split(".")

    def delete(current: dict[str, Any], index: int) -> bool:
        part = parts[index]
        if part not in current:
            return False
        if index == len(parts) - 1:
            current.pop(part, None)
        else:
            child = current.get(part)
            if isinstance(child, dict) and delete(child, index + 1) and not child:
                current.pop(part, None)
        return not current

    delete(value, 0)


def _apply_dotted_field_map(payload: dict[str, Any], field_map: dict[str, str], value_maps: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = copy.deepcopy(payload)
    mapped: dict[str, Any] = {}
    for source_path, target_path in field_map.items():
        if "." not in source_path:
            continue
        found, value = _get_path(source, source_path)
        if not found:
            continue
        mapped_value = _replace_mapped_value(target_path, _map_value(value, value_maps, target_path), value_maps)
        _set_path(mapped, target_path, mapped_value)
        _delete_path(source, source_path)
    return source, mapped


def build_mcp_payload(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    field_map = spec.get("mcp_field_map", {})
    array_field_map = spec.get("mcp_array_field_map", {})
    value_maps = spec.get("mcp_value_maps", {})
    batch_field = spec.get("batch_field")
    mcp_batch_field = spec.get("mcp_batch_field", "data")
    source_payload, mapped = _apply_dotted_field_map(payload, field_map, value_maps)
    direct_field_map = {key: value for key, value in field_map.items() if "." not in key}

    for key, value in source_payload.items():
        if key == batch_field:
            mapped[mcp_batch_field] = [_map_value(item) for item in value]
            for item in mapped[mcp_batch_field]:
                for value_key, replacements in value_maps.items():
                    if "." in value_key:
                        _, item_key = value_key.split(".", 1)
                        if item_key in item and item[item_key] in replacements:
                            item[item_key] = replacements[item[item_key]]
            continue

        if key in array_field_map:
            mcp_key = array_field_map[key]
            mapped[mcp_key] = value if isinstance(value, list) else [value]
            continue

        mcp_key = direct_field_map.get(key) or _snake_to_camel(key)
        mapped[mcp_key] = _replace_mapped_value(mcp_key, _map_value(value, value_maps, mcp_key), value_maps)

    if spec.get("mcp_wrap_request"):
        return {"request": mapped}
    return mapped


def _invoke_tool(tool: Any, payload: dict[str, Any]) -> Any:
    if hasattr(tool, "invoke"):
        return tool.invoke(payload)
    func = getattr(tool, "func", None)
    if callable(func):
        return func(**payload)
    coroutine = getattr(tool, "coroutine", None)
    if callable(coroutine):
        return asyncio.run(coroutine(**payload))
    raise McpToolError("匹配到了 MCP 工具，但该工具没有可调用入口。")


def invoke_endpoint(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    try:
        repo_root = find_repo_root()
    except McpToolError as exc:
        raise McpToolError(f"无法解析 MCP 服务地址：{exc}") from exc
    config = load_config(repo_root)
    server_name = _spec_server_name(spec, expected_server_name(config))
    try:
        tools = asyncio.run(_load_mcp_tools(repo_root))
    except McpToolError:
        return invoke_endpoint_via_nacos(spec, payload, server_name)
    mcp_payload = build_mcp_payload(spec, payload)
    mcp_tool_name = spec.get("mcp_tool_name")
    tool = _tool_by_name(tools, mcp_tool_name) if mcp_tool_name else select_tool(tools, spec, server_name)
    if tool is not None:
        result = _invoke_tool(tool, mcp_payload)
        return {
            "tool_name": getattr(tool, "name", None),
            "raw": result,
            "request_id": result.get("request_id") if isinstance(result, dict) else None,
        }

    router_tool = _tool_by_name(tools, "nacos-mcp-router_use_tool")
    if router_tool is None or not mcp_tool_name:
        return invoke_endpoint_via_nacos(spec, payload, server_name)

    result = _invoke_tool(
        router_tool,
        {
            "mcp_server_name": server_name,
            "mcp_tool_name": mcp_tool_name,
            "params": json.dumps(mcp_payload, ensure_ascii=False),
        },
    )
    if _is_server_not_found_result(result):
        return invoke_endpoint_via_nacos(spec, payload, server_name)
    _ensure_mcp_tool_result_usable(result, server_name)
    return {
        "tool_name": f"{getattr(router_tool, 'name', 'nacos-mcp-router_use_tool')}:{mcp_tool_name}",
        "raw": result,
        "request_id": result.get("request_id") if isinstance(result, dict) else None,
    }
