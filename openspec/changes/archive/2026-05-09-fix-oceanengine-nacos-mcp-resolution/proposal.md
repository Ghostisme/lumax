# 修正 OceanEngine 本地推 MCP Nacos 解析链路

## 背景

当前 OceanEngine 本地推原生业务工具在 `tools/oceanengine_local_project_runtime/mcp_client.py` 中存在一条固定本机 Router 兜底链路：当 DeerFlow MCP tools 加载失败或找不到目标工具时，会默认请求 `http://127.0.0.1:18000/mcp/`，再通过 `nacos-mcp-router` 的 `add_mcp_server` / `use_tool` 间接调用 `platform-agent-biz`。

这与预期链路不一致。预期行为是：业务工具应先通过 Nacos 解析 `platform-agent-biz` 对应 MCP server 的实际地址、端口和路径，再调用解析到的真实 MCP 服务端点；如果 Nacos 中不存在目标 server、目标 tool 未注册，或解析到的服务端点不可达，应返回明确失败诊断，而不是继续尝试本机固定 IP、curl、SDK、HTTP API 或 mock 路径。

该问题会影响本地推素材管理和单元管理能力，也会影响复用同一公共运行时的项目管理能力。用户可见症状是 MCP 调用一直落到本机 IP，而不是使用 Nacos 注册的真实服务地址。

## 目标

- OceanEngine 原生业务工具调用 MCP 前，必须以 Nacos 注册信息或 DeerFlow 已加载的 Nacos MCP server 配置为权威来源。
- `platform-agent-biz` 的实际 MCP 地址、端口和路径必须来自 Nacos 解析结果，不得由业务工具默认写死为本机固定 Router 地址。
- 当 Nacos 解析失败、目标 MCP tool 缺失或解析到的服务端点不可达时，系统必须返回中文失败诊断。
- 本地参数校验、payload 映射、受管理 MCP guard 和用户可见清洗行为保持不变。

## 非目标

- 不修改巨量官方接口参数、枚举、响应字段或 capability 范围。
- 不新增 curl、SDK 或直连开放平台 HTTP API 的替代调用链路。
- 不绕过 `oceanengine_local_material`、`oceanengine_local_unit`、`oceanengine_local_project` 原生业务工具。
- 不修改前端展示逻辑。
- 不修复与本需求无关的 Nacos 服务注册、Java 服务启动或网络环境问题。

## 影响范围

- `tools/oceanengine_local_project_runtime/mcp_client.py`：调整 MCP endpoint 解析和调用失败策略。
- OceanEngine 本地推项目、单元、素材原生业务工具：共享公共 MCP 调用运行时，行为同步受影响。
- 后端测试：增加或调整覆盖 Nacos 解析失败、端点不可达和不再默认落到本机 Router 的用例。
- 配置诊断：错误信息需要帮助用户区分 Nacos 未注册、tool 缺失、endpoint 不可达和本地配置缺失。

## 风险与约束

- 这是 MCP 调用链路变更，若 Nacos 解析逻辑与现有运行时配置不兼容，可能导致原本依赖本机 Router 的测试或调试路径失败。
- 修改 `mcp_client.py` 中函数前必须按 GitNexus 规则执行 impact analysis；当前索引为 stale，Apply 前需先运行 `npx gitnexus analyze` 或记录工具约束。
- 若 GitNexus MCP 工具仍未在当前环境暴露，需要使用可用 CLI 或静态调用关系补充影响范围说明。
- OpenSpec Apply 阶段涉及代码变更时，必须遵守仓库现有 AGENTS 规则和受保护源码边界。
