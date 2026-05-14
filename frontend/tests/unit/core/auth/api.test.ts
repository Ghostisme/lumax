import { describe, expect, test } from "vitest";

import { parsePasswordLoginResponse } from "@/core/auth/api";

describe("parsePasswordLoginResponse", () => {
  test("supports plain oauth payload", () => {
    const parsed = parsePasswordLoginResponse({
      access_token: "token-123",
      token_type: "Bearer",
      refresh_token: "refresh-123",
      expires_in: 7200,
    });

    expect(parsed.access_token).toBe("token-123");
    expect(parsed.token_type).toBe("Bearer");
    expect(parsed.refresh_token).toBe("refresh-123");
    expect(parsed.expires_in).toBe(7200);
  });

  test("supports business envelope with code=0 and nested claims", () => {
    const parsed = parsePasswordLoginResponse({
      code: 0,
      msg: "ok",
      data: {
        accessToken: "token-business",
        tokenType: "Bearer",
        userInfo: {
          id: 42,
          username: "alice",
          permissions: ["memory:read", "memory:write"],
          roles: [{ code: "admin" }],
        },
      },
    });

    expect(parsed.access_token).toBe("token-business");
    expect(parsed.user_id).toBe("42");
    expect(parsed.username).toBe("alice");
    expect(parsed.permissions).toEqual(["memory:read", "memory:write"]);
    expect(parsed.roles).toEqual(["admin"]);
  });

  test("throws when business code is non-zero", () => {
    expect(() =>
      parsePasswordLoginResponse({
        code: 40101,
        msg: "captcha expired",
      }),
    ).toThrowError("captcha expired");
  });
});
