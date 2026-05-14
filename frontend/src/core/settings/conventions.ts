export const SESSION_CONVENTIONS_KEY = "deerflow.session-conventions";
export const SESSION_CONVENTIONS_VERSION = "1.0.0";

export type ConventionConflictResolution =
  | "keepExisting"
  | "useIncoming"
  | "mergeContent";

export interface SessionConventionItem {
  id: string;
  topic: string;
  content: string;
  updatedAt: string;
}

export interface SessionConventionsSnapshot {
  version: string;
  lastUpdated: string;
  items: SessionConventionItem[];
}

export interface MergedConventionItem extends SessionConventionItem {
  source: "repo" | "session";
}

export interface SessionConventionConflict {
  topic: string;
  existing: SessionConventionItem;
  incoming: SessionConventionItem;
}

export const REPO_BASELINE_CONVENTIONS: readonly SessionConventionItem[] = [
  {
    id: "repo-architecture-boundary",
    topic: "Architecture Boundary",
    content:
      "Keep page-level routing in src/app and business logic in src/core; do not move thread ownership boundaries without explicit request.",
    updatedAt: "2026-04-24T00:00:00.000Z",
  },
  {
    id: "repo-settings-persistence",
    topic: "Settings Persistence",
    content:
      "Use core/settings for local persistent preferences and prefix localStorage keys with deerflow.",
    updatedAt: "2026-04-24T00:00:00.000Z",
  },
  {
    id: "repo-i18n-required",
    topic: "I18N Required",
    content:
      "Any user-facing text in settings and memory flows must have en-US and zh-CN translations.",
    updatedAt: "2026-04-24T00:00:00.000Z",
  },
] as const;

