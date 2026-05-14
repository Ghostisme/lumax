"""Async usage reporter for lumax metering."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from time import time
from typing import Any

import httpx

from app.gateway.lumax_db_metering import (
    check_quota_db,
    persist_settlement_db,
)
from app.gateway.tenant import normalize_tenant_id

logger = logging.getLogger(__name__)

MAX_BUFFER_SIZE = 1000
MAX_RETRIES = 3


class LumaxServiceError(RuntimeError):
    """Raised when lumax metering operations fail."""


@dataclass
class UsageRecord:
    tenant_id: str
    user_id: str
    thread_id: str
    model_name: str
    tokens_in: int
    tokens_out: int
    agent_name: str = ""
    skill_name: str = ""
    tool_calls_count: int = 0
    response_time_ms: int = 0
    conversation_id: int | None = None
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    inference_mode: str = "online"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class UsageSettlementMessage:
    message_id: str
    role: str
    content: str
    message_index: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class UsageSettlement:
    idempotency_key: str
    tenant_id: str
    user_id: str
    thread_id: str
    run_id: str
    model_name: str
    tokens_in: int
    tokens_out: int
    username: str = ""
    dept_id: str = ""
    title: str = ""
    tokens_total: int = 0
    agent_name: str = ""
    skill_name: str = ""
    tool_calls_count: int = 0
    response_time_ms: int = 0
    status: str = "completed"
    error_message: str | None = None
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    inference_mode: str = "online"
    messages: list[UsageSettlementMessage] = field(default_factory=list)


@dataclass
class AgentRunEvent:
    tenant_id: str
    user_id: str
    thread_id: str
    event_type: str
    agent_name: str = ""
    skill_name: str = ""
    model_name: str = ""
    status: str = ""
    duration_ms: int = 0
    tokens_total: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    run_id: int | None = None


class UsageReporter:
    """Async reporter that sends usage data to lumax-service or lumax DB."""

    _instance: UsageReporter | None = None

    def __init__(self):
        self._base_url = os.getenv("LUMAX_SERVICE_URL", "https://dev-lumax.jialugroup.cn/api")
        self._enabled = os.getenv("USAGE_REPORTING_ENABLED", "true").lower() == "true"
        self._internal_secret = os.getenv("LUMAX_INTERNAL_SECRET", "")
        self._db_dsn = os.getenv("LUMAX_DB_DSN", "").strip()
        self._db_mode_enabled = bool(self._db_dsn)
        self._buffer: deque[UsageRecord] = deque(maxlen=MAX_BUFFER_SIZE)
        self._event_buffer: deque[AgentRunEvent] = deque(maxlen=MAX_BUFFER_SIZE)

    @classmethod
    def get_instance(cls) -> UsageReporter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def report_usage(self, record: UsageRecord) -> None:
        if not self._enabled:
            return
        asyncio.create_task(self._send_usage(record))

    async def report_settlement(self, settlement: UsageSettlement) -> dict:
        if not self._enabled:
            logger.info("Usage settlement skipped: USAGE_REPORTING_ENABLED is false")
            return {}
        if self._db_mode_enabled:
            try:
                return await self._send_settlement_db(settlement)
            except Exception:
                logger.warning("DB settlement failed", exc_info=True)
                raise
        return await self._send_settlement(settlement)

    async def report_agent_event(self, event: AgentRunEvent) -> int | None:
        if not self._enabled:
            return None
        return await self._send_agent_event(event)

    async def _send_usage(self, record: UsageRecord) -> None:
        payload = {
            "tenantId": record.tenant_id,
            "userId": record.user_id,
            "threadId": record.thread_id,
            "modelName": record.model_name,
            "agentName": record.agent_name,
            "skillName": record.skill_name,
            "tokensIn": record.tokens_in,
            "tokensOut": record.tokens_out,
            "cacheReadTokens": record.cache_read_tokens,
            "cacheWriteTokens": record.cache_write_tokens,
            "reasoningTokens": record.reasoning_tokens,
            "inferenceMode": record.inference_mode,
            "toolCallsCount": record.tool_calls_count,
            "responseTimeMs": record.response_time_ms,
            "conversationId": record.conversation_id,
        }

        for attempt in range(MAX_RETRIES):
            try:
                await self._post_lumax("/lumax/v1/usage/report", payload)
                return
            except Exception:
                logger.warning(
                    "Usage report failed (attempt %d)", attempt + 1, exc_info=True
                )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

        self._buffer.append(record)
        logger.warning(
            "Usage record buffered locally (buffer size: %d)", len(self._buffer)
        )

    async def _send_settlement(self, settlement: UsageSettlement) -> dict:
        payload = {
            "idempotencyKey": settlement.idempotency_key,
            "tenantId": settlement.tenant_id,
            "userId": settlement.user_id,
            "threadId": settlement.thread_id,
            "runId": settlement.run_id,
            "modelName": settlement.model_name,
            "username": settlement.username,
            "deptId": settlement.dept_id,
            "agentName": settlement.agent_name,
            "skillName": settlement.skill_name,
            "title": settlement.title,
            "tokensIn": settlement.tokens_in,
            "tokensOut": settlement.tokens_out,
            "tokensTotal": settlement.tokens_total
            or (settlement.tokens_in + settlement.tokens_out),
            "cacheReadTokens": settlement.cache_read_tokens,
            "cacheWriteTokens": settlement.cache_write_tokens,
            "reasoningTokens": settlement.reasoning_tokens,
            "inferenceMode": settlement.inference_mode,
            "toolCallsCount": settlement.tool_calls_count,
            "responseTimeMs": settlement.response_time_ms,
            "status": settlement.status,
            "errorMessage": settlement.error_message,
            "messages": [
                {
                    "messageId": message.message_id,
                    "role": message.role,
                    "content": message.content,
                    "messageIndex": message.message_index,
                    "createdAt": message.created_at,
                }
                for message in settlement.messages
            ],
        }
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await self._post_lumax("/lumax/v1/usage/report", payload)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "用量结算失败（第 %d 次尝试）", attempt + 1, exc_info=True
                )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)
        raise LumaxServiceError(f"用量结算重试后仍失败：{last_error}") from last_error

    async def _send_agent_event(self, event: AgentRunEvent) -> int | None:
        payload = {
            "tenantId": event.tenant_id,
            "userId": event.user_id,
            "threadId": event.thread_id,
            "eventType": event.event_type,
            "agentName": event.agent_name,
            "skillName": event.skill_name,
            "modelName": event.model_name,
            "status": event.status,
            "durationMs": event.duration_ms,
            "tokensTotal": event.tokens_total,
            "tokensIn": event.tokens_in,
            "tokensOut": event.tokens_out,
            "toolCallsCount": event.tool_calls_count,
            "errorType": event.error_type,
            "errorMessage": event.error_message,
            "runId": event.run_id,
        }
        try:
            data = await self._post_lumax("/lumax/v1/agent-monitor/events", payload)
            return data.get("runId")
        except Exception:
            logger.warning("Agent event report failed", exc_info=True)
            self._event_buffer.append(event)
        return None

    async def check_quota(self, tenant_id: str, user_id: str) -> dict:
        """Check quota before agent execution."""
        user_id = _normalize_user_id(user_id)
        if user_id is None:
            return {"allowed": False, "remaining": 0, "message": "额度不足"}
        if user_id == "-1":
            return {"allowed": True, "remaining": -1, "message": "系统用户不限额"}

        if self._db_mode_enabled:
            try:
                return await self._check_quota_db(tenant_id, user_id)
            except Exception:
                logger.warning(
                    "DB quota check failed, fallback to lumax-service HTTP quota check",
                    exc_info=True,
                )

        try:
            return await self._post_lumax(
                "/lumax/v1/internal/check-quota",
                {"tenantId": tenant_id, "userId": user_id},
            )
        except Exception:
            logger.warning("Quota check failed, denying by default", exc_info=True)
        return {"allowed": False, "remaining": 0, "message": "额度不足"}

    async def _check_quota_db(self, tenant_id: str, user_id: str) -> dict:
        if not self._db_dsn:
            raise LumaxServiceError("LUMAX_DB_DSN is not configured")
        return await check_quota_db(self._db_dsn, tenant_id, user_id)

    async def _send_settlement_db(self, settlement: UsageSettlement) -> dict:
        if not self._db_dsn:
            raise LumaxServiceError("LUMAX_DB_DSN is not configured")
        return await persist_settlement_db(self._db_dsn, _settlement_payload(settlement))

    async def _post_lumax(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                json=payload,
                headers=self._signature_headers(payload),
            )

        if resp.status_code < 200 or resp.status_code >= 300:
            raise LumaxServiceError(f"lumax-service returned HTTP {resp.status_code}")

        data = resp.json()
        if isinstance(data, dict) and "code" in data:
            if data.get("code") != 0:
                raise LumaxServiceError(
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


def _settlement_payload(settlement: UsageSettlement) -> dict[str, Any]:
    return {
        "idempotency_key": settlement.idempotency_key,
        "tenant_id": settlement.tenant_id,
        "user_id": settlement.user_id,
        "username": settlement.username,
        "dept_id": settlement.dept_id,
        "thread_id": settlement.thread_id,
        "run_id": settlement.run_id,
        "model_name": settlement.model_name,
        "title": settlement.title,
        "tokens_in": settlement.tokens_in,
        "tokens_out": settlement.tokens_out,
        "tokens_total": settlement.tokens_total
        or (settlement.tokens_in + settlement.tokens_out),
        "agent_name": settlement.agent_name,
        "skill_name": settlement.skill_name,
        "tool_calls_count": settlement.tool_calls_count,
        "response_time_ms": settlement.response_time_ms,
        "status": settlement.status,
        "error_message": settlement.error_message,
        "cache_read_tokens": settlement.cache_read_tokens,
        "cache_write_tokens": settlement.cache_write_tokens,
        "reasoning_tokens": settlement.reasoning_tokens,
        "inference_mode": settlement.inference_mode,
        "messages": [
            {
                "message_id": message.message_id,
                "role": message.role,
                "content": message.content,
                "message_index": message.message_index,
                "created_at": message.created_at,
            }
            for message in settlement.messages
        ],
    }


def _normalize_user_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _canonical_json(payload: dict) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
