"use client";

import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { type PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import {
  ChatBox,
  useSpecificChatMode,
  useThreadChat,
} from "@/components/workspace/chats";
import { ExportTrigger } from "@/components/workspace/export-trigger";
import { InputBox } from "@/components/workspace/input-box";
import {
  MessageList,
  MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM,
} from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Welcome } from "@/components/workspace/welcome";
import type { FeedbackRating } from "@/core/api/feedback";
import { canAgentCapability, useAuthSession } from "@/core/auth";
import { getFigmaAssetURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";
import { useModels } from "@/core/models/hooks";
import { useNotification } from "@/core/notification/hooks";
import { useThreadSettings } from "@/core/settings";
import { useThreadStream } from "@/core/threads/hooks";
import { textOfMessage } from "@/core/threads/utils";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const { t } = useI18n();
  const [showFollowups, setShowFollowups] = useState(false);
  const [feedbackIpSignal, setFeedbackIpSignal] = useState<{
    rating: FeedbackRating;
    nonce: number;
  } | null>(null);
  const { threadId, setThreadId, isNewThread, setIsNewThread, isMock } =
    useThreadChat();
  const [settings, setSettings] = useThreadSettings(threadId);
  const [mounted, setMounted] = useState(false);
  const [composerHeight, setComposerHeight] = useState(isNewThread ? 160 : 118);
  const { tokenUsageEnabled } = useModels();
  const authSession = useAuthSession();
  useSpecificChatMode();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setComposerHeight(isNewThread ? 160 : 118);
  }, [isNewThread]);

  const { showNotification } = useNotification();

  const [thread, sendMessage, isUploading] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: settings.context,
    isMock,
    onStart: (createdThreadId) => {
      setThreadId(createdThreadId);
      setIsNewThread(false);
      // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
      history.replaceState(null, "", `/workspace/chats/${createdThreadId}`);
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages.at(-1);
        if (lastMessage) {
          const textContent = textOfMessage(lastMessage);
          if (textContent) {
            body =
              textContent.length > 200
                ? textContent.substring(0, 200) + "..."
                : textContent;
          }
        }
        showNotification(state.title, { body });
      }
    },
  });

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      void sendMessage(threadId, message);
    },
    [sendMessage, threadId],
  );
  const handleClarificationSubmit = useCallback(
    async (answer: string) => {
      await sendMessage(threadId, { text: answer, files: [] });
    },
    [sendMessage, threadId],
  );
  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);
  const handleFeedbackSubmitted = useCallback(
    ({
      rating,
    }: {
      messageId: string;
      runId: string;
      rating: FeedbackRating;
    }) => {
      setFeedbackIpSignal({ rating, nonce: Date.now() });
    },
    [],
  );

  const messageListPaddingBottom = showFollowups
    ? MESSAGE_LIST_DEFAULT_PADDING_BOTTOM +
      MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM
    : undefined;
  const shellHeaderBaseClass =
    "absolute top-0 right-0 left-0 z-30 px-2 pt-1 flex h-[72px] shrink-0 items-center rounded-xl sm:px-4 sm:pt-1 sm:h-[72px]";
  const messageListTopPaddingClass = !isNewThread
    ? "pt-[50px] sm:pt-[50px]"
    : "";
  const composerBottomClass = isNewThread ? "bottom-[20%]" : "bottom-[8%]";
  const composerMaxWidthClass = "max-w-[900px] sm:max-w-[900px]";
  const authReady = authSession?.agentPermissionStatus === "ready";
  const hasAiChatPermission = Boolean(
    authReady && canAgentCapability(authSession?.agentCapabilities, "aiChat"),
  );
  const permissionLoading =
    Boolean(authSession?.accessToken) &&
    (authSession?.agentPermissionStatus === "idle" ||
      authSession?.agentPermissionStatus === "loading");
  const permissionError =
    Boolean(authSession?.accessToken) &&
    authSession?.agentPermissionStatus === "error";
  const chatForbidden =
    Boolean(authSession?.accessToken) && authReady && !hasAiChatPermission;
  const permissionLocked =
    permissionLoading || permissionError || chatForbidden;
  const composerDisabled =
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
    isUploading ||
    permissionLocked;
  const composerHint =
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"
      ? t.common.notAvailableInDemoMode
      : permissionLoading
        ? t.workspace.permissionsLoading
        : permissionError
          ? t.workspace.permissionsLoadFailed
          : chatForbidden
            ? t.workspace.noAiChatPermission
            : null;
  const chatLineAssetLeft = isNewThread
    ? getFigmaAssetURL("lumax-common/high-chat-line-left.svg")
    : getFigmaAssetURL("lumax-common/low-chat-line-left.svg");
  const chatLineAssetRight = isNewThread
    ? getFigmaAssetURL("lumax-common/high-chat-line-right.svg")
    : getFigmaAssetURL("lumax-common/low-chat-line-right.svg");
  const chatLineSizeClass = isNewThread ? "h-[181px]" : "h-[138px]";
  const chatLineStyle = (asset: string) =>
    ({
      "--chat-line-image": `url(${asset})`,
      backgroundImage: "var(--chat-line-image)",
    }) as CSSProperties;

  return (
    <ThreadContext.Provider value={{ thread, isMock }}>
      <ChatBox threadId={threadId}>
        <div
          className={cn(
            "relative flex size-full min-h-0 justify-between overflow-hidden",
            isNewThread
              ? "chat-shell-background bg-[#02060a]"
              : "chat-shell-conversation-background",
          )}
        >
          {isNewThread && (
            <>
              <div
                aria-hidden
                className="chat-shell-stars pointer-events-none absolute inset-0 z-0"
              />
              <div
                aria-hidden
                className="chat-shell-planet pointer-events-none absolute inset-x-0 bottom-0 z-0 h-[70%]"
              />
            </>
          )}
          <header
            className={cn(
              shellHeaderBaseClass,
              "bg-[linear-gradient(180deg,#F1F5FA_60%,rgba(241,245,250,0)_100%)] dark:bg-[linear-gradient(180deg,#0B110B_60%,rgba(11,17,11,0)_100%)]",
            )}
          >
            <div className="flex w-full flex-col items-start justify-center">
              <ThreadTitle
                className="pb-1.5 text-[16px] font-semibold text-[#02060A] dark:text-[#FAFAFA]"
                threadId={threadId}
                thread={thread}
              />
              <div className="text-[12px] text-[#999999] dark:text-[#999999]">
                {t.workspace.generatedDisclaimer}
              </div>
            </div>
            {/* legacy-mismatch(chat): screenshot top bar keeps focus on title/disclaimer only */}
            <div className="hidden items-center gap-2">
              <TokenUsageIndicator
                enabled={tokenUsageEnabled}
                messages={thread.messages}
              />
              <ExportTrigger threadId={threadId} />
              <ArtifactTrigger />
            </div>
          </header>
          <main className="relative flex min-h-0 max-w-full grow flex-col">
            <div
              className="flex min-h-0 w-full justify-center"
              style={{
                height: `max(0px, calc(100% - ${composerHeight}px))`,
              }}
            >
              <MessageList
                className={cn(
                  "size-full px-2 pb-2 sm:px-4",
                  messageListTopPaddingClass,
                )}
                threadId={threadId}
                thread={thread}
                paddingBottom={messageListPaddingBottom}
                tokenUsageEnabled={tokenUsageEnabled}
                onClarificationSubmit={handleClarificationSubmit}
                onFeedbackSubmitted={handleFeedbackSubmitted}
              />
            </div>
            <div
              className={cn(
                "absolute right-0 left-0 z-30 flex justify-center px-2 sm:px-4",
                composerBottomClass,
              )}
            >
              <div
                className={cn(
                  "relative w-full pb-3 sm:pb-4",
                  composerMaxWidthClass,
                )}
              >
                <div className="absolute -top-4 right-0 left-0 z-0">
                  <div className="absolute right-0 bottom-0 left-0">
                    <TodoList
                      className="rounded-2xl backdrop-blur-md"
                      todos={thread.values.todos ?? []}
                      hidden={
                        !thread.values.todos || thread.values.todos.length === 0
                      }
                    />
                  </div>
                </div>
                {mounted ? (
                  <InputBox
                    isNewThread={isNewThread}
                    threadId={threadId}
                    autoFocus={isNewThread}
                    status={
                      thread.error
                        ? "error"
                        : thread.isLoading
                          ? "streaming"
                          : "ready"
                    }
                    context={settings.context}
                    extraHeader={
                      isNewThread && <Welcome mode={settings.context.mode} />
                    }
                    disabled={composerDisabled}
                    onContextChange={(context) =>
                      setSettings("context", context)
                    }
                    onFollowupsVisibilityChange={setShowFollowups}
                    onInputHeightChange={setComposerHeight}
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                    feedbackIpSignal={feedbackIpSignal}
                  />
                ) : (
                  <div
                    aria-hidden="true"
                    className={cn(
                      "flex w-full -translate-y-4 flex-col justify-between rounded-2xl p-5",
                      isNewThread ? "h-[160px]" : "h-[118px]",
                    )}
                  >
                    <div className="min-h-0 flex-1" />
                    <div className="h-9" />
                  </div>
                )}
                <div
                  aria-hidden
                  className={cn(
                    "chat-line-electric pointer-events-none absolute -bottom-[10px] -left-[20px] hidden w-[13.4375rem] overflow-visible bg-contain bg-no-repeat sm:block",
                    chatLineSizeClass,
                  )}
                  style={chatLineStyle(chatLineAssetLeft)}
                />
                <div
                  aria-hidden
                  className={cn(
                    "chat-line-electric chat-line-electric-right pointer-events-none absolute -right-[20px] -bottom-[10px] hidden w-[13.4375rem] overflow-visible bg-contain bg-no-repeat sm:block",
                    chatLineSizeClass,
                  )}
                  style={chatLineStyle(chatLineAssetRight)}
                />
                {composerHint && (
                  <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                    {composerHint}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
