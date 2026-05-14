# 获取可用留资组件详情

来源 URL：https://open.oceanengine.com/labels/37/docs/1848481896981834
Path：`/open_api/v3.0/local/tool_pack/detail/`
方法：`POST`
脚本：`scripts/endpoints/get_tool_pack_detail.py`

## 必填参数

- `local_account_id`：本地推投放账户ID。
- `tool_pack_id`：留资组件ID。

## 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `data.tool_pack_info` | object | 留资组件详情。 |
| `data.tool_pack_info.tool_pack_id` | number | 留资组件 id。 |
| `data.tool_pack_info.tool_pack_name` | string | 留资组件名称。 |
| `data.tool_pack_info.tool_pack_types[]` | string | 留资方式，`TOOL_TYPE_CONSULT` 私信咨询、`TOOL_TYPE_FORM` 表单预约、`TOOL_TYPE_PHONE_SMART` 电话咨询。 |
| `data.tool_pack_info.enable` | bool | 组件是否可用，不可用则创编时不支持传入。 |
| `data.tool_pack_info.enable_intelligent_selection` | bool | 是否支持优选。 |
| `request_id` | string | 请求日志 id，仅用于诊断，不面向用户展示。 |

## 输出建议

展示留资组件字段配置、状态和可投限制，用于创建或更新获取线索项目。
