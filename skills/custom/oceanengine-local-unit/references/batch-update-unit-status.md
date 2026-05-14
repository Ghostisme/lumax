# 批量更新单元状态

- path: `/open_api/v3.0/local/promotion/status/update/`
- MCP: `platform-agent-biz/localUnitStatusBatchUpdate`
- capability: `batch-update-unit-status`

## 请求字段摘要

必填字段：`local_account_id`、`data`、`data[].promotion_id`、`data[].opt_status`。

`data` 为批量更新单元状态列表，长度限制 `1-50`。

`opt_status` 可选值：
- `ENABLE`: 启用单元
- `PAUSED`: 暂停单元

本地工具会按 `request` 包装，并将 `data[]` 内字段转换为 camelCase。

## 响应字段

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `number` | 返回码；返回码,详见 【附录-返回码】 |
| `message` | `string` | 返回信息；返回信息,详见 【附录-返回码】 |
| `data` | `json` | json返回值 |
| `data.promotion_ids[]` | `number[]` | 更新成功的单元ID |
| `data.errors[]` | `object[]` | 更新失败的单元列表 |
| `data.errors[].promotion_id` | `number` | 单元ID |
| `data.errors[].error_message` | `string` | 失败信息 |
| `request_id` | `string` | 请求日志id |
