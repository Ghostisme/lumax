import { describe, expect, test } from "vitest";

import {
  detectSessionConventionConflicts,
  importSessionConventions,
  isSessionConventionsSnapshot,
  mergeRepoAndSessionConventions,
  mergeSessionConventionItems,
  recordConversationConventionDelta,
  upsertSessionConvention,
  type SessionConventionsSnapshot,
} from "@/core/settings/conventions";

function createSnapshot(
  items: SessionConventionsSnapshot["items"],
): SessionConventionsSnapshot {
  return {
    version: "1.0.0",
    lastUpdated: "2026-04-24T00:00:00.000Z",
    items,
  };
}

describe("session conventions helpers", () => {
  test("validates snapshot payload shape", () => {
    expect(
      isSessionConventionsSnapshot({
        version: "1.0.0",
        lastUpdated: "2026-04-24T00:00:00.000Z",
        items: [
          {
            id: "session-1",
            topic: "State",
            content: "Use immutable updates.",
            updatedAt: "2026-04-24T00:00:00.000Z",
          },
        ],
      }),
    ).toBe(true);

    expect(
      isSessionConventionsSnapshot({
        version: "1.0.0",
        lastUpdated: "2026-04-24T00:00:00.000Z",
        items: [{ topic: "missing-id" }],
      }),
    ).toBe(false);
  });

  test("upsert replaces existing topic and preserves stable id", () => {
    const initial = createSnapshot([
      {
        id: "session-state",
        topic: "State",
        content: "Use useSyncExternalStore.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ]);

    const updated = upsertSessionConvention(initial, {
      topic: "state",
      content: "Use immutable updates with explicit merge rules.",
    });

    expect(updated.items).toHaveLength(1);
    const first = updated.items.at(0);
    expect(first).toBeDefined();
    expect(first!.id).toBe("session-state");
    expect(first!.content).toContain("immutable updates");
  });

  test("detects conflicts by topic with different content", () => {
    const conflicts = detectSessionConventionConflicts(
      [
        {
          id: "a",
          topic: "API Contract",
          content: "Use typed payloads.",
          updatedAt: "2026-04-24T00:00:00.000Z",
        },
      ],
      [
        {
          id: "b",
          topic: "api contract",
          content: "Allow dynamic JSON.",
          updatedAt: "2026-04-24T00:00:00.000Z",
        },
      ],
    );

    expect(conflicts).toHaveLength(1);
    const firstConflict = conflicts.at(0);
    expect(firstConflict).toBeDefined();
    expect(firstConflict!.topic).toBe("api contract");
  });

  test("merge policy chooses existing, incoming, or merged content", () => {
    const existing = [
      {
        id: "state",
        topic: "State",
        content: "Use immutable updates.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ];
    const incoming = [
      {
        id: "state-import",
        topic: "state",
        content: "Allow mutable updates in some components.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ];

    const keepExisting = mergeSessionConventionItems(
      existing,
      incoming,
      "keepExisting",
    );
    const useIncoming = mergeSessionConventionItems(
      existing,
      incoming,
      "useIncoming",
    );
    const mergeContent = mergeSessionConventionItems(
      existing,
      incoming,
      "mergeContent",
    );

    const keepFirst = keepExisting.at(0);
    const incomingFirst = useIncoming.at(0);
    const mergedFirst = mergeContent.at(0);
    expect(keepFirst).toBeDefined();
    expect(incomingFirst).toBeDefined();
    expect(mergedFirst).toBeDefined();
    expect(keepFirst!.content).toContain("immutable");
    expect(incomingFirst!.content).toContain("mutable");
    expect(mergedFirst!.content).toContain("immutable");
    expect(mergedFirst!.content).toContain("mutable");
  });

  test("imports conventions with selected conflict strategy", () => {
    const current = createSnapshot([
      {
        id: "state",
        topic: "State",
        content: "Use immutable updates.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ]);

    const incoming = createSnapshot([
      {
        id: "state-import",
        topic: "state",
        content: "Use reducers for complex state transitions.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
      {
        id: "new-topic",
        topic: "I18N",
        content: "Avoid inline user-facing strings.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ]);

    const imported = importSessionConventions(current, incoming, "useIncoming");
    expect(imported.items).toHaveLength(2);
    expect(imported.items.find((item) => item.topic.toLowerCase() === "state"))
      .toBeTruthy();
    expect(imported.items.find((item) => item.topic.toLowerCase() === "i18n"))
      .toBeTruthy();
  });

  test("records conversation delta as reusable session convention", () => {
    const initial = createSnapshot([]);
    const next = recordConversationConventionDelta(
      initial,
      "Always update both en-US and zh-CN keys for new settings text.",
    );

    expect(next.items).toHaveLength(1);
    const first = next.items.at(0);
    expect(first).toBeDefined();
    expect(first!.topic).toBe("Conversation Delta");
    expect(first!.content).toContain("en-US");
  });

  test("merged conventions include repo baseline and session entries", () => {
    const merged = mergeRepoAndSessionConventions([
      {
        id: "session-i18n",
        topic: "I18N",
        content: "Localize all new settings labels.",
        updatedAt: "2026-04-24T00:00:00.000Z",
      },
    ]);

    expect(merged.some((item) => item.source === "repo")).toBe(true);
    expect(merged.some((item) => item.source === "session")).toBe(true);
  });
});
