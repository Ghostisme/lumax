# Lumax 模型 Token 计费改造文档

本文档只描述当前项目 `lumax` 中需要实现的 token 计费逻辑。价格配置、模型价格维护和服务端管理接口不在本文范围内。Redis 价格缓存由 `lumax-service` 已实现的模型价格缓存功能生成和刷新；当前项目 `lumax` 只消费该缓存，不负责生成和刷新。

## 1. 目标

当前项目 `lumax` 在每次模型调用结算时读取 Redis 价格缓存，按输入 token、输出 token、推理模式、缓存命中和缓存写入计算费用，并将费用字段写入 Lumax 数据表。

职责边界：

1. 当前项目 `lumax` 负责读取 Redis 价格缓存。
2. 当前项目 `lumax` 负责归一化 provider usage。
3. 当前项目 `lumax` 负责计算 `input_cost/output_cost/cache_cost/total_cost`。
4. 当前项目 `lumax` 负责直写 Lumax 数据表完成用量和费用落库。
5. `/lumax/v1/usage/report` 不作为本期计费结算链路。
6. Redis key 不包含 `businessCode`。
7. `cache_storage_price` 不参与本期实时计费。
8. `lumax-service` 已负责生成和刷新 Redis 价格缓存，当前项目 `lumax` 只消费缓存。

## 2. 模型编码契约

当前项目 `lumax` 的模型名必须直接对应 Redis 价格缓存中的模型编码：

```text
lumax model_name = Redis value modelCode
```

Redis key 使用当前项目 `lumax` settlement 中的 `model_name` 拼接：

```text
${tenantId}:lumax:model_pricing:${model_name}
0:lumax:model_pricing:${model_name}
```

如果 `model_name` 与 `modelCode` 不一致，Redis 会 miss，应视为配置错误并导致结算失败。

## 3. Redis 价格缓存格式

### 3.1 Key 规则

```text
${tenantId}:lumax:model_pricing:${modelCode}
0:lumax:model_pricing:${modelCode}
```

规则：

1. `${tenantId}:...` 是租户价格。
2. `0:...` 是全局兜底价格。
3. key 不包含 `businessCode`。
4. 租户 key miss 后允许读 `0:` key。
5. 两个 key 都 miss 时结算失败。

### 3.2 Value 结构

```json
{
  "tenantId": "2052263773707833345",
  "modelCode": "glm-5.1",
  "priceUnit": "per_1m_tokens",
  "currency": "CNY",
  "hasTieredPricing": true,
  "supportedInferenceModes": ["online", "online_low_latency", "batch"],
  "flatPrice": {
    "inputPrice": 6,
    "outputPrice": 24,
    "cacheReadPrice": 1.3,
    "cacheWritePrice": 0,
    "cacheStoragePrice": 0
  },
  "pricesByInferenceMode": {
    "online": [
      {
        "id": 1,
        "inferenceMode": "online",
        "inputLengthMin": 0,
        "inputLengthMax": 32,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 6,
        "outputPrice": 24,
        "cacheReadPrice": 1.3,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0,
        "sortOrder": 1
      }
    ]
  },
  "tiers": [
    {
      "id": 1,
      "inferenceMode": "online",
      "inputLengthMin": 0,
      "inputLengthMax": 32,
      "outputLengthMin": 0,
      "outputLengthMax": -1,
      "inputPrice": 6,
      "outputPrice": 24,
      "cacheReadPrice": 1.3,
      "cacheWritePrice": 0,
      "cacheStoragePrice": 0,
      "sortOrder": 1
    }
  ],
  "pricingRules": [
    "online 输入 [0,32k) = 6 元 / 百万 token，输出 = 24 元 / 百万 token，缓存命中 = 1.3 元 / 百万 token"
  ],
  "updatedAt": "2026-05-01T00:00:00.000Z"
}
```

权威关系：

1. `tiers` 是权威分段价格明细。
2. `pricesByInferenceMode` 是由 `tiers` 派生的索引。
3. `pricingRules` 仅用于人工查看，不参与计算。
4. `flatPrice` 仅用于非分段模型。

