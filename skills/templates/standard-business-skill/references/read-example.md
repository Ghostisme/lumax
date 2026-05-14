# 读取示例

用于说明读取类能力的 reference 写法。读取类接口只返回查询结果和摘要，不需要后置确认。

## 用户输入

| 字段 | 中文名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `account_id` | 账户 ID | integer | 是 | 业务账户标识 |
| `status` | 状态 | string | 否 | 允许值见 `rules/read-example.json` |

## 示例

```json
{
  "account_id": 123456,
  "status": "ENABLE"
}
```
