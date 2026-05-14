import { requestLoginDialog, type LoginDialogReason } from "./login-dialog";
import {
  clearAuthSession,
  getAuthorizationHeaderValue,
  getBusinessCode,
  getTenantId,
} from "./session";

const AUTH_BLOCK_STATUSES = new Set([401, 429]);

export const BUSINESS_CODE_HEADER = "Business-Code";
export const TENANT_ID_HEADER = "TENANT-ID";

export class AuthRequiredError extends Error {
  constructor(public readonly status: number) {
    super(
      status === 429
        ? "Too many requests. Please sign in again."
        : "Authentication required.",
    );
    this.name = "AuthRequiredError";
  }
}

/**
 * 在已有 Headers 基础上叠加一份当前会话上下文：
 * - Authorization: 由 access token 拼接得到
 * - Business-Code: 当前业务线编码
 * - TENANT-ID: 当前租户 ID
 *
 * 调用方若已经显式指定了对应字段，则不会被覆盖；
 * 这保证登录接口（自带 Basic / talent 头）等场景不会被破坏。
 */
export function buildAuthHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders);
  const authorization = getAuthorizationHeaderValue();
  if (authorization && !headers.has("Authorization")) {
    headers.set("Authorization", authorization);
  }

  const businessCode = getBusinessCode();
  if (businessCode && !headers.has(BUSINESS_CODE_HEADER)) {
    headers.set(BUSINESS_CODE_HEADER, businessCode);
  }

  const tenantId = getTenantId();
  if (
    typeof tenantId === "string" &&
    tenantId.trim() &&
    !headers.has(TENANT_ID_HEADER)
  ) {
    headers.set(TENANT_ID_HEADER, tenantId);
  }

  return headers;
}

function reasonForStatus(status: number): LoginDialogReason {
  return status === 429 ? "rate_limited" : "unauthorized";
}

export function handleAuthBlockedResponse(response: Response): Response {
  if (AUTH_BLOCK_STATUSES.has(response.status)) {
    clearAuthSession();
    requestLoginDialog(reasonForStatus(response.status));
    throw new AuthRequiredError(response.status);
  }
  return response;
}

export async function fetchWithAuth(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: buildAuthHeaders(init?.headers),
  });
  return handleAuthBlockedResponse(response);
}
