# Lumax Metering Integration

DeerFlow reports AI usage to lumax-service at the run boundary. Token facts are
collected through LangChain callbacks, then settled once per run with an
idempotency key.

## Flow

1. The gateway merges authenticated `request.state.user` into
   `RunnableConfig.configurable` as `tenant_id`, `user_id`, and `user_context`. `tenant_id` is a digit string and may be longer than JavaScript safe integers, so it must not be converted to a numeric type.
   The user context includes the Redis-token-derived `username`.
2. Before LangChain execution, the run worker rejects missing identity and checks
   quota.
   - If `LUMAX_DB_DSN` is set, DeerFlow checks `lumax_user_quota` directly.
   - Otherwise DeerFlow calls `POST /lumax/v1/internal/check-quota`.
3. `LumaxMeteringCallbackHandler` records LLM token usage and tool calls in the
   current run context.
4. When the run ends, DeerFlow settles one usage record with
   `idempotencyKey=deerflow:<run_id>:settlement`.
   - If `LUMAX_DB_DSN` is set, DeerFlow writes settlement rows directly into
     `lumax_conversation`, `lumax_token_consumption`, `lumax_conversation_message`,
     and atomically updates `lumax_user_quota.used_quota`. When the quota row does
     not exist, DeerFlow inserts `lumax_user_quota` with `username`.
     `lumax_conversation` also stores `username` (from authenticated
     `nickname`, falling back to account `username`), `dept_id` (the first
     `deptIds` value), `agent_name`, and the final checkpoint `title` for the
     thread.
   - Otherwise DeerFlow sends `POST /lumax/v1/usage/report`.
5. Banned word middleware logs matched input/output text through
   `UsageReporter.report_banned_word_hit`.
   - If `LUMAX_DB_DSN` is set, DeerFlow inserts directly into
     `lumax_banned_word_trigger`.
   - Otherwise DeerFlow sends `POST /lumax/v1/collector/banned-word-hit`.

## Environment

- `LUMAX_SERVICE_URL`: lumax-service API base URL. Defaults to
  `http://localhost:9008/api`.
- `USAGE_REPORTING_ENABLED`: set to `false` to disable reporting.
- `LUMAX_INTERNAL_SECRET`: shared HMAC secret. When configured in lumax-service,
  DeerFlow must use the same value for quota checks and usage reports.
- `LUMAX_DB_DSN`: PostgreSQL DSN for direct metering mode. When set, quota check,
  settlement, and banned word hit persistence are handled by direct SQL instead
  of lumax-service HTTP APIs.

## Failure Behavior

- Missing `tenant_id` or `user_id` fails before any LangChain model call.
- Quota check failure denies by default.
- Usage settlement retries three times. If all attempts fail, the run is marked
  as failed so unbilled usage is not silently treated as successful.

## Routing Requirement

- Billing settlement runs in DeerFlow Gateway (`/api/*` and `/api/langgraph-compat/*`).
- Through the nginx entrypoint on port 2026, `/api/langgraph/*` is rewritten to
  `/api/*` and still runs through the gateway lifecycle, including quota check,
  banned word checks before/after model calls, and usage settlement.
- Requests sent directly to a raw LangGraph server port bypass gateway lifecycle
  hooks and will not trigger lumax settlement or banned word persistence.
