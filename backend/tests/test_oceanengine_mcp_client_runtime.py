from unittest.mock import patch

import pytest

from tools.oceanengine_local_project_runtime import mcp_client


TEST_SPEC = {
    "path": "/open_api/v3.0/local/project/list/",
    "title": "获取项目列表",
    "mcp_tool_name": "localProjectList",
    "mcp_wrap_request": False,
}


def test_load_config_prefers_runtime_config_path(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "config.yaml").write_text(
        "nacos:\n"
        "  server-addr: dev-nacos.example:8848\n"
        "  namespace: dev\n",
        encoding="utf-8",
    )
    runtime_config = tmp_path / "runtime-public-config.yaml"
    runtime_config.write_text(
        "nacos:\n"
        "  server-addr: 127.0.0.1:8848\n"
        "  namespace: public\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DEER_FLOW_CONFIG_PATH", str(runtime_config))

    config = mcp_client.load_config(repo_root)

    assert config["nacos"]["server-addr"] == "127.0.0.1:8848"
    assert config["nacos"]["namespace"] == "public"


def raise_mcp_tools_unavailable(coro):
    coro.close()
    raise mcp_client.McpToolError("MCP tools unavailable")


def test_invoke_endpoint_via_nacos_resolves_endpoint_before_calling_tool():
    calls: list[tuple[str, str, dict, int]] = []

    def fake_call_mcp_tool_endpoint(endpoint: str, tool_name: str, arguments: dict, *, request_id: int):
        calls.append((endpoint, tool_name, arguments, request_id))
        return [{"type": "text", "text": '{"code":0,"data":{"list":[]}}'}]

    with (
        patch.object(mcp_client, "find_repo_root", return_value=mcp_client.Path("/tmp/repo")),
        patch.object(mcp_client, "load_config", return_value={"nacos": {"server-addr": "nacos.example:8848"}}),
        patch.object(mcp_client, "_resolve_nacos_mcp_endpoint", return_value="http://10.0.0.8:8010/mcp"),
        patch.object(mcp_client, "_call_mcp_tool_endpoint", side_effect=fake_call_mcp_tool_endpoint),
    ):
        result = mcp_client.invoke_endpoint_via_nacos(TEST_SPEC, {"local_account_id": 1}, "platform-agent-biz")

    assert result["tool_name"] == "platform-agent-biz:localProjectList"
    assert calls == [("http://10.0.0.8:8010/mcp", "localProjectList", {"localAccountId": 1}, 2)]


def test_invoke_endpoint_keeps_loaded_router_tool_path_without_local_install_call():
    router_calls: list[dict] = []

    class FakeRouterTool:
        name = "nacos-mcp-router_use_tool"

        def invoke(self, payload: dict):
            router_calls.append(payload)
            return [{"type": "text", "text": '{"code":0,"data":{"list":[]}}'}]

    with (
        patch.object(mcp_client, "find_repo_root", return_value=mcp_client.Path("/tmp/repo")),
        patch.object(mcp_client, "load_config", return_value={}),
        patch.object(mcp_client, "_load_mcp_tools", return_value=[FakeRouterTool()]),
        patch("tools.oceanengine_local_project_runtime.mcp_client.asyncio.run", side_effect=lambda coro: coro.close() or [FakeRouterTool()]),
    ):
        result = mcp_client.invoke_endpoint(TEST_SPEC, {"local_account_id": 1})

    assert result["tool_name"] == "nacos-mcp-router_use_tool:localProjectList"
    assert router_calls == [
        {
            "mcp_server_name": "platform-agent-biz",
            "mcp_tool_name": "localProjectList",
            "params": '{"localAccountId": 1}',
        }
    ]


