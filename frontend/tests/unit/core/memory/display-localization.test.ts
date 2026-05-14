import { describe, expect, test } from "vitest";

import { localizeMemoryTextForDisplay } from "@/core/memory/display-localization";

describe("localizeMemoryTextForDisplay", () => {
  test("keeps original text for non-zh locale", () => {
    const input =
      "User is comfortable communicating in Chinese, as indicated by the initial test message.";
    expect(localizeMemoryTextForDisplay(input, "en-US")).toBe(input);
  });

  test("translates known memory summary sentence in zh locale", () => {
    const input =
      "User is comfortable communicating in Chinese, as indicated by the initial test message.";
    expect(localizeMemoryTextForDisplay(input, "zh-CN")).toBe(
      "用户更习惯使用中文沟通，这一点可从初始测试消息中看出。",
    );
  });

  test("keeps chinese text unchanged in zh locale", () => {
    const input = "用户目前处于初步探索阶段。";
    expect(localizeMemoryTextForDisplay(input, "zh-CN")).toBe(input);
  });
});
