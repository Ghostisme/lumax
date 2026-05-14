import { fetchWithAuth } from "../auth/request";
import { getFileName } from "../utils/files";

import { urlOfArtifact } from "./utils";

type BrowserDownloadOptions = {
  blob: Blob;
  filename: string;
  createObjectURL?: (blob: Blob) => string;
  revokeObjectURL?: (url: string) => void;
  documentRef?: Document;
};

type DownloadArtifactFileOptions = {
  filepath: string;
  threadId: string;
  isMock?: boolean;
};

type ArtifactWindow = {
  close: () => void;
  location: {
    href: string;
  };
  opener: unknown;
};

type OpenArtifactFileOptions = DownloadArtifactFileOptions & {
  createObjectURL?: (blob: Blob) => string;
  openWindow?: (
    url?: string | URL,
    target?: string,
    features?: string,
  ) => ArtifactWindow | null;
  revokeObjectURL?: (url: string) => void;
  setTimeoutFn?: (handler: () => void, timeout: number) => void;
};

const TEXT_FILE_EXTENSIONS = new Set([
  "csv",
  "css",
  "html",
  "htm",
  "js",
  "json",
  "log",
  "md",
  "mdx",
  "svg",
  "txt",
  "xml",
  "yaml",
  "yml",
]);

function normalizeHeaderValue(value: string): string {
  const trimmed = value.trim();
  if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function decodeDispositionValue(value: string): string {
  const normalized = normalizeHeaderValue(value);
  const encodedValue = normalized.includes("''")
    ? normalized.slice(normalized.indexOf("''") + 2)
    : normalized;

  try {
    return decodeURIComponent(encodedValue);
  } catch {
    return encodedValue;
  }
}

export function filenameFromContentDisposition(
  contentDisposition: string | null,
): string | null {
  if (!contentDisposition) {
    return null;
  }

  const encodedMatch = /filename\*\s*=\s*([^;]+)/i.exec(contentDisposition);
  if (encodedMatch?.[1]) {
    return decodeDispositionValue(encodedMatch[1]);
  }

  const plainMatch = /filename\s*=\s*([^;]+)/i.exec(contentDisposition);
  if (plainMatch?.[1]) {
    return decodeDispositionValue(plainMatch[1]);
  }

  return null;
}

function getFileExtension(filepath: string): string {
  const filename = getFileName(filepath);
  const extension = filename.includes(".") ? filename.split(".").pop() : "";
  return extension?.toLowerCase() ?? "";
}

function isTextualContentType(contentType: string): boolean {
  const mimeType = contentType.split(";")[0]?.trim().toLowerCase() ?? "";
  return (
    mimeType.startsWith("text/") ||
    mimeType === "application/json" ||
    mimeType === "application/javascript" ||
    mimeType === "application/xml" ||
    mimeType === "application/xhtml+xml" ||
    mimeType === "image/svg+xml"
  );
}

function defaultTextContentType(filepath: string): string {
  const extension = getFileExtension(filepath);
  if (extension === "md" || extension === "mdx") {
    return "text/markdown;charset=utf-8";
  }
  if (extension === "html" || extension === "htm") {
    return "text/html;charset=utf-8";
  }
  if (extension === "svg") {
    return "image/svg+xml;charset=utf-8";
  }
  if (extension === "json") {
    return "application/json;charset=utf-8";
  }
  if (extension === "css") {
    return "text/css;charset=utf-8";
  }
  if (extension === "js") {
    return "application/javascript;charset=utf-8";
  }
  if (extension === "xml") {
    return "application/xml;charset=utf-8";
  }
  return "text/plain;charset=utf-8";
}

function contentTypeForArtifact(response: Response, filepath: string): string {
  const contentType = response.headers.get("Content-Type")?.trim() ?? "";
  if (contentType) {
    if (
      isTextualContentType(contentType) &&
      !/;\s*charset\s*=/i.test(contentType)
    ) {
      return `${contentType};charset=utf-8`;
    }
    return contentType;
  }

  if (TEXT_FILE_EXTENSIONS.has(getFileExtension(filepath))) {
    return defaultTextContentType(filepath);
  }

  return "application/octet-stream";
}

export async function blobFromArtifactResponse(
  response: Response,
  filepath: string,
): Promise<Blob> {
  const buffer = await response.arrayBuffer();
  return new Blob([buffer], {
    type: contentTypeForArtifact(response, filepath),
  });
}

export function triggerBrowserDownload({
  blob,
  filename,
  createObjectURL = URL.createObjectURL.bind(URL),
  revokeObjectURL = URL.revokeObjectURL.bind(URL),
  documentRef = document,
}: BrowserDownloadOptions) {
  const objectUrl = createObjectURL(blob);
  const anchor = documentRef.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";

  documentRef.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  revokeObjectURL(objectUrl);
}

export async function downloadArtifactFile({
  filepath,
  threadId,
  isMock = false,
}: DownloadArtifactFileOptions) {
  const response = await fetchWithAuth(
    urlOfArtifact({ filepath, threadId, download: true, isMock }),
  );
  const blob = await blobFromArtifactResponse(response, filepath);
  const filename =
    filenameFromContentDisposition(
      response.headers.get("Content-Disposition"),
    ) ?? getFileName(filepath);

  triggerBrowserDownload({ blob, filename });
}

export async function openArtifactInNewWindow({
  filepath,
  threadId,
  isMock = false,
  createObjectURL = URL.createObjectURL.bind(URL),
  openWindow = window.open.bind(window),
  revokeObjectURL = URL.revokeObjectURL.bind(URL),
  setTimeoutFn = window.setTimeout.bind(window),
}: OpenArtifactFileOptions) {
  const openedWindow = openWindow("about:blank", "_blank");
  if (!openedWindow) {
    throw new Error("Failed to open a new window.");
  }
  openedWindow.opener = null;

  try {
    const response = await fetchWithAuth(
      urlOfArtifact({ filepath, threadId, isMock }),
    );
    const blob = await blobFromArtifactResponse(response, filepath);
    const contentDisposition = response.headers.get("Content-Disposition");
    const filename =
      filenameFromContentDisposition(contentDisposition) ??
      getFileName(filepath);

    if (contentDisposition?.toLowerCase().includes("attachment")) {
      openedWindow.close();
      triggerBrowserDownload({ blob, filename });
      return;
    }

    const objectUrl = createObjectURL(blob);
    openedWindow.location.href = objectUrl;
    setTimeoutFn(() => revokeObjectURL(objectUrl), 60_000);
  } catch (error) {
    openedWindow.close();
    throw error;
  }
}
