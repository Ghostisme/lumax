import { useSyncExternalStore } from "react";

import {
  AGENT_CAPABILITY_KEYS,
  canAgentCapability,
  createEmptyAgentCapabilities,
  resolveAgentCapabilities,
  type AgentCapabilityFlags,
  type AgentCapabilityKey,
  type TenantAiAgentVO,
} from "./agent-permissions";
import type { PasswordLoginResponse } from "./api";

const AUTH_SESSION_STORAGE_KEY = "deerflow.auth.session";
const AUTH_TOKEN_LEGACY_KEY = "deerflow.auth.token";

type Listener = () => void;

export type AuthSession = {
  accessToken: string;
  tokenType: string;
  refreshToken?: string;
  expiresIn?: number;
  scope?: string;
  username?: string;
  userId?: string;
  /**
   * 当前登录所选的租户 ID，用于后续请求的 TENANT-ID 头。
   */
  tenantId?: string;
  /**
   * 当前业务线编码，用于后续请求的 Business-Code 头。
   * 默认与登录预置 `LOGIN_BUSINESS_CODE_HEADER` 保持一致。
   */
  businessCode?: string;
  permissions: string[];
  roles: string[];
  agentPermissionStatus: "idle" | "loading" | "ready" | "error";
  agentCapabilities: AgentCapabilityFlags;
  availableAgents: Record<string, unknown>[];
  agentPermissionsLoadedAt?: string;
  loggedInAt: string;
  raw: Record<string, unknown>;
};

const listeners = new Set<Listener>();
let storageListenerRegistered = false;
let cachedSession: AuthSession | null = null;
let cacheLoaded = false;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(
    new Set(values.map((value) => value.trim()).filter(Boolean)),
  );
}

