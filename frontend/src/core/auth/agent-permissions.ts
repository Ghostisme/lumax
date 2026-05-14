import { getAuthApiBaseURL } from "@/core/config";

import { fetchWithAuth } from "./request";

export const AGENT_CAPABILITY_REGISTRY = {
  10001: "aiChat",
  20001: "smartDistribution",
  30001: "contentFactory",
} as const;

export type AgentCapabilityKey =
  (typeof AGENT_CAPABILITY_REGISTRY)[keyof typeof AGENT_CAPABILITY_REGISTRY];

export type AgentCapabilityFlags = Record<AgentCapabilityKey, boolean>;

export const AGENT_CAPABILITY_KEYS = Array.from(
  new Set(Object.values(AGENT_CAPABILITY_REGISTRY)),
) as AgentCapabilityKey[];

export type TenantAiAgentVO = {
  agentCode?: number;
  agentIntro?: string;
  agentLogo?: string;
  agentName?: string;
  aiCapabilityCode?: number;
  aiCode?: number;
  id?: number;
  selected?: number;
  [property: string]: unknown;
};

type AvailableAgentsResponse = {
  code?: number;
  data?: TenantAiAgentVO[];
  msg?: string;
  [property: string]: unknown;
};

export type AvailableAgentPermissions = {
  capabilities: AgentCapabilityFlags;
  items: TenantAiAgentVO[];
};

function normalizeNumericCode(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return undefined;
    }
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeCapabilityCode(item: TenantAiAgentVO): number | undefined {
  return (
    normalizeNumericCode(item.agentCode) ??
    normalizeNumericCode(item.aiCapabilityCode) ??
    normalizeNumericCode(item.aiCode)
  );
}

export function createEmptyAgentCapabilities(): AgentCapabilityFlags {
  return AGENT_CAPABILITY_KEYS.reduce((acc, key) => {
    acc[key] = false;
    return acc;
  }, {} as AgentCapabilityFlags);
}

export function canAgentCapability(
  capabilities: Partial<Record<AgentCapabilityKey, boolean>> | null | undefined,
  capability: AgentCapabilityKey,
): boolean {
  return Boolean(capabilities?.[capability]);
}

export function resolveAgentCapabilities(
  items: TenantAiAgentVO[],
): AgentCapabilityFlags {
  const capabilities = createEmptyAgentCapabilities();
  for (const item of items) {
    const capabilityCode = normalizeCapabilityCode(item);
    if (capabilityCode === undefined) {
      continue;
    }
    const capability =
      AGENT_CAPABILITY_REGISTRY[
        capabilityCode as keyof typeof AGENT_CAPABILITY_REGISTRY
      ];
    if (capability) {
      capabilities[capability] = true;
    }
  }
  return capabilities;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function parseAvailableAgentsBody(body: unknown): AvailableAgentsResponse {
  if (!isRecord(body)) {
    throw new Error("智能体权限响应格式无效");
  }
  return body as AvailableAgentsResponse;
}

export async function fetchAvailableAgentPermissions(): Promise<AvailableAgentPermissions> {
  const response = await fetchWithAuth(
    `${getAuthApiBaseURL()}/api/admin/user/availableAgents`,
  );
  const body = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error("获取智能体权限失败");
  }

  const parsedBody = parseAvailableAgentsBody(body);
  if (typeof parsedBody.code === "number" && parsedBody.code !== 0) {
    throw new Error(parsedBody.msg?.trim() ?? "获取智能体权限失败");
  }

  const items = Array.isArray(parsedBody.data) ? parsedBody.data : null;
  if (!items) {
    throw new Error("智能体权限数据缺失");
  }

  return {
    items,
    capabilities: resolveAgentCapabilities(items),
  };
}
