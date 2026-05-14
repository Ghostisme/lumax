import { beforeEach, expect, test, vi } from "vitest";

import {
  blobFromArtifactResponse,
  downloadArtifactFile,
  filenameFromContentDisposition,
  openArtifactInNewWindow,
  triggerBrowserDownload,
} from "@/core/artifacts/download";
import { fetchWithAuth } from "@/core/auth/request";

vi.mock("@/core/auth/request", () => ({
  fetchWithAuth: vi.fn(),
}));

const fetchWithAuthMock = vi.mocked(fetchWithAuth);

beforeEach(() => {
  vi.restoreAllMocks();
  fetchWithAuthMock.mockReset();
});

test("parses RFC 5987 filenames from Content-Disposition", () => {
  expect(
    filenameFromContentDisposition(
      "attachment; filename*=UTF-8''4%E5%91%A8AI%E5%AD%A6%E4%B9%A0%E8%AE%A1%E5%88%92.md",
    ),
  ).toBe("4周AI学习计划.md");
});

test("falls back to plain Content-Disposition filename", () => {
  expect(
    filenameFromContentDisposition('attachment; filename="report.md"'),
  ).toBe("report.md");
});

test("triggers a browser download and revokes the Blob URL", () => {
  const anchor = {
    click: vi.fn(),
    download: "",
    href: "",
    remove: vi.fn(),
    style: { display: "" },
  };
  const documentRef = {
    body: { appendChild: vi.fn() },
    createElement: vi.fn(() => anchor),
  } as unknown as Document;
  const createObjectURL = vi.fn(() => "blob:artifact");
  const revokeObjectURL = vi.fn();

  triggerBrowserDownload({
    blob: new Blob(["content"]),
    filename: "report.md",
    createObjectURL,
    revokeObjectURL,
    documentRef,
  });

  expect(anchor.href).toBe("blob:artifact");
  expect(anchor.download).toBe("report.md");
  expect(anchor.click).toHaveBeenCalledOnce();
  expect(anchor.remove).toHaveBeenCalledOnce();
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:artifact");
});

test("downloads artifacts through fetchWithAuth", async () => {
  const anchor = {
    click: vi.fn(),
    download: "",
    href: "",
    remove: vi.fn(),
    style: { display: "" },
  };
  const documentRef = {
    body: { appendChild: vi.fn() },
    createElement: vi.fn(() => anchor),
  };
  const createObjectURL = vi.fn(() => "blob:download");
  const revokeObjectURL = vi.fn();

  vi.stubGlobal("document", documentRef);
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: createObjectURL,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: revokeObjectURL,
  });

  fetchWithAuthMock.mockResolvedValue({
    arrayBuffer: () =>
      Promise.resolve(new TextEncoder().encode("artifact").buffer),
    headers: new Headers({
      "Content-Disposition": "attachment; filename*=UTF-8''result.md",
    }),
  } as Response);

  await downloadArtifactFile({
    filepath: "/mnt/user-data/outputs/fallback.md",
    threadId: "thread-1",
  });

  expect(fetchWithAuthMock).toHaveBeenCalledWith(
    "/api/threads/thread-1/artifacts/mnt/user-data/outputs/fallback.md?download=true",
  );
  expect(anchor.download).toBe("result.md");
  expect(createObjectURL).toHaveBeenCalledOnce();
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:download");
});

test("opens artifacts through fetchWithAuth in a Blob URL window", async () => {
  const openedWindow = {
    close: vi.fn(),
    location: { href: "" },
    opener: {},
  };
  const openWindow = vi.fn(() => openedWindow);
  const createObjectURL = vi.fn((_blob: Blob) => "blob:artifact-open");
  const revokeObjectURL = vi.fn();
  const setTimeoutFn = vi.fn((handler: () => void) => handler());

  fetchWithAuthMock.mockResolvedValue({
    arrayBuffer: () =>
      Promise.resolve(new TextEncoder().encode("中文 artifact").buffer),
    headers: new Headers(),
  } as Response);

  await openArtifactInNewWindow({
    filepath: "/mnt/user-data/outputs/report.md",
    threadId: "thread-1",
    createObjectURL,
    openWindow,
    revokeObjectURL,
    setTimeoutFn,
  });

  expect(openWindow).toHaveBeenCalledWith("about:blank", "_blank");
  expect(fetchWithAuthMock).toHaveBeenCalledWith(
    "/api/threads/thread-1/artifacts/mnt/user-data/outputs/report.md",
  );
  expect(openedWindow.opener).toBeNull();
  expect(openedWindow.location.href).toBe("blob:artifact-open");
  expect(createObjectURL.mock.calls[0]?.[0].type).toBe(
    "text/markdown;charset=utf-8",
  );
  expect(setTimeoutFn).toHaveBeenCalledWith(expect.any(Function), 60_000);
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:artifact-open");
});

test("adds UTF-8 charset to textual artifact Blob responses", async () => {
  const blob = await blobFromArtifactResponse(
    {
      arrayBuffer: () =>
        Promise.resolve(new TextEncoder().encode("中文内容").buffer),
      headers: new Headers({ "Content-Type": "text/markdown" }),
    } as Response,
    "/mnt/user-data/outputs/计划.md",
  );

  expect(blob.type).toBe("text/markdown;charset=utf-8");
});

test("closes the pre-opened window when authenticated open fails", async () => {
  const openedWindow = {
    close: vi.fn(),
    location: { href: "" },
    opener: {},
  };

  fetchWithAuthMock.mockRejectedValue(new Error("unauthorized"));

  await expect(
    openArtifactInNewWindow({
      filepath: "/mnt/user-data/outputs/report.md",
      threadId: "thread-1",
      createObjectURL: vi.fn(() => "blob:unused"),
      openWindow: vi.fn(() => openedWindow),
      revokeObjectURL: vi.fn(),
      setTimeoutFn: vi.fn(),
    }),
  ).rejects.toThrow("unauthorized");

  expect(openedWindow.close).toHaveBeenCalledOnce();
});
