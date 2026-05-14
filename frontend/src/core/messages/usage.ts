import type { Message } from "@langchain/langgraph-sdk";

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toTokenCount(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/**
 * Extract usage_metadata from an AI message if present.
 * The field is added by the backend (PR #1218) but not typed in the SDK.
 */
export function getUsageMetadata(
  message: Message | null | undefined,
): TokenUsage | null {
  if (!isRecord(message) || message.type !== "ai") {
    return null;
  }

  const usage = message.usage_metadata;
  if (!isRecord(usage)) {
    return null;
  }

  return {
    inputTokens: toTokenCount(usage.input_tokens),
    outputTokens: toTokenCount(usage.output_tokens),
    totalTokens: toTokenCount(usage.total_tokens),
  };
}

/**
 * Accumulate token usage across all AI messages in a thread.
 */
export function accumulateUsage(
  messages: readonly (Message | null | undefined)[] | null | undefined,
): TokenUsage | null {
  const cumulative: TokenUsage = {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  };
  let hasUsage = false;
  for (const message of messages ?? []) {
    const usage = getUsageMetadata(message);
    if (usage) {
      hasUsage = true;
      cumulative.inputTokens += usage.inputTokens;
      cumulative.outputTokens += usage.outputTokens;
      cumulative.totalTokens += usage.totalTokens;
    }
  }
  return hasUsage ? cumulative : null;
}

/**
 * Format a token count for display: 1234 -> "1,234", 12345 -> "12.3K"
 */
export function formatTokenCount(count: number): string {
  if (count < 10_000) {
    return count.toLocaleString();
  }
  return `${(count / 1000).toFixed(1)}K`;
}
