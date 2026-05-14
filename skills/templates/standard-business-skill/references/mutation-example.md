# 增删改示例

用于说明增删改类能力的 reference 写法。增删改类接口必须在规则配置中启用 `confirmation`，并通过后置查询确认目标状态。

## 用户输入

| 字段 | 中文名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `account_id` | 账户 ID | integer | 是 | 业务账户标识 |
| `resource_id` | 资源 ID | integer | 是 | 被修改的资源 |
| `status` | 目标状态 | string | 是 | 允许值见 `rules/mutation-example.json` |

## 示例

```json
{
  "account_id": 123456,
  "resource_id": 9001,
  "status": "DISABLE"
}
```