def test_invoke_endpoint_without_loaded_tools_resolves_nacos_endpoint_not_localhost_router():
    calls: list[tuple[str, str, dict, int]] = []

    def fake_call_mcp_tool_endpoint(endpoint: str, tool_name: str, arguments: dict, *, request_id: int):
        calls.append((endpoint, tool_name, arguments, request_id))
        return [{"type": "text", "text": '{"code":0,"data":{"list":[]}}'}]

    with (
        patch.object(mcp_client, "find_repo_root", return_value=mcp_client.Path("/tmp/repo")),
        patch.object(mcp_client, "load_config", return_value={"nacos": {"server-addr": "nacos.example:8848"}}),
        patch.object(mcp_client, "_load_mcp_tools", side_effect=mcp_client.McpToolError("MCP tools unavailable")),
        patch.object(mcp_client, "_resolve_nacos_mcp_endpoint", return_value="http://10.0.0.8:8010/mcp"),
        patch.object(mcp_client, "_call_mcp_tool_endpoint", side_effect=fake_call_mcp_tool_endpoint),
        patch("tools.oceanengine_local_project_runtime.mcp_client.asyncio.run", side_effect=raise_mcp_tools_unavailable),
    ):
        result = mcp_client.invoke_endpoint(TEST_SPEC, {"local_account_id": 1})

    assert result["tool_name"] == "platform-agent-biz:localProjectList"
    assert calls[0][0] == "http://10.0.0.8:8010/mcp"


def test_resolve_nacos_mcp_endpoint_raises_when_server_missing():
    with (
        patch.object(mcp_client, "_nacos_get_json", return_value={"code": 0, "message": "success", "data": None}),
    ):
        with pytest.raises(mcp_client.McpToolError, match="Nacos 中不存在"):
            mcp_client._resolve_nacos_mcp_endpoint({"nacos": {"server-addr": "nacos.example:8848"}}, "platform-agent-biz")


def test_resolve_nacos_mcp_endpoint_raises_when_no_instance_endpoint():
    def fake_nacos_get_json(config: dict, path: str, params: dict):
        if path == "nacos/v3/admin/ai/mcp":
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "name": "platform-agent-biz",
                    "remoteServerConfig": {
                        "serviceRef": {
                            "namespaceId": "public",
                            "groupName": "DEFAULT_GROUP",
                            "serviceName": "platform-agent-biz::1.0.0",
                        },
                        "exportPath": "/mcp",
                    },
                },
            }
        if path == "nacos/v3/client/ns/instance/list":
            return {"code": 0, "message": "success", "data": []}
        raise AssertionError(path)

    with patch.object(mcp_client, "_nacos_get_json", side_effect=fake_nacos_get_json):
        with pytest.raises(mcp_client.McpToolError, match="未解析到可用的实例地址"):
            mcp_client._resolve_nacos_mcp_endpoint({"nacos": {"server-addr": "nacos.example:8848"}}, "platform-agent-biz")


def test_resolve_nacos_mcp_endpoint_builds_endpoint_from_instance_and_export_path(monkeypatch):
    monkeypatch.delenv("NACOS_NAMESPACE", raising=False)
    seen_params: list[dict] = []

    def fake_nacos_get_json(config: dict, path: str, params: dict):
        seen_params.append(params)
        if path == "nacos/v3/admin/ai/mcp":
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "name": "platform-agent-biz",
                    "remoteServerConfig": {
                        "serviceRef": {"serviceName": "platform-agent-biz::1.0.0"},
                        "exportPath": "/mcp",
                    },
                },
            }
        if path == "nacos/v3/client/ns/instance/list":
            return {"code": 0, "message": "success", "data": [{"ip": "10.0.0.8", "port": 8010}]}
        raise AssertionError(path)

    with patch.object(mcp_client, "_nacos_get_json", side_effect=fake_nacos_get_json):
        endpoint = mcp_client._resolve_nacos_mcp_endpoint({"nacos": {"server-addr": "nacos.example:8848", "namespace": "dev"}}, "platform-agent-biz")

    assert endpoint == "http://10.0.0.8:8010/mcp"
    assert seen_params[0]["namespaceId"] == "dev"


