"""DB-first lumax metering helpers.

This module keeps direct-SQL quota and settlement logic isolated from
UsageReporter to reduce changes in the existing gateway flow.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.gateway.lumax_pricing_cache import PricingCacheError, get_model_pricing
from app.gateway.tenant import GLOBAL_TENANT_ID, normalize_tenant_id

try:
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional runtime dependency
    AsyncConnection = None
    dict_row = None

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MONEY_QUANT = Decimal("0.000001")
# lumax_conversation_message.message_id is VARCHAR(255) in legacy migrations
DB_MESSAGE_ID_MAX_LEN = 250
QUOTA_INSUFFICIENT_MESSAGE = "Token 总配额不足"
PRICE_UNITS = {
    "per_1m_tokens": Decimal("1000000"),
    "per_1k_tokens": Decimal("1000"),
}


def _ensure_driver() -> None:
    if AsyncConnection is None or dict_row is None:
        raise RuntimeError("psycopg is required for LUMAX_DB_DSN mode")


def _storage_message_id_for_db(raw: str) -> str:
    """Fit message_id into DB VARCHAR(255); long client ids must not break settlement."""
    text = str(raw or "").strip() or "unknown"
    if len(text) <= DB_MESSAGE_ID_MAX_LEN:
        return text
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dsn_log_target(dsn: str) -> str:
    """Host/db fragment for logs (no password)."""
    text = str(dsn or "")
    if "@" in text:
        return text.rsplit("@", 1)[-1]
    return text[:120]


def _normalize_user_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def check_quota_db(dsn: str, tenant_id: str, user_id: str) -> dict:
    _ensure_driver()
    tenant_id = normalize_tenant_id(tenant_id)
    if tenant_id is None:
        return {
            "allowed": False,
            "remaining": 0,
            "message": "tenantId must not be less than 1",
        }
    user_id = _normalize_user_id(user_id)
    if user_id is None:
        return {"allowed": False, "remaining": 0, "message": QUOTA_INSUFFICIENT_MESSAGE}
    if user_id == "-1":
        return {"allowed": True, "remaining": -1, "message": "系统用户不限额"}

    async with await AsyncConnection.connect(dsn) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT total_quota, used_quota
                FROM lumax_user_quota
                WHERE tenant_id = %s AND user_id = %s
                LIMIT 1
                """,
                (tenant_id, user_id),
            )
            row = await cur.fetchone()

    if row is None:
        return {"allowed": False, "remaining": 0, "message": QUOTA_INSUFFICIENT_MESSAGE}

    total_quota = _quota_int(row.get("total_quota"))
    if total_quota is None:
        return {"allowed": False, "remaining": 0, "message": QUOTA_INSUFFICIENT_MESSAGE}
    used_quota = _quota_int(row.get("used_quota"), default=0) or 0
    if total_quota == -1:
        return {"allowed": True, "remaining": -1, "message": "unlimited"}

    remaining = total_quota - used_quota
    if remaining <= 0:
        return {"allowed": False, "remaining": 0, "message": QUOTA_INSUFFICIENT_MESSAGE}
    return {"allowed": True, "remaining": remaining, "message": "ok"}


async def persist_settlement_db(dsn: str, settlement: dict[str, Any]) -> dict[str, Any]:
    _ensure_driver()
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await _persist_once(dsn, settlement)
            return result
        except Exception as exc:
            last_error = exc
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2**attempt)
    raise RuntimeError(f"用量结算重试后仍失败：{last_error}") from last_error


