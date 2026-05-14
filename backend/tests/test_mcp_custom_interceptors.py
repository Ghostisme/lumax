"""Tests for custom MCP tool interceptors loaded via extensions_config.json."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from deerflow.mcp.tools import get_mcp_tools


def _make_patches(*, interceptor_paths=None):
    """Set up mocks for get_mcp_tools() with optional custom interceptors.

    Returns a dict of patch context managers.
    """
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=[])

    extra = {}
    if interceptor_paths is not None:
        extra["mcpInterceptors"] = interceptor_paths

    return {
        "client_cls": patch(
            "langchain_mcp_adapters.client.MultiServerMCPClient",
            return_value=mock_client,
        ),
        "from_file": patch(
            "deerflow.config.extensions_config.ExtensionsConfig.from_file",
            return_value=MagicMock(
                model_extra=extra,
                get_enabled_mcp_servers=MagicMock(return_value={}),
            ),
        ),
        "build_servers": patch(
            "deerflow.mcp.tools.build_servers_config",
            return_value={"test-server": {}},
        ),
        "oauth_headers": patch(
            "deerflow.mcp.tools.get_initial_oauth_headers",
            new_callable=AsyncMock,
            return_value={},
        ),
        "oauth_interceptor": patch(
            "deerflow.mcp.tools.build_oauth_tool_interceptor",
            return_value=None,
        ),
    }


def _get_interceptors(mock_cls):
    """Extract the tool_interceptors list passed to MultiServerMCPClient."""
    kw = mock_cls.call_args
    return kw.kwargs.get("tool_interceptors") or kw[1].get("tool_interceptors", [])


def _custom_interceptors(mock_cls):
    """Return configured interceptors after DeerFlow's built-in MCP guard."""
    return _get_interceptors(mock_cls)[1:]


def test_custom_interceptor_loaded_and_appended():
    """A valid interceptor builder path is resolved, called, and appended to tool_interceptors."""

    async def fake_interceptor(request, handler):
        return await handler(request)

    def fake_builder():
        return fake_interceptor

    p = _make_patches(interceptor_paths=["my_package.auth:build_interceptor"])

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", return_value=fake_builder),
    ):
        asyncio.run(get_mcp_tools())

        interceptors = _custom_interceptors(mock_cls)
        assert len(interceptors) == 1
        assert interceptors[0] is fake_interceptor


def test_default_managed_mcp_guard_interceptor_blocks_direct_router_use_tool():
    p = _make_patches()

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
    ):
        asyncio.run(get_mcp_tools())

        interceptors = _get_interceptors(mock_cls)
        request = SimpleNamespace(
            server_name="nacos-mcp-router",
            name="use_tool",
            args={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localProjectDetail",
                "params": "{}",
            },
        )
        handler = AsyncMock(return_value=object())

        try:
            asyncio.run(interceptors[0](request, handler))
        except PermissionError as exc:
            assert "oceanengine_local_project" in str(exc)
        else:
            raise AssertionError("direct managed MCP router call was not blocked")

        handler.assert_not_awaited()


