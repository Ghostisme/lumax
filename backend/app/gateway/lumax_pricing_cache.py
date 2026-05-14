"""Redis-backed Lumax model pricing cache reader."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.gateway.redis_client import GatewayRedis
from app.gateway.tenant import GLOBAL_TENANT_ID, normalize_tenant_id

logger = logging.getLogger(__name__)

CACHE_KEY_SEGMENT = "lumax:model_pricing"


class PricingCacheError(RuntimeError):
    """Raised when model pricing cannot be loaded from Redis."""


class ModelPricingCache:
    """Read model pricing JSON written by lumax-service."""

    _instance: ModelPricingCache | None = None

    def __init__(self, redis_client: Any | None = None) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            self._redis = GatewayRedis.get_client()

    @classmethod
    def get_instance(cls) -> ModelPricingCache:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_pricing(self, *, tenant_id: str, model_name: str) -> dict[str, Any]:
        model_code = str(model_name or "").strip()
        tenant_id = normalize_tenant_id(tenant_id)
        if tenant_id is None:
            raise PricingCacheError("tenant_id must be positive")
        if not model_code:
            raise PricingCacheError("model_name is required for pricing lookup")
        if self._redis is None:
            raise PricingCacheError("Redis client is not configured for pricing lookup")

        keys = [
            f"{tenant_id}:{CACHE_KEY_SEGMENT}:{model_code}",
            f"{GLOBAL_TENANT_ID}:{CACHE_KEY_SEGMENT}:{model_code}",
        ]
        for key in keys:
            raw = await self._read_key(key)
            if raw is None:
                continue
            parsed = _parse_json(raw)
            if isinstance(parsed, dict):
                return parsed
            raise PricingCacheError(f"invalid model pricing payload: key={key}")

        raise PricingCacheError(
            f"模型计费信息未配置：租户ID={tenant_id}，模型={model_code}"
        )

    async def _read_key(self, key: str) -> Any:
        try:
            return await self._redis.get(key)
        except Exception as exc:
            logger.warning(
                "Failed to read model pricing from Redis: key=%s", key, exc_info=True
            )
            raise PricingCacheError(
                f"failed to read model pricing from Redis: key={key}"
            ) from exc


async def get_model_pricing(*, tenant_id: str, model_name: str) -> dict[str, Any]:
    return await ModelPricingCache.get_instance().get_pricing(
        tenant_id=tenant_id, model_name=model_name
    )


def _parse_json(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray, memoryview)):
        return json.loads(bytes(raw).decode("utf-8"))
    if isinstance(raw, str):
        return json.loads(raw)
    return raw
