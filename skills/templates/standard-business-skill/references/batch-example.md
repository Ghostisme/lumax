# 批量示例

用于说明批量能力的 reference 写法。批量接口必须能把错误定位到具体项。

## 用户输入

| 字段 | 中文名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `account_id` | 账户 ID | integer | 是 | 业务账户标识 |
| `items` | 批量项 | array | 是 | 每项结构见规则配置 |

## 示例

```json
{
  "account_id": 123456,
  "items": [
    {
      "resource_id": 9001,
      "status": "ENABLE"
    }
  ]
}
```
