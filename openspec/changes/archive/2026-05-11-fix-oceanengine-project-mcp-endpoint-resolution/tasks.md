# 任务清单

## 1. 规格与现状确认

- [x] 1.1 确认 `oceanengine-local-project-template-migration` 当前缺少项目管理 MCP endpoint Nacos 解析要求。
- [x] 1.2 对比 `oceanengine-local-unit-management` 和 `oceanengine-local-material-management` 中已归档的 Nacos endpoint 解析要求，确认项目管理需要对齐。
- [x] 1.3 梳理 `skills/custom/oceanengine-local-project/SKILL.md`、`skills/custom/oceanengine-local-project/scripts/common/mcp_client.py` 和 `tools/oceanengine_local_project_runtime/mcp_client.py` 的现有调用差异。
- [x] 1.4 在修改目标符号前完成 GitNexus 影响分析；如 GitNexus 工具不可用，记录约束并用静态调用关系补充影响评估。

## 2. 实现

- [x] 2.1 修正 `skills/custom/oceanengine-local-project/SKILL.md`，删除或改写脚本会默认直连 `http://127.0.0.1:18000/mcp/` 的说明。
- [x] 2.2 移除 `skills/custom/oceanengine-local-project/scripts/common/mcp_client.py` 对固定本机 Router 地址的默认业务兜底。
- [x] 2.3 使项目管理脚本真实 MCP 调用复用或对齐 `tools/oceanengine_local_project_runtime/mcp_client.py` 的 Nacos endpoint 解析逻辑。
- [x] 2.4 保持 `mcp_server_name`、`mcp_tool_name`、payload 映射、`mcp_wrap_request`、后置确认和失败输出结构不变。
- [x] 2.5 当 Nacos 配置缺失、`platform-agent-biz` 未注册、解析不到 endpoint、endpoint 不可达或目标 MCP tool 缺失时，返回明确中文失败诊断，不自动改用 curl、SDK、HTTP API、mock 或本机固定 Router。

## 3. 测试

- [x] 3.1 增加或调整测试，验证项目管理脚本无法加载 DeerFlow MCP tools 时，会通过 Nacos 解析真实 MCP endpoint。
- [x] 3.2 增加或调整测试，验证 Nacos 未注册 `platform-agent-biz` 时不会请求 `http://127.0.0.1:18000/mcp/`。
- [x] 3.3 增加或调整测试，验证 Nacos 返回 `backendEndpoints[]` / `frontendEndpoints[]` 时优先使用 endpoint 自身的 `path`，仅在缺少 `path` 时才使用 `remoteServerConfig.exportPath`。
- [x] 3.4 增加或调整测试，验证 streamable HTTP MCP endpoint 调用会先执行 `initialize`、再发送 `notifications/initialized`，后续 `tools/call` 携带 `Mcp-Session-Id`。

## 4. 验证

- [x] 4.1 运行 `openspec validate fix-oceanengine-project-mcp-endpoint-resolution --strict`。
- [x] 4.2 运行项目管理 MCP runtime 定向测试，例如 `cd backend && uv run pytest tests/test_oceanengine_mcp_client_runtime.py -q`，或按最终测试落点运行等价命令。
- [x] 4.3 若修改了 `skills/custom/oceanengine-local-project/scripts/**` 的公共脚本，运行对应 skill 脚本测试。
- [x] 4.4 运行变更范围检查，确认只影响项目管理 MCP endpoint 解析、相关文档和定向测试。
