import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SKILL_ROOT.parents[2]
SCRIPTS_ROOT = SKILL_ROOT / "scripts"

for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import mcp_client
from tools.oceanengine_local_project_runtime import mcp_client as runtime_mcp_client


TEST_SPEC = {
    "title": "获取项目列表",
    "path": "/open_api/v3.0/local/project/list/",
    "mcp_tool_name": "localProjectList",
}


class OceanEngineProjectMcpClientTest(unittest.TestCase):
    def _raise_mcp_tools_unavailable(self, coro):
        coro.close()
        raise runtime_mcp_client.McpToolError("MCP tools unavailable")

    def test_invoke_endpoint_without_loaded_tools_resolves_nacos_endpoint_not_localhost_router(self):
        calls: list[tuple[str, str, dict, int]] = []

        def fake_call_mcp_tool_endpoint(endpoint: str, tool_name: str, arguments: dict, *, request_id: int):
            calls.append((endpoint, tool_name, arguments, request_id))
            return [{"type": "text", "text": '{"code":0,"data":{"projectList":[]}}'}]

        with (
            patch.object(runtime_mcp_client, "find_repo_root", return_value=Path("/tmp/repo")),
            patch.object(runtime_mcp_client, "load_config", return_value={"nacos": {"server-addr": "nacos.example:8848"}}),
            patch.object(runtime_mcp_client, "_load_mcp_tools", side_effect=runtime_mcp_client.McpToolError("MCP tools unavailable")),
            patch.object(runtime_mcp_client, "_resolve_nacos_mcp_endpoint", return_value="http://10.0.0.8:8010/mcp"),
            patch.object(runtime_mcp_client, "_call_mcp_tool_endpoint", side_effect=fake_call_mcp_tool_endpoint),
            patch(
                "tools.oceanengine_local_project_runtime.mcp_client.asyncio.run",
                side_effect=self._raise_mcp_tools_unavailable,
            ),
            patch.object(mcp_client, "_call_router_tool", side_effect=AssertionError("不应请求固定本机 Router")),
        ):
            result = mcp_client.invoke_endpoint(TEST_SPEC, {"local_account_id": 1})

        self.assertEqual("platform-agent-biz:localProjectList", result["tool_name"])
        self.assertEqual([("http://10.0.0.8:8010/mcp", "localProjectList", {"localAccountId": 1}, 2)], calls)

    def test_nacos_missing_server_does_not_fallback_to_localhost_router(self):
        with (
            patch.object(runtime_mcp_client, "find_repo_root", return_value=Path("/tmp/repo")),
            patch.object(runtime_mcp_client, "load_config", return_value={"nacos": {"server-addr": "nacos.example:8848"}}),
            patch.object(runtime_mcp_client, "_load_mcp_tools", side_effect=runtime_mcp_client.McpToolError("MCP tools unavailable")),
            patch.object(runtime_mcp_client, "_resolve_nacos_mcp_endpoint", side_effect=runtime_mcp_client.McpToolError("Nacos 中不存在 MCP server platform-agent-biz")),
            patch(
                "tools.oceanengine_local_project_runtime.mcp_client.asyncio.run",
                side_effect=self._raise_mcp_tools_unavailable,
            ),
            patch.object(mcp_client, "_call_router_tool", side_effect=AssertionError("不应请求固定本机 Router")),
        ):
            with self.assertRaisesRegex(mcp_client.McpToolError, "Nacos 中不存在 MCP server platform-agent-biz"):
                mcp_client.invoke_endpoint(TEST_SPEC, {"local_account_id": 1})


if __name__ == "__main__":
    unittest.main()
