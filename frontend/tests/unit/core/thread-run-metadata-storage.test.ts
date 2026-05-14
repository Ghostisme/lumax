import { describe, expect, test, vi } from "vitest";

import {
  getRunMetadataStorage,
  normalizeStoredRunId,
} from "@/core/threads/hooks";

describe("normalizeStoredRunId", () => {
  test("keeps plain run ids", () => {
    expect(normalizeStoredRunId("run-123")).toBe("run-123");
  });

  test("extracts run ids from run resource paths", () => {
    expect(
      normalizeStoredRunId("/api/threads/thread-1/runs/run-123/stream"),
    ).toBe("run-123");
  });

  test("extracts run ids from query strings", () => {
    expect(normalizeStoredRunId("/join?run_id=run-456")).toBe("run-456");
  });

  test("rejects empty values", () => {
    expect(normalizeStoredRunId("  ")).toBeNull();
    expect(normalizeStoredRunId(null)).toBeNull();
  });
});

describe("getRunMetadataStorage", () => {
  test("normalizes existing storage values and removes invalid entries", () => {
    const store = new Map<string, string>();
    const getItem = vi.fn((key: string) => store.get(key) ?? null);
    const setItem = vi.fn((key: string, value: string) => {
      store.set(key, value);
    });
    const removeItem = vi.fn((key: string) => {
      store.delete(key);
    });

    vi.stubGlobal("window", {
      sessionStorage: {
        getItem,
        setItem,
        removeItem,
      },
    });

    store.set("lg:stream:thread-1", "/api/threads/thread-1/runs/run-1/stream");
    const storage = getRunMetadataStorage();

    expect(storage.getItem("lg:stream:thread-1")).toBe("run-1");
    expect(setItem).toHaveBeenCalledWith("lg:stream:thread-1", "run-1");

    store.set("lg:stream:thread-2", "  ");
    expect(storage.getItem("lg:stream:thread-2")).toBeNull();
    expect(removeItem).toHaveBeenCalledWith("lg:stream:thread-2");

    vi.unstubAllGlobals();
  });
});
