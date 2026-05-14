"""MCP 运行时配置组装（静态配置 + Nacos Router 注入）。"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from deerflow.config.app_config import AppConfig, get_app_config, reload_app_config
from deerflow.config.extensions_config import McpServerConfig

logger = logging.getLogger(__name__)

McpServerSource = Literal["static", "nacos"]
_SENSITIVE_KEYS = ("password", "token", "secret", "key", "authorization")

# Cache for nacos router server view; rebuilt only when the inputs change
# (config mtime, enabled flag, transport, port, command/args/env, credentials).
_ROUTER_CACHE_LOCK = threading.Lock()
_ROUTER_CACHE_KEY: tuple[Any, ...] | None = None
_ROUTER_CACHE_VALUE: dict[str, McpServerConfig] = {}


@dataclass(frozen=True)
class McpServerView:
    """API/UI 使用的 MCP 服务视图。"""

    config: McpServerConfig
    source: McpServerSource
    read_only: bool


def _mask_sensitive(value: str | None) -> str:
    if value is None:
        return ""
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def _sanitize_env(env: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in env.items():
        if any(token in key.lower() for token in _SENSITIVE_KEYS):
            sanitized[key] = _mask_sensitive(value)
        else:
            sanitized[key] = value
    return sanitized


def _router_cache_key(app_config: AppConfig) -> tuple[Any, ...]:
    """构造用于 router 视图缓存失效的 key。"""
    nacos_cfg = app_config.nacos
    mcp_cfg = nacos_cfg.mcp
    try:
        config_path = AppConfig.resolve_config_path()
        mtime = config_path.stat().st_mtime if config_path.exists() else None
    except Exception:
        mtime = None

    env_items = tuple(sorted((str(k), str(v)) for k, v in (getattr(mcp_cfg, "env", None) or {}).items() if v is not None))
    return (
        mtime,
        bool(getattr(mcp_cfg, "enabled", False)),
        (getattr(mcp_cfg, "transport", "stdio") or "stdio").lower(),
        int(getattr(mcp_cfg, "port", 0) or 0),
        getattr(mcp_cfg, "router_name", ""),
        getattr(mcp_cfg, "command", ""),
        tuple(getattr(mcp_cfg, "args", None) or ()),
        getattr(nacos_cfg, "server_addr", ""),
        getattr(nacos_cfg, "namespace", "") or "",
        getattr(mcp_cfg, "username", "") or getattr(nacos_cfg, "username", ""),
        getattr(mcp_cfg, "password", "") or getattr(nacos_cfg, "password", ""),
        int(getattr(mcp_cfg, "update_interval", 0) or 0),
        env_items,
    )


def _build_nacos_router_server(app_config: AppConfig) -> dict[str, McpServerConfig]:
    """根据 nacos 配置构建自动注入的 Router 服务（带缓存）。"""
    global _ROUTER_CACHE_KEY, _ROUTER_CACHE_VALUE

    cache_key = _router_cache_key(app_config)
    with _ROUTER_CACHE_LOCK:
        if _ROUTER_CACHE_KEY == cache_key:
            return dict(_ROUTER_CACHE_VALUE)

    value = _build_nacos_router_server_uncached(app_config)

    with _ROUTER_CACHE_LOCK:
        _ROUTER_CACHE_KEY = cache_key
        _ROUTER_CACHE_VALUE = dict(value)
    return value


def _build_nacos_router_server_uncached(app_config: AppConfig) -> dict[str, McpServerConfig]:
    """实际构建逻辑；调用方负责缓存。"""
    nacos_cfg = app_config.nacos
    mcp_cfg = nacos_cfg.mcp
    mcp_username = getattr(mcp_cfg, "username", "") or nacos_cfg.username
    mcp_password = getattr(mcp_cfg, "password", "") or nacos_cfg.password

    if not mcp_cfg.enabled:
        logger.info("Nacos MCP Router 注入已关闭（nacos.mcp.enabled=false）")
        return {}
    if not mcp_password:
        logger.info("Nacos MCP Router 注入已跳过：有效密码为空")
        return {}

    transport = (getattr(mcp_cfg, "transport", "stdio") or "stdio").lower()
    env: dict[str, str] = {
        "NACOS_ADDR": nacos_cfg.server_addr,
        "NACOS_USERNAME": mcp_username,
        "NACOS_PASSWORD": mcp_password,
    }
    if nacos_cfg.namespace:
        env["NACOS_NAMESPACE"] = nacos_cfg.namespace

    update_interval = int(getattr(mcp_cfg, "update_interval", 0) or 0)
    if update_interval > 0:
        env["UPDATE_INTERVAL"] = str(update_interval)

    for key, value in (getattr(mcp_cfg, "env", None) or {}).items():
        if value is not None:
            env[str(key)] = str(value)

    if transport == "streamable_http":
        from deerflow.mcp.router_sidecar import ensure_nacos_router_http_url

        port = int(getattr(mcp_cfg, "port", 18000) or 18000)
        env["TRANSPORT_TYPE"] = "streamable_http"
        env["PORT"] = str(port)

        router_params = {"command": mcp_cfg.command, "args": mcp_cfg.args, "env": env}
        url = ensure_nacos_router_http_url(router_params, mcp_cfg.router_name, port=port)
        if not url:
            logger.error(
                "Nacos MCP Router sidecar 启动失败：transport=streamable_http port=%s，跳过注入",
                port,
            )
            return {}

        server = McpServerConfig(enabled=True, type="http", url=url, description=mcp_cfg.description)
        logger.info(
            "已注入 Nacos MCP Router（streamable_http）：name=%s url=%s env=%s",
            mcp_cfg.router_name,
            url,
            _sanitize_env(env),
        )
        return {mcp_cfg.router_name: server}

    env["TRANSPORT_TYPE"] = "stdio"
    server = McpServerConfig(
        enabled=True,
        type="stdio",
        command=mcp_cfg.command,
        args=mcp_cfg.args,
        env=env,
        description=mcp_cfg.description,
    )
    logger.info(
        "已注入 Nacos MCP Router（stdio）：name=%s command=%s args=%s env=%s",
        mcp_cfg.router_name,
        mcp_cfg.command,
        mcp_cfg.args,
        _sanitize_env(env),
    )
    return {mcp_cfg.router_name: server}


def reset_nacos_discovery_cache() -> None:
    """清空 router 视图缓存。"""
    global _ROUTER_CACHE_KEY, _ROUTER_CACHE_VALUE
    with _ROUTER_CACHE_LOCK:
        _ROUTER_CACHE_KEY = None
        _ROUTER_CACHE_VALUE = {}


def get_mcp_server_views() -> dict[str, McpServerView]:
    """获取 MCP 合并视图（静态服务 + nacos router）。"""
    app_config = get_app_config()
    views: dict[str, McpServerView] = {
        name: McpServerView(config=cfg, source="static", read_only=False)
        for name, cfg in app_config.mcp.static_servers.items()
    }

    # router 视图会覆盖同名静态服务
    for name, cfg in _build_nacos_router_server(app_config).items():
        views[name] = McpServerView(config=cfg, source="nacos", read_only=True)

    logger.debug(
        "MCP 服务视图构建完成：total=%d servers=%s",
        len(views),
        {name: view.source for name, view in views.items()},
    )
    return views


def get_merged_mcp_servers() -> dict[str, McpServerConfig]:
    """获取工具加载使用的 MCP 合并配置。"""
    return {name: view.config for name, view in get_mcp_server_views().items()}


def get_mcp_cache_state_token() -> tuple[float | None, int]:
    """返回用于 MCP 缓存失效的状态标记。"""
    try:
        config_path = AppConfig.resolve_config_path()
        mtime = config_path.stat().st_mtime if config_path.exists() else None
    except Exception:
        mtime = None
    return mtime, 0


def write_static_mcp_servers(mcp_servers: dict[str, McpServerConfig | dict]) -> dict[str, McpServerConfig]:
    """将静态 MCP 服务写回 config.yaml，并刷新 app 配置缓存。"""
    config_path = AppConfig.resolve_config_path()
    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f) or {}

    static_servers: dict[str, dict] = {}
    for name, raw in mcp_servers.items():
        model = raw if isinstance(raw, McpServerConfig) else McpServerConfig.model_validate(raw)
        static_servers[name] = model.model_dump(exclude_none=True)

    mcp_section = config_data.get("mcp")
    if not isinstance(mcp_section, dict):
        mcp_section = {}
        config_data["mcp"] = mcp_section
    mcp_section["static_servers"] = static_servers

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f, sort_keys=False, allow_unicode=True)

    reloaded = reload_app_config(str(Path(config_path)))
    logger.info("静态 MCP 配置写入完成：count=%d", len(reloaded.mcp.static_servers))
    return dict(reloaded.mcp.static_servers)