## 4. 分段规则

分段单位统一为 `k token`，`1k = 1000 token`。

区间统一使用左闭右开：

```text
[0,32)
[32,128)
[128,256)
[32,-1)  # -1 表示无上限
```

边界示例：

| token 数 | 命中分段 |
| ---: | --- |
| `31_999` | `[0,32)` |
| `32_000` | `[32,128)` 或 `[32,-1)` |
| `127_999` | `[32,128)` |
| `128_000` | `[128,256)` |

实现时不要使用 `ceil(tokens / 1000)` 做分段判断。建议直接用 token 数比较，或使用 `tokens / 1000` 按左闭右开判断。

## 5. 推理模式策略

支持的推理模式：

```text
online
online_low_latency
batch
```

规则：

1. 当前项目 `lumax` 使用 settlement 中的 `inference_mode` 命中对应价格。
2. 当前项目 `lumax` 未传 `inference_mode` 时默认使用 `online`。
3. `inference_mode` 必须在 `supportedInferenceModes` 内，否则结算失败。
4. 不支持的推理模式不能回退到 `flatPrice`。
5. 不同推理模式价格是否相同完全由 Redis value 决定。

## 6. 费用计算规则

金额计算必须使用 Python `Decimal`，禁止使用 `float`。

计费单位：

```text
per_1m_tokens => unit = 1_000_000
per_1k_tokens => unit = 1_000
```

归一化后的 token 字段：

| 字段 | 含义 |
| --- | --- |
| `tokensIn` | 完整输入 token，包含普通输入、缓存命中输入、缓存写入输入。 |
| `tokensOut` | 完整输出 token，归一化后应包含 reasoning tokens。 |
| `cacheReadTokens` | 缓存命中 token。 |
| `cacheWriteTokens` | 缓存写入 token。 |
| `reasoningTokens` | 推理 token。若已包含在 `tokensOut` 中，仅用于边界兜底。 |

费用公式：

```text
billableInputTokens = max(tokensIn - cacheReadTokens - cacheWriteTokens, 0)
outputBillableTokens = max(tokensOut, reasoningTokens)

inputCost = Decimal(billableInputTokens) * inputPrice / Decimal(unit)
outputCost = Decimal(outputBillableTokens) * outputPrice / Decimal(unit)
cacheCost = Decimal(cacheReadTokens) * cacheReadPrice / Decimal(unit)
          + Decimal(cacheWriteTokens) * cacheWritePrice / Decimal(unit)
totalCost = inputCost + outputCost + cacheCost
```

说明：

1. `cacheWritePrice` 表示缓存写入 token 的完整单价，不是普通输入价上的增量加价。
2. `cache_storage_price` 不参与本期实时计费。
3. Redis 中读取到的价格必须先用字符串转 `Decimal`，例如 `Decimal(str(inputPrice))`。
4. token 数保持 `int`。
5. 每个费用字段写库前统一量化到 6 位小数：`quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)`。
6. `tokensTotal` 只用于 token 额度口径，不用于费用反推。
7. 本期只支持单币种 `CNY`。如果 Redis value 中 `currency` 不是 `CNY`，必须按配置错误处理并终止结算。

## 7. 费用字段说明

| 字段 | 来源 | 类型 | 说明 |
| --- | --- | --- | --- |
| `tokensIn` | lumax settlement | int | 本次模型调用完整输入 token。 |
| `tokensOut` | lumax settlement | int | 本次模型调用完整输出 token。 |
| `tokensTotal` | lumax settlement | int | 本次模型调用总 token，用于额度扣减。 |
| `cacheReadTokens` | lumax settlement | int | 缓存命中 token。 |
| `cacheWriteTokens` | lumax settlement | int | 缓存写入 token。 |
| `reasoningTokens` | lumax settlement | int | 推理 token。 |
| `inputCost` | lumax 计算 | Decimal | 输入费用，写入 `lumax_token_consumption.input_cost`。 |
| `outputCost` | lumax 计算 | Decimal | 输出费用，写入 `lumax_token_consumption.output_cost`。 |
| `cacheCost` | lumax 计算 | Decimal | 缓存费用，写入 `lumax_token_consumption.cache_cost`。 |
| `totalCost` | lumax 计算 | Decimal | 总费用，写入 `lumax_token_consumption.total_cost` 并累计到会话和日统计。 |
| `priceTierId` | Redis matched tier | int/null | 命中的分段价格 ID，走 `flatPrice` 时为 `null`。 |
| `priceSnapshot` | Redis pricing | object | 本次结算实际使用的价格快照，写入 `lumax_token_consumption.price_snapshot`。 |

