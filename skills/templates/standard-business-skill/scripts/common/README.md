# 公共脚本说明

标准业务 skill 的公共脚本应提供以下能力：

- `validators.py`：读取 `rules/*.json`，执行必填、类型、枚举、条件依赖、互斥、范围和批量项校验。
- `mcp_client.py`：根据规则配置中的 `mcp.server`、`mcp.tool`、`mcp.match_tokens`、`field_map` 和 `value_maps` 选择并调用 MCP 工具。
- `response.py`：统一输出 `success`、`message`、`data`、`errors`、`tool_name`、`request_id`、`retry_count`。
- `runner.py`：封装 endpoint 脚本的输入读取、dry-run、本地校验、MCP 调用和后置确认流程。

公共脚本可以从现有业务 skill 中复制后收敛，但新增能力前应优先通过规则配置表达差异。