function parseStringArray(value: unknown): string[] {
  if (typeof value === "string") {
    return value
      .split(/[,\s]+/g)
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  if (!Array.isArray(value)) {
    return [];
  }
  return uniqueStrings(
    value
      .map((entry) => {
        if (typeof entry === "string") {
          return entry;
        }
        if (isRecord(entry)) {
          const candidate = entry.code ?? entry.value ?? entry.name;
          return typeof candidate === "string" ? candidate : "";
        }
        return "";
      })
      .filter(Boolean),
  );
}

function parseAgentPermissionStatus(
  value: unknown,
): "idle" | "loading" | "ready" | "error" {
  if (
    value === "idle" ||
    value === "loading" ||
    value === "ready" ||
    value === "error"
  ) {
    return value;
  }
  return "idle";
}

function parseAgentCapabilities(value: unknown): AgentCapabilityFlags {
  const fallback = createEmptyAgentCapabilities();
  if (!isRecord(value)) {
    return fallback;
  }
  const parsed = { ...fallback };
  for (const key of AGENT_CAPABILITY_KEYS) {
    parsed[key] = Boolean(value[key]);
  }
  return parsed;
}

export function normalizeTenantId(value: unknown): string | undefined {
  const text =
    typeof value === "string"
      ? value.trim()
      : typeof value === "number" && Number.isFinite(value)
        ? String(value)
        : undefined;
  if (!text || !/^\d+$/.test(text) || /^0+$/.test(text)) {
    return undefined;
  }
  return text;
}

function parseSession(value: unknown): AuthSession | null {
  if (!isRecord(value)) {
    return null;
  }
  const accessTokenCandidate = value.accessToken ?? value.access_token;
  if (
    typeof accessTokenCandidate !== "string" ||
    !accessTokenCandidate.trim()
  ) {
    return null;
  }

  const tokenTypeCandidate = value.tokenType ?? value.token_type;
  const tokenType =
    typeof tokenTypeCandidate === "string" && tokenTypeCandidate.trim()
      ? tokenTypeCandidate.trim()
      : "Bearer";

  const loggedInAtCandidate = value.loggedInAt;
  const loggedInAt =
    typeof loggedInAtCandidate === "string" && loggedInAtCandidate.trim()
      ? loggedInAtCandidate
      : new Date().toISOString();

  const refreshTokenCandidate = value.refreshToken ?? value.refresh_token;
  const refreshToken =
    typeof refreshTokenCandidate === "string" && refreshTokenCandidate.trim()
      ? refreshTokenCandidate.trim()
      : undefined;

  const expiresInCandidate = value.expiresIn ?? value.expires_in;
  const expiresIn =
    typeof expiresInCandidate === "number"
      ? expiresInCandidate
      : typeof expiresInCandidate === "string"
        ? Number(expiresInCandidate)
        : undefined;

  const scope = typeof value.scope === "string" ? value.scope : undefined;
  const usernameCandidate = value.username ?? value.account ?? value.user_name;
  const username =
    typeof usernameCandidate === "string" && usernameCandidate.trim()
      ? usernameCandidate.trim()
      : undefined;

  const userIdCandidate = value.userId ?? value.user_id ?? value.id;
  const userId =
    typeof userIdCandidate === "string"
      ? userIdCandidate
      : typeof userIdCandidate === "number"
        ? String(userIdCandidate)
        : undefined;

  const tenantId = normalizeTenantId(value.tenantId ?? value.tenant_id);

  const businessCodeCandidate = value.businessCode ?? value.business_code;
  const businessCode =
    typeof businessCodeCandidate === "string" && businessCodeCandidate.trim()
      ? businessCodeCandidate.trim()
      : undefined;

  const permissions = uniqueStrings(
    parseStringArray(value.permissions).concat(
      parseStringArray(value.authorities),
    ),
  );
  const roles = uniqueStrings(
    parseStringArray(value.roles).concat(parseStringArray(value.roleCodes)),
  );
  const agentPermissionStatus = parseAgentPermissionStatus(
    value.agentPermissionStatus,
  );
  const availableAgents = (
    Array.isArray(value.availableAgents)
      ? value.availableAgents.filter((item): item is Record<string, unknown> =>
          isRecord(item),
        )
      : []
  ) as TenantAiAgentVO[];
  const agentCapabilities =
    availableAgents.length > 0
      ? resolveAgentCapabilities(availableAgents)
      : parseAgentCapabilities(value.agentCapabilities);
  const agentPermissionsLoadedAtCandidate = value.agentPermissionsLoadedAt;
  const agentPermissionsLoadedAt =
    typeof agentPermissionsLoadedAtCandidate === "string" &&
    agentPermissionsLoadedAtCandidate.trim()
      ? agentPermissionsLoadedAtCandidate.trim()
      : undefined;

  return {
    accessToken: accessTokenCandidate.trim(),
    tokenType,
    refreshToken,
    expiresIn: Number.isFinite(expiresIn) ? expiresIn : undefined,
    scope,
    username,
    userId,
    tenantId,
    businessCode,
    permissions,
    roles,
    agentPermissionStatus,
    agentCapabilities,
    availableAgents,
    agentPermissionsLoadedAt,
    loggedInAt,
    raw: { ...value },
  };
}

function readFromStorage(key: string): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parseSession(parsed);
  } catch {
    return null;
  }
}

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

function ensureStorageListenerRegistered() {
  if (storageListenerRegistered || typeof window === "undefined") {
    return;
  }
  window.addEventListener("storage", handleStorage);
  storageListenerRegistered = true;
}

function ensureCacheLoaded() {
  if (cacheLoaded) {
    return;
  }
  cachedSession =
    readFromStorage(AUTH_SESSION_STORAGE_KEY) ??
    readFromStorage(AUTH_TOKEN_LEGACY_KEY);
  cacheLoaded = true;
}

function writeSessionToStorage(session: AuthSession | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (!session) {
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_TOKEN_LEGACY_KEY);
    return;
  }
  const payload = JSON.stringify(session);
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, payload);
  window.localStorage.setItem(AUTH_TOKEN_LEGACY_KEY, payload);
}

function handleStorage(event: StorageEvent) {
  if (event.storageArea && event.storageArea !== window.localStorage) {
    return;
  }
  if (
    event.key !== null &&
    event.key !== AUTH_SESSION_STORAGE_KEY &&
    event.key !== AUTH_TOKEN_LEGACY_KEY
  ) {
    return;
  }
  ensureCacheLoaded();
  cachedSession =
    readFromStorage(AUTH_SESSION_STORAGE_KEY) ??
    readFromStorage(AUTH_TOKEN_LEGACY_KEY);
  emitChange();
}

export type CreateAuthSessionInput = {
  username?: string;
  tenantId?: string;
  businessCode?: string;
};

