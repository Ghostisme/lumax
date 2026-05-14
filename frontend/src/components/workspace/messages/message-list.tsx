import type { BaseStream } from "@langchain/langgraph-sdk/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  Conversation,
  ConversationContent,
} from "@/components/ai-elements/conversation";
import {
  feedbackDisplayPolarity,
  isFeedbackStatusError,
  isFeedbackUnauthorizedError,
  listThreadFeedback,
  type FeedbackRating,
  type ThreadFeedbackEntry,
} from "@/core/api/feedback";
import { useI18n } from "@/core/i18n/hooks";
import {
  parseStructuredClarification,
  parseStructuredClarificationsFromMessage,
  selectMatchingStructuredClarifications,
  type StructuredClarification,
} from "@/core/messages/clarification";
import {
  extractFeedbackRunId,
  findMessageConversationIndex,
  normalizeFeedbackRunId,
  recordValue,
  stringValue,
} from "@/core/messages/feedback-run-id";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractTextFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
  hasReasoning,
  hasToolCalls,
  isClarificationToolMessage,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import type { Subtask } from "@/core/tasks";
import { useUpdateSubtask } from "@/core/tasks/context";
import type { AgentThreadState } from "@/core/threads";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { StreamingIndicator } from "../streaming-indicator";

import {
  ClarificationCard,
  type ClarificationSubmitHandler,
} from "./clarification-card";
import { MarkdownContent } from "./markdown-content";
import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import { MessageTokenUsageList } from "./message-token-usage";
import { MessageListSkeleton } from "./skeleton";
import { SubtaskCard } from "./subtask-card";

export const MESSAGE_LIST_DEFAULT_PADDING_BOTTOM = 160;
export const MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM = 80;

type FeedbackLookup = {
  byMessageId: Map<string, FeedbackRating>;
  byRunId: Map<string, FeedbackRating>;
};

