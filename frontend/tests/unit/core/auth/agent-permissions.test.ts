import { describe, expect, test } from "vitest";

import { resolveAgentCapabilities } from "@/core/auth/agent-permissions";

const AI_CAPABILITY_CHAT = 10001;
const AI_CAPABILITY_SMART_DISTRIBUTION = 20001;
const AI_CAPABILITY_CONTENT_FACTORY = 30001;

describe("resolveAgentCapabilities", () => {
  test("maps capabilities by agentCode even when selected is 0", () => {
    const result = resolveAgentCapabilities([
      { agentCode: AI_CAPABILITY_CHAT, selected: 0 },
      { agentCode: AI_CAPABILITY_SMART_DISTRIBUTION, selected: 0 },
    ]);

    expect(result).toEqual({
      aiChat: true,
      smartDistribution: true,
      contentFactory: false,
    });
  });

  test("supports aiCapabilityCode/aiCode fallback and ignores unknown code", () => {
    const result = resolveAgentCapabilities([
      { aiCapabilityCode: AI_CAPABILITY_SMART_DISTRIBUTION, selected: 0 },
      { aiCode: AI_CAPABILITY_CONTENT_FACTORY, selected: 0 },
      { agentCode: 10001, selected: 0 },
      { aiCode: 9999, selected: 0 },
    ]);

    expect(result).toEqual({
      aiChat: true,
      smartDistribution: true,
      contentFactory: true,
    });
  });
});
