import type { Message } from "@langchain/langgraph-sdk";
import { expect, test } from "vitest";

import { accumulateUsage, getUsageMetadata } from "@/core/messages/usage";

test("getUsageMetadata ignores missing and non-AI messages", () => {
  expect(getUsageMetadata(undefined)).toBeNull();
  expect(getUsageMetadata(null)).toBeNull();
  expect(
    getUsageMetadata({
      type: "human",
      content: "hello",
      additional_kwargs: {},
    } as Message),
  ).toBeNull();
});

test("getUsageMetadata reads numeric AI usage metadata", () => {
  const message = {
    type: "ai",
    content: "hello",
    additional_kwargs: {},
    usage_metadata: {
      input_tokens: 12,
      output_tokens: 34,
      total_tokens: 46,
    },
  } as Message;

  expect(getUsageMetadata(message)).toEqual({
    inputTokens: 12,
    outputTokens: 34,
    totalTokens: 46,
  });
});

test("accumulateUsage skips missing messages while summing AI usage", () => {
  const messages = [
    undefined,
    {
      type: "human",
      content: "hello",
      additional_kwargs: {},
    } as Message,
    {
      type: "ai",
      content: "first",
      additional_kwargs: {},
      usage_metadata: {
        input_tokens: 1,
        output_tokens: 2,
        total_tokens: 3,
      },
    } as Message,
    {
      type: "ai",
      content: "second",
      additional_kwargs: {},
      usage_metadata: {
        input_tokens: 4,
        output_tokens: 5,
        total_tokens: 9,
      },
    } as Message,
  ];

  expect(accumulateUsage(messages)).toEqual({
    inputTokens: 5,
    outputTokens: 7,
    totalTokens: 12,
  });
});
