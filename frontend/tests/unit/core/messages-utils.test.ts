import type { Message } from "@langchain/langgraph-sdk";
import { expect, test } from "vitest";

import {
  groupMessages,
  isHiddenFromUIMessage,
  isClarificationToolMessage,
} from "@/core/messages/utils";

test("isHiddenFromUIMessage hides summary messages without a backend hide flag", () => {
  const summaryMessage = {
    type: "human",
    name: "summary",
    content: "Here is a summary of the conversation to date:\n\nSESSION INTENT",
    additional_kwargs: {},
  } as Message;

  expect(isHiddenFromUIMessage(summaryMessage)).toBe(true);
});

test("groupMessages excludes summary messages without a backend hide flag", () => {
  const summaryMessage = {
    type: "human",
    name: "summary",
    content: "Here is a summary of the conversation to date:\n\nSUMMARY",
    additional_kwargs: {},
  } as Message;
  const visibleMessage = {
    type: "human",
    content: "帮我创建一个本地推项目",
    additional_kwargs: {},
  } as Message;

  const groups = groupMessages([summaryMessage, visibleMessage], (group) => ({
    type: group.type,
    contents: group.messages.map((message) => message.content),
  }));

  expect(groups).toHaveLength(1);
  expect(groups[0]).toEqual({
    type: "human",
    contents: ["帮我创建一个本地推项目"],
  });
  expect(JSON.stringify(groups)).not.toContain("SUMMARY");
});

test("isClarificationToolMessage recognizes structured clarification tool", () => {
  const structuredClarificationTool = {
    type: "tool",
    name: "structured_clarification",
    content: "营销场景是什么值？可选：直播、短视频/图文。",
    additional_kwargs: {},
  } as Message;

  expect(isClarificationToolMessage(structuredClarificationTool)).toBe(true);
});

test("groupMessages keeps hidden structured clarification tool as clarification group", () => {
  const hiddenStructuredClarificationTool = {
    type: "tool",
    name: "structured_clarification",
    content: "营销场景是什么值？可选：直播、短视频/图文。",
    additional_kwargs: { hide_from_ui: true },
    tool_call_id: "call_1",
    id: "tool_1",
  } as Message;

  const groups = groupMessages([hiddenStructuredClarificationTool], (group) => ({
    type: group.type,
    names: group.messages.map((message) => message.name ?? ""),
  }));

  expect(groups).toEqual([
    {
      type: "assistant:clarification",
      names: ["structured_clarification"],
    },
  ]);
});

test("groupMessages suppresses assistant echo after clarification tool", () => {
  const clarificationTool = {
    type: "tool",
    name: "structured_clarification",
    content: "营销场景是什么值？可选：直播、短视频/图文。",
    additional_kwargs: { hide_from_ui: true },
    tool_call_id: "call_1",
    id: "tool_1",
  } as Message;
  const assistantEcho = {
    type: "ai",
    name: undefined,
    content:
      "创建本地推项目需要指定营销场景，请告诉我这个项目的营销场景是什么？您可以选择直播或短视频/图文。",
    additional_kwargs: {},
    id: "ai_1",
  } as Message;

  const groups = groupMessages([clarificationTool, assistantEcho], (group) => ({
    type: group.type,
    names: group.messages.map((message) => message.name ?? ""),
  }));

  expect(groups).toEqual([
    {
      type: "assistant:clarification",
      names: ["structured_clarification"],
    },
  ]);
});

test("groupMessages does not suppress assistant after user answers clarification", () => {
  const clarificationTool = {
    type: "tool",
    name: "structured_clarification",
    content: "营销场景是什么值？可选：直播、短视频/图文。",
    additional_kwargs: { hide_from_ui: true },
    tool_call_id: "call_1",
    id: "tool_1",
  } as Message;
  const userAnswer = {
    type: "human",
    name: "user-input",
    content: "营销场景：LIVE（直播）",
    additional_kwargs: {},
    id: "human_1",
  } as Message;
  const assistantReply = {
    type: "ai",
    name: undefined,
    content: "继续创建项目，请补充营销目的。",
    additional_kwargs: {},
    id: "ai_1",
  } as Message;

  const groups = groupMessages(
    [clarificationTool, userAnswer, assistantReply],
    (group) => ({
      type: group.type,
      contents: group.messages.map((message) => message.content),
    }),
  );

  expect(groups).toEqual([
    {
      type: "assistant:clarification",
      contents: ["营销场景是什么值？可选：直播、短视频/图文。"],
    },
    {
      type: "human",
      contents: ["营销场景：LIVE（直播）"],
    },
    {
      type: "assistant",
      contents: ["继续创建项目，请补充营销目的。"],
    },
  ]);
});