def test_resolve_nacos_mcp_endpoint_prefers_backend_endpoint_path_over_export_path():
    def fake_nacos_get_json(config: dict, path: str, params: dict):
        assert path == "nacos/v3/admin/ai/mcp"
        return {
            "code": 0,
            "message": "success",
            "data": {
                "name": "platform-agent-biz",
                "remoteServerConfig": {
                    "serviceRef": {"serviceName": "platform-agent-biz::1.0.0"},
                    "exportPath": "/wrong-default",
                },
                "backendEndpoints": [
                    {
                        "address": "10.0.0.8",
                        "port": 8010,
                        "path": "/real-mcp",
                    }
                ],
            },
        }

    with patch.object(mcp_client, "_nacos_get_json", side_effect=fake_nacos_get_json):
        endpoint = mcp_client._resolve_nacos_mcp_endpoint({"nacos": {"server-addr": "nacos.example:8848", "namespace": "dev"}}, "platform-agent-biz")

    assert endpoint == "http://10.0.0.8:8010/real-mcp"


def test_nacos_endpoint_unreachable_raises_diagnostic():
    def fake_urlopen(*args, **kwargs):
        raise OSError("connection refused")

    with patch.object(mcp_client.urllib.request, "urlopen", side_effect=fake_urlopen):
        with pytest.raises(mcp_client.McpToolError, match="MCP 服务端点不可达"):
            mcp_client._call_jsonrpc("http://10.0.0.8:8010/mcp", "tools/call", {}, request_id=2)


def test_call_mcp_tool_endpoint_initializes_session_before_tool_call():
    seen: list[tuple[str, str | None, str]] = []

    class FakeResponse:
        status = 200

        def __init__(self, text: str, session_id: str | None = None):
            self._text = text
            self.headers = {}
            if session_id:
                self.headers["Mcp-Session-Id"] = session_id

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._text.encode("utf-8")

    def fake_urlopen(request, timeout=60):
        payload = mcp_client.json.loads(request.data.decode("utf-8"))
        seen.append((payload["method"], request.headers.get("Mcp-session-id"), request.full_url))
        if payload["method"] == "initialize":
            return FakeResponse('{"jsonrpc":"2.0","id":1,"result":{}}', "sid-1")
        if payload["method"] == "notifications/initialized":
            return FakeResponse("")
        if payload["method"] == "tools/call":
            return FakeResponse('{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"ok"}]}}')
        raise AssertionError(payload["method"])

    with patch.object(mcp_client.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = mcp_client._call_mcp_tool_endpoint("http://10.0.0.8:8010/mcp", "localProjectList", {"localAccountId": 1}, request_id=2)

    assert result == [{"type": "text", "text": "ok"}]
    assert seen == [
        ("initialize", None, "http://10.0.0.8:8010/mcp"),
        ("notifications/initialized", "sid-1", "http://10.0.0.8:8010/mcp"),
        ("tools/call", "sid-1", "http://10.0.0.8:8010/mcp"),
    ]


def test_router_tool_result_server_not_found_text_falls_back_to_nacos_endpoint():
    calls: list[tuple[str, str, dict, int]] = []

    class FakeRouterTool:
        name = "nacos-mcp-router_use_tool"

        def invoke(self, payload: dict):
            return [{"type": "text", "text": "mcp server not found, use search_mcp_server to get mcp servers"}]

    def fake_call_mcp_tool_endpoint(endpoint: str, tool_name: str, arguments: dict, *, request_id: int):
        calls.append((endpoint, tool_name, arguments, request_id))
        return [{"type": "text", "text": '{"code":0,"data":{"list":[]}}'}]

    with (
        patch.object(mcp_client, "find_repo_root", return_value=mcp_client.Path("/tmp/repo")),
        patch.object(mcp_client, "load_config", return_value={"nacos": {"server-addr": "nacos.example:8848"}}),
        patch.object(mcp_client, "_load_mcp_tools", return_value=[FakeRouterTool()]),
        patch.object(mcp_client, "_resolve_nacos_mcp_endpoint", return_value="http://10.0.0.8:8010/mcp"),
        patch.object(mcp_client, "_call_mcp_tool_endpoint", side_effect=fake_call_mcp_tool_endpoint),
        patch("tools.oceanengine_local_project_runtime.mcp_client.asyncio.run", side_effect=lambda coro: coro.close() or [FakeRouterTool()]),
    ):
        result = mcp_client.invoke_endpoint(TEST_SPEC, {"local_account_id": 1})

    assert result["tool_name"] == "platform-agent-biz:localProjectList"
    assert calls == [("http://10.0.0.8:8010/mcp", "localProjectList", {"localAccountId": 1}, 2)]