## 8. 当前项目 lumax 实现要求

### 8.1 Redis 客户端

当前项目 `lumax` 复用现有 Redis env 族：

```text
LUMAX_BANNED_WORDS_REDIS_URL -> AUTH_REDIS_URL -> REDIS_URL
```

新增 `lumax_pricing_cache.py` 读取价格缓存，并复用同一个 Redis 单例，避免每次请求新建连接。

### 8.2 inference_mode 上下文

`MeteringRunContext`、`UsageRecord`、`UsageSettlement` 增加 `inference_mode` 字段，默认值为 `online`。

注入路径：

1. 客户端把 `inference_mode` 放在 `request.body.config.configurable` 或 `context` 中。
2. `app/gateway/services.py::merge_gateway_context` 将 `inference_mode` 加入 `configurable_keys`。
3. `runs/worker.py` 构造 `MeteringRunContext` 时从 `configurable.get("inference_mode")` 读取。
4. `_report_lumax_settlement` 写入 `UsageSettlement.inference_mode`。

### 8.3 token 归一化

不同 provider 的 usage 字段必须在 `metering._coerce_usage` 中归一化。

| Provider | 归一化规则 |
| --- | --- |
| OpenAI | `prompt_tokens` 已包含 `cached_tokens`；`cacheReadTokens = cached_tokens`。 |
| Anthropic | `tokensIn = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`；`cacheReadTokens = cache_read_input_tokens`；`cacheWriteTokens = cache_creation_input_tokens`。 |
| 火山方舟 / 豆包 | 按 OpenAI 口径处理。 |

`tokensOut` 归一化后应包含 reasoning tokens。`outputBillableTokens` 使用 `max(tokensOut, reasoningTokens)` 只处理边界情况。

### 8.4 tier 选择伪代码

```text
pricing = JSON.parse(redis.get("${tenantId}:lumax:model_pricing:${model_name}")
                    or redis.get("0:lumax:model_pricing:${model_name}"))
if pricing is None:
    raise SettlementError("model pricing missing")

mode = settlement.inference_mode or "online"
if mode not in pricing.supportedInferenceModes:
    raise SettlementError("unsupported inference mode")

if pricing.hasTieredPricing:
    candidates = pricing.pricesByInferenceMode.get(mode, [])
    if not candidates and pricing.tiers:
        candidates = [t for t in pricing.tiers if t.inferenceMode == mode]
else:
    candidates = []

input_k = tokensIn / 1000
output_k = max(tokensOut, reasoningTokens) / 1000

matched = None
for tier in sorted(candidates, key=lambda t: t.sortOrder):
    if input_k < tier.inputLengthMin:
        continue
    if tier.inputLengthMax != -1 and input_k >= tier.inputLengthMax:
        continue
    if output_k < tier.outputLengthMin:
        continue
    if tier.outputLengthMax != -1 and output_k >= tier.outputLengthMax:
        continue
    matched = tier
    break

if pricing.hasTieredPricing:
    if matched is None:
        raise SettlementError("no tier matched")
    prices = matched
    price_tier_id = matched.id
else:
    prices = pricing.flatPrice
    price_tier_id = None
```

### 8.5 直写 DB 字段映射

`lumax_db_metering._persist_once` 需要写入费用字段：

```text
input_cost
output_cost
cache_cost
total_cost
price_tier_id
price_snapshot
```

需要新增 schema 字段：

```sql
ALTER TABLE lumax_token_consumption ADD COLUMN price_snapshot JSONB;
```

`price_snapshot` 保存本次结算实际使用的价格快照，至少包含：

