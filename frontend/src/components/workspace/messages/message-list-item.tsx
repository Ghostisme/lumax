import type { Message } from "@langchain/langgraph-sdk";
import { FileIcon, Loader2Icon } from "lucide-react";
import { Share2Icon, ThumbsDownIcon, ThumbsUpIcon } from "lucide-react";
import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type AnchorHTMLAttributes,
  type ImgHTMLAttributes,
  type MouseEvent,
} from "react";
import rehypeKatex from "rehype-katex";
import { toast } from "sonner";

import { Loader } from "@/components/ai-elements/loader";
import {
  Message as AIElementMessage,
  MessageContent as AIElementMessageContent,
  MessageResponse as AIElementMessageResponse,
  MessageToolbar,
} from "@/components/ai-elements/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import { Task, TaskTrigger } from "@/components/ai-elements/task";
import { Badge } from "@/components/ui/badge";
import {
  isFeedbackStatusError,
  isFeedbackUnauthorizedError,
  submitThreadFeedback,
  type FeedbackRating,
} from "@/core/api/feedback";
import { openArtifactInNewWindow } from "@/core/artifacts/download";
import { resolveArtifactURL } from "@/core/artifacts/utils";
import { useI18n } from "@/core/i18n/hooks";
import {
  parseStructuredClarificationContent,
  parseStructuredClarificationsFromMessage,
  type StructuredClarification,
} from "@/core/messages/clarification";
import {
  extractFeedbackRunId,
  type FeedbackRunResolutionOptions,
  recordValue,
  stringValue,
} from "@/core/messages/feedback-run-id";
import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  parseUploadedFiles,
  stripUploadedFilesTag,
  type FileInMessage,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import { humanMessagePlugins } from "@/core/streamdown";
import { cn } from "@/lib/utils";

export type { FeedbackRunResolutionOptions } from "@/core/messages/feedback-run-id";

import { CopyButton } from "../copy-button";

import {
  ClarificationCard,
  type ClarificationSubmitHandler,
} from "./clarification-card";
import { MarkdownContent } from "./markdown-content";
// import { MessageTokenUsage } from "./message-token-usage";

const MARKDOWN_INLINE_CODE_CLASS =
  "[&_:not(pre)>code]:rounded-[4px] [&_:not(pre)>code]:border [&_:not(pre)>code]:border-[#E5E5E5] [&_:not(pre)>code]:bg-[#F3F4F6] [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:py-0.5 [&_:not(pre)>code]:font-mono [&_:not(pre)>code]:text-[#999999]";

const MARKDOWN_INLINE_CODE_IMPORTANT_CLASS =
  "[&_:not(pre)>code]:!rounded-[4px] [&_:not(pre)>code]:!border [&_:not(pre)>code]:!border-[#E5E5E5] [&_:not(pre)>code]:!bg-[#F3F4F6] [&_:not(pre)>code]:!px-1 [&_:not(pre)>code]:!py-0.5 [&_:not(pre)>code]:!font-mono [&_:not(pre)>code]:!text-[#999999]";



export function MessageListItem({
  className,
  message,
  isLoading,
  threadId,
  feedbackRating,
  onFeedbackSubmitted,
  onClarificationSubmit,
  fallbackStructuredClarifications,
  tokenUsageEnabled = false,
  feedbackRunResolution,
}: {
  className?: string;
  message: Message;
  isLoading?: boolean;
  threadId: string;
  feedbackRating?: FeedbackRating | null;
  onFeedbackSubmitted?: (feedback: {
    messageId: string;
    runId: string;
    rating: FeedbackRating;
  }) => void;
  onClarificationSubmit?: ClarificationSubmitHandler;
  fallbackStructuredClarifications?: StructuredClarification[];
  tokenUsageEnabled?: boolean;
  feedbackRunResolution?: FeedbackRunResolutionOptions;
}) {
  const isHuman = message.type === "human";
  return (
    <AIElementMessage
      className={cn(
        "group/conversation-message relative w-full",
        isHuman ? "items-end" : "items-start",
        className,
      )}
      from={isHuman ? "user" : "assistant"}
    >
      <MessageContent
        className={
          isHuman ? "w-fit max-w-[min(78%,520px)]" : "w-full max-w-[715px]"
        }
        message={message}
        isLoading={isLoading}
        threadId={threadId}
        feedbackRating={feedbackRating}
        onFeedbackSubmitted={onFeedbackSubmitted}
        onClarificationSubmit={onClarificationSubmit}
        fallbackStructuredClarifications={fallbackStructuredClarifications}
        tokenUsageEnabled={tokenUsageEnabled}
        feedbackRunResolution={feedbackRunResolution}
      />
    </AIElementMessage>
  );
}

