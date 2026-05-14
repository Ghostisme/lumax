import { env } from "@/env";

const DEFAULT_FIGMA_ASSET_BASE_URL =
  "https://prod-upload.jialugroup.cn/lumax-ai/figma";

function getBaseOrigin() {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  // Fallback for SSR
  return "http://localhost:2026";
}

export function getBackendBaseURL() {
  if (env.NEXT_PUBLIC_BACKEND_BASE_URL) {
    return new URL(env.NEXT_PUBLIC_BACKEND_BASE_URL, getBaseOrigin())
      .toString()
      .replace(/\/+$/, "");
  } else {
    return "";
  }
}

export function getFigmaAssetURL(path: string) {
  const baseURL =
    env.NEXT_PUBLIC_FIGMA_ASSET_BASE_URL ?? DEFAULT_FIGMA_ASSET_BASE_URL;
  return `${baseURL.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

/**
 * Base URL for `/api/auth/*` (login, logout, captcha, token).
 * Falls back to {@link getBackendBaseURL} when `NEXT_PUBLIC_AUTH_API_BASE_URL` is unset
 * (then auth and other APIs use the same base — set AUTH explicitly to split them).
 */
export function getAuthApiBaseURL() {
  if (env.NEXT_PUBLIC_AUTH_API_BASE_URL) {
    return new URL(env.NEXT_PUBLIC_AUTH_API_BASE_URL, getBaseOrigin())
      .toString()
      .replace(/\/+$/, "");
  }
  return getBackendBaseURL();
}

export function getLangGraphBaseURL(isMock?: boolean) {
  if (env.NEXT_PUBLIC_LANGGRAPH_BASE_URL) {
    return new URL(
      env.NEXT_PUBLIC_LANGGRAPH_BASE_URL,
      getBaseOrigin(),
    ).toString();
  } else if (isMock) {
    if (typeof window !== "undefined") {
      return `${window.location.origin}/mock/api`;
    }
    return "http://localhost:3000/mock/api";
  } else {
    // LangGraph SDK requires a full URL, construct it from current origin
    if (typeof window !== "undefined") {
      return `${window.location.origin}/api/langgraph`;
    }
    // Fallback for SSR
    return "http://localhost:2026/api/langgraph";
  }
}
