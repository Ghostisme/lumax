import type { Message } from "@langchain/langgraph-sdk";

export function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function recordValue(value: unknown, key: string): unknown {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return undefined;
  }
  return (value as Record<string, unknown>)[key];
}

export function normalizeFeedbackRunId(value: unknown): string | null {
  const runId = stringValue(value);
  if (!runId) {
    return null;
  }

  const queryIndex = runId.indexOf("?");
  if (queryIndex >= 0) {
    const queryRunId = new URLSearchParams(runId.slice(queryIndex + 1))
      .get("run_id")
      ?.trim();
    if (queryRunId) {
      return queryRunId;
    }
  }

  const path = runId.split(/[?#]/, 1)[0]?.trim() ?? "";
  const runsIndex = path.lastIndexOf("/runs/");
  if (runsIndex >= 0) {
    return path.slice(runsIndex + "/runs/".length).split("/", 1)[0] ?? null;
  }

  return path.startsWith("lc_run--") ? path.slice("lc_run--".length) : path;
}

export type FeedbackRunResolutionOptions = {
  /** Thread messages in display order (same array as the stream `messages`). */
  conversationMessages?: Message[];
  /** Index of this message in `conversationMessages`, when already known. */
  messageIndex?: number;
  /**
   * LangGraph SDK per-message stream metadata from
   * `thread.getMessagesMetadata(message, index)?.streamMetadata`
   * (backed by `runs/stream` message chunks; may echo `run_id`).
   */
  streamMetadata?: unknown;
};

const NEST_RUN_ID_KEYS = [
  "metadata",
  "additional_kwargs",
  "response_metadata",
  "kwargs",
] as const;

function extractRunIdFromNestedObjects(root: unknown, maxDepth: number): string | null {
  const stack: Array<{ node: unknown; depth: number }> = [{ node: root, depth: 0 }];
  const seen = new Set<unknown>();

  while (stack.length > 0) {
    const { node, depth } = stack.pop()!;
    if (node == null || depth > maxDepth) {
      continue;
    }
    if (typeof node !== "object") {
      continue;
    }
    if (seen.has(node)) {
      continue;
    }
    seen.add(node);

    if (Array.isArray(node)) {
      for (let i = node.length - 1; i >= 0; i -= 1) {
        stack.push({ node: node[i], depth: depth + 1 });
      }
      continue;
    }

    const o = node as Record<string, unknown>;
    const direct =
      normalizeFeedbackRunId(o.run_id) ?? normalizeFeedbackRunId(o.runId);
    if (direct) {
      return direct;
    }

    for (const key of NEST_RUN_ID_KEYS) {
      if (key in o) {
        stack.push({ node: o[key], depth: depth + 1 });
      }
    }
  }

  return null;
}

function runIdFromDirectMessageFields(message: Message): string | null {
  const responseMetadata = recordValue(message, "response_metadata");
  const additionalKwargs = recordValue(message, "additional_kwargs");
  const metadata = recordValue(message, "metadata");

  return (
    normalizeFeedbackRunId(recordValue(message, "run_id")) ??
    normalizeFeedbackRunId(recordValue(message, "runId")) ??
    normalizeFeedbackRunId(recordValue(responseMetadata, "run_id")) ??
    normalizeFeedbackRunId(recordValue(responseMetadata, "runId")) ??
    normalizeFeedbackRunId(recordValue(additionalKwargs, "run_id")) ??
    normalizeFeedbackRunId(recordValue(additionalKwargs, "runId")) ??
    normalizeFeedbackRunId(recordValue(metadata, "run_id")) ??
    normalizeFeedbackRunId(recordValue(metadata, "runId"))
  );
}

export function findMessageConversationIndex(
  conversationMessages: Message[],
  message: Message,
): number {
  const id = typeof message?.id === "string" ? message.id : undefined;
  if (id !== undefined && id !== "") {
    const byId = conversationMessages.findIndex((m) => m?.id === id);
    if (byId >= 0) {
      return byId;
    }
  }
  const byRef = conversationMessages.indexOf(message);
  return byRef >= 0 ? byRef : -1;
}

function extractRunIdFromPrecedingHumanTurn(
  conversationMessages: Message[],
  messageIndex: number,
): string | null {
  if (messageIndex <= 0) {
    return null;
  }
  for (let i = messageIndex - 1; i >= 0; i -= 1) {
    const m = conversationMessages[i];
    if (!m) {
      continue;
    }
    const t = m.type;
    if (t === "human") {
      return runIdFromDirectMessageFields(m) ?? extractRunIdFromNestedObjects(m, 8);
    }
  }
  return null;
}

/**
 * Resolves the LangGraph run id for feedback.
 *
 * Priority: stream chunk metadata → fields on the message (including nested
 * `metadata` / `additional_kwargs`) → same-turn human message (backend injects
 * `run_id` into the user message `additional_kwargs`).
 *
 * Does not fall back to `message.id` (often a Redis stream id like `…-0`, not a run UUID).
 */
export function extractFeedbackRunId(
  message: Message,
  options?: FeedbackRunResolutionOptions,
): string | null {
  const fromStreamMeta = extractRunIdFromNestedObjects(options?.streamMetadata, 6);
  if (fromStreamMeta) {
    return fromStreamMeta;
  }

  const fromMessage =
    runIdFromDirectMessageFields(message) ?? extractRunIdFromNestedObjects(message, 10);
  if (fromMessage) {
    return fromMessage;
  }

  const conversation = options?.conversationMessages;
  if (!conversation?.length) {
    return null;
  }

  const idx =
    typeof options?.messageIndex === "number" && options.messageIndex >= 0
      ? options.messageIndex
      : findMessageConversationIndex(conversation, message);

  if (idx < 0) {
    return null;
  }

  if (message.type === "ai") {
    return extractRunIdFromPrecedingHumanTurn(conversation, idx);
  }

  return null;
}