async def _persist_once(dsn: str, settlement: dict[str, Any]) -> dict[str, Any]:
    tenant_id = normalize_tenant_id(settlement.get("tenant_id"))
    if tenant_id is None:
        raise RuntimeError("tenantId must not be less than 1")
    user_id = _normalize_user_id(settlement.get("user_id"))
    if user_id is None:
        raise RuntimeError("userId must not be empty")
    settlement = {
        **settlement,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "thread_id": str(settlement.get("thread_id") or ""),
        "run_id": str(settlement.get("run_id") or ""),
        "idempotency_key": str(settlement.get("idempotency_key") or ""),
        "dept_id": str(settlement.get("dept_id") or ""),
    }
    total_tokens = int(settlement.get("tokens_total") or 0)
    pricing_result = (
        _zero_pricing_result(settlement)
        if total_tokens <= 0
        else await _calculate_pricing(dsn, settlement)
    )
    duration_seconds = max(0, int((settlement.get("response_time_ms") or 0) / 1000))
    raw_status = str(settlement.get("status") or "completed")
    status = (
        raw_status
        if raw_status in {"completed", "failed", "cancelled"}
        else "completed"
    )

    async with await AsyncConnection.connect(dsn) as conn:
        async with conn.transaction():
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT id, username, dept_id, title, model_name, agent_name, skill_name
                    FROM lumax_conversation
                    WHERE tenant_id = %s AND thread_id = %s AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (
                        settlement["tenant_id"],
                        settlement["thread_id"],
                        settlement["user_id"],
                    ),
                )
                conversation = await cur.fetchone()
                if conversation is None:
                    await cur.execute(
                        """
                        INSERT INTO lumax_conversation (
                            tenant_id, thread_id, user_id, username, dept_id, model_name, agent_name, title, skill_name,
                            message_count, input_tokens, output_tokens, total_tokens, start_time, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 0, NOW(), 'ongoing')
                        RETURNING id
                        """,
                        (
                            settlement["tenant_id"],
                            settlement["thread_id"],
                            settlement["user_id"],
                            settlement.get("username") or "",
                            settlement.get("dept_id") or "",
                            settlement.get("model_name") or "",
                            settlement.get("agent_name") or "",
                            settlement.get("title") or "",
                            settlement.get("skill_name") or "",
                        ),
                    )
                    created = await cur.fetchone()
                    conversation_id = int(created["id"])
                    previous_username = ""
                    previous_dept_id = ""
                    previous_title = ""
                    previous_model = ""
                    previous_agent = ""
                    previous_skill = ""
                else:
                    conversation_id = int(conversation["id"])
                    previous_username = str(conversation.get("username") or "")
                    previous_dept_id = str(conversation.get("dept_id") or "")
                    previous_title = str(conversation.get("title") or "")
                    previous_model = str(conversation.get("model_name") or "")
                    previous_agent = str(conversation.get("agent_name") or "")
                    previous_skill = str(conversation.get("skill_name") or "")

                await cur.execute(
                    """
                    UPDATE lumax_conversation
                    SET username = %s,
                        dept_id = %s,
                        model_name = %s,
                        agent_name = %s,
                        title = %s,
                        skill_name = %s,
                        message_count = COALESCE(message_count, 0) + %s,
                        input_tokens = COALESCE(input_tokens, 0) + %s,
                        output_tokens = COALESCE(output_tokens, 0) + %s,
                        total_tokens = COALESCE(total_tokens, 0) + %s,
                        cache_read_tokens = COALESCE(cache_read_tokens, 0) + %s,
                        reasoning_tokens = COALESCE(reasoning_tokens, 0) + %s,
                        total_cost = COALESCE(total_cost, 0) + %s,
                        duration_seconds = COALESCE(duration_seconds, 0) + %s,
                        end_time = NOW(),
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        settlement.get("username") or previous_username,
                        settlement.get("dept_id") or previous_dept_id,
                        settlement.get("model_name") or previous_model,
                        settlement.get("agent_name") or previous_agent,
                        settlement.get("title") or previous_title,
                        settlement.get("skill_name") or previous_skill,
                        len(settlement.get("messages") or []),
                        int(settlement.get("tokens_in") or 0),
                        int(settlement.get("tokens_out") or 0),
                        total_tokens,
                        int(settlement.get("cache_read_tokens") or 0),
                        int(settlement.get("reasoning_tokens") or 0),
                        pricing_result["total_cost"],
                        duration_seconds,
                        status,
                        conversation_id,
                    ),
                )

                await cur.execute(
                    """
                    INSERT INTO lumax_token_consumption (
                        tenant_id, conversation_id, thread_id, run_id, idempotency_key,
                        user_id, model_name, agent_name, skill_name, tool_calls_count,
                        input_tokens, output_tokens, total_tokens,
                        cache_read_tokens, cache_write_tokens, reasoning_tokens, inference_mode,
                        input_cost, output_cost, cache_cost, total_cost, price_tier_id, price_snapshot,
                        response_time_ms, consumed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s::jsonb,
                        %s, NOW()
                    )
                    """,
                    (
                        settlement["tenant_id"],
                        conversation_id,
                        settlement["thread_id"],
                        settlement["run_id"],
                        settlement["idempotency_key"],
                        settlement["user_id"],
                        settlement["model_name"],
                        settlement.get("agent_name") or "",
                        settlement.get("skill_name") or "",
                        int(settlement.get("tool_calls_count") or 0),
                        int(settlement.get("tokens_in") or 0),
                        int(settlement.get("tokens_out") or 0),
                        total_tokens,
                        int(settlement.get("cache_read_tokens") or 0),
                        int(settlement.get("cache_write_tokens") or 0),
                        int(settlement.get("reasoning_tokens") or 0),
                        settlement.get("inference_mode") or "online",
                        pricing_result["input_cost"],
                        pricing_result["output_cost"],
                        pricing_result["cache_cost"],
                        pricing_result["total_cost"],
                        pricing_result["price_tier_id"],
                        json.dumps(
                            pricing_result["price_snapshot"],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        int(settlement.get("response_time_ms") or 0),
                    ),
                )

                for message in settlement.get("messages") or []:
                    mid = _storage_message_id_for_db(str(message.get("message_id") or ""))
                    await cur.execute(
                        """
                        INSERT INTO lumax_conversation_message (
                            tenant_id, conversation_id, thread_id, run_id, idempotency_key,
                            user_id, message_id, role, content, message_index, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s::timestamp
                        )
                        ON CONFLICT (tenant_id, user_id, message_id) DO UPDATE SET
                            conversation_id = EXCLUDED.conversation_id,
                            thread_id = EXCLUDED.thread_id,
                            run_id = EXCLUDED.run_id,
                            idempotency_key = EXCLUDED.idempotency_key,
                            role = EXCLUDED.role,
                            content = EXCLUDED.content,
                            message_index = EXCLUDED.message_index,
                            created_at = EXCLUDED.created_at
                        """,
                        (
                            settlement["tenant_id"],
                            conversation_id,
                            settlement["thread_id"],
                            settlement["run_id"],
                            settlement["idempotency_key"],
                            settlement["user_id"],
                            mid,
                            message["role"],
                            message["content"],
                            int(message.get("message_index") or 0),
                            message["created_at"],
                        ),
                    )

                logger.info(
                    "lumax_settlement_committed db=%s tenant=%s user=%s thread=%s run=%s "
                    "conversation_id=%s messages=%d",
                    _dsn_log_target(dsn),
                    settlement["tenant_id"],
                    settlement["user_id"],
                    settlement["thread_id"],
                    settlement["run_id"],
                    conversation_id,
                    len(settlement.get("messages") or []),
                )

                if total_tokens > 0:
                    await _consume_user_quota(
                        cur,
                        settlement["tenant_id"],
                        settlement["user_id"],
                        settlement.get("username"),
                        total_tokens,
                    )
                    await _upsert_daily_stats(
                        cur, settlement, pricing_result["total_cost"]
                    )

                return {"conversationId": conversation_id}


def _zero_pricing_result(settlement: dict[str, Any]) -> dict[str, Any]:
    zero = Decimal("0.000000")
    return {
        "input_cost": zero,
        "output_cost": zero,
        "cache_cost": zero,
        "total_cost": zero,
        "price_tier_id": None,
        "price_snapshot": {
            "modelCode": str(settlement.get("model_name") or ""),
            "inferenceMode": str(settlement.get("inference_mode") or "online"),
            "priceUnit": "zero_tokens",
        },
    }


async def _calculate_pricing(dsn: str, settlement: dict[str, Any]) -> dict[str, Any]:
    tenant_id = normalize_tenant_id(settlement["tenant_id"])
    if tenant_id is None:
        raise RuntimeError("tenantId must not be less than 1")
    model_name = str(settlement.get("model_name") or "")
    try:
        pricing = await get_model_pricing(tenant_id=tenant_id, model_name=model_name)
    except PricingCacheError:
        pricing = await _get_model_pricing_from_db(
            dsn, tenant_id=tenant_id, model_name=model_name
        )

    if str(pricing.get("currency") or "").upper() != "CNY":
        raise RuntimeError("unsupported pricing currency")

    price_unit = str(pricing.get("priceUnit") or "")
    unit = PRICE_UNITS.get(price_unit)
    if unit is None:
        raise RuntimeError(f"unsupported price unit: {price_unit}")

    mode = str(settlement.get("inference_mode") or "online")
    supported_modes = _supported_modes(pricing.get("supportedInferenceModes"))
    if mode not in supported_modes:
        raise RuntimeError(f"unsupported inference mode: {mode}")

    tokens_in = int(settlement.get("tokens_in") or 0)
    tokens_out = int(settlement.get("tokens_out") or 0)
    cache_read_tokens = int(settlement.get("cache_read_tokens") or 0)
    cache_write_tokens = int(settlement.get("cache_write_tokens") or 0)
    reasoning_tokens = int(settlement.get("reasoning_tokens") or 0)
    output_billable_tokens = max(tokens_out, reasoning_tokens)

    tier = _match_tier(pricing, mode, tokens_in, output_billable_tokens)
    if bool(pricing.get("hasTieredPricing")):
        if tier is None:
            raise RuntimeError("no model pricing tier matched")
        prices = tier
        price_tier_id = _optional_int(tier.get("id"))
        boundaries = {
            "inputLengthMin": tier.get("inputLengthMin"),
            "inputLengthMax": tier.get("inputLengthMax"),
            "outputLengthMin": tier.get("outputLengthMin"),
            "outputLengthMax": tier.get("outputLengthMax"),
        }
    else:
        prices = pricing.get("flatPrice")
        if not isinstance(prices, dict):
            raise RuntimeError("模型基础计费信息未配置")
        price_tier_id = None
        boundaries = {
            "inputLengthMin": None,
            "inputLengthMax": None,
            "outputLengthMin": None,
            "outputLengthMax": None,
        }

    input_price = _decimal_price(prices.get("inputPrice"))
    output_price = _decimal_price(prices.get("outputPrice"))
    cache_read_price = _decimal_price(prices.get("cacheReadPrice"))
    flat_price = (
        pricing.get("flatPrice") if isinstance(pricing.get("flatPrice"), dict) else {}
    )
    cache_write_price = _decimal_price(
        prices.get("cacheWritePrice", flat_price.get("cacheWritePrice"))
    )

    billable_input_tokens = max(tokens_in - cache_read_tokens - cache_write_tokens, 0)
    input_cost = _money(Decimal(billable_input_tokens) * input_price / unit)
    output_cost = _money(Decimal(output_billable_tokens) * output_price / unit)
    cache_cost = _money(
        Decimal(cache_read_tokens) * cache_read_price / unit
        + Decimal(cache_write_tokens) * cache_write_price / unit
    )
    total_cost = _money(input_cost + output_cost + cache_cost)
    price_snapshot = {
        "modelCode": str(
            pricing.get("modelCode") or settlement.get("model_name") or ""
        ),
        "inferenceMode": mode,
        "hasTieredPricing": bool(pricing.get("hasTieredPricing")),
        "priceUnit": price_unit,
        "priceTierId": price_tier_id,
        **boundaries,
        "inputPrice": _decimal_string(input_price),
        "outputPrice": _decimal_string(output_price),
        "cacheReadPrice": _decimal_string(cache_read_price),
        "cacheWritePrice": _decimal_string(cache_write_price),
        "pricingUpdatedAt": pricing.get("updatedAt"),
    }
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_cost": cache_cost,
        "total_cost": total_cost,
        "price_tier_id": price_tier_id,
        "price_snapshot": price_snapshot,
    }


async def _get_model_pricing_from_db(
    dsn: str, *, tenant_id: str, model_name: str
) -> dict[str, Any]:
    _ensure_driver()
    return await asyncio.to_thread(
        _get_model_pricing_from_db_sync, dsn, tenant_id=tenant_id, model_name=model_name
    )


def _get_model_pricing_from_db_sync(
    dsn: str, *, tenant_id: str, model_name: str
) -> dict[str, Any]:
    tenant_id = normalize_tenant_id(tenant_id)
    if tenant_id is None:
        raise PricingCacheError("tenant_id must be positive")
    model_code = str(model_name or "").strip()
    if not model_code:
        raise PricingCacheError("model_name is required for pricing lookup")

    import psycopg
    from psycopg.rows import dict_row as sync_dict_row

    with psycopg.connect(dsn, row_factory=sync_dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id, tenant_id, model_code, price_unit, currency,
                    has_tiered_pricing, supported_inference_modes,
                    input_price, output_price, cache_write_price,
                    cache_read_price, cache_storage_price, updated_at
                FROM lumax_llm_model
                WHERE model_code = %s AND tenant_id IN (%s, %s)
                ORDER BY CASE WHEN tenant_id = %s THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (model_code, tenant_id, GLOBAL_TENANT_ID, tenant_id),
            )
            model = cur.fetchone()
            if model is None:
                raise PricingCacheError(
                    f"模型计费信息未配置：租户ID={tenant_id}，模型={model_code}"
                )

            tiers: list[dict[str, Any]] = []
            if bool(model.get("has_tiered_pricing")):
                cur.execute(
                    """
                    SELECT
                        id, inference_mode, input_length_min, input_length_max,
                        output_length_min, output_length_max,
                        input_price, output_price, cache_storage_price,
                        cache_read_price, sort_order
                    FROM lumax_llm_model_price_tier
                    WHERE model_id = %s
                    ORDER BY sort_order ASC, id ASC
                    """,
                    (model["id"],),
                )
                tiers = [_format_pricing_tier(row, model) for row in cur.fetchall()]

    by_mode: dict[str, list[dict[str, Any]]] = {}
    for tier in tiers:
        by_mode.setdefault(str(tier.get("inferenceMode") or "online"), []).append(tier)

    supported_modes = _supported_modes(model.get("supported_inference_modes"))
    return {
        "tenantId": str(model.get("tenant_id") or tenant_id),
        "modelCode": str(model.get("model_code") or model_code),
        "priceUnit": str(model.get("price_unit") or "per_1k_tokens"),
        "currency": str(model.get("currency") or "CNY"),
        "hasTieredPricing": bool(model.get("has_tiered_pricing")),
        "supportedInferenceModes": sorted(supported_modes)
        if supported_modes
        else ["online"],
        "flatPrice": {
            "inputPrice": _decimal_string(_decimal_price(model.get("input_price"))),
            "outputPrice": _decimal_string(_decimal_price(model.get("output_price"))),
            "cacheReadPrice": _decimal_string(
                _decimal_price(model.get("cache_read_price"))
            ),
            "cacheWritePrice": _decimal_string(
                _decimal_price(model.get("cache_write_price"))
            ),
            "cacheStoragePrice": _decimal_string(
                _decimal_price(model.get("cache_storage_price"))
            ),
        },
        "tiers": tiers,
        "pricesByInferenceMode": by_mode,
        "updatedAt": _json_safe_value(model.get("updated_at")),
    }


def _format_pricing_tier(row: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _optional_int(row.get("id")),
        "inferenceMode": str(row.get("inference_mode") or "online"),
        "inputLengthMin": _number_value(row.get("input_length_min"), default=0),
        "inputLengthMax": _number_value(row.get("input_length_max"), default=-1),
        "outputLengthMin": _number_value(row.get("output_length_min"), default=0),
        "outputLengthMax": _number_value(row.get("output_length_max"), default=-1),
        "inputPrice": _decimal_string(_decimal_price(row.get("input_price"))),
        "outputPrice": _decimal_string(_decimal_price(row.get("output_price"))),
        "cacheReadPrice": _decimal_string(_decimal_price(row.get("cache_read_price"))),
        "cacheWritePrice": _decimal_string(
            _decimal_price(model.get("cache_write_price"))
        ),
        "cacheStoragePrice": _decimal_string(
            _decimal_price(row.get("cache_storage_price"))
        ),
        "sortOrder": _number_value(row.get("sort_order"), default=0),
    }


def _number_value(value: Any, *, default: int) -> int | float:
    if value is None:
        return default
    decimal = _decimal_price(value)
    if decimal == decimal.to_integral_value():
        return int(decimal)
    return float(decimal)


def _json_safe_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _supported_modes(raw: Any) -> set[str]:
    if isinstance(raw, list):
        return {str(item) for item in raw if str(item).strip()}
    if isinstance(raw, str):
        return {item.strip() for item in raw.split(",") if item.strip()}
    return {"online"}


def _match_tier(
    pricing: dict[str, Any], mode: str, tokens_in: int, output_tokens: int
) -> dict[str, Any] | None:
    if not bool(pricing.get("hasTieredPricing")):
        return None
    by_mode = pricing.get("pricesByInferenceMode") or {}
    candidates = by_mode.get(mode, []) if isinstance(by_mode, dict) else []
    tiers = pricing.get("tiers") or []
    if not candidates and isinstance(tiers, list):
        candidates = [
            tier
            for tier in tiers
            if isinstance(tier, dict) and str(tier.get("inferenceMode") or "") == mode
        ]
    if not isinstance(candidates, list):
        return None

    input_k = Decimal(tokens_in) / Decimal(1000)
    output_k = Decimal(output_tokens) / Decimal(1000)
    for tier in sorted(
        (item for item in candidates if isinstance(item, dict)),
        key=lambda item: int(item.get("sortOrder") or 0),
    ):
        input_min = _decimal_price(tier.get("inputLengthMin"))
        input_max = _decimal_price(tier.get("inputLengthMax"))
        output_min = _decimal_price(tier.get("outputLengthMin"))
        output_max = _decimal_price(tier.get("outputLengthMax"))
        if input_k < input_min:
            continue
        if input_max != Decimal("-1") and input_k >= input_max:
            continue
        if output_k < output_min:
            continue
        if output_max != Decimal("-1") and output_k >= output_max:
            continue
        return tier
    return None


def _decimal_price(value: Any) -> Decimal:
    return Decimal(str(value if value is not None else 0))


def _decimal_string(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quota_int(value: Any, *, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _upsert_daily_stats(
    cur: Any, settlement: dict[str, Any], total_cost: Decimal
) -> None:
    tokens_in = int(settlement.get("tokens_in") or 0)
    tokens_out = int(settlement.get("tokens_out") or 0)
    cache_read_tokens = int(settlement.get("cache_read_tokens") or 0)
    reasoning_tokens = int(settlement.get("reasoning_tokens") or 0)
    response_time_ms = int(settlement.get("response_time_ms") or 0)
    await cur.execute(
        """
        INSERT INTO lumax_usage_daily_stats (
            tenant_id, user_id, date, model_name,
            tokens_in_total, tokens_out_total, calls_count, avg_duration_ms,
            cache_read_total, reasoning_total, cost_total, created_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, 1, %s,
            %s, %s, %s, NOW()
        )
        ON CONFLICT (tenant_id, user_id, date, model_name) DO UPDATE SET
            tokens_in_total = lumax_usage_daily_stats.tokens_in_total + EXCLUDED.tokens_in_total,
            tokens_out_total = lumax_usage_daily_stats.tokens_out_total + EXCLUDED.tokens_out_total,
            avg_duration_ms = (
                (lumax_usage_daily_stats.avg_duration_ms * lumax_usage_daily_stats.calls_count)
                + EXCLUDED.avg_duration_ms
            ) / (lumax_usage_daily_stats.calls_count + 1),
            calls_count = lumax_usage_daily_stats.calls_count + 1,
            cache_read_total = COALESCE(lumax_usage_daily_stats.cache_read_total, 0) + EXCLUDED.cache_read_total,
            reasoning_total = COALESCE(lumax_usage_daily_stats.reasoning_total, 0) + EXCLUDED.reasoning_total,
            cost_total = COALESCE(lumax_usage_daily_stats.cost_total, 0) + EXCLUDED.cost_total
        """,
        (
            settlement["tenant_id"],
            settlement["user_id"],
            date.today(),
            settlement.get("model_name") or "",
            tokens_in,
            tokens_out,
            response_time_ms,
            cache_read_tokens,
            reasoning_tokens,
            total_cost,
        ),
    )


async def _consume_user_quota(
    cur: Any, tenant_id: str, user_id: str, username: Any, total_tokens: int
) -> None:
    if total_tokens <= 0:
        return
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    if normalized_tenant_id is None:
        raise RuntimeError("tenantId must not be less than 1")
    normalized_user_id = _normalize_user_id(user_id)
    if normalized_user_id is None:
        raise RuntimeError("userId must not be empty")
    if normalized_user_id == "-1":
        return

    await cur.execute(
        """
        SELECT total_quota, used_quota
        FROM lumax_user_quota
        WHERE tenant_id = %s AND user_id = %s
        FOR UPDATE
        """,
        (normalized_tenant_id, normalized_user_id),
    )
    quota = await cur.fetchone()

    if quota is None:
        raise RuntimeError(QUOTA_INSUFFICIENT_MESSAGE)

    total_quota = _quota_int(quota.get("total_quota"))
    if total_quota is None:
        raise RuntimeError(QUOTA_INSUFFICIENT_MESSAGE)
    if total_quota == -1:
        await cur.execute(
            """
            UPDATE lumax_user_quota
            SET used_quota = used_quota + %s, updated_at = NOW()
            WHERE tenant_id = %s AND user_id = %s
            """,
            (total_tokens, normalized_tenant_id, normalized_user_id),
        )
        return

    await cur.execute(
        """
        UPDATE lumax_user_quota
        SET used_quota = used_quota + %s, updated_at = NOW()
        WHERE tenant_id = %s AND user_id = %s
        """,
        (total_tokens, normalized_tenant_id, normalized_user_id),
    )
