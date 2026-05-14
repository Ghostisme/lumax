"""Centralised async Redis client for the Lumax gateway.

All gateway modules that need Redis should obtain the client through
:class:`GatewayRedis` rather than building their own connection.  The
singleton is created lazily on first access so that every consumer shares
the exact same underlying connection pool.

When a Redis operation fails with a connection error, callers should invoke
``GatewayRedis.reconnect()`` to discard the dead client and build a fresh
one on the next ``get_client()`` call.

Environment variables
---------------------
* ``AUTH_REDIS_URL``          – full URL (takes precedence)
* ``AUTH_REDIS_HOST``         – host (required when URL is absent)
* ``AUTH_REDIS_PORT``         – port (default ``6379``)
* ``AUTH_REDIS_DB``           – database index (default ``0``)
* ``AUTH_REDIS_USERNAME``     – username (optional)
* ``AUTH_REDIS_PASSWORD``     – password (optional)

Legacy ``REDIS_URL`` is accepted as a fallback for ``AUTH_REDIS_URL``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import redis.asyncio as redis_asyncio
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import RedisError
    from redis.exceptions import TimeoutError as RedisTimeoutError
except Exception:  # pragma: no cover - optional dependency
    redis_asyncio = None
    RedisConnectionError = type("RedisConnectionError", (Exception,), {})
    RedisError = type("RedisError", (Exception,), {})
    RedisTimeoutError = type("RedisTimeoutError", (Exception,), {})

logger = logging.getLogger(__name__)


def is_redis_connection_error(exc: BaseException) -> bool:
    """Return True if *exc* indicates a broken or unusable Redis connection.

    Includes read/write timeouts so the auth layer can reconnect and retry once
    instead of returning 401 and logging a false \"unexpected\" error.
    """
    return isinstance(
        exc,
        (
            RedisConnectionError,
            RedisTimeoutError,
            ConnectionError,
            OSError,
            TimeoutError,
        ),
    )


class GatewayRedis:
    """Module-level singleton async Redis client manager.

    All consumers call ``GatewayRedis.get_client()`` to obtain the shared
    Redis connection.  If the connection breaks, call ``reconnect()`` to
    rebuild the client on the next access.

    In tests, call ``GatewayRedis.reset(my_fake_redis)`` to inject a fake.
    """

    _client: Any | None = None
    _initialised: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get_client(cls) -> Any | None:
        """Return the shared async Redis client (lazy init on first call)."""
        if not cls._initialised:
            cls._client = _build_redis_client_from_env()
            cls._initialised = True
            logger.info(
                "GatewayRedis client %s",
                "created" if cls._client is not None else "not configured (no AUTH_REDIS_*)",
            )
        return cls._client

    @classmethod
    def reconnect(cls) -> Any | None:
        """Discard the current client and build a fresh one.

        Returns the newly created client (or ``None``).
        """
        old = cls._client
        cls._client = None
        cls._initialised = False
        logger.warning("GatewayRedis: discarding dead client, will rebuild on next access")
        if old is not None:
            try:
                import asyncio
                asyncio.get_event_loop().create_task(_safe_close(old))
            except Exception:
                pass
        return cls.get_client()

    @classmethod
    def reset(cls, redis_client: Any | None = None) -> None:
        """Replace the shared client — intended for tests."""
        cls._client = redis_client
        cls._initialised = True

    def __bool__(self) -> bool:
        return self.get_client() is not None


async def _safe_close(client: Any) -> None:
    """Best-effort close of an old redis client."""
    try:
        await client.aclose()
    except Exception:
        pass


def _build_redis_client_from_env() -> Any | None:
    """Build an async Redis client from ``AUTH_REDIS_*`` environment variables.

    The connection is created with health-check and retry options so that
    transient network blips or idle-timeout disconnects are handled
    transparently without surfacing 401 errors to end users.

    Returns ``None`` when:
    * ``redis`` package is not installed, or
    * neither ``AUTH_REDIS_URL`` nor ``AUTH_REDIS_HOST`` is set.
    """
    if redis_asyncio is None:
        return None

    _retry: Any = None
    try:
        from redis.backoff import ExponentialBackoff
        from redis.retry import Retry

        _retry = Retry(ExponentialBackoff(cap=2, base=0.1), retries=3)
    except ImportError:
        pass

    _pool_kwargs: dict[str, Any] = dict(
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=15,
    )
    if _retry is not None:
        _pool_kwargs["retry"] = _retry
        _pool_kwargs["retry_on_error"] = [
            RedisConnectionError,
            RedisTimeoutError,
            ConnectionError,
            OSError,
        ]

    redis_url = os.getenv("AUTH_REDIS_URL") or os.getenv("REDIS_URL")
    if redis_url:
        return redis_asyncio.from_url(redis_url, **_pool_kwargs)

    host = os.getenv("AUTH_REDIS_HOST")
    if not host:
        return None

    return redis_asyncio.Redis(
        host=host,
        port=int(os.getenv("AUTH_REDIS_PORT", "6379")),
        db=int(os.getenv("AUTH_REDIS_DB", "0")),
        username=os.getenv("AUTH_REDIS_USERNAME") or None,
        password=os.getenv("AUTH_REDIS_PASSWORD") or None,
        **_pool_kwargs,
    )
