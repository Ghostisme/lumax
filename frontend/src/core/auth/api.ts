import { getAuthApiBaseURL } from "@/core/config";

import { encryptPassword } from "./crypto";
import { buildAuthHeaders } from "./request";

const LOGIN_AUTHORIZATION_HEADER = "Basic cGxhdGZvcm06cGxhdGZvcm0=";
const LOGIN_BUSINESS_CODE_HEADER = "ai";

/**
 * 登录通道默认使用的业务线编码，对外暴露给登录后续上下文使用。
 */
export const DEFAULT_BUSINESS_CODE = LOGIN_BUSINESS_CODE_HEADER;

/**
 * 从一个租户的 businessCodes 列表里挑选一个最合适的业务线编码：
 * - 优先选择默认业务线（如 "talent"）
 * - 否则取列表中第一个非空项
 * - 都没有时返回默认值
 */
export function pickPrimaryBusinessCode(
  businessCodes?: string[] | null,
  fallback: string = DEFAULT_BUSINESS_CODE,
): string {
  if (!Array.isArray(businessCodes) || businessCodes.length === 0) {
    return fallback;
  }
  const normalized = businessCodes
    .map((code) => (typeof code === "string" ? code.trim() : ""))
    .filter(Boolean);
  if (normalized.length === 0) {
    return fallback;
  }
  if (normalized.includes(fallback)) {
    return fallback;
  }
  return normalized[0]!;
}

export type PasswordLoginInput = {
  username: string;
  password: string;
  mobile?: string;
  code?: string;
  randomStr?: string;
  tenantId?: string;
};

export type PasswordLoginResponse = {
  access_token: string;
  token_type: string;
  refresh_token?: string;
  expires_in?: number;
  scope?: string;
  permissions?: string[];
  roles?: string[];
  user_id?: string;
  username?: string;
  [key: string]: unknown;
};

export type PreLoginInput = {
  /**
   * 授权类型（当前预登录仅支持 password）
   */
  grantType?: string;
  /**
   * 密码
   */
  password: string;
  /**
   * 用户名
   */
  username: string;
  [property: string]: unknown;
};

export type LoginTenantOption = {
  /**
   * 租户下业务线标识列表
   */
  businessCodes?: string[];
  /**
   * 状态 0:正常 1:禁用
   */
  status?: number;
  /**
   * 租户编码
   */
  tenantCode?: string;
  /**
   * 租户ID
   */
  tenantId?: string;
  /**
   * 租户名称
   */
  tenantName?: string;
  [property: string]: unknown;
};

export type PreLoginUserInfo = {
  /**
   * 昵称
   */
  nickname?: string;
  /**
   * 手机号
   */
  phone?: string;
  /**
   * 可选租户列表
   */
  tenantOptions?: LoginTenantOption[];
  /**
   * 用户ID
   */
  userId?: number;
  /**
   * 用户名
   */
  username?: string;
  [property: string]: unknown;
};

export type PreLoginResponse = {
  code?: number;
  data?: PreLoginUserInfo;
  msg?: string;
  [property: string]: unknown;
};

export type CaptchaStatusResponse = {
  captchaEnabled: boolean;
  [key: string]: unknown;
};