```json
{
  "modelCode": "doubao-seed-2.0-pro",
  "inferenceMode": "online",
  "hasTieredPricing": true,
  "priceUnit": "per_1m_tokens",
  "priceTierId": 101,
  "inputLengthMin": 0,
  "inputLengthMax": 32,
  "outputLengthMin": 0,
  "outputLengthMax": -1,
  "inputPrice": "3.2",
  "outputPrice": "16",
  "cacheReadPrice": "0.64",
  "cacheWritePrice": "0",
  "pricingUpdatedAt": "2026-05-01T00:00:00.000Z"
}
```

说明：

1. `pricingUpdatedAt` 来自 Redis value 的 `updatedAt`。
2. 价格字段必须先转为 `Decimal`，再使用 `Decimal` 规范化后的字符串保存，避免 JSON number 或 float 序列化带来的精度歧义。
3. 走 `flatPrice` 时 `priceTierId` 为 `null`。
4. 走 `flatPrice` 时 `inputLengthMin/inputLengthMax/outputLengthMin/outputLengthMax` 为 `null`。
5. `price_snapshot.priceTierId` 必须等于独立字段 `lumax_token_consumption.price_tier_id`。
6. 本期暂不要求在价格快照中保存 `currency`。

落库规则：

1. `INSERT INTO lumax_token_consumption(...)` 增加费用字段、`price_tier_id` 和 `price_snapshot`。
2. `UPDATE lumax_conversation` 累计 `total_cost = COALESCE(total_cost, 0) + %s`。
3. `lumax_usage_daily_stats.cost_total` 与 token 统计一起累计。
4. `lumax_user_quota.used_quota` 仍按 `tokensTotal` 扣减，不按金额扣减。
5. 费用、用量、额度更新必须在同一个事务中完成。
6. 本期不要求结算幂等，不使用 `idempotency_key` 防止重复写入；如果同一次模型调用被重复结算，按实际执行的写入结果累计费用和额度。

## 9. Redis miss 处理

Redis miss 指 `${tenantId}:...` 和 `0:...` 都未读取到。

处理规则：

1. 视为配置错误或 Redis 故障。
2. 结算失败。
3. 不写 `lumax_token_consumption`。
4. 不累计 `lumax_conversation.total_cost`。
5. 不累计 `lumax_usage_daily_stats.cost_total`。
6. 不扣 `lumax_user_quota.used_quota`。
7. 抛出 `SettlementError`，由 worker 将 run 状态置为 `error`。

## 10. 验收测试

当前项目 `lumax` 至少覆盖：

1. Redis key 不包含 `businessCode`。
2. Redis value 包含 `modelCode`、`priceUnit`、`supportedInferenceModes`、`pricesByInferenceMode`、`tiers`。
3. `[0,32k)` 和 `[32k,+∞)` 能正确命中。
4. `31,999 token` 命中第一档，`32,000 token` 命中第二档。
5. 非法 `inference_mode` 结算失败。
6. 非 `CNY` 币种结算失败。
7. `cacheReadTokens` 和 `cacheWriteTokens` 都进入 `cacheCost`。
8. `cacheWriteTokens` 不再进入普通输入费用。
9. `cache_storage_price` 不参与实时计费。
10. 当前项目 `lumax` 使用 `Decimal`，费用保留 6 位小数。
11. Redis miss 时结算失败，不写用量，不扣额度。
12. 直写数据库时费用字段能落库，并同步更新会话费用、日维度费用和 token 额度。
13. 每条消费记录必须保存 `price_snapshot`，价格变更后仍可按当次价格口径对账。
14. 本期不要求 `idempotency_key`，重复结算不做去重保护。
15. Anthropic / OpenAI 风格 usage 归一化后，`billableInputTokens` 计算结果符合预期。

## 11. 暂不处理

1. 缓存存储时长费用。
2. 模型 alias 或额外映射表。
3. 复杂重复 tier 配置校验。
4. 历史价格审计快照字段。
5. Redis 价格缓存生成和刷新机制。
6. 服务端模型价格维护接口。

