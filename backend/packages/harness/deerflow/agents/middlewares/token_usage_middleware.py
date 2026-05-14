"""Middleware for logging LLM token usage.

Final usage settlement is handled by the LangChain callback based metering
pipeline. This middleware intentionally does not report usage to lumax-service
to avoid double counting.
"""

import logging
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class TokenUsageMiddleware(AgentMiddleware):
    """Logs token usage from model response usage_metadata."""

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._log_usage(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._log_usage(state, runtime)

    def _log_usage(self, state: AgentState, runtime: Runtime) -> None:
        usage_data = self._extract_usage(state)
        if usage_data:
            logger.info(
                "LLM token usage: input=%s output=%s total=%s",
                usage_data.get("input_tokens", "?"),
                usage_data.get("output_tokens", "?"),
                usage_data.get("total_tokens", "?"),
            )
        return None

    def _extract_usage(self, state: AgentState) -> dict | None:
        messages = state.get("messages", [])
        if not messages:
            return None
        last = messages[-1]
        usage = getattr(last, "usage_metadata", None)
        if not usage:
            return None

        data = dict(usage)

        # LangChain / OpenAI 兼容格式中可能存在的扩展字段：
        #   cache_creation_input_tokens — 新写入缓存的 token
        #   cache_read_input_tokens    — 命中缓存的 token（Anthropic/火山方舟）
        #   reasoning_tokens           — 推理模型思考 token（DeepSeek-R1 等）
        # 部分供应商将这些放在 response_metadata 中
        resp_meta = getattr(last, "response_metadata", {}) or {}
        token_usage = resp_meta.get("token_usage") or resp_meta.get("usage") or {}

        data.setdefault("cache_read_input_tokens", token_usage.get("cache_read_input_tokens", 0))
        data.setdefault("cache_creation_input_tokens", token_usage.get("cache_creation_input_tokens", 0))

        reasoning = (
            token_usage.get("reasoning_tokens")
            or token_usage.get("completion_tokens_details", {}).get("reasoning_tokens")
            or data.get("reasoning_tokens")
            or 0
        )
        data["reasoning_tokens"] = reasoning

        return data