function createRandomStr(): string {
  return typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}`;
}

function buildLoginErrorMessage(
  errorBody: unknown,
  statusText: string,
): string {
  if (!errorBody || typeof errorBody !== "object") {
    return `Login failed: ${statusText}`;
  }

  const record = errorBody as Record<string, unknown>;
  const detail =
    (typeof record.detail === "string" ? record.detail : undefined) ??
    (typeof record.error_description === "string"
      ? record.error_description
      : undefined) ??
    (typeof record.error === "string" ? record.error : undefined) ??
    (typeof record.message === "string" ? record.message : undefined);

  return detail ?? `Login failed: ${statusText}`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  return value as Record<string, unknown>;
}

function pickString(
  record: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function pickNumber(
  record: Record<string, unknown>,
  keys: string[],
): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string") {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return null;
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(
    new Set(values.map((value) => value.trim()).filter(Boolean)),
  );
}

function extractStringList(value: unknown): string[] {
  if (typeof value === "string") {
    return value
      .split(/[,\s]+/g)
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  if (Array.isArray(value)) {
    return uniqueStrings(
      value
        .map((entry) => {
          if (typeof entry === "string") {
            return entry;
          }
          if (entry && typeof entry === "object") {
            const record = entry as Record<string, unknown>;
            return (
              pickString(record, [
                "code",
                "roleCode",
                "name",
                "value",
                "authority",
              ]) ?? ""
            );
          }
          return "";
        })
        .filter(Boolean),
    );
  }
  return [];
}

function extractClaimList(
  source: Record<string, unknown>,
  keys: string[],
): string[] {
  const result: string[] = [];
  for (const key of keys) {
    result.push(...extractStringList(source[key]));
  }
  return uniqueStrings(result);
}

function resolveLoginPayload(body: unknown): Record<string, unknown> | null {
  const record = asRecord(body);
  if (!record) {
    return null;
  }
  const businessCode = extractBusinessCode(body);
  if (businessCode === null) {
    return record;
  }
  if (businessCode !== 0) {
    return null;
  }

  const nestedPayload =
    asRecord(record.data) ??
    asRecord(record.result) ??
    asRecord(record.payload) ??
    asRecord(record.response);
  return nestedPayload ?? record;
}

export function parsePasswordLoginResponse(
  body: unknown,
): PasswordLoginResponse {
  const businessCode = extractBusinessCode(body);
  if (businessCode !== null && businessCode !== 0) {
    const businessMessage = extractBusinessMessage(body);
    throw new Error(
      businessMessage ?? `Login failed with code ${businessCode}`,
    );
  }

  const payload = resolveLoginPayload(body);
  if (!payload) {
    throw new Error("Login failed: invalid token response");
  }

  const accessToken = pickString(payload, [
    "access_token",
    "accessToken",
    "token",
  ]);
  const tokenType =
    pickString(payload, ["token_type", "tokenType"]) ?? "Bearer";

  if (!accessToken) {
    throw new Error("Login failed: invalid token response");
  }

  const profile =
    asRecord(payload.userInfo) ??
    asRecord(payload.user) ??
    asRecord(payload.profile) ??
    payload;

  const permissions = uniqueStrings([
    ...extractClaimList(payload, [
      "permissions",
      "permission",
      "perms",
      "authorities",
      "authority",
      "permissionCodes",
    ]),
    ...extractClaimList(profile, [
      "permissions",
      "permission",
      "perms",
      "authorities",
      "authority",
      "permissionCodes",
    ]),
  ]);

  const roles = uniqueStrings([
    ...extractClaimList(payload, ["roles", "roleCodes", "role", "userRoles"]),
    ...extractClaimList(profile, ["roles", "roleCodes", "role", "userRoles"]),
  ]);

  const userId =
    pickString(profile, ["user_id", "userId", "id"]) ??
    (typeof profile.id === "number" ? String(profile.id) : null);

  const username =
    pickString(profile, ["username", "user_name", "account", "mobile"]) ??
    pickString(payload, ["username", "user_name", "account", "mobile"]);

  const normalized: PasswordLoginResponse = {
    ...payload,
    access_token: accessToken,
    token_type: tokenType,
  };

  const refreshToken = pickString(payload, ["refresh_token", "refreshToken"]);
  if (refreshToken) {
    normalized.refresh_token = refreshToken;
  }

  const expiresIn = pickNumber(payload, ["expires_in", "expiresIn", "expire"]);
  if (expiresIn !== null) {
    normalized.expires_in = expiresIn;
  }

  const scope = pickString(payload, ["scope"]);
  if (scope) {
    normalized.scope = scope;
  }

  if (permissions.length > 0) {
    normalized.permissions = permissions;
  }
  if (roles.length > 0) {
    normalized.roles = roles;
  }
  if (userId) {
    normalized.user_id = userId;
  }
  if (username) {
    normalized.username = username;
  }

  return normalized;
}

export async function getCaptchaStatus(): Promise<boolean> {
  const response = await fetch(`${getAuthApiBaseURL()}/api/auth/code/status`, {
    headers: {
      "Business-Code": LOGIN_BUSINESS_CODE_HEADER,
    },
  });
  const body = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    return false;
  }
  if (!body || typeof body !== "object") {
    return false;
  }
  const record = body as Record<string, unknown>;
  if (typeof record.captchaEnabled === "boolean") {
    return record.captchaEnabled;
  }

  const data = record.data;
  if (data && typeof data === "object") {
    const dataRecord = data as Record<string, unknown>;
    if (typeof dataRecord.captchaEnabled === "boolean") {
      return dataRecord.captchaEnabled;
    }
  }

  return false;
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Failed to read captcha image"));
    };
    reader.onerror = () => reject(new Error("Failed to read captcha image"));
    reader.readAsDataURL(blob);
  });
}

function normalizeDataImageUrl(value: string): string {
  const trimmed = value.trim();
  const dataUrlPattern = /^data:([^;,]+)(;base64)?,(.*)$/i;
  const match = dataUrlPattern.exec(trimmed);
  if (!match) {
    return trimmed;
  }

  const mimeType = match[1];
  const isBase64 = Boolean(match[2]);
  const payload = match[3] ?? "";

  if (!isBase64) {
    return `data:${mimeType},${payload.trim()}`;
  }

  // Some gateways return wrapped/pretty-formatted base64 strings with spaces
  // or newlines, which breaks <img src="data:..."> rendering.
  const normalizedPayload = payload.replace(/\s+/g, "");
  return `data:${mimeType};base64,${normalizedPayload}`;
}

function extractBusinessCode(value: unknown): number | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (typeof record.code === "number") {
    return record.code;
  }
  if (typeof record.code === "string") {
    const parsed = Number(record.code);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function extractBusinessMessage(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  const candidates = [record.msg, record.message, record.error_description];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }
  return null;
}

export async function getCaptchaImage(randomStr?: string): Promise<{
  randomStr: string;
  imageDataUrl: string;
}> {
  const resolvedRandomStr = randomStr ?? createRandomStr();
  const response = await fetch(
    `${getAuthApiBaseURL()}/api/auth/code/image?randomStr=${encodeURIComponent(resolvedRandomStr)}`,
    {
      headers: {
        "Business-Code": LOGIN_BUSINESS_CODE_HEADER,
      },
    },
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch captcha image: ${response.statusText}`);
  }
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";

  let imageDataUrl = "";
  if (contentType.includes("image/")) {
    const blob = await response.blob();
    imageDataUrl = await blobToDataUrl(blob);
  } else {
    const text = await response.text();
    const parsed = (() => {
      try {
        return JSON.parse(text) as unknown;
      } catch {
        return text;
      }
    })();

    const businessCode = extractBusinessCode(parsed);
    if (businessCode !== null && businessCode !== 0) {
      const businessMsg =
        extractBusinessMessage(parsed) ??
        `captcha image request failed with code ${businessCode}`;
      throw new Error(businessMsg);
    }

    const resolveImageCandidate = (value: unknown): string | null => {
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
      if (!value || typeof value !== "object") {
        return null;
      }
      const record = value as Record<string, unknown>;
      const candidates = [
        record.img,
        record.image,
        record.captcha,
        record.captchaImg,
        record.imageBase64,
        record.data,
      ];
      for (const candidate of candidates) {
        const found = resolveImageCandidate(candidate);
        if (found) {
          return found;
        }
      }
      return null;
    };

    const candidate = resolveImageCandidate(parsed);
    if (!candidate) {
      const businessMsg = extractBusinessMessage(parsed);
      throw new Error(businessMsg ?? "Failed to parse captcha image data");
    }

    if (candidate.startsWith("data:image")) {
      imageDataUrl = normalizeDataImageUrl(candidate);
    } else if (candidate.startsWith("<svg")) {
      imageDataUrl = `data:image/svg+xml;utf8,${encodeURIComponent(candidate)}`;
    } else {
      imageDataUrl = `data:image/png;base64,${candidate.replace(/\s+/g, "")}`;
    }
  }

  return { randomStr: resolvedRandomStr, imageDataUrl };
}

