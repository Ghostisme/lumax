from types import SimpleNamespace

import yaml

from deerflow.config.extensions_config import McpServerConfig
from deerflow.mcp import runtime


def test_get_mcp_server_views_merges_static_and_router(monkeypatch):
    static_srv = McpServerConfig(enabled=True, type="http", url="http://static.local/mcp", description="static")
    fake_cfg = SimpleNamespace(
        mcp=SimpleNamespace(static_servers={"shared": static_srv}),
        nacos=SimpleNamespace(
            server_addr="127.0.0.1:8848",
            username="nacos",
            password="secret",
            namespace="public",
            mcp=SimpleNamespace(
                enabled=True,
                router_name="shared",
                command="uvx",
                args=["nacos-mcp-router@latest"],
                description="Nacos MCP Router",
            ),
        ),
    )
    monkeypatch.setattr(runtime, "get_app_config", lambda: fake_cfg)

    views = runtime.get_mcp_server_views()

    assert views["shared"].source == "nacos"
    assert views["shared"].read_only is True
    assert views["shared"].config.command == "uvx"
    assert views["shared"].config.args == ["nacos-mcp-router@latest"]
    assert views["shared"].config.env["NACOS_ADDR"] == "127.0.0.1:8848"
    assert views["shared"].config.env["NACOS_PASSWORD"] == "secret"


def test_get_mcp_server_views_skips_router_when_password_empty(monkeypatch):
    static_srv = McpServerConfig(enabled=True, type="http", url="http://static.local/mcp", description="static")
    fake_cfg = SimpleNamespace(
        mcp=SimpleNamespace(static_servers={"static-only": static_srv}),
        nacos=SimpleNamespace(
            server_addr="127.0.0.1:8848",
            username="nacos",
            password="",
            namespace="public",
            mcp=SimpleNamespace(
                enabled=True,
                router_name="nacos-mcp-router",
                command="uvx",
                args=["nacos-mcp-router@latest"],
                description="Nacos MCP Router",
            ),
        ),
    )
    monkeypatch.setattr(runtime, "get_app_config", lambda: fake_cfg)

    views = runtime.get_mcp_server_views()
    assert list(views.keys()) == ["static-only"]
    assert views["static-only"].source == "static"


def test_get_mcp_server_views_streamable_http_uses_sidecar(monkeypatch):
    captured: dict = {}

    def _fake_ensure(router_params, router_name, port=None):
        captured["params"] = dict(router_params)
        captured["name"] = router_name
        captured["port"] = port
        return f"http://127.0.0.1:{port}/mcp/"

    import deerflow.mcp.router_sidecar as sidecar_mod

    monkeypatch.setattr(sidecar_mod, "ensure_nacos_router_http_url", _fake_ensure)

    fake_cfg = SimpleNamespace(
        mcp=SimpleNamespace(static_servers={}),
        nacos=SimpleNamespace(
            server_addr="127.0.0.1:8848",
            username="nacos",
            password="secret",
            namespace="public",
            mcp=SimpleNamespace(
                enabled=True,
                router_name="nacos-mcp-router",
                command="uvx",
                args=["nacos-mcp-router@latest"],
                description="Nacos MCP Router",
                transport="streamable_http",
                port=18000,
                update_interval=5,
                env={"EXTRA": "1"},
            ),
        ),
    )
    monkeypatch.setattr(runtime, "get_app_config", lambda: fake_cfg)

    views = runtime.get_mcp_server_views()

    assert views["nacos-mcp-router"].source == "nacos"
    assert views["nacos-mcp-router"].config.type == "http"
    assert views["nacos-mcp-router"].config.url == "http://127.0.0.1:18000/mcp/"
    assert captured["port"] == 18000
    env = captured["params"]["env"]
    assert env["TRANSPORT_TYPE"] == "streamable_http"
    assert env["PORT"] == "18000"
    assert env["UPDATE_INTERVAL"] == "5"
    assert env["EXTRA"] == "1"
    assert env["NACOS_PASSWORD"] == "secret"