const EMPTY_SNAPSHOT: SessionConventionsSnapshot = {
  version: SESSION_CONVENTIONS_VERSION,
  lastUpdated: "",
  items: [],
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function normalizeTopic(topic: string): string {
  return topic.trim().toLowerCase();
}

function normalizeContent(content: string): string {
  return content.trim().replace(/\s+/g, " ");
}

function createId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

function normalizeItem(item: SessionConventionItem): SessionConventionItem {
  return {
    ...item,
    topic: item.topic.trim(),
    content: item.content.trim(),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSessionConventionItem(value: unknown): value is SessionConventionItem {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.topic === "string" &&
    typeof value.content === "string" &&
    typeof value.updatedAt === "string"
  );
}

export function isSessionConventionsSnapshot(
  value: unknown,
): value is SessionConventionsSnapshot {
  return (
    isRecord(value) &&
    typeof value.version === "string" &&
    typeof value.lastUpdated === "string" &&
    Array.isArray(value.items) &&
    value.items.every(isSessionConventionItem)
  );
}

export function getSessionConventions(): SessionConventionsSnapshot {
  if (!isBrowser()) {
    return EMPTY_SNAPSHOT;
  }

  const raw = localStorage.getItem(SESSION_CONVENTIONS_KEY);
  if (!raw) {
    return EMPTY_SNAPSHOT;
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isSessionConventionsSnapshot(parsed)) {
      return EMPTY_SNAPSHOT;
    }
    return {
      version: parsed.version || SESSION_CONVENTIONS_VERSION,
      lastUpdated: parsed.lastUpdated || "",
      items: parsed.items.map(normalizeItem),
    };
  } catch {
    return EMPTY_SNAPSHOT;
  }
}

export function saveSessionConventions(snapshot: SessionConventionsSnapshot) {
  if (!isBrowser()) {
    return;
  }
  localStorage.setItem(SESSION_CONVENTIONS_KEY, JSON.stringify(snapshot));
}

function touchSnapshot(items: SessionConventionItem[]): SessionConventionsSnapshot {
  return {
    version: SESSION_CONVENTIONS_VERSION,
    lastUpdated: new Date().toISOString(),
    items,
  };
}

export function upsertSessionConvention(
  snapshot: SessionConventionsSnapshot,
  input: Pick<SessionConventionItem, "topic" | "content"> & { id?: string },
): SessionConventionsSnapshot {
  const topic = input.topic.trim();
  const content = input.content.trim();
  if (!topic || !content) {
    return snapshot;
  }

  const updatedAt = new Date().toISOString();
  const nextItem: SessionConventionItem = {
    id: input.id ?? createId("session"),
    topic,
    content,
    updatedAt,
  };

  const nextItems = [...snapshot.items];
  const indexById = nextItems.findIndex((item) => item.id === nextItem.id);
  if (indexById >= 0) {
    nextItems[indexById] = nextItem;
    return touchSnapshot(nextItems);
  }

  const indexByTopic = nextItems.findIndex(
    (item) => normalizeTopic(item.topic) === normalizeTopic(topic),
  );
  if (indexByTopic >= 0) {
    const existingTopicItem = nextItems[indexByTopic];
    if (!existingTopicItem) {
      return snapshot;
    }
    nextItems[indexByTopic] = {
      ...nextItem,
      id: existingTopicItem.id,
    };
    return touchSnapshot(nextItems);
  }

  nextItems.unshift(nextItem);
  return touchSnapshot(nextItems);
}

export function deleteSessionConvention(
  snapshot: SessionConventionsSnapshot,
  id: string,
): SessionConventionsSnapshot {
  const nextItems = snapshot.items.filter((item) => item.id !== id);
  if (nextItems.length === snapshot.items.length) {
    return snapshot;
  }
  return touchSnapshot(nextItems);
}

export function detectSessionConventionConflicts(
  existing: SessionConventionItem[],
  incoming: SessionConventionItem[],
): SessionConventionConflict[] {
  const byTopic = new Map(
    existing.map((item) => [normalizeTopic(item.topic), normalizeItem(item)]),
  );
  const conflicts: SessionConventionConflict[] = [];

  for (const candidate of incoming) {
    const normalizedCandidate = normalizeItem(candidate);
    const key = normalizeTopic(normalizedCandidate.topic);
    const current = byTopic.get(key);
    if (!current) {
      continue;
    }
    if (normalizeContent(current.content) !== normalizeContent(candidate.content)) {
      conflicts.push({
        topic: normalizedCandidate.topic,
        existing: current,
        incoming: normalizedCandidate,
      });
    }
  }

  return conflicts;
}

export function mergeSessionConventionItems(
  existing: SessionConventionItem[],
  incoming: SessionConventionItem[],
  resolution: ConventionConflictResolution,
): SessionConventionItem[] {
  const byTopic = new Map<string, SessionConventionItem>(
    existing.map((item) => [normalizeTopic(item.topic), normalizeItem(item)]),
  );

  for (const rawIncoming of incoming) {
    const nextIncoming = normalizeItem(rawIncoming);
    if (!nextIncoming.topic || !nextIncoming.content) {
      continue;
    }

    const key = normalizeTopic(nextIncoming.topic);
    const current = byTopic.get(key);
    if (!current) {
      byTopic.set(key, {
        ...nextIncoming,
        id: nextIncoming.id || createId("session"),
        updatedAt: nextIncoming.updatedAt || new Date().toISOString(),
      });
      continue;
    }

    if (normalizeContent(current.content) === normalizeContent(nextIncoming.content)) {
      continue;
    }

    if (resolution === "keepExisting") {
      continue;
    }

    if (resolution === "useIncoming") {
      byTopic.set(key, {
        ...nextIncoming,
        id: current.id,
        updatedAt: new Date().toISOString(),
      });
      continue;
    }

    const merged = [current.content.trim(), nextIncoming.content.trim()]
      .filter(Boolean)
      .join("\n\n");
    byTopic.set(key, {
      ...current,
      content: merged,
      updatedAt: new Date().toISOString(),
    });
  }

  return [...byTopic.values()].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt),
  );
}

export function importSessionConventions(
  snapshot: SessionConventionsSnapshot,
  incomingSnapshot: SessionConventionsSnapshot,
  resolution: ConventionConflictResolution,
): SessionConventionsSnapshot {
  const mergedItems = mergeSessionConventionItems(
    snapshot.items,
    incomingSnapshot.items,
    resolution,
  );
  return touchSnapshot(mergedItems);
}

export function exportSessionConventions(
  snapshot: SessionConventionsSnapshot,
): SessionConventionsSnapshot {
  return {
    version: snapshot.version,
    lastUpdated: snapshot.lastUpdated,
    items: snapshot.items.map(normalizeItem),
  };
}

export function mergeRepoAndSessionConventions(
  sessionItems: SessionConventionItem[],
): MergedConventionItem[] {
  const merged: MergedConventionItem[] = REPO_BASELINE_CONVENTIONS.map((item) => ({
    ...item,
    source: "repo",
  }));

  for (const item of sessionItems) {
    merged.push({
      ...item,
      source: "session",
    });
  }

  return merged.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function recordConversationConventionDelta(
  snapshot: SessionConventionsSnapshot,
  summary: string,
): SessionConventionsSnapshot {
  const trimmed = summary.trim();
  if (!trimmed) {
    return snapshot;
  }

  return upsertSessionConvention(snapshot, {
    topic: "Conversation Delta",
    content: trimmed,
  });
}