def test_managed_mcp_guard_preserves_original_arguments_in_project_guidance():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localAwemeAuthorizedGet",
                "params": (
                    '{"localAccountId":1854708763953159,'
                    '"marketingGoal":"LIVE",'
                    '"searchKeyWord":"34162141808",'
                    '"page":1,'
                    '"pageSize":5}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "oceanengine_local_project" in message
    assert "list-authorized-awemes" in message
    assert "34162141808" in message
    assert "341621408" not in message
    assert '"filtering": {"search_key_word": "34162141808"}' in message


def test_managed_mcp_guard_preserves_custom_audience_arguments_in_project_guidance():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localCustomAudienceGet",
                "params": (
                    '{"localAccountId":1854708763953159,'
                    '"tagsType":"SYS_RECOMMEND",'
                    '"page":2,'
                    '"pageSize":1001}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "oceanengine_local_project" in message
    assert "list-custom-audiences" in message
    assert "SYS_RECOMMEND" in message
    assert "1001" in message
    assert '"tags_type": "SYS_RECOMMEND"' in message
    assert '"page_size": 1001' in message


def test_managed_mcp_guard_tells_project_requests_to_read_skill_before_native_tool():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localCustomAudienceGet",
                "params": (
                    '{"localAccountId":1854708763953159,'
                    '"tagsType":"CUSTOM",'
                    '"page":1,'
                    '"pageSize":5}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "先调用 read_file 读取 /mnt/skills/custom/oceanengine-local-project/SKILL.md" in message
    assert "理解项目管理接口导航和 capability 规则后" in message
    assert "tool=oceanengine_local_project" in message
    assert "capability=list-custom-audiences" in message


def test_managed_mcp_guard_preserves_multi_poi_arguments_in_project_guidance():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localMultiPoiIdPoiIdsGet",
                "params": (
                    '{"localAccountId":1854708763953159,'
                    '"multiPoiIds":[6932952586303604740],'
                    '"needEnable":true}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "oceanengine_local_project" in message
    assert "get-poi-ids-by-multi-poi-id" in message
    assert "6932952586303604740" in message
    assert '"multi_poi_ids": [6932952586303604740]' in message
    assert '"need_enable": true' in message


def test_managed_mcp_guard_preserves_tool_pack_arguments_in_project_guidance():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localToolPackListGet",
                "params": (
                    '{"local_account_id":1854708763953159,'
                    '"delivery_goal":"POI",'
                    '"poi_ids":[6932952586303604740],'
                    '"intelligent_selection_mode":"INTELLIGENT_SELECTION_MODE_OFF",'
                    '"page":1,'
                    '"page_size":5}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "先调用 read_file 读取 /mnt/skills/custom/oceanengine-local-project/SKILL.md" in message
    assert "list-tool-packs" in message
    assert "dry_run=false" in message
    assert '"local_account_id": 1854708763953159' in message
    assert '"poi_ids": [6932952586303604740]' in message
    assert '"intelligent_selection_mode": "INTELLIGENT_SELECTION_MODE_OFF"' in message
    assert '"page_size": 5' in message


def test_managed_mcp_guard_preserves_market_page_detail_arguments_in_project_guidance():
    from tools.managed_mcp_guard import guard_managed_mcp_tool_call

    try:
        guard_managed_mcp_tool_call(
            tool_name="nacos-mcp-router_use_tool",
            arguments={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localMarketPageGet",
                "params": (
                    '{"localAccountId":1854708763953159,'
                    '"marketPageIds":[7628817210925580351]}'
                ),
            },
        )
    except PermissionError as exc:
        message = str(exc)
    else:
        raise AssertionError("direct managed MCP router call was not blocked")

    assert "先调用 read_file 读取 /mnt/skills/custom/oceanengine-local-project/SKILL.md" in message
    assert "get-market-page-detail" in message
    assert "dry_run=false" in message
    assert '"local_account_id": 1854708763953159' in message
    assert '"market_page_ids": [7628817210925580351]' in message


def test_default_managed_mcp_guard_interceptor_allows_business_tool_context():
    from tools.managed_mcp_guard import allow_managed_mcp_calls

    p = _make_patches()

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
    ):
        asyncio.run(get_mcp_tools())

        interceptors = _get_interceptors(mock_cls)
        request = SimpleNamespace(
            server_name="nacos-mcp-router",
            name="use_tool",
            args={
                "mcp_server_name": "platform-agent-biz",
                "mcp_tool_name": "localProjectDetail",
                "params": "{}",
            },
        )
        expected = object()
        handler = AsyncMock(return_value=expected)

        with allow_managed_mcp_calls("oceanengine_local_project"):
            result = asyncio.run(interceptors[0](request, handler))

        assert result is expected
        handler.assert_awaited_once_with(request)


def test_multiple_custom_interceptors():
    """Multiple interceptor paths are all loaded in order."""

    async def interceptor_a(request, handler):
        return await handler(request)

    async def interceptor_b(request, handler):
        return await handler(request)

    builders = {
        "pkg.a:build_a": lambda: interceptor_a,
        "pkg.b:build_b": lambda: interceptor_b,
    }

    p = _make_patches(interceptor_paths=["pkg.a:build_a", "pkg.b:build_b"])

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", side_effect=lambda path: builders[path]),
    ):
        asyncio.run(get_mcp_tools())

        interceptors = _custom_interceptors(mock_cls)
        assert len(interceptors) == 2
        assert interceptors[0] is interceptor_a
        assert interceptors[1] is interceptor_b


def test_custom_interceptor_builder_returning_none_is_skipped():
    """If a builder returns None, it is not appended to the interceptor list."""
    p = _make_patches(interceptor_paths=["pkg.noop:build_noop"])

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", return_value=lambda: None),
    ):
        asyncio.run(get_mcp_tools())

        assert len(_custom_interceptors(mock_cls)) == 0


def test_custom_interceptor_resolve_error_logs_warning_and_continues():
    """A broken interceptor path logs a warning and does not block tool loading."""
    p = _make_patches(interceptor_paths=["broken.path:does_not_exist"])

    with (
        p["client_cls"],
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", side_effect=ImportError("no such module")),
        patch("deerflow.mcp.tools.logger.warning") as mock_warn,
    ):
        tools = asyncio.run(get_mcp_tools())

        assert tools == []
        mock_warn.assert_called_once()
        assert "broken.path:does_not_exist" in mock_warn.call_args[0][0]


def test_custom_interceptor_builder_exception_logs_warning_and_continues():
    """If the builder function itself raises, the error is caught and logged."""

    def exploding_builder():
        raise RuntimeError("builder exploded")

    p = _make_patches(interceptor_paths=["pkg.bad:exploding_builder"])

    with (
        p["client_cls"],
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", return_value=exploding_builder),
        patch("deerflow.mcp.tools.logger.warning") as mock_warn,
    ):
        tools = asyncio.run(get_mcp_tools())

        assert tools == []
        mock_warn.assert_called_once()
        assert "pkg.bad:exploding_builder" in mock_warn.call_args[0][0]


def test_no_mcp_interceptors_field_is_safe():
    """When mcpInterceptors is absent from config, no interceptors are added."""
    p = _make_patches(interceptor_paths=None)

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
    ):
        asyncio.run(get_mcp_tools())

        assert len(_custom_interceptors(mock_cls)) == 0


def test_custom_interceptor_coexists_with_oauth_interceptor():
    """Custom interceptors are appended after the OAuth interceptor."""

    async def oauth_fn(request, handler):
        return await handler(request)

    async def custom_fn(request, handler):
        return await handler(request)

    p = _make_patches(interceptor_paths=["pkg.custom:build_custom"])

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        patch("deerflow.mcp.tools.build_oauth_tool_interceptor", return_value=oauth_fn),
        patch("deerflow.mcp.tools.resolve_variable", return_value=lambda: custom_fn),
    ):
        asyncio.run(get_mcp_tools())

        interceptors = _custom_interceptors(mock_cls)
        assert len(interceptors) == 2
        assert interceptors[0] is oauth_fn
        assert interceptors[1] is custom_fn


