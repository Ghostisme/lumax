import type { Message } from "@langchain/langgraph-sdk";
import { describe, expect, it } from "vitest";

import {
  extractFeedbackRunId,
  findMessageConversationIndex,
} from "@/core/messages/feedback-run-id";

const RUN = "645bd191-3312-4695-9cc2-7f2de0b0337b";

describe("extractFeedbackRunId", () => {
  it("extracts run_id from nested additional_kwargs.metadata on the assistant message", () => {
    const ai = {
      type: "ai",
      id: "1778468102271-0",
      content: "hi",
      additional_kwargs: { metadata: { run_id: RUN } },
    } as unknown as Message;

    expect(extractFeedbackRunId(ai)).toBe(RUN);
  });

  it("does not fall back to Redis-style message ids", () => {
    const ai = { type: "ai", id: "1778468102271-0", content: "x" } as Message;
    expect(extractFeedbackRunId(ai)).toBe(null);
  });

  it("resolves assistant run id from preceding human additional_kwargs.run_id", () => {
    const human = {
      type: "human",
      id: "h1",
      content: "q",
      additional_kwargs: { run_id: RUN },
    } as unknown as Message;
    const ai = { type: "ai", id: "a1", content: "a" } as Message;
    const conversation = [human, ai];

    expect(
      extractFeedbackRunId(ai, {
        conversationMessages: conversation,
        messageIndex: 1,
      }),
    ).toBe(RUN);
  });

  it("prioritizes streamMetadata from runs/stream chunks over message fields", () => {
    const streamRun = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    const ai = {
      type: "ai",
      id: "a",
      additional_kwargs: { metadata: { run_id: RUN } },
    } as unknown as Message;

    expect(
      extractFeedbackRunId(ai, {
        streamMetadata: { run_id: streamRun },
        conversationMessages: [ai],
      }),
    ).toBe(streamRun);
  });
});

describe("findMessageConversationIndex", () => {
  it("finds index by stable id when object references differ", () => {
    const m = { type: "ai", id: "same", content: "x" } as Message;
    const copy = { ...m } as Message;
    expect(findMessageConversationIndex([copy], m)).toBe(0);
  });
});
