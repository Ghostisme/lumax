import { describe, expect, it } from "vitest";

import {
  configureSpeechRecognitionMode,
  shouldFallbackToSingleShotRecognition,
} from "@/components/ai-elements/prompt-input";

describe("speech recognition fallback", () => {
  it("detects realtime streaming unsupported ASR errors", () => {
    expect(
      shouldFallbackToSingleShotRecognition({
        event: "error",
        message: "current ASR strategy does not support realtime streaming",
      }),
    ).toBe(true);
  });

  it("configures single-shot recognition without realtime streaming flags", () => {
    const recognition = {
      continuous: true,
      interimResults: true,
    };

    configureSpeechRecognitionMode(recognition, "single-shot");

    expect(recognition.continuous).toBe(false);
    expect(recognition.interimResults).toBe(false);
  });
});
