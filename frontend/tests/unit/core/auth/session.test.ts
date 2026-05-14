import { afterEach, describe, expect, test, vi } from "vitest";

const LONG_TENANT_ID = "2052263773707833345";

function stubWindow() {
  const values = new Map<string, string>();
  vi.stubGlobal("window", {
    addEventListener: vi.fn(),
    localStorage: {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => {
        values.delete(key);
      },
      setItem: (key: string, value: string) => {
        values.set(key, value);
      },
    },
  });
}

describe("auth tenant session", () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  test("keeps long numeric tenant ids as strings", async () => {
    const { createAuthSession, normalizeTenantId } =
      await import("@/core/auth/session");

    expect(normalizeTenantId(LONG_TENANT_ID)).toBe(LONG_TENANT_ID);
    expect(normalizeTenantId("tenant-a")).toBeUndefined();
    expect(normalizeTenantId("0")).toBeUndefined();

    const session = createAuthSession({
      access_token: "token",
      token_type: "Bearer",
      tenantId: LONG_TENANT_ID,
    });

    expect(session.tenantId).toBe(LONG_TENANT_ID);
  });

  test("writes long tenant ids to auth headers without numeric conversion", async () => {
    stubWindow();

    const { createAuthSession, setAuthSession } =
      await import("@/core/auth/session");
    const { buildAuthHeaders } = await import("@/core/auth/request");

    setAuthSession(
      createAuthSession(
        {
          access_token: "token",
          token_type: "Bearer",
        },
        { tenantId: LONG_TENANT_ID },
      ),
    );

    const headers = buildAuthHeaders();

    expect(headers.get("TENANT-ID")).toBe(LONG_TENANT_ID);
  });
});
