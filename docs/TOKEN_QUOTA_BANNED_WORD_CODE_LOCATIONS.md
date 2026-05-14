# DeerFlow 代码位置清单：Token 计算、Token 扣减、违禁词检查

更新时间：2026-05-01

## 1) 模型 Token 计算与汇总

### 1.1 Run 级计量主链路（用于结算）
- `backend/packages/harness/deerflow/metering.py`
  - `UsageTotals.add`：累计 `input_tokens/output_tokens/total_tokens` 等
  - `_coerce_usage`：统一兼容不同供应商 usage 字段
  - `LumaxMeteringCallbackHandler.on_llm_end`：在每次 LLM 返回时采集 usage
- `backend/packages/harness/deerflow/runtime/runs/worker.py`
  - `_report_lumax_settlement`：将 run 期间累计 token 汇总到 settlement（`tokens_in/tokens_out/tokens_total`）

### 1.2 文本 Token 计数（非计费扣减）
- `backend/packages/harness/deerflow/agents/memory/prompt.py`
  - `_count_tokens`：用 `tiktoken` 计算文本 token（用于 memory 注入预算）

## 2) Token 扣减 / 配额检查

### 2.1 运行前配额检查
- `backend/packages/harness/deerflow/runtime/runs/worker.py`
  - 在 `run_agent` 早期调用 `UsageReporter.check_quota(...)`
  - 配额不足直接返回 `429`

### 2.2 配额与结算上报入口
- `backend/app/gateway/usage_reporter.py`
  - `check_quota`：配额检查（DB 模式优先，否则走 HTTP）
  - `report_settlement`：run 完成后结算上报
  - `_post_lumax`：HTTP 调用
    - `/lumax/v1/internal/check-quota`
    - `/lumax/v1/usage/report`

### 2.3 数据库模式下的真实扣减
- `backend/app/gateway/lumax_db_metering.py`
  - `check_quota_db`：查询 `lumax_user_quota`
  - `persist_settlement_db`：写入消费和会话记录
  - `_consume_user_quota`：执行 `used_quota = used_quota + total_tokens`
    - 有限配额：超额会抛出 `quota insufficient`
    - 无限配额（`total_quota = -1`）：仍累加 `used_quota`

## 3) 违禁词检查

### 3.1 违禁词匹配核心
- `backend/app/gateway/banned_words_guard.py`
  - `BannedWordsGuard.check_text`
    - 从 Redis 读取词库缓存
    - 按 `exact/fuzzy` 模式匹配
  - `extract_matched_sentence`：抽取命中句子
  - 关键缓存 key 规则：
    - `"{tenant_id}:lumax:banned_words:{trigger_source}:{match_mode}"`
    - `"{tenant_id}:lumax:banned_words:{trigger_source}:__modes"`

### 3.2 中间件触发点
- `backend/app/gateway/middlewares/banned_words_middleware.py`
  - `abefore_model`：检查用户输入（`input`）
  - `aafter_model`：检查模型输出（`output`）
  - 当前行为：命中后记录 warning 日志，不阻断会话

### 3.3 中间件注入入口
- `backend/app/gateway/services.py`
  - 在运行配置中注入 `BannedWordsMiddleware`
