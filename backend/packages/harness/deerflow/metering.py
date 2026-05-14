"""Run-scoped metering collection for Lumax settlement.

The callback records low-level LangChain activity. Final billing still happens
at the run boundary so retries and multiple model calls can be settled once.
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


@dataclass
class UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, usage: dict[str, int]) -> None:
        self.input_tokens += int(usage.get("input_tokens", 0) or 0)
        self.output_tokens += int(usage.get("output_tokens", 0) or 0)
        self.total_tokens += int(usage.get("total_tokens", 0) or 0)
        self.cache_read_tokens += int(usage.get("cache_read_tokens", 0) or 0)
        self.cache_write_tokens += int(usage.get("cache_write_tokens", 0) or 0)
        self.reasoning_tokens += int(usage.get("reasoning_tokens", 0) or 0)

    def as_dict(self) -> dict[str, int]:
        total = self.total_tokens or (self.input_tokens + self.output_tokens)
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "reasoning_tokens": self.reasoning_tokens,
        }


@dataclass
class MeteringRunContext:
    run_id: str
    thread_id: str
    tenant_id: str
    user_id: str
    username: str = ""
    dept_id: str = ""
    agent_name: str = ""
    skill_name: str = ""
    model_name: str = ""
    inference_mode: str = "online"
    started_at: float = field(default_factory=time.monotonic)
    usage: UsageTotals = field(default_factory=UsageTotals)
    tool_calls_count: int = 0
    errors: list[str] = field(default_factory=list)
    _counted_llm_runs: set[str] = field(default_factory=set)

    def record_usage(
        self, run_id: UUID | str | None, usage: dict[str, int], model_name: str = ""
    ) -> None:
        key = str(run_id) if run_id else ""
        if key and key in self._counted_llm_runs:
            return
        if key:
            self._counted_llm_runs.add(key)
        if model_name and not self.model_name:
            self.model_name = model_name
        self.usage.add(usage)

    def set_model_name(self, model_name: str | None) -> None:
        if model_name:
            self.model_name = model_name

    def record_tool_call(self) -> None:
        self.tool_calls_count += 1

    def record_error(self, error: BaseException | str) -> None:
        self.errors.append(str(error))

    @property
    def duration_ms(self) -> int:
        return max(0, int((time.monotonic() - self.started_at) * 1000))


_current_metering_context: ContextVar[MeteringRunContext | None] = ContextVar(
    "deerflow_lumax_metering_context",
    default=None,
)


def get_metering_context() -> MeteringRunContext | None:
    return _current_metering_context.get()


def set_metering_context(context: MeteringRunContext):
    return _current_metering_context.set(context)


def reset_metering_context(token) -> None:
    _current_metering_context.reset(token)


def set_metering_model_name(model_name: str | None) -> None:
    context = get_metering_context()
    if context is not None:
        context.set_model_name(model_name)


def _coerce_usage(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}

    input_tokens = raw.get("input_tokens", raw.get("prompt_tokens", 0)) or 0
    output_tokens = raw.get("output_tokens", raw.get("completion_tokens", 0)) or 0
    total_tokens = raw.get("total_tokens", 0) or 0
    details = raw.get("completion_tokens_details") or {}
    prompt_details = raw.get("prompt_tokens_details") or {}
    input_details = raw.get("input_token_details") or {}
    output_details = raw.get("output_token_details") or {}
    cache_read_tokens = int(
        raw.get(
            "cache_read_input_tokens",
            raw.get(
                "cache_read_tokens",
                raw.get(
                    "cached_tokens",
                    prompt_details.get(
                        "cached_tokens", input_details.get("cache_read", 0)
                    ),
                ),
            ),
        )
        or 0
    )
    cache_write_tokens = int(
        raw.get(
            "cache_creation_input_tokens",
            raw.get(
                "cache_write_tokens",
                input_details.get(
                    "cache_creation", input_details.get("cache_write", 0)
                ),
            ),
        )
        or 0
    )
    if "input_tokens" in raw and (
        "cache_read_input_tokens" in raw or "cache_creation_input_tokens" in raw
    ):
        input_tokens = int(input_tokens) + cache_read_tokens + cache_write_tokens
    reasoning_tokens = int(
        raw.get(
            "reasoning_tokens",
            details.get(
                "reasoning_tokens",
                output_details.get(
                    "reasoning", output_details.get("reasoning_tokens", 0)
                ),
            ),
        )
        or 0
    )
    computed_total_tokens = int(input_tokens) + int(output_tokens)
    normalized_total_tokens = int(total_tokens or 0)
    if normalized_total_tokens < computed_total_tokens:
        normalized_total_tokens = computed_total_tokens

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": normalized_total_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def _extract_usage_from_generation(generation: Any) -> tuple[dict[str, int], str]:
    message = getattr(generation, "message", None)
    if message is None:
        return {}, ""

    usage = _coerce_usage(getattr(message, "usage_metadata", None))
    response_metadata = getattr(message, "response_metadata", None) or {}
    token_usage = (
        response_metadata.get("token_usage") or response_metadata.get("usage") or {}
    )
    usage = {**_coerce_usage(token_usage), **{k: v for k, v in usage.items() if v}}
    return usage, str(response_metadata.get("model_name") or "")


def _extract_usage_from_llm_result(response: Any) -> tuple[dict[str, int], str]:
    llm_output = getattr(response, "llm_output", None) or {}
    usage = _coerce_usage(
        llm_output.get("token_usage") or llm_output.get("usage") or {}
    )
    model_name = str(llm_output.get("model_name") or "")

    for generations in getattr(response, "generations", []) or []:
        for generation in generations or []:
            generation_usage, generation_model = _extract_usage_from_generation(
                generation
            )
            if generation_usage:
                usage = {**usage, **{k: v for k, v in generation_usage.items() if v}}
            if generation_model and not model_name:
                model_name = generation_model

    return usage, model_name


class LumaxMeteringCallbackHandler(BaseCallbackHandler):
    """LangChain callback that records metering facts into the current run."""

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> Any:
        context = get_metering_context()
        if context is None:
            return None
        usage, model_name = _extract_usage_from_llm_result(response)
        if usage:
            context.record_usage(run_id, usage, model_name=model_name)
        return None

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> Any:
        context = get_metering_context()
        if context is not None:
            context.record_error(error)
        return None

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> Any:
        context = get_metering_context()
        if context is not None:
            context.record_tool_call()
        return None

    def on_tool_error(
        self, error: BaseException, *, run_id: UUID, **kwargs: Any
    ) -> Any:
        context = get_metering_context()
        if context is not None:
            context.record_tool_call()
            context.record_error(error)
        return None