def test_mcp_interceptors_single_string_is_normalized():
    """A single string value for mcpInterceptors is normalized to a list."""

    async def fake_interceptor(request, handler):
        return await handler(request)

    p = _make_patches(interceptor_paths="pkg.single:build_it")

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", return_value=lambda: fake_interceptor),
    ):
        asyncio.run(get_mcp_tools())

        assert len(_custom_interceptors(mock_cls)) == 1


def test_mcp_interceptors_invalid_type_logs_warning():
    """A non-list, non-string value for mcpInterceptors logs a warning and is skipped."""
    p = _make_patches(interceptor_paths=42)

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.logger.warning") as mock_warn,
    ):
        asyncio.run(get_mcp_tools())

        assert len(_custom_interceptors(mock_cls)) == 0
        mock_warn.assert_called_once()
        assert "must be a list" in mock_warn.call_args[0][0]


def test_custom_interceptor_non_callable_return_logs_warning():
    """If a builder returns a non-callable value, it is skipped with a warning."""
    p = _make_patches(interceptor_paths=["pkg.bad:returns_string"])

    with (
        p["client_cls"] as mock_cls,
        p["from_file"],
        p["build_servers"],
        p["oauth_headers"],
        p["oauth_interceptor"],
        patch("deerflow.mcp.tools.resolve_variable", return_value=lambda: "not_a_callable"),
        patch("deerflow.mcp.tools.logger.warning") as mock_warn,
    ):
        asyncio.run(get_mcp_tools())

        assert len(_custom_interceptors(mock_cls)) == 0
        mock_warn.assert_called_once()
        assert "non-callable" in mock_warn.call_args[0][0]
