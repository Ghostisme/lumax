# Lumax Token 计费 — Redis 缓存格式参考

本文档描述 lumax-service 写入、deer-flow 读取的模型价格 Redis 缓存格式。所有费用计算以本文 value 结构为权威输入。

## 1. 写入与读取路径

- **写入方**：`lumax-service`，命中以下任一时机即重建缓存
  1. 模型新增 / 更新 / 启用 / 停用 / 删除
  2. 价格 tier 新增 / 更新 / 删除
  写入时序：Prisma 事务提交成功 → `ModelPricingCacheService.rebuildModelCache(tenantId, modelCode)` 写 Redis。事务失败不写缓存；写缓存失败仅记 `ERROR` 日志，DB 不回滚（运维通过重建接口手动恢复）。
- **读取方**：`deer-flow`，结算时按 `tenant_id + model_name` 拼 key，逐级回退到 `0:` 全局兜底。Redis miss 视为配置错误，结算失败、不写用量、不扣额度。

Redis 客户端：

- lumax-service 复用 `auth/redis.provider.ts` 暴露的 `REDIS_CLIENT`（`AuthModule` 已 `@Global()`），通过 `@Inject(REDIS_CLIENT)` 注入。
- deer-flow 复用 `app/gateway/banned_words_guard.py` 同一套 env（`LUMAX_BANNED_WORDS_REDIS_URL` → `AUTH_REDIS_URL` → `REDIS_URL` 或 host/port/password 拆分变量），抽出单例工厂 `app/gateway/lumax_redis.py` 给 `lumax_pricing_cache.py` 共享。

## 2. Key 规则

```text
${tenantId}:lumax:model_pricing:${modelCode}
0:lumax:model_pricing:${modelCode}
```

| 段 | 含义 |
| --- | --- |
| `${tenantId}` | 价格所属租户。`0` 表示全局兜底（运营按需手动写入 `lumax_llm_model.tenant_id = 0` 行后才会出现） |
| `lumax:model_pricing` | 业务命名空间，与 `lumax:banned_words` 同级 |
| `${modelCode}` | `lumax_llm_model.model_code`，**与 deer-flow `model_name` 字符级一致**（区分大小写、空格、`/`） |

key 中**不**包含 `businessCode`。读取顺序固定：先 `${tenantId}:…` → 后 `0:…`，全部 miss 即结算失败。

## 3. Value 结构

JSON 编码，UTF-8。一个 modelCode 对应一条 value，包含：

- 顶层模型元数据（`tenantId` / `modelCode` / `priceUnit` / `currency` / 开关位 / 模式列表 / 时间戳）
- `flatPrice`：模型级 flat 价格（兜底用）
- `tiers[]`：分段价格的**权威**列表
- `pricesByInferenceMode`：从 `tiers[]` 派生的索引，按 `inferenceMode` 分组，便于 deer-flow O(1) 查找
- `pricingRules[]`：人工可读规则字符串，仅排查/展示用

> 权威关系：`tiers` > `pricesByInferenceMode` > `flatPrice` > `pricingRules`。`pricesByInferenceMode` 必须严格由 `tiers` 派生，二者不一致以 `tiers` 为准。

## 4. 完整示例（GLM-5.1 三档 + 三种推理模式）