export function createAuthSession(
  payload: PasswordLoginResponse,
  input: CreateAuthSessionInput = {},
): AuthSession {
  const session = parseSession({
    ...payload,
    accessToken: payload.access_token,
    tokenType: payload.token_type,
    refreshToken: payload.refresh_token,
    expiresIn: payload.expires_in,
    username: payload.username ?? input.username,
    userId: payload.user_id,
    tenantId: input.tenantId ?? payload.tenant_id ?? payload.tenantId,
    businessCode:
      input.businessCode ?? payload.business_code ?? payload.businessCode,
    loggedInAt: new Date().toISOString(),
  });
  if (!session) {
    throw new Error("Invalid auth payload");
  }
  return session;
}

export function getAuthSessionSnapshot(): AuthSession | null {
  ensureCacheLoaded();
  return cachedSession;
}

export function subscribeAuthSession(listener: Listener): () => void {
  ensureCacheLoaded();
  ensureStorageListenerRegistered();
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useAuthSession(): AuthSession | null {
  return useSyncExternalStore(
    subscribeAuthSession,
    getAuthSessionSnapshot,
    () => null,
  );
}

export function setAuthSession(session: AuthSession) {
  ensureCacheLoaded();
  ensureStorageListenerRegistered();
  cachedSession = session;
  writeSessionToStorage(session);
  emitChange();
}

export function clearAuthSession() {
  ensureCacheLoaded();
  ensureStorageListenerRegistered();
  cachedSession = null;
  writeSessionToStorage(null);
  emitChange();
}

export function getAccessToken(): string | null {
  return getAuthSessionSnapshot()?.accessToken ?? null;
}

export function getAuthorizationHeaderValue(): string | null {
  const session = getAuthSessionSnapshot();
  if (!session?.accessToken) {
    return null;
  }
  const tokenType = session.tokenType?.trim() || "Bearer";
  return `${tokenType} ${session.accessToken}`;
}

export function getTenantId(): string | null {
  return getAuthSessionSnapshot()?.tenantId ?? null;
}

export function getBusinessCode(): string | null {
  return getAuthSessionSnapshot()?.businessCode ?? null;
}

export function updateAuthSessionContext(
  patch: Partial<Pick<AuthSession, "tenantId" | "businessCode">>,
): AuthSession | null {
  ensureCacheLoaded();
  if (!cachedSession) {
    return null;
  }
  const next: AuthSession = {
    ...cachedSession,
    ...("tenantId" in patch ? { tenantId: patch.tenantId } : {}),
    ...("businessCode" in patch ? { businessCode: patch.businessCode } : {}),
  };
  setAuthSession(next);
  return next;
}

export function hasPermission(required: string | string[]): boolean {
  const session = getAuthSessionSnapshot();
  if (!session) {
    return false;
  }
  const requiredList = Array.isArray(required) ? required : [required];
  if (requiredList.length === 0) {
    return true;
  }
  const currentPermissions = new Set(session.permissions);
  return requiredList.every((item) => currentPermissions.has(item));
}

export function hasAnyPermission(required: string[]): boolean {
  const session = getAuthSessionSnapshot();
  if (!session || required.length === 0) {
    return false;
  }
  const currentPermissions = new Set(session.permissions);
  return required.some((item) => currentPermissions.has(item));
}

export function hasAgentCapability(required: AgentCapabilityKey): boolean {
  const session = getAuthSessionSnapshot();
  if (session?.agentPermissionStatus !== "ready") {
    return false;
  }
  return canAgentCapability(session.agentCapabilities, required);
}

export function updateAuthSessionAgentPermissions(input: {
  status: "loading" | "ready" | "error";
  capabilities?: AgentCapabilityFlags;
  availableAgents?: Record<string, unknown>[];
}) {
  ensureCacheLoaded();
  if (!cachedSession) {
    return null;
  }
  const next: AuthSession = {
    ...cachedSession,
    agentPermissionStatus: input.status,
    ...(input.capabilities ? { agentCapabilities: input.capabilities } : {}),
    ...(input.availableAgents
      ? { availableAgents: input.availableAgents }
      : {}),
    ...(input.status === "ready" || input.status === "error"
      ? { agentPermissionsLoadedAt: new Date().toISOString() }
      : {}),
  };
  setAuthSession(next);
  return next;
}
