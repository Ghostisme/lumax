"""MCP client using langchain-mcp-adapters."""

import logging
from typing import Any

from deerflow.config.extensions_config import ExtensionsConfig, McpServerConfig
from deerflow.mcp.context import build_mcp_request_auth

logger = logging.getLogger(__name__)


def build_server_params(server_name: str, config: McpServerConfig) -> dict[str, Any]:
    """Build server parameters for MultiServerMCPClient.

    Args:
        server_name: Name of the MCP server.
        config: Configuration for the MCP server.

    Returns:
        Dictionary of server parameters for langchain-mcp-adapters.
    """
    transport_type = config.type or "stdio"
    params: dict[str, Any] = {"transport": transport_type}

    if transport_type == "stdio":
        if not config.command:
            raise ValueError(f"MCP server '{server_name}' with stdio transport requires 'command' field")
        params["command"] = config.command
        params["args"] = config.args
        # Add environment variables if present
        if config.env:
            params["env"] = config.env
    elif transport_type in ("sse", "http"):
        if not config.url:
            raise ValueError(f"MCP server '{server_name}' with {transport_type} transport requires 'url' field")
        params["url"] = config.url
        # Add headers if present
        if config.headers:
            params["headers"] = config.headers
        # Inject per-request user/tenant/business headers via httpx.Auth.
        # Reads ContextVar at send time; session-level static headers remain unchanged.
        params["auth"] = build_mcp_request_auth()
    else:
        raise ValueError(f"MCP server '{server_name}' has unsupported transport type: {transport_type}")

    return params


def get_enabled_mcp_server_configs(extensions_config: ExtensionsConfig) -> dict[str, McpServerConfig]:
    """Get effective enabled MCP server configs from both config sources.

    MCP servers can come from:
    - ``extensions_config.json`` (legacy/current dynamic source)
    - ``config.yaml`` via DeerFlow MCP runtime merge (static + nacos router)

    Precedence rule for same-name servers:
    ``extensions_config.json`` overrides runtime-merged entries to preserve
    existing behavior for previously configured servers.
    """
    enabled_from_extensions = extensions_config.get_enabled_mcp_servers()

    try:
        from deerflow.mcp.runtime import get_merged_mcp_servers

        enabled_from_runtime = {
            name: cfg
            for name, cfg in get_merged_mcp_servers().items()
            if getattr(cfg, "enabled", True)
        }
    except Exception as e:
        logger.warning(f"Failed to read runtime MCP servers from config.yaml: {e}")
        enabled_from_runtime = {}

    merged_enabled = dict(enabled_from_runtime)
    merged_enabled.update(enabled_from_extensions)
    return merged_enabled


def build_servers_config(extensions_config: ExtensionsConfig) -> dict[str, dict[str, Any]]:
    """Build servers configuration for MultiServerMCPClient.

    Args:
        extensions_config: Extensions configuration containing all MCP servers.

    Returns:
        Dictionary mapping server names to their parameters.
    """
    enabled_servers = get_enabled_mcp_server_configs(extensions_config)

    if not enabled_servers:
        logger.info("No enabled MCP servers found")
        return {}

    servers_config = {}
    for server_name, server_config in enabled_servers.items():
        try:
            servers_config[server_name] = build_server_params(server_name, server_config)
            logger.info(f"Configured MCP server: {server_name}")
        except Exception as e:
            logger.error(f"Failed to configure MCP server '{server_name}': {e}")

    return servers_config