function MessageItemToolbar({
  className,
  isHuman,
  message,
  threadId,
  feedbackRating,
  onFeedbackSubmitted,
  feedbackRunResolution,
}: {
  className?: string;
  isHuman: boolean;
  message: Message;
  threadId: string;
  feedbackRating?: FeedbackRating | null;
  onFeedbackSubmitted?: (feedback: {
    messageId: string;
    runId: string;
    rating: FeedbackRating;
  }) => void;
  feedbackRunResolution?: FeedbackRunResolutionOptions;
}) {
  const { t } = useI18n();
  const [selectedRating, setSelectedRating] = useState<FeedbackRating | null>(
    feedbackRating ?? null,
  );
  const [pendingRating, setPendingRating] = useState<FeedbackRating | null>(
    null,
  );

  useEffect(() => {
    setSelectedRating(feedbackRating ?? null);
  }, [feedbackRating]);

  const handleFeedback = useCallback(
    async (rating: FeedbackRating) => {
      const runId = extractFeedbackRunId(message, feedbackRunResolution);
      if (!runId) {
        toast.error(t.feedback.missingRunId);
        return;
      }

      setPendingRating(rating);
      try {
        const messageId = stringValue(recordValue(message, "id")) ?? "";
        await submitThreadFeedback(threadId, {
          messageId,
          runId,
          rating,
          comment: "",
          tags: [],
        });
        setSelectedRating(rating);
        onFeedbackSubmitted?.({ messageId, runId, rating });
        toast.success(t.feedback.submitted);
      } catch (error) {
        console.error("Failed to submit feedback:", error);
        if (
          !isFeedbackUnauthorizedError(error) &&
          !isFeedbackStatusError(error, 500)
        ) {
          toast.error(t.feedback.failed);
        }
      } finally {
        setPendingRating(null);
      }
    },
    [feedbackRunResolution, message, onFeedbackSubmitted, t, threadId],
  );

  // Lumax: 分享入口暂时隐藏；保留 icon 引用和下方 JSX 注释，便于后续恢复。
  void Share2Icon;

  return (
    <MessageToolbar
      className={cn(
        "mt-1 justify-start transition-opacity duration-300",
        isHuman &&
          "justify-end opacity-0 delay-200 group-hover/conversation-message:opacity-100",
        className,
      )}
    >
      <div className="flex gap-1">
        <CopyButton
          clipboardData={
            extractContentFromMessage(message) ??
            extractReasoningContentFromMessage(message) ??
            ""
          }
        />
        {!isHuman && (
          <>
            <button
              type="button"
              aria-pressed={selectedRating === "positive"}
              className={cn(
                "text-muted-foreground hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md border border-transparent hover:bg-[oklch(0.67_0.13_145_/_0.14)] disabled:cursor-not-allowed disabled:opacity-60",
                selectedRating === "positive" &&
                  "border-[#157575]/30 bg-[oklch(0.67_0.13_145_/_0.14)] text-[#157575]",
              )}
              disabled={pendingRating !== null}
              aria-label="like"
              onClick={() => void handleFeedback("positive")}
            >
              <ThumbsUpIcon className="size-3.5" />
            </button>
            <button
              type="button"
              aria-pressed={selectedRating === "negative"}
              className={cn(
                "text-muted-foreground hover:text-destructive inline-flex h-7 w-7 items-center justify-center rounded-md border border-transparent hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-60",
                selectedRating === "negative" &&
                  "border-destructive/30 bg-destructive/14 text-destructive",
              )}
              disabled={pendingRating !== null}
              aria-label="dislike"
              onClick={() => void handleFeedback("negative")}
            >
              <ThumbsDownIcon className="size-3.5" />
            </button>
            {/*
             * Lumax: 分享入口暂时隐藏。
             * 恢复：删除包裹本段的 JSX 块注释即可。
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md border border-transparent hover:bg-[oklch(0.67_0.13_145_/_0.14)]"
              aria-label="share"
            >
              <Share2Icon className="size-3.5" />
            </button>
            */}
          </>
        )}
      </div>
    </MessageToolbar>
  );
}

