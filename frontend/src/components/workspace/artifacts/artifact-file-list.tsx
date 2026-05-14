import { DownloadIcon, LoaderIcon, PackageIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { downloadArtifactFile } from "@/core/artifacts/download";
import { useArtifactContent } from "@/core/artifacts/hooks";
import { urlOfArtifact } from "@/core/artifacts/utils";
import { useI18n } from "@/core/i18n/hooks";
import { installSkill } from "@/core/skills/api";
import {
  getFileExtension,
  getFileExtensionDisplayName,
  getFileIcon,
  getFileName,
} from "@/core/utils/files";
import { cn } from "@/lib/utils";

import { useArtifacts } from "./context";
import {
  EChartsArtifactPreview,
  isEChartsArtifact,
} from "./echarts-artifact-preview";

const IMAGE_EXTENSIONS = new Set([
  "jpg",
  "jpeg",
  "png",
  "gif",
  "bmp",
  "webp",
  "svg",
]);

function isImageArtifact(filepath: string) {
  return IMAGE_EXTENSIONS.has(getFileExtension(filepath));
}

export function ArtifactFileList({
  className,
  files,
  threadId,
}: {
  className?: string;
  files: string[];
  threadId: string;
}) {
  const { select: selectArtifact, setOpen } = useArtifacts();
  const [installingFile, setInstallingFile] = useState<string | null>(null);
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);

  const handleClick = useCallback(
    (filepath: string) => {
      selectArtifact(filepath);
      setOpen(true);
    },
    [selectArtifact, setOpen],
  );

  const handleInstallSkill = useCallback(
    async (e: React.MouseEvent, filepath: string) => {
      e.stopPropagation();
      e.preventDefault();

      if (installingFile) return;

      setInstallingFile(filepath);
      try {
        const result = await installSkill({
          thread_id: threadId,
          path: filepath,
        });
        if (result.success) {
          toast.success(result.message);
        } else {
          toast.error(result.message || "Failed to install skill");
        }
      } catch (error) {
        console.error("Failed to install skill:", error);
        toast.error("Failed to install skill");
      } finally {
        setInstallingFile(null);
      }
    },
    [threadId, installingFile],
  );

  const handleDownload = useCallback(
    async (e: React.MouseEvent, filepath: string) => {
      e.stopPropagation();
      e.preventDefault();

      if (downloadingFile) return;

      setDownloadingFile(filepath);
      try {
        await downloadArtifactFile({ filepath, threadId });
      } catch (error) {
        console.error("Failed to download artifact:", error);
        toast.error("Failed to download artifact");
      } finally {
        setDownloadingFile(null);
      }
    },
    [downloadingFile, threadId],
  );

  return (
    <ul className={cn("flex w-full flex-col gap-4", className)}>
      {files.map((file) => (
        <ArtifactFileListItem
          key={file}
          file={file}
          threadId={threadId}
          installingFile={installingFile}
          downloadingFile={downloadingFile}
          onClick={handleClick}
          onInstallSkill={handleInstallSkill}
          onDownload={handleDownload}
        />
      ))}
    </ul>
  );
}

function ArtifactFileListItem({
  file,
  threadId,
  installingFile,
  downloadingFile,
  onClick,
  onInstallSkill,
  onDownload,
}: {
  file: string;
  threadId: string;
  installingFile: string | null;
  downloadingFile: string | null;
  onClick: (filepath: string) => void;
  onInstallSkill: (e: React.MouseEvent, filepath: string) => void;
  onDownload: (e: React.MouseEvent, filepath: string) => void;
}) {
  const { t } = useI18n();
  const isChart = isEChartsArtifact(file);
  const isImage = isImageArtifact(file);
  const { content } = useArtifactContent({
    filepath: file,
    threadId,
    enabled: isChart,
  });

  return (
    <Card
      className="relative cursor-pointer overflow-hidden p-3"
      onClick={() => onClick(file)}
    >
      {(isChart || isImage) && (
        <div className="mb-3 overflow-hidden rounded-lg border bg-white">
          {isChart ? (
            <EChartsArtifactPreview content={content} />
          ) : (
            <img
              src={urlOfArtifact({ filepath: file, threadId })}
              alt={getFileName(file)}
              className="max-h-[360px] w-full object-contain"
            />
          )}
        </div>
      )}
      <CardHeader className="grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 pr-2 pl-1">
        <CardTitle className="relative min-w-0 pl-8 leading-tight [overflow-wrap:anywhere] break-words">
          <div className="min-w-0">{getFileName(file)}</div>
          <div className="absolute top-2 -left-0.5">
            {getFileIcon(file, "size-6")}
          </div>
        </CardTitle>
        <CardDescription className="min-w-0 pl-8 text-xs">
          {isChart ? "ECharts" : getFileExtensionDisplayName(file)} file
        </CardDescription>
        <CardAction className="row-span-1 self-center">
          {file.endsWith(".skill") && (
            <Button
              variant="ghost"
              disabled={installingFile === file}
              onClick={(e) => onInstallSkill(e, file)}
            >
              {installingFile === file ? (
                <LoaderIcon className="size-4 animate-spin" />
              ) : (
                <PackageIcon className="size-4" />
              )}
              {t.common.install}
            </Button>
          )}
          <Button
            variant="ghost"
            disabled={downloadingFile === file}
            onClick={(e) => onDownload(e, file)}
          >
            {downloadingFile === file ? (
              <LoaderIcon className="size-4 animate-spin" />
            ) : (
              <DownloadIcon className="size-4" />
            )}
            {t.common.download}
          </Button>
        </CardAction>
      </CardHeader>
    </Card>
  );
}