```json
{
  "tenantId": "2052263773707833345",
  "modelCode": "doubao-seed-2.0-pro",
  "priceUnit": "per_1m_tokens",
  "currency": "CNY",
  "hasTieredPricing": true,
  "supportedInferenceModes": ["online", "online_low_latency", "batch"],
  "flatPrice": {
    "inputPrice": 3.2,
    "outputPrice": 16,
    "cacheReadPrice": 0.64,
    "cacheWritePrice": 0,
    "cacheStoragePrice": 0
  },
  "pricesByInferenceMode": {
    "online": [
      {
        "id": 101,
        "inferenceMode": "online",
        "inputLengthMin": 0,
        "inputLengthMax": 32,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 3.2,
        "outputPrice": 16,
        "cacheReadPrice": 0.64,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0.017,
        "sortOrder": 1
      },
      {
        "id": 102,
        "inferenceMode": "online",
        "inputLengthMin": 32,
        "inputLengthMax": 128,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 4.8,
        "outputPrice": 24,
        "cacheReadPrice": 0.96,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0.017,
        "sortOrder": 2
      },
      {
        "id": 103,
        "inferenceMode": "online",
        "inputLengthMin": 128,
        "inputLengthMax": 256,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 9.6,
        "outputPrice": 48,
        "cacheReadPrice": 1.92,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0.017,
        "sortOrder": 3
      }
    ],
    "online_low_latency": [
      {
        "id": 104,
        "inferenceMode": "online_low_latency",
        "inputLengthMin": 0,
        "inputLengthMax": 32,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 9.6,
        "outputPrice": 48,
        "cacheReadPrice": 1.92,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0,
        "sortOrder": 1
      }
    ],
    "batch": [
      {
        "id": 107,
        "inferenceMode": "batch",
        "inputLengthMin": 0,
        "inputLengthMax": 32,
        "outputLengthMin": 0,
        "outputLengthMax": -1,
        "inputPrice": 1.6,
        "outputPrice": 8,
        "cacheReadPrice": 0.64,
        "cacheWritePrice": 0,
        "cacheStoragePrice": 0,
        "sortOrder": 1
      }
    ]
  },
  "tiers": [
    { "id": 101, "inferenceMode": "online",             "inputLengthMin": 0,   "inputLengthMax": 32,  "outputLengthMin": 0, "outputLengthMax": -1, "inputPrice": 3.2,  "outputPrice": 16, "cacheReadPrice": 0.64, "cacheWritePrice": 0, "cacheStoragePrice": 0.017, "sortOrder": 1 },
    { "id": 102, "inferenceMode": "online",             "inputLengthMin": 32,  "inputLengthMax": 128, "outputLengthMin": 0, "outputLengthMax": -1, "inputPrice": 4.8,  "outputPrice": 24, "cacheReadPrice": 0.96, "cacheWritePrice": 0, "cacheStoragePrice": 0.017, "sortOrder": 2 },
    { "id": 103, "inferenceMode": "online",             "inputLengthMin": 128, "inputLengthMax": 256, "outputLengthMin": 0, "outputLengthMax": -1, "inputPrice": 9.6,  "outputPrice": 48, "cacheReadPrice": 1.92, "cacheWritePrice": 0, "cacheStoragePrice": 0.017, "sortOrder": 3 },
    { "id": 104, "inferenceMode": "online_low_latency", "inputLengthMin": 0,   "inputLengthMax": 32,  "outputLengthMin": 0, "outputLengthMax": -1, "inputPrice": 9.6,  "outputPrice": 48, "cacheReadPrice": 1.92, "cacheWritePrice": 0, "cacheStoragePrice": 0,     "sortOrder": 1 },
    { "id": 107, "inferenceMode": "batch",              "inputLengthMin": 0,   "inputLengthMax": 32,  "outputLengthMin": 0, "outputLengthMax": -1, "inputPrice": 1.6,  "outputPrice": 8,  "cacheReadPrice": 0.64, "cacheWritePrice": 0, "cacheStoragePrice": 0,     "sortOrder": 1 }
  ],
  "pricingRules": [
    "online 输入 [0,32k) = 3.2 元/百万 token，输出 = 16 元/百万 token，缓存命中 = 0.64 元/百万 token",
    "online 输入 [32k,128k) = 4.8 元/百万 token，输出 = 24 元/百万 token，缓存命中 = 0.96 元/百万 token",
    "online 输入 [128k,256k) = 9.6 元/百万 token，输出 = 48 元/百万 token，缓存命中 = 1.92 元/百万 token",
    "online_low_latency 输入 [0,32k) = 9.6 元/百万 token，输出 = 48 元/百万 token，缓存命中 = 1.92 元/百万 token",
    "batch 输入 [0,32k) = 1.6 元/百万 token，输出 = 8 元/百万 token，缓存命中 = 0.64 元/百万 token"
  ],
  "updatedAt": "2026-05-01T00:00:00.000Z"
}
```

## 5. 顶层字段说明

