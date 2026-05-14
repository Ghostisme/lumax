"""HTTP client for banned-words checking and hit reporting via lumax-service.

All matching logic lives in lumax-service; this module is a thin async
HTTP wrapper that signs requests with the shared HMAC secret.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
from dataclasses import dataclass
from time import time
from typing import Any

import httpx

from app.gateway.tenant import normalize_tenant_id

logger = logging.getLogger(__name__)

BANNED_WORD_FALLBACK_MESSAGES = (
    "无法提供相关内容",
    # "换个话题聊聊",
    # "这个话题暂时不能继续",
    "亲，当前对话中有敏感词哦，请核对后重新对话啦~"
)

MAX_RETRIES = 2


@dataclass(slots=True)
class BannedWordMatch:
    word_id: int
    category_id: int
    word: str
    matched_mode: str
    matched_sentence: str


@dataclass(slots=True)
class BannedWordsCheckResult:
    hit: bool
    matched_words: list[BannedWordMatch]
    skipped_modes: list[str]


_EMPTY_RESULT = BannedWordsCheckResult(hit=False, matched_words=[], skipped_modes=[])


class BannedWordsClient:
    """Singleton async HTTP client for the lumax-service banned-words API."""

    _instance: BannedWordsClient | None = None

    def __init__(self) -> None:
        self._base_url = os.getenv("LUMAX_SERVICE_URL", "https://dev-lumax.jialugroup.cn/api")
        self._internal_secret = os.getenv("LUMAX_INTERNAL_SECRET", "")
        self._enabled = os.getenv("BANNED_WORDS_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @classmethod
    def get_instance(cls) -> BannedWordsClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def check_text(
        self,
        *,
        tenant_id: str,
        text: str,
        trigger_mode: str = "input",
    ) -> BannedWordsCheckResult:
        """Check whether *text* contains banned words for *tenant_id*."""
        if not self._enabled:
            logger.debug("Banned words check skipped: disabled")
            return _EMPTY_RESULT

        normalized_tenant = normalize_tenant_id(tenant_id)
        if normalized_tenant is None or not str(text or "").strip():
            logger.debug(
                "Banned words check skipped: tenant=%r text_empty=%s",
                tenant_id,
                not str(text or "").strip(),
            )
            return _EMPTY_RESULT

        payload = {
            "tenantId": normalized_tenant,
            "text": text,
            "triggerMode": trigger_mode,
        }
        data: dict | None = None
        for attempt in range(MAX_RETRIES):
            try:
                data = await self._post("/lumax/v1/internal/check-banned-words", payload)
                break
            except Exception:
                logger.warning(
                    "Banned words check request failed (attempt %d/%d)",
                    attempt + 1,
                    MAX_RETRIES,
                    exc_info=True,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        if data is None:
            return _EMPTY_RESULT

        logger.info(
            "Banned words check response: tenant=%s text_len=%d hit=%s matched=%d",
            normalized_tenant,
            len(text),
            data.get("hit") if isinstance(data, dict) else "N/A",
            len(data.get("matchedWords") or []) if isinstance(data, dict) else 0,
        )

        if not isinstance(data, dict) or not data.get("hit"):
            return _EMPTY_RESULT

        matched_words = [
            BannedWordMatch(
                word_id=int(w.get("wordId", 0)),
                category_id=int(w.get("categoryId", 0)),
                word=str(w.get("word", "")),
                matched_mode=str(w.get("matchedMode", "")),
                matched_sentence=str(w.get("matchedSentence", "")),
            )
            for w in (data.get("matchedWords") or [])
            if isinstance(w, dict) and int(w.get("wordId", 0)) > 0
        ]

        return BannedWordsCheckResult(
            hit=bool(matched_words),
            matched_words=matched_words,
            skipped_modes=data.get("skippedModes") or [],
        )

    async def report_hit(
        self,
        *,
        tenant_id: str,
        user_id: str,
        word_id: int,
        category_id: int,
        thread_id: str = "",
        username: str = "",
        conversation_id: int | None = None,
        matched_word: str = "",
        matched_sentence: str = "",
        trigger_source: str = "input",
        matched_mode: str = "",
    ) -> None:
        """Fire-and-forget report of a banned-word hit to lumax-service."""
        payload: dict[str, Any] = {
            "tenantId": tenant_id,
            "wordId": word_id,
            "categoryId": category_id,
            "userId": user_id,
            "matchedWord": matched_word,
            "matchedSentence": matched_sentence,
            "triggerSource": trigger_source,
            "matchedMode": matched_mode,
        }
        if conversation_id is not None:
            payload["conversationId"] = conversation_id
        if thread_id:
            payload["threadId"] = thread_id
        for attempt in range(MAX_RETRIES):
            try:
                await self._post("/lumax/v1/collector/banned-word-hit", payload)
                return
            except Exception:
                logger.warning(
                    "Banned word hit report failed (attempt %d)",
                    attempt + 1,
                    exc_info=True,
                )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

    # ------------------------------------------------------------------
    # HTTP internals (mirrors UsageReporter._post_lumax / _signature_headers)
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: dict) -> dict:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(
            timeout=8.0, proxy=None, trust_env=False
        ) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=self._signature_headers(payload),
            )
        if resp.status_code < 200 or resp.status_code >= 300:
            raise RuntimeError(
                f"lumax-service returned HTTP {resp.status_code} for {path}"
            )

        data = resp.json()
        if isinstance(data, dict) and "code" in data:
            if data.get("code") != 0:
                raise RuntimeError(
                    str(data.get("msg") or "lumax-service business error")
                )
            result = data.get("data")
            return result if isinstance(result, dict) else {}
        return data if isinstance(data, dict) else {}

    def _signature_headers(self, payload: dict) -> dict[str, str]:
        if not self._internal_secret:
            return {}
        timestamp = str(int(time()))
        nonce_source = f"{timestamp}:{_canonical_json(payload)}".encode()
        nonce = hashlib.sha256(nonce_source).hexdigest()[:32]
        signed = f"{timestamp}.{nonce}.{_canonical_json(payload)}".encode()
        signature = hmac.new(
            self._internal_secret.encode(), signed, hashlib.sha256
        ).hexdigest()
        return {
            "X-Lumax-Timestamp": timestamp,
            "X-Lumax-Nonce": nonce,
            "X-Lumax-Signature": signature,
        }


def random_banned_word_reply() -> str:
    return random.choice(BANNED_WORD_FALLBACK_MESSAGES)


def _canonical_json(payload: dict) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
