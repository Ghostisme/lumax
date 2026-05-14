# 任务清单

## 1. 设计与影响分析

- [x] 1.1 梳理 `mcp_client.py` 中本机 Router 兜底、DeerFlow MCP tools 加载和 Nacos server/tool 查找的现有链路。
- [x] 1.2 刷新 GitNexus 索引，并对计划修改的 `invoke_endpoint`、`invoke_endpoint_via_router`、`_router_url` 或替代解析函数执行 upstream impact analysis。
- [x] 1.3 若 GitNexus MCP 工具不可用，记录限制并用 CLI 状态、静态调用点和测试覆盖说明影响范围。
- [x] 1.4 明确失败口径：Nacos 未注册、目标 tool 未注册、解析到的 MCP endpoint 不可达、配置缺失分别返回中文诊断。

## 2. 实现

- [x] 2.1 移除 OceanEngine 业务工具对 `http://127.0.0.1:18000/mcp/` 的默认业务兜底依赖。
- [x] 2.2 实现或复用从 Nacos / DeerFlow Nacos MCP 配置解析 `platform-agent-biz` 实际 MCP endpoint 的逻辑。
- [x] 2.3 解析成功后直接调用解析到的 MCP endpoint；端点不通时返回失败，不自动切换到本机 Router、curl、SDK、HTTP API 或 mock。
- [x] 2.4 保持本地参数校验、MCP payload 构造、受管理 MCP guard、后置确认和用户可见输出清洗行为不变。
- [x] 2.5 确保素材、单元、项目三类原生业务工具仍只通过根目录 `tools.oceanengine_local_*` 主路径注册和引用。

## 3. 测试

- [x] 3.1 增加测试覆盖：Nacos 未返回 `platform-agent-biz` 时，不请求本机 `127.0.0.1:18000`，并返回中文失败。
- [x] 3.2 增加测试覆盖：Nacos 返回目标 server 但目标 tool 缺失时，返回中文失败且不改用其它调用路径。
- [x] 3.3 增加测试覆盖：Nacos 返回 endpoint 但连接失败时，返回中文失败且不声明 MCP 调用成功。
- [x] 3.4 增加测试覆盖：解析成功时，payload 仍按规则映射，受管理 MCP guard 仍生效。

## 4. 验证

- [x] 4.1 运行后端定向测试，覆盖 OceanEngine MCP client runtime 和素材/单元原生业务工具。
- [x] 4.2 运行 `openspec validate fix-oceanengine-nacos-mcp-resolution --strict`。
- [x] 4.3 运行 `gitnexus_detect_changes()` 或可用替代检查，确认影响范围符合预期。
- [x] 4.4 汇总实际修改文件、测试结果和剩余环境风险。