export async function preLoginWithPassword(
  input: PreLoginInput,
): Promise<PreLoginUserInfo> {
  const payload = new URLSearchParams({
    grantType: input.grantType ?? "password",
    username: input.username,
    password: encryptPassword(input.password),
  });

  const response = await fetch(
    `${getAuthApiBaseURL()}/api/auth/oauth2/pre-login?${payload.toString()}`,
    {
      method: "POST",
      headers: {
        Authorization: LOGIN_AUTHORIZATION_HEADER,
        "Business-Code": LOGIN_BUSINESS_CODE_HEADER,
        "Content-Type": "application/x-www-form-urlencoded",
      },
    },
  );

  const body = (await response
    .json()
    .catch(() => null)) as PreLoginResponse | null;

  if (!response.ok) {
    throw new Error(buildLoginErrorMessage(body, response.statusText));
  }

  const businessCode = extractBusinessCode(body);
  if (businessCode !== null && businessCode !== 0) {
    throw new Error(
      extractBusinessMessage(body) ??
        `Pre-login failed with code ${businessCode}`,
    );
  }

  return body?.data ?? {};
}

export async function loginWithPassword(
  input: PasswordLoginInput,
): Promise<PasswordLoginResponse> {
  const shouldUseCaptcha = Boolean(input.code?.trim());
  if (shouldUseCaptcha && !input.randomStr?.trim()) {
    throw new Error(
      "Captcha randomStr is required when submitting captcha code",
    );
  }

  const trimmedRandomStr = input.randomStr?.trim();
  const randomStr =
    trimmedRandomStr && trimmedRandomStr.length > 0
      ? trimmedRandomStr
      : createRandomStr();
  const encryptedPassword = encryptPassword(input.password);

  const payload = new URLSearchParams({
    // mobile: input.mobile ?? input.username,
    code: input.code ?? "9",
    grant_type: "password",
    username: input.username,
    password: encryptedPassword,
    randomStr,
  });

  // The auth gateway expects query-style parameters for password login.
  const headers: Record<string, string> = {
    Authorization: LOGIN_AUTHORIZATION_HEADER,
    "Business-Code": LOGIN_BUSINESS_CODE_HEADER,
    "Content-Type": "application/x-www-form-urlencoded",
  };
  if (input.tenantId !== undefined) {
    headers["TENANT-ID"] = String(input.tenantId);
  }

  const response = await fetch(
    `${getAuthApiBaseURL()}/api/auth/oauth2/token?${payload.toString()}`,
    {
      method: "POST",
      headers,
    },
  );

  const body = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(buildLoginErrorMessage(body, response.statusText));
  }

  return parsePasswordLoginResponse(body);
}

export async function logoutWithToken(): Promise<void> {
  const response = await fetch(`${getAuthApiBaseURL()}/api/auth/token/logout`, {
    method: "DELETE",
    headers: buildAuthHeaders({
      "Business-Code": LOGIN_BUSINESS_CODE_HEADER,
    }),
  });

  const body = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new Error(buildLoginErrorMessage(body, response.statusText));
  }

  const businessCode = extractBusinessCode(body);
  if (businessCode !== null && businessCode !== 0) {
    throw new Error(
      extractBusinessMessage(body) ?? `Logout failed with code ${businessCode}`,
    );
  }
}
