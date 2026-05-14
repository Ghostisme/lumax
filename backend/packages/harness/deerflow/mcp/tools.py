"""Load MCP tools using langchain-mcp-adapters."""

import asyncio
import atexit
import concurrent.futures
import contextvars
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool

from deerflow.config.extensions_config import ExtensionsConfig
from deerflow.mcp.client import build_servers_config, get_enabled_mcp_server_configs
from deerflow.mcp.oauth import build_oauth_tool_interceptor, get_initial_oauth_headers
from deerflow.mcp.router_sidecar import build_windows_stdio_fallback_servers_config
from deerflow.reflection import resolve_variable

logger = logging.getLogger(__name__)

# Global thread pool for sync tool invocation in async environments
_SYNC_TOOL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="mcp-sync-tool")

# Register shutdown hook for the global executor
atexit.register(lambda: _SYNC_TOOL_EXECUTOR.shutdown(wait=False))


def _make_sync_tool_wrapper(coro: Callable[..., Any], tool_name: str) -> Callable[..., Any]:
    """Build a synchronous wrapper for an asynchronous tool coroutine.

    Args:
        coro: The tool's asynchronous coroutine.
        tool_name: Name of the tool (for logging).

    Returns:
        A synchronous function that correctly handles nested event loops.
    """

    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        try:
            if loop is not None and loop.is_running():
                # Use global executor to avoid nested loop issues and improve performance
                ctx = contextvars.copy_context()
                future = _SYNC_TOOL_EXECUTOR.submit(ctx.run, asyncio.run, coro(*args, **kwargs))
                return future.result()
            else:
                return asyncio.run(coro(*args, **kwargs))
        except Exception as e:
            logger.error(f"Error invoking MCP tool '{tool_name}' via sync wrapper: {e}", exc_info=True)
            raise

    return sync_wrapper


def _summarize_tools(tools: list[BaseTool], max_items: int = 30) -> list[str]:
    names = [getattr(t, "name", "<unknown>") for t in tools]
    if len(names) <= max_items:
        return names
    return names[:max_items] + [f"...(+{len(names) - max_items} more)"]


def _attach_sync_wrappers(tools: list[BaseTool]) -> None:
    for tool in tools:
        if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None) is not None:
            tool.func = _make_sync_tool_wrapper(tool.coroutine, tool.name)


def _build_managed_mcp_guard_interceptor() -> Any:
    async def managed_mcp_guard_interceptor(request: Any, handler: Any) -> Any:
        from tools.managed_mcp_guard import guard_managed_mcp_tool_call

        server_name = str(getattr(request, "server_name", ""))
        tool_name = str(getattr(request, "name", ""))
        prefixed_tool_name = f"{server_name}_{tool_name}" if server_name else tool_name
        guard_managed_mcp_tool_call(prefixed_tool_name, getattr(request, "args", None))
        return await handler(request)

    return managed_mcp_guard_interceptor


async def _load_tools_from_servers_config(
    servers_config: dict[str, dict[str, Any]],
    enabled_servers: dict[str, Any],
    tool_interceptors: list[Any],
) -> list[BaseTool]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    initial_oauth_headers = await get_initial_oauth_headers(enabled_servers)
    for server_name, auth_header in initial_oauth_headers.items():
        if server_name not in servers_config:
            continue
        if servers_config[server_name].get("transport") in ("sse", "http"):
            existing_headers = dict(servers_config[server_name].get("headers", {}))
            existing_headers["Authorization"] = auth_header
            servers_config[server_name]["headers"] = existing_headers

    client = MultiServerMCPClient(servers_config, tool_interceptors=tool_interceptors, tool_name_prefix=True)
    tools = await client.get_tools()
    _attach_sync_wrappers(tools)
    return tools


async def get_mcp_tools() -> list[BaseTool]:
    """Get all tools from enabled MCP servers.

    Returns:
        List of LangChain tools from all enabled MCP servers.
    """
    try:
        __import__("langchain_mcp_adapters.client")
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed. Install it to enable MCP tools: pip install langchain-mcp-adapters")
        return []

    # NOTE: We use ExtensionsConfig.from_file() instead of get_extensions_config()
    # to always read the latest configuration from disk. This ensures that changes
    # made through the Gateway API (which runs in a separate process) are immediately
    # reflected when initializing MCP tools.
    extensions_config = ExtensionsConfig.from_file()
    enabled_servers = get_enabled_mcp_server_configs(extensions_config)
    servers_config = build_servers_config(extensions_config)

    if not servers_config:
        logger.info("No enabled MCP servers configured")
        return []

    tool_interceptors = [_build_managed_mcp_guard_interceptor()]
    oauth_interceptor = build_oauth_tool_interceptor(enabled_servers)
    if oauth_interceptor is not None:
        tool_interceptors.append(oauth_interceptor)

    # Load custom interceptors declared in extensions_config.json
    # Format: "mcpInterceptors": ["pkg.module:builder_func", ...]
    raw_interceptor_paths = (extensions_config.model_extra or {}).get("mcpInterceptors")
    if isinstance(raw_interceptor_paths, str):
        raw_interceptor_paths = [raw_interceptor_paths]
    elif not isinstance(raw_interceptor_paths, list):
        if raw_interceptor_paths is not None:
            logger.warning(f"mcpInterceptors must be a list of strings, got {type(raw_interceptor_paths).__name__}; skipping")
        raw_interceptor_paths = []
    for interceptor_path in raw_interceptor_paths:
        try:
            builder = resolve_variable(interceptor_path)
            interceptor = builder()
            if callable(interceptor):
                tool_interceptors.append(interceptor)
                logger.info(f"Loaded MCP interceptor: {interceptor_path}")
            elif interceptor is not None:
                logger.warning(f"Builder {interceptor_path} returned non-callable {type(interceptor).__name__}; skipping")
        except Exception as e:
            logger.warning(f"Failed to load MCP interceptor {interceptor_path}: {e}", exc_info=True)

    try:
        logger.info(f"Initializing MCP client with {len(servers_config)} server(s)")
        tools = await _load_tools_from_servers_config(dict(servers_config), enabled_servers, tool_interceptors)
        logger.info("Successfully loaded %d tool(s) from MCP servers: %s", len(tools), _summarize_tools(tools))
        return tools

    except PermissionError as e:
        logger.error(f"MCP stdio subprocess failed with a permission error: {e}", exc_info=True)
        fallback_servers_config = await asyncio.to_thread(build_windows_stdio_fallback_servers_config, servers_config)
        if not fallback_servers_config:
            return []
        logger.info(
            "Retrying MCP tools with Windows HTTP fallback: server_count=%d names=%s",
            len(fallback_servers_config),
            list(fallback_servers_config.keys()),
        )
        try:
            tools = await _load_tools_from_servers_config(dict(fallback_servers_config), enabled_servers, tool_interceptors)
            logger.info("Successfully loaded %d MCP tool(s) via HTTP fallback: %s", len(tools), _summarize_tools(tools))
            return tools
        except Exception as fallback_error:
            logger.error(f"Failed to load MCP tools via HTTP fallback: {fallback_error}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return []