def test_nacos_router_sidecar_uses_configured_startup_timeout(monkeypatch):
    import deerflow.mcp.router_sidecar as sidecar_mod

    captured: dict[str, float] = {}

    class FakeProcess:
        pid = 12345

        def poll(self):
            return None

        def terminate(self):
            pass

    monkeypatch.setattr(sidecar_mod, "_ROUTER_PROCESS", None)
    monkeypatch.setattr(sidecar_mod, "_is_http_endpoint_reachable", lambda _url: False)
    monkeypatch.setattr(sidecar_mod, "_start_router_process", lambda *_args, **_kwargs: (FakeProcess(), "sidecar.log"))

    def _fake_wait(_base_url, timeout_seconds=None):
        captured["startup_timeout"] = timeout_seconds
        return "http://127.0.0.1:18000/mcp/"

    monkeypatch.setattr(sidecar_mod, "_wait_router_ready", _fake_wait)

    url = sidecar_mod.ensure_nacos_router_http_url(
        {"command": "uvx", "args": ["nacos-mcp-router@latest"], "startup_timeout": 180},
        port=18000,
    )

    assert url == "http://127.0.0.1:18000/mcp/"
    assert captured["startup_timeout"] == 180


def test_get_mcp_server_views_streamable_http_skips_when_sidecar_fails(monkeypatch):
    import deerflow.mcp.router_sidecar as sidecar_mod

    monkeypatch.setattr(sidecar_mod, "ensure_nacos_router_http_url", lambda *a, **kw: None)

    fake_cfg = SimpleNamespace(
        mcp=SimpleNamespace(static_servers={}),
        nacos=SimpleNamespace(
            server_addr="127.0.0.1:8848",
            username="nacos",
            password="secret",
            namespace="public",
            mcp=SimpleNamespace(
                enabled=True,
                router_name="nacos-mcp-router",
                command="uvx",
                args=["nacos-mcp-router@latest"],
                description="Nacos MCP Router",
                transport="streamable_http",
                port=18000,
                update_interval=5,
                env={},
            ),
        ),
    )
    monkeypatch.setattr(runtime, "get_app_config", lambda: fake_cfg)

    views = runtime.get_mcp_server_views()
    assert views == {}


def test_get_mcp_server_views_prefers_mcp_credentials_override(monkeypatch):
    static_srv = McpServerConfig(enabled=True, type="http", url="http://static.local/mcp", description="static")
    fake_cfg = SimpleNamespace(
        mcp=SimpleNamespace(static_servers={"shared": static_srv}),
        nacos=SimpleNamespace(
            server_addr="127.0.0.1:8848",
            username="global-user",
            password="global-pass",
            namespace="public",
            mcp=SimpleNamespace(
                enabled=True,
                router_name="shared",
                username="mcp-user",
                password="mcp-pass",
                command="uvx",
                args=["nacos-mcp-router@latest"],
                description="Nacos MCP Router",
            ),
        ),
    )
    monkeypatch.setattr(runtime, "get_app_config", lambda: fake_cfg)

    views = runtime.get_mcp_server_views()
    env = views["shared"].config.env

    assert env["NACOS_USERNAME"] == "mcp-user"
    assert env["NACOS_PASSWORD"] == "mcp-pass"


def test_write_static_mcp_servers_updates_config_yaml(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("config_version: 8\nmcp:\n  static_servers: {}\n", encoding="utf-8")

    monkeypatch.setattr(runtime.AppConfig, "resolve_config_path", staticmethod(lambda config_path=None: cfg_path))

    captured = {}

    def _fake_reload(path: str):
        captured["path"] = path
        return SimpleNamespace(
            mcp=SimpleNamespace(
                static_servers={
                    "demo": McpServerConfig(enabled=True, type="http", url="http://127.0.0.1:4000/mcp", description="demo"),
                }
            )
        )

    monkeypatch.setattr(runtime, "reload_app_config", _fake_reload)

    written = runtime.write_static_mcp_servers(
        {
            "demo": {
                "enabled": True,
                "type": "http",
                "url": "http://127.0.0.1:4000/mcp",
                "description": "demo",
            }
        }
    )

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert data["mcp"]["static_servers"]["demo"]["url"] == "http://127.0.0.1:4000/mcp"
    assert captured["path"] == str(cfg_path)
    assert "demo" in written