| 字段 | 类型 | 来源 | 说明 |
| --- | --- | --- | --- |
| `tenantId` | `string` | `lumax_llm_model.tenant_id` | 数字字符串；`"0"` 表示全局兜底 |
| `modelCode` | `string` | `lumax_llm_model.model_code` | DeerFlow `model_name` 必须等于此值 |
| `priceUnit` | `string` | `lumax_llm_model.price_unit` | `per_1m_tokens` 或 `per_1k_tokens`；适用于 `flatPrice` 与全部 tier |
| `currency` | `string` | `lumax_llm_model.currency` | 币种，例 `CNY` |
| `hasTieredPricing` | `boolean` | `lumax_llm_model.has_tiered_pricing` | true 时优先按 tier，未命中走 `flatPrice` |
| `supportedInferenceModes` | `string[]` | `lumax_llm_model.supported_inference_modes` 拆分 | 用于校验请求 `inferenceMode` 合法性 |
| `flatPrice` | `object` | `lumax_llm_model.*_price` | tier 未命中时的兜底价格 |
| `pricesByInferenceMode` | `object<string, tier[]>` | 由 `tiers` 派生 | key 为推理模式名，value 为该模式下的 tier 数组 |
| `tiers` | `object[]` | `lumax_llm_model_price_tier` 全部行 | **权威**分段价格明细 |
| `pricingRules` | `string[]` | 服务端自动拼接 | 仅供人工查看，不参与计算 |
| `updatedAt` | `string` | `Date.toISOString()` | 缓存生成时间，ISO 8601 |

## 6. `flatPrice` 字段说明

| 字段 | 类型 | DB 来源 | 说明 |
| --- | --- | --- | --- |
| `inputPrice` | `number` | `input_price` | 基础输入单价 |
| `outputPrice` | `number` | `output_price` | 基础输出单价 |
| `cacheReadPrice` | `number` | `cache_read_price` | 基础缓存命中单价 |
| `cacheWritePrice` | `number` | `cache_write_price` | 基础缓存写入单价；tier 未配置 `cacheWritePrice` 时回退到这里 |
| `cacheStoragePrice` | `number` | `cache_storage_price` | 基础缓存存储单价；本期不参与实时计费 |

## 7. `tiers[]` / `pricesByInferenceMode[mode][]` 字段说明

| 字段 | 类型 | DB 来源 | 说明 |
| --- | --- | --- | --- |
| `id` | `number` | `lumax_llm_model_price_tier.id` | DeerFlow 写入 `lumax_token_consumption.price_tier_id` |
| `inferenceMode` | `string` | `inference_mode` | 该分段适用的推理模式 |
| `inputLengthMin` | `number` | `input_length_min` | 输入长度下限，单位 `k token`，**左闭** |
| `inputLengthMax` | `number` | `input_length_max` | 输入长度上限，单位 `k token`，**右开**；`-1` 表示无上限 |
| `outputLengthMin` | `number` | `output_length_min` | 输出长度下限，单位 `k token`，左闭 |
| `outputLengthMax` | `number` | `output_length_max` | 输出长度上限，单位 `k token`，右开；`-1` 表示无上限 |
| `inputPrice` | `number` | `input_price` | 该分段输入单价 |
| `outputPrice` | `number` | `output_price` | 该分段输出单价 |
| `cacheReadPrice` | `number` | `cache_read_price` | 该分段缓存命中单价 |
| `cacheWritePrice` | `number` | `cache_write_price` | 该分段缓存写入单价 |
| `cacheStoragePrice` | `number` | `cache_storage_price` | 该分段缓存存储单价；本期不参与实时计费 |
| `sortOrder` | `number` | `sort_order` | 多 tier 命中时按此字段稳定取首条 |

## 8. 计价单位换算

```text
per_1m_tokens => unit = 1_000_000
per_1k_tokens => unit = 1_000
```

`priceUnit` 是模型级配置，对本次缓存内**全部**价格字段（`flatPrice` 与所有 `tiers`）一致。

费用公式（DeerFlow 端必须使用 Python `Decimal`）：

```text
billableInputTokens  = max(tokensIn - cacheReadTokens, 0)
outputBillableTokens = max(tokensOut, reasoningTokens)

inputCost  = Decimal(billableInputTokens)  * inputPrice  / Decimal(unit)
outputCost = Decimal(outputBillableTokens) * outputPrice / Decimal(unit)
cacheCost  = Decimal(cacheReadTokens)  * cacheReadPrice  / Decimal(unit)
           + Decimal(cacheWriteTokens) * cacheWritePrice / Decimal(unit)
totalCost  = inputCost + outputCost + cacheCost
```

精度：

1. 价格读出后用字符串转 `Decimal`：`Decimal(str(value))`，避免 float 引入误差。
2. token 数保持 `int`。
3. 写库前量化到 6 位小数：`quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)`。

## 9. tier 选择算法