/**
 * Custom image component that handles artifact URLs
 */
function MessageImage({
  src,
  alt,
  threadId,
  maxWidth = "90%",
  ...props
}: React.ImgHTMLAttributes<HTMLImageElement> & {
  threadId: string;
  maxWidth?: string;
}) {
  if (!src) return null;

  const imgClassName = cn("overflow-hidden rounded-lg", `max-w-[${maxWidth}]`);

  if (typeof src !== "string") {
    return <img className={imgClassName} src={src} alt={alt} {...props} />;
  }

  const url = src.startsWith("/mnt/") ? resolveArtifactURL(src, threadId) : src;
  const handleClick = async (event: MouseEvent<HTMLAnchorElement>) => {
    if (!src.startsWith("/mnt/")) return;

    event.preventDefault();
    try {
      await openArtifactInNewWindow({ filepath: src, threadId });
    } catch (error) {
      console.error("Failed to open artifact:", error);
      toast.error("Failed to open artifact");
    }
  };

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
    >
      <img className={imgClassName} src={url} alt={alt} {...props} />
    </a>
  );
}

function MessageContent_({
  className,
  message,
  isLoading = false,
  threadId,
  feedbackRating,
  onFeedbackSubmitted,
  onClarificationSubmit,
  fallbackStructuredClarifications,
  tokenUsageEnabled: _tokenUsageEnabled = false,
  feedbackRunResolution,
}: {
  className?: string;
  message: Message;
  isLoading?: boolean;
  threadId: string;
  feedbackRating?: FeedbackRating | null;
  onFeedbackSubmitted?: (feedback: {
    messageId: string;
    runId: string;
    rating: FeedbackRating;
  }) => void;
  onClarificationSubmit?: ClarificationSubmitHandler;
  fallbackStructuredClarifications?: StructuredClarification[];
  tokenUsageEnabled?: boolean;
  feedbackRunResolution?: FeedbackRunResolutionOptions;
}) {
  const rehypePlugins = useRehypeSplitWordsIntoSpans(isLoading);
  const isHuman = message.type === "human";
  const components = useMemo(
    () => ({
      img: (props: ImgHTMLAttributes<HTMLImageElement>) => (
        <MessageImage {...props} threadId={threadId} maxWidth="90%" />
      ),
      a: ({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) => {
        if (href?.startsWith("/mnt/")) {
          const url = resolveArtifactURL(href, threadId);
          return (
            <a
              {...props}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={async (event) => {
                event.preventDefault();
                try {
                  await openArtifactInNewWindow({ filepath: href, threadId });
                } catch (error) {
                  console.error("Failed to open artifact:", error);
                  toast.error("Failed to open artifact");
                }
              }}
            />
          );
        }
        return <a {...props} href={href} />;
      },
    }),
    [threadId],
  );

  const rawContent = extractContentFromMessage(message);
  const reasoningContent = extractReasoningContentFromMessage(message);

  const files = useMemo(() => {
    const files = message.additional_kwargs?.files;
    if (!Array.isArray(files) || files.length === 0) {
      if (rawContent.includes("<uploaded_files>")) {
        // If the content contains the <uploaded_files> tag, we return the parsed files from the content for backward compatibility.
        return parseUploadedFiles(rawContent);
      }
      return null;
    }
    return files as FileInMessage[];
  }, [message.additional_kwargs?.files, rawContent]);

  const contentToDisplay = useMemo(() => {
    if (isHuman) {
      return rawContent ? stripUploadedFilesTag(rawContent) : "";
    }
    return rawContent ?? "";
  }, [rawContent, isHuman]);
  const messageStructuredClarifications = useMemo(() => {
    if (isHuman || isLoading || !onClarificationSubmit) {
      return [];
    }
    return parseStructuredClarificationsFromMessage(message);
  }, [isHuman, isLoading, message, onClarificationSubmit]);
  const usesFallbackStructuredClarifications =
    messageStructuredClarifications.length === 0 &&
    (fallbackStructuredClarifications?.length ?? 0) > 0;
  const structuredClarifications = useMemo(() => {
    if (isHuman || isLoading || !onClarificationSubmit) {
      return [];
    }
    if (messageStructuredClarifications.length > 0) {
      return messageStructuredClarifications;
    }
    return fallbackStructuredClarifications ?? [];
  }, [
    fallbackStructuredClarifications,
    isHuman,
    isLoading,
    messageStructuredClarifications,
    onClarificationSubmit,
  ]);
  const clarificationContentSegments = useMemo(() => {
    if (
      isHuman ||
      isLoading ||
      !onClarificationSubmit ||
      !contentToDisplay ||
      structuredClarifications.length > 0
    ) {
      return null;
    }
    const segments = parseStructuredClarificationContent(contentToDisplay);
    return segments.some((segment) => segment.type === "clarification")
      ? segments
      : null;
  }, [
    contentToDisplay,
    isHuman,
    isLoading,
    onClarificationSubmit,
    structuredClarifications.length,
  ]);

  const filesList =
    files && files.length > 0 ? (
      <RichFilesList files={files} threadId={threadId} />
    ) : null;

  // Uploading state: mock AI message shown while files upload
  if (message.additional_kwargs?.element === "task") {
    return (
      <AIElementMessageContent className={className}>
        <Task defaultOpen={false}>
          <TaskTrigger title="">
            <div className="text-muted-foreground flex w-full cursor-default items-center gap-2 text-sm select-none">
              <Loader className="size-4" />
              <span>{contentToDisplay}</span>
            </div>
          </TaskTrigger>
        </Task>
      </AIElementMessageContent>
    );
  }

  // Reasoning-only AI message (no main response content yet)
  if (!isHuman && reasoningContent && !rawContent) {
    return (
      <AIElementMessageContent className={className}>
        <Reasoning isStreaming={isLoading}>
          <ReasoningTrigger />
          <ReasoningContent>{reasoningContent}</ReasoningContent>
        </Reasoning>
        {!isLoading && (
          <MessageItemToolbar
            isHuman={isHuman}
            message={message}
            threadId={threadId}
            feedbackRating={feedbackRating}
            onFeedbackSubmitted={onFeedbackSubmitted}
            feedbackRunResolution={feedbackRunResolution}
          />
        )}
        {/* <MessageTokenUsage
          enabled={tokenUsageEnabled}
          isLoading={isLoading}
          message={message}
        /> */}
      </AIElementMessageContent>
    );
  }

  if (isHuman) {
    const messageResponse = contentToDisplay ? (
      <AIElementMessageResponse
        className={MARKDOWN_INLINE_CODE_IMPORTANT_CLASS}
        remarkPlugins={humanMessagePlugins.remarkPlugins}
        rehypePlugins={humanMessagePlugins.rehypePlugins}
        components={components}
        parseIncompleteMarkdown={false}
      >
        {contentToDisplay}
      </AIElementMessageResponse>
    ) : null;
    return (
      <div className={cn("ml-auto flex flex-col gap-2", className)}>
        {filesList}
        {messageResponse && (
          <AIElementMessageContent className="w-fit rounded-[20px] border border-[var(--chat-human-bubble)] bg-[var(--chat-human-bubble)] px-[17px] py-[12px] text-[var(--chat-human-bubble-text)] shadow-[0_12px_28px_oklch(0_0_0_/_0.28)] [&_*]:!text-[var(--chat-human-bubble-text)]">
            {messageResponse}
          </AIElementMessageContent>
        )}
      </div>
    );
  }

  return (
    <AIElementMessageContent
      className={cn(
        "relative w-full rounded-[20px] border border-[var(--chat-assistant-bubble-border)] bg-[var(--chat-assistant-bubble)] px-[17px] py-[16px] text-[var(--chat-assistant-bubble-text)] shadow-[0_13px_34px_oklch(0_0_0_/_0.29)]",
        className,
      )}
    >
      <div
        aria-hidden="true"
        className="absolute top-2 -left-[60px] flex size-[42px] items-center justify-center rounded-full border border-[#157575]"
      >
        <svg
          className="size-[30px]"
          viewBox="0 0 30 30"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M23 8V26L15 22C15 24.2091 13.2091 26 11 26C8.79086 26 7 24.2091 7 22V17L15 21V4L23 8Z"
            fill="url(#jialu-logo-gradient)"
          />
          <defs>
            <linearGradient
              id="jialu-logo-gradient"
              x1="15"
              y1="4"
              x2="15"
              y2="26"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="20%" stopColor="#157575" />
              <stop offset="100%" stopColor="#90F4E2" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      {filesList}
      {structuredClarifications.length > 0 ? (
        <div className="my-1 flex flex-col gap-3">
          {contentToDisplay.trim() && !usesFallbackStructuredClarifications ? (
            <MarkdownContent
              content={contentToDisplay}
              isLoading={isLoading}
              rehypePlugins={[
                ...rehypePlugins,
                [rehypeKatex, { output: "html" }],
              ]}
              className={cn(
                "text-[16px] leading-6",
                MARKDOWN_INLINE_CODE_CLASS,
              )}
              components={components}
            />
          ) : null}
          {structuredClarifications.map((clarification, index) => (
            <ClarificationCard
              key={`structured-clarification-${index}`}
              clarification={clarification}
              onSubmit={onClarificationSubmit}
              variant="embedded"
            />
          ))}
        </div>
      ) : clarificationContentSegments ? (
        <div className="my-1 flex flex-col gap-3">
          {clarificationContentSegments.map((segment, index) => {
            if (segment.type === "clarification") {
              return (
                <ClarificationCard
                  key={`clarification-${index}`}
                  clarification={segment.clarification}
                  onSubmit={onClarificationSubmit}
                  variant="embedded"
                />
              );
            }

            return (
              <MarkdownContent
                key={`markdown-${index}`}
                content={segment.content}
                isLoading={isLoading}
                rehypePlugins={[
                  ...rehypePlugins,
                  [rehypeKatex, { output: "html" }],
                ]}
                className={cn(
                  "text-[16px] leading-6",
                  MARKDOWN_INLINE_CODE_CLASS,
                )}
                components={components}
              />
            );
          })}
        </div>
      ) : (
        <MarkdownContent
          content={contentToDisplay}
          isLoading={isLoading}
          rehypePlugins={[...rehypePlugins, [rehypeKatex, { output: "html" }]]}
          className={cn(
            "my-1 text-[16px] leading-6",
            MARKDOWN_INLINE_CODE_CLASS,
          )}
          components={components}
        />
      )}
      {!isLoading && (
        <MessageItemToolbar
          isHuman={isHuman}
          message={message}
          threadId={threadId}
          feedbackRating={feedbackRating}
          onFeedbackSubmitted={onFeedbackSubmitted}
          feedbackRunResolution={feedbackRunResolution}
        />
      )}
      {/* <MessageTokenUsage
        enabled={tokenUsageEnabled}
        isLoading={isLoading}
        message={message}
      /> */}
    </AIElementMessageContent>
  );
}

/**
 * Get file extension and check helpers
 */
const getFileExt = (filename: string) =>
  filename.split(".").pop()?.toLowerCase() ?? "";

const FILE_TYPE_MAP: Record<string, string> = {
  json: "JSON",
  csv: "CSV",
  txt: "TXT",
  md: "Markdown",
  py: "Python",
  js: "JavaScript",
  ts: "TypeScript",
  tsx: "TSX",
  jsx: "JSX",
  html: "HTML",
  css: "CSS",
  xml: "XML",
  yaml: "YAML",
  yml: "YAML",
  pdf: "PDF",
  png: "PNG",
  jpg: "JPG",
  jpeg: "JPEG",
  gif: "GIF",
  svg: "SVG",
  zip: "ZIP",
  tar: "TAR",
  gz: "GZ",
};

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"];

function getFileTypeLabel(filename: string): string {
  const ext = getFileExt(filename);
  return FILE_TYPE_MAP[ext] ?? (ext.toUpperCase() || "FILE");
}

function isImageFile(filename: string): boolean {
  return IMAGE_EXTENSIONS.includes(getFileExt(filename));
}

/**
 * Format bytes to human-readable size string
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return "—";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/**
 * List of files from additional_kwargs.files (with optional upload status)
 */
function RichFilesList({
  files,
  threadId,
}: {
  files: FileInMessage[];
  threadId: string;
}) {
  if (files.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap justify-end gap-2">
      {files.map((file, index) => (
        <RichFileCard
          key={`${file.filename}-${index}`}
          file={file}
          threadId={threadId}
        />
      ))}
    </div>
  );
}

/**
 * Single file card that handles FileInMessage (supports uploading state)
 */
function RichFileCard({
  file,
  threadId,
}: {
  file: FileInMessage;
  threadId: string;
}) {
  const { t } = useI18n();
  const isUploading = file.status === "uploading";
  const isImage = isImageFile(file.filename);

  if (isUploading) {
    return (
      <div className="bg-background border-border/40 flex max-w-50 min-w-30 flex-col gap-1 rounded-lg border p-3 opacity-60 shadow-sm">
        <div className="flex items-start gap-2">
          <Loader2Icon className="text-muted-foreground mt-0.5 size-4 shrink-0 animate-spin" />
          <span
            className="text-foreground truncate text-sm font-medium"
            title={file.filename}
          >
            {file.filename}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <Badge
            variant="secondary"
            className="rounded px-1.5 py-0.5 text-[10px] font-normal"
          >
            {getFileTypeLabel(file.filename)}
          </Badge>
          <span className="text-muted-foreground text-[10px]">
            {t.uploads.uploading}
          </span>
        </div>
      </div>
    );
  }

  if (!file.path) return null;

  const fileUrl = resolveArtifactURL(file.path, threadId);

  if (isImage) {
    return (
      <a
        href={fileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="group border-border/40 relative block overflow-hidden rounded-lg border"
      >
        <img
          src={fileUrl}
          alt={file.filename}
          className="h-32 w-auto max-w-60 object-cover transition-transform group-hover:scale-105"
        />
      </a>
    );
  }

  return (
    <div className="bg-background border-border/40 flex max-w-50 min-w-30 flex-col gap-1 rounded-lg border p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <FileIcon className="text-muted-foreground mt-0.5 size-4 shrink-0" />
        <span
          className="text-foreground truncate text-sm font-medium"
          title={file.filename}
        >
          {file.filename}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <Badge
          variant="secondary"
          className="rounded px-1.5 py-0.5 text-[10px] font-normal"
        >
          {getFileTypeLabel(file.filename)}
        </Badge>
        <span className="text-muted-foreground text-[10px]">
          {formatBytes(file.size)}
        </span>
      </div>
    </div>
  );
}

const MessageContent = memo(MessageContent_);