function buildFeedbackLookup(feedback: ThreadFeedbackEntry[]): FeedbackLookup {
  const byMessageId = new Map<string, FeedbackRating>();
  const byRunId = new Map<string, FeedbackRating>();

  for (const item of feedback) {
    const polarity = feedbackDisplayPolarity(item);
    if (!polarity) {
      continue;
    }

    const messageId = stringValue(item.message_id);
    if (messageId && !byMessageId.has(messageId)) {
      byMessageId.set(messageId, polarity);
    }

    const runId = normalizeFeedbackRunId(item.run_id);
    if (runId && !byRunId.has(runId)) {
      byRunId.set(runId, polarity);
    }
  }

  return { byMessageId, byRunId };
}

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  tokenUsageEnabled = false,
  onClarificationSubmit,
  onFeedbackSubmitted,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
  paddingBottom?: number;
  tokenUsageEnabled?: boolean;
  onClarificationSubmit?: ClarificationSubmitHandler;
  onFeedbackSubmitted?: (feedback: {
    messageId: string;
    runId: string;
    rating: FeedbackRating;
  }) => void;
}) {
  const { t } = useI18n();
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  const updateSubtask = useUpdateSubtask();
  const messages = thread.messages;
  const [feedbackEntries, setFeedbackEntries] = useState<ThreadFeedbackEntry[]>(
    [],
  );
  const feedbackLookup = useMemo(
    () => buildFeedbackLookup(feedbackEntries),
    [feedbackEntries],
  );
  const threadStructuredClarifications = useMemo(
    () => parseStructuredClarificationsFromMessage(thread.values),
    [thread.values],
  );
  const [pendingStructuredClarifications, setPendingStructuredClarifications] =
    useState<StructuredClarification[]>([]);
  useEffect(() => {
    if (threadStructuredClarifications.length > 0) {
      setPendingStructuredClarifications(threadStructuredClarifications);
    }
  }, [threadStructuredClarifications]);
  useEffect(() => {
    setPendingStructuredClarifications([]);
  }, [threadId]);
  const activeStructuredClarifications =
    threadStructuredClarifications.length > 0
      ? threadStructuredClarifications
      : pendingStructuredClarifications;
  const handleClarificationSubmit = useCallback<ClarificationSubmitHandler>(
    async (answer) => {
      setPendingStructuredClarifications([]);
      await onClarificationSubmit?.(answer);
    },
    [onClarificationSubmit],
  );
  const getClarificationSubmittedAnswer = useCallback(
    (clarification: StructuredClarification) => {
      const label = clarification.fieldLabel ?? clarification.question;
      const answerPrefix = `${label}：`;

      for (let index = messages.length - 1; index >= 0; index -= 1) {
        const message = messages[index];
        if (message?.type !== "human") {
          continue;
        }
        const content = extractContentFromMessage(message).trim();
        if (content.startsWith(answerPrefix)) {
          return content;
        }
      }
      return undefined;
    },
    [messages],
  );
  const resolveStructuredClarificationFallback = useCallback(
    (message: AgentThreadState["messages"][number]) => {
      if (message.type !== "ai" || activeStructuredClarifications.length === 0) {
        return undefined;
      }
      if (message.name === "structured_clarification") {
        return activeStructuredClarifications;
      }

      const messageText = extractContentFromMessage(message).trim();
      if (!messageText) {
        return undefined;
      }

      const matchingClarifications = selectMatchingStructuredClarifications(
        messageText,
        activeStructuredClarifications,
      );
      return matchingClarifications.length > 0
        ? matchingClarifications
        : undefined;
    },
    [activeStructuredClarifications],
  );
  const getFeedbackRating = useCallback(
    (message: AgentThreadState["messages"][number]): FeedbackRating | null => {
      const messageId = stringValue(recordValue(message, "id"));
      if (messageId) {
        const rating = feedbackLookup.byMessageId.get(messageId);
        if (rating) {
          return rating;
        }
      }

      const messageIndex = findMessageConversationIndex(messages, message);
      const streamMetadata =
        messageIndex >= 0
          ? thread.getMessagesMetadata(message, messageIndex)?.streamMetadata
          : undefined;
      const runId = extractFeedbackRunId(message, {
        conversationMessages: messages,
        messageIndex,
        streamMetadata,
      });
      return runId ? (feedbackLookup.byRunId.get(runId) ?? null) : null;
    },
    [feedbackLookup, messages, thread],
  );
  const handleFeedbackSubmitted = useCallback(
    (feedback: {
      messageId: string;
      runId: string;
      rating: FeedbackRating;
    }) => {
      setFeedbackEntries((current) => [
        {
          id: `local-${feedback.messageId || feedback.runId}`,
          thread_id: threadId,
          message_id: feedback.messageId,
          run_id: feedback.runId,
          rating: feedback.rating,
          result: feedback.rating,
        },
        ...current,
      ]);
      onFeedbackSubmitted?.(feedback);
    },
    [onFeedbackSubmitted, threadId],
  );

  useEffect(() => {
    if (!threadId || threadId === "new") {
      setFeedbackEntries([]);
      return;
    }

    let cancelled = false;
    listThreadFeedback(threadId)
      .then((feedback) => {
        if (!cancelled) {
          setFeedbackEntries(feedback);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.error("Failed to load thread feedback:", error);
          if (
            !isFeedbackUnauthorizedError(error) &&
            !isFeedbackStatusError(error, 500)
          ) {
            toast.error(t.feedback.failed);
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [t, threadId]);

  if (thread.isThreadLoading && messages.length === 0) {
    return <MessageListSkeleton />;
  }
  return (
    <Conversation
      className={cn("flex size-full flex-col justify-center", className)}
    >
      <ConversationContent className="mx-auto w-full max-w-[900px] gap-[1.2rem] px-1 pt-[3.65rem] sm:gap-6 sm:px-2 sm:pt-[4.1rem]">
        {groupMessages(messages, (group) => {
          if (group.type === "human" || group.type === "assistant") {
            return group.messages.map((msg) => {
              const messageIndex = findMessageConversationIndex(messages, msg);
              const streamMetadata =
                messageIndex >= 0
                  ? thread.getMessagesMetadata(msg, messageIndex)?.streamMetadata
                  : undefined;
              return (
                <MessageListItem
                  key={`${group.id}/${msg.id}`}
                  message={msg}
                  isLoading={thread.isLoading}
                  threadId={threadId}
                  feedbackRating={getFeedbackRating(msg)}
                  feedbackRunResolution={{
                    conversationMessages: messages,
                    messageIndex,
                    streamMetadata,
                  }}
                  onFeedbackSubmitted={handleFeedbackSubmitted}
                  onClarificationSubmit={
                    onClarificationSubmit ? handleClarificationSubmit : undefined
                  }
                  fallbackStructuredClarifications={resolveStructuredClarificationFallback(
                    msg,
                  )}
                  tokenUsageEnabled={tokenUsageEnabled}
                />
              );
            });
          } else if (group.type === "assistant:clarification") {
            const message = group.messages[0];
            if (message) {
              const structuredClarifications =
                parseStructuredClarificationsFromMessage(message);
              const content = extractContentFromMessage(message);
              const fallbackClarifications =
                structuredClarifications.length > 0
                  ? structuredClarifications
                  : selectMatchingStructuredClarifications(
                      content,
                      activeStructuredClarifications,
                    );
              if (fallbackClarifications.length > 0) {
                return (
                  <div key={group.id} className="w-full">
                    {fallbackClarifications.map((clarification, index) => (
                      <ClarificationCard
                        key={`${group.id}-structured-${index}`}
                        clarification={clarification}
                        submittedAnswer={getClarificationSubmittedAnswer(
                          clarification,
                        )}
                        onSubmit={
                          onClarificationSubmit
                            ? handleClarificationSubmit
                            : undefined
                        }
                      />
                    ))}
                    <MessageTokenUsageList
                      enabled={tokenUsageEnabled}
                      isLoading={thread.isLoading}
                      messages={group.messages}
                    />
                  </div>
                );
              }
            }
            if (message && hasContent(message)) {
              const content = extractContentFromMessage(message);
              const clarification = parseStructuredClarification(content);
              if (clarification) {
                return (
                  <div key={group.id} className="w-full">
                    <ClarificationCard
                      clarification={clarification}
                      submittedAnswer={getClarificationSubmittedAnswer(
                        clarification,
                      )}
                      onSubmit={
                        onClarificationSubmit
                          ? handleClarificationSubmit
                          : undefined
                      }
                    />
                    <MessageTokenUsageList
                      enabled={tokenUsageEnabled}
                      isLoading={thread.isLoading}
                      messages={group.messages}
                    />
                  </div>
                );
              }
              if (isClarificationToolMessage(message)) {
                return null;
              }
              return (
                <div key={group.id} className="w-full">
                  <MarkdownContent
                    content={content}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                  />
                  <MessageTokenUsageList
                    enabled={tokenUsageEnabled}
                    isLoading={thread.isLoading}
                    messages={group.messages}
                  />
                </div>
              );
            }
            return null;
          } else if (group.type === "assistant:present-files") {
            const files: string[] = [];
            for (const message of group.messages) {
              if (hasPresentFiles(message)) {
                const presentFiles = extractPresentFilesFromMessage(message);
                files.push(...presentFiles);
              }
            }
            return (
              <div className="w-full" key={group.id}>
                {group.messages[0] && hasContent(group.messages[0]) && (
                  <MarkdownContent
                    content={extractContentFromMessage(group.messages[0])}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                    className="mb-4"
                  />
                )}
                <ArtifactFileList files={files} threadId={threadId} />
                <MessageTokenUsageList
                  enabled={tokenUsageEnabled}
                  isLoading={thread.isLoading}
                  messages={group.messages}
                />
              </div>
            );
          } else if (group.type === "assistant:subagent") {
            const tasks = new Set<Subtask>();
            for (const message of group.messages) {
              if (message.type === "ai") {
                for (const toolCall of message.tool_calls ?? []) {
                  if (toolCall.name === "task") {
                    const task: Subtask = {
                      id: toolCall.id!,
                      subagent_type: toolCall.args.subagent_type,
                      description: toolCall.args.description,
                      prompt: toolCall.args.prompt,
                      status: "in_progress",
                    };
                    updateSubtask(task);
                    tasks.add(task);
                  }
                }
              } else if (message.type === "tool") {
                const taskId = message.tool_call_id;
                if (taskId) {
                  const result = extractTextFromMessage(message);
                  if (result.startsWith("Task Succeeded. Result:")) {
                    updateSubtask({
                      id: taskId,
                      status: "completed",
                      result: result
                        .split("Task Succeeded. Result:")[1]
                        ?.trim(),
                    });
                  } else if (result.startsWith("Task failed.")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result.split("Task failed.")[1]?.trim(),
                    });
                  } else if (result.startsWith("Task timed out")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result,
                    });
                  } else {
                    updateSubtask({
                      id: taskId,
                      status: "in_progress",
                    });
                  }
                }
              }
            }
            const results: React.ReactNode[] = [];
            for (const message of group.messages.filter(
              (message) => message.type === "ai",
            )) {
              if (hasReasoning(message)) {
                results.push(
                  <MessageGroup
                    key={"thinking-group-" + message.id}
                    messages={[message]}
                    isLoading={thread.isLoading}
                  />,
                );
              }
              results.push(
                <div
                  key="subtask-count"
                  className="text-muted-foreground pt-2 text-sm font-normal"
                >
                  {t.subtasks.executing(tasks.size)}
                </div>,
              );
              const taskIds = message.tool_calls
                ?.filter((toolCall) => toolCall.name === "task")
                .map((toolCall) => toolCall.id);
              for (const taskId of taskIds ?? []) {
                results.push(
                  <SubtaskCard
                    key={"task-group-" + taskId}
                    taskId={taskId!}
                    isLoading={thread.isLoading}
                  />,
                );
              }
            }
            return (
              <div
                key={"subtask-group-" + group.id}
                className="relative z-1 flex flex-col gap-2"
              >
                {results}
                <MessageTokenUsageList
                  enabled={tokenUsageEnabled}
                  isLoading={thread.isLoading}
                  messages={group.messages}
                />
              </div>
            );
          }
          const tokenUsageMessages = group.messages.filter(
            (message) =>
              message.type === "ai" &&
              (hasToolCalls(message) ? true : !hasContent(message)),
          );
          return (
            <div key={"group-" + group.id} className="w-full">
              <MessageGroup
                messages={group.messages}
                isLoading={thread.isLoading}
              />
              <MessageTokenUsageList
                enabled={tokenUsageEnabled}
                isLoading={thread.isLoading}
                messages={tokenUsageMessages}
              />
            </div>
          );
        })}
        {thread.isLoading && <StreamingIndicator className="my-4" />}
        <div style={{ height: `${paddingBottom}px` }} />
      </ConversationContent>
    </Conversation>
  );
}