```text
pricing = JSON.parse(redis.get("${tenantId}:lumax:model_pricing:${model_name}")
                    or redis.get("0:lumax:model_pricing:${model_name}"))
if pricing is None: raise SettlementError("model pricing missing")

mode = settlement.inference_mode or "online"
candidates = pricing.pricesByInferenceMode.get(mode, [])
if not candidates and pricing.tiers:
    candidates = [t for t in pricing.tiers if t.inferenceMode == mode]

input_k  = tokens_in / 1000
output_k = max(tokens_out, reasoning_tokens) / 1000

matched = None
for tier in sorted(candidates, key=lambda t: t.sortOrder):
    if not (tier.inputLengthMin <= input_k < tier_input_max(tier)):
        continue
    if tier.outputLengthMax != -1 and not (tier.outputLengthMin <= output_k < tier.outputLengthMax):
        continue
    matched = tier
    break

if matched is None:
    if pricing.hasTieredPricing:
        prices = pricing.flatPrice
        price_tier_id = None
    else:
        raise SettlementError("no tier matched and no flat price")
else:
    prices = matched
    price_tier_id = matched.id
```

`tier_input_max(tier)` 的实现：`+∞ if tier.inputLengthMax == -1 else tier.inputLengthMax`。`outputLengthMin/Max` 同理。

边界示例（GLM-5.1 `[0,32k)` / `[32k,+∞)`）：

| `tokens_in` | 命中分段 |
| ---: | --- |
| `31_999` | `[0, 32)` |
| `32_000` | `[32, +∞)` |
| `127_999` | `[32, 128)` |
| `128_000` | `[128, 256)` |

## 10. token 归一化（写入 Redis 之前已无关，DeerFlow 算费时处理）

不同 provider 的 `cache_*_tokens` 语义不一致，DeerFlow 在写库前必须归一化到统一口径：

| Provider | 行为 | 处理 |
| --- | --- | --- |
| OpenAI | `prompt_tokens` 已包含 `cached_tokens` | `cache_read_tokens = cached_tokens`，不要再从 `tokens_in` 扣 cache_write |
| Anthropic | `input_tokens` 不含 `cache_creation_input_tokens` 与 `cache_read_input_tokens` | 把 `cache_creation_input_tokens` 加回 `tokens_in`，再令 `billableInputTokens = max(tokens_in - cache_read_tokens, 0)` |
| 火山方舟 / 豆包 | 与 OpenAI 一致 | 同 OpenAI 口径 |

归一化集中在 `metering._coerce_usage`，让 worker 拿到的 `tokens_in / cache_read_tokens / cache_write_tokens` 已是统一语义；公式直接套用即可。

## 11. 推理模式策略

支持的模式：

```text
online
online_low_latency
batch
```

规则：

1. 模型按 `inferenceMode` 区分价格时，DeerFlow 用请求 `inferenceMode` 命中对应价格。
2. 模型未按 `inferenceMode` 区分价格时，lumax-service 生成 Redis 缓存时把同一套 tier 复制到 `online`、`online_low_latency`、`batch` 三个 mode 子数组，DeerFlow 仍按 `inferenceMode` 查找，三种模式价格相同。
3. DeerFlow 未传 `inferenceMode` 时默认按 `online`。
4. 请求里的 `inferenceMode` 必须落在 `supportedInferenceModes` 内，否则结算失败。

## 12. 缓存失效与重建

| 触发动作 | 服务端方法 | 写 Redis |
| --- | --- | --- |
| 模型新增 / 更新 / 启用 / 停用 | `LlmModelService` | `rebuildModelCache(tenantId, modelCode)` |
| 模型删除 | `LlmModelService.delete` | `clearModelCache(tenantId, modelCode)` |
| tier 增 / 改 / 删 | `LlmModelPriceTierService` | `rebuildModelCache(tenantId, modelCode)` |
| 租户维度全量重建 | 运维接口 | `rebuildTenantCache(tenantId)` |

时序：Prisma 事务提交成功 → 同步写 Redis。事务失败不写缓存；写缓存失败仅记 `ERROR` 日志、DB 不回滚（运维通过重建接口手动恢复）。

## 13. DeerFlow 端 miss 的处理

Redis miss（`${tenantId}` 与 `0:` 都没读到）按以下规则处理：

1. 视为配置错误（model_code 不一致 / 缓存未写入 / Redis 故障）。
2. **不**写 `lumax_token_consumption`。
3. **不**累加 `lumax_conversation.total_cost` 与 `lumax_usage_daily_stats.cost_total`。
4. **不**扣 `lumax_user_quota.used_quota`。
5. 抛 `SettlementError`，由 `worker.py` 的结算流程捕获后置 run 状态为 `error`。

历史数据无需考虑兼容，开发库可随时清空重建。
