"use client";

import type { ChatStatus } from "ai";
import {
  CheckIcon,
  FactoryIcon,
  FolderOpenIcon,
  GraduationCapIcon,
  LightbulbIcon,
  MessageSquareIcon,
  PaperclipIcon,
  RocketIcon,
  TrendingUpIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ComponentProps,
  type MouseEvent,
} from "react";

import {
  PromptInput,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputAttachments,
  usePromptInputController,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import type { FeedbackRating } from "@/core/api/feedback";
import {
  canAgentCapability,
  fetchWithAuth,
  requestLoginDialog,
  useAuthSession,
  type AgentCapabilityKey,
} from "@/core/auth";
import { getBackendBaseURL, getFigmaAssetURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";
import { useModels } from "@/core/models/hooks";
import type { AgentThreadContext } from "@/core/threads";
import { textOfMessage } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "../ai-elements/model-selector";
import { Suggestion, Suggestions } from "../ai-elements/suggestion";

import { useThread } from "./messages/context";
import { ModeHoverGuide } from "./mode-hover-guide";
import { Tooltip } from "./tooltip";

type InputMode = "flash" | "thinking" | "pro" | "ultra";

function getResolvedMode(
  mode: InputMode | undefined,
  supportsThinking: boolean,
): InputMode {
  if (!supportsThinking && mode !== "flash") {
    return "flash";
  }
  if (mode) {
    return mode;
  }
  return supportsThinking ? "pro" : "flash";
}

const INPUT_EXPAND_LINE_THRESHOLD = 4;
const IP_IDLE_TIMEOUT_MS = 60_000;
const IP_CANCEL_TO_THINKING_DISPLAY_MS = 2500;
const IP_THINKING_TO_RESULT_DISPLAY_MS = 2500;
const IP_GOOD_DISPLAY_MS = 4_000;
const IP_FEEDBACK_DISPLAY_MS = 6_500;

type ChatIpState =
  | "thinking"
  | "good"
  | "sleep"
  | "fail"
  | "thinkingtoresult"
  | "canceltothinking"
  | "negative"
  | "positive";

const CHAT_IP_IMAGE_BY_STATE: Record<ChatIpState, string> = {
  thinking: getFigmaAssetURL("jialu-chat/thinking-ip.gif"),
  thinkingtoresult: getFigmaAssetURL("jialu-chat/thinkingtoresult-ip.gif"),
  good: getFigmaAssetURL("jialu-chat/good-ip.gif"),
  sleep: getFigmaAssetURL("jialu-chat/sleep-ip.gif"),
  fail: getFigmaAssetURL("jialu-chat/fail-ip.gif"),
  canceltothinking: getFigmaAssetURL("jialu-chat/canceltothinking.gif"),
  negative: getFigmaAssetURL("jialu-chat/negative-ip.gif"),
  positive: getFigmaAssetURL("jialu-chat/positive-ip.gif"),
};

type ChatIpRenderCalibration = {
  scale: number;
  x: number;
  y: number;
};

const CHAT_IP_RENDER_CALIBRATION_BY_STATE: Record<
  ChatIpState,
  ChatIpRenderCalibration
> = {
  thinking: { scale: 0.9, x: 0, y: 0 },
  thinkingtoresult: { scale: 0.9, x: 0, y: 0 },
  good: { scale: 0.9, x: 0, y: 10 },
  fail: { scale: 1.1, x: 0, y: 0 },
  sleep: { scale: 0.9, x: 8, y: 8 },
  canceltothinking: { scale: 0.9, x: -18, y: -2 },
  negative: { scale: 0.9, x: 0, y: 10 },
  positive: { scale: 0.9, x: 0, y: 14 },
};

function getTextareaLineHeight(textarea: HTMLTextAreaElement): number {
  const styles = window.getComputedStyle(textarea);
  const lineHeight = Number.parseFloat(styles.lineHeight);

  if (Number.isFinite(lineHeight)) {
    return lineHeight;
  }

  const fontSize = Number.parseFloat(styles.fontSize);
  return Number.isFinite(fontSize) ? fontSize * 1.5 : 24;
}

function shouldExpandInput(textarea: HTMLTextAreaElement): boolean {
  if (textarea.value.trim().length === 0) {
    return false;
  }

  const previousHeight = textarea.style.height;
  const previousMinHeight = textarea.style.minHeight;
  const previousMaxHeight = textarea.style.maxHeight;

  textarea.style.height = "0px";
  textarea.style.minHeight = "0px";
  textarea.style.maxHeight = "none";
  const contentHeight = textarea.scrollHeight;
  textarea.style.height = previousHeight;
  textarea.style.minHeight = previousMinHeight;
  textarea.style.maxHeight = previousMaxHeight;

  return (
    contentHeight >
    getTextareaLineHeight(textarea) * INPUT_EXPAND_LINE_THRESHOLD + 1
  );
}

export function InputBox({
  className,
  disabled,
  autoFocus,
  status = "ready",
  context,
  extraHeader,
  isNewThread,
  threadId,
  initialValue,
  onContextChange,
  onFollowupsVisibilityChange,
  onInputHeightChange,
  onSubmit,
  onStop,
  feedbackIpSignal,
  ...props
}: Omit<ComponentProps<typeof PromptInput>, "onSubmit"> & {
  assistantId?: string | null;
  status?: ChatStatus;
  disabled?: boolean;
  context: Omit<
    AgentThreadContext,
    "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
  > & {
    mode: "flash" | "thinking" | "pro" | "ultra" | undefined;
    reasoning_effort?: "minimal" | "low" | "medium" | "high";
  };
  extraHeader?: React.ReactNode;
  isNewThread?: boolean;
  threadId: string;
  initialValue?: string;
  onContextChange?: (
    context: Omit<
      AgentThreadContext,
      "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
    > & {
      mode: "flash" | "thinking" | "pro" | "ultra" | undefined;
      reasoning_effort?: "minimal" | "low" | "medium" | "high";
    },
  ) => void;
  onFollowupsVisibilityChange?: (visible: boolean) => void;
  onInputHeightChange?: (height: number) => void;
  onSubmit?: (message: PromptInputMessage) => void;
  onStop?: () => void;
  feedbackIpSignal?: {
    rating: FeedbackRating;
    nonce: number;
  } | null;
}) {
  const { t } = useI18n();
  const authSession = useAuthSession();
  const searchParams = useSearchParams();
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const { models } = useModels();
  const { thread, isMock } = useThread();
  const { textInput } = usePromptInputController();
  const attachments = usePromptInputAttachments();
  const shouldReduceMotion = useReducedMotion();
  const hasInputContent = textInput.value.trim().length > 0;
  const canUseCapability = useCallback(
    (capability: AgentCapabilityKey): boolean => {
      if (!authSession?.accessToken) {
        return true;
      }
      if (authSession.agentPermissionStatus !== "ready") {
        return false;
      }
      return canAgentCapability(authSession.agentCapabilities, capability);
    },
    [
      authSession?.accessToken,
      authSession?.agentCapabilities,
      authSession?.agentPermissionStatus,
    ],
  );
  const promptRootRef = useRef<HTMLDivElement | null>(null);
  const [isInputExpanded, setIsInputExpanded] = useState(false);
  const [smartDistributionSelected, setSmartDistributionSelected] =
    useState(false);

  const [followups, setFollowups] = useState<string[]>([]);
  const [followupsHidden, setFollowupsHidden] = useState(false);
  const [followupsLoading, setFollowupsLoading] = useState(false);
  const lastGeneratedForAiIdRef = useRef<string | null>(null);
  const wasStreamingRef = useRef(false);
  const [chatIpState, setChatIpState] = useState<ChatIpState | null>(null);
  const wasStreamingForIpRef = useRef(false);
  const shouldShowCancelToThinkingRef = useRef(false);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(
    null,
  );
  const hasConversationAttachments =
    !isNewThread && attachments.files.length > 0;
  const inputHeight = isInputExpanded
    ? 280
    : hasConversationAttachments
      ? 174
      : isNewThread
        ? 160
        : 118;

  useEffect(() => {
    onInputHeightChange?.(inputHeight);
  }, [inputHeight, onInputHeightChange]);

  useEffect(() => {
    setChatIpState(null);
    wasStreamingForIpRef.current = false;
    shouldShowCancelToThinkingRef.current = false;
  }, [isNewThread, threadId]);

  useEffect(() => {
    Object.values(CHAT_IP_IMAGE_BY_STATE).forEach((src) => {
      const image = new Image();
      image.src = src;
    });
  }, []);

  useEffect(() => {
    if (isNewThread) {
      return;
    }

    if (status === "error") {
      setChatIpState("fail");
      wasStreamingForIpRef.current = false;
      shouldShowCancelToThinkingRef.current = true;
      return;
    }

    if (status === "streaming") {
      wasStreamingForIpRef.current = true;
      if (shouldShowCancelToThinkingRef.current) {
        shouldShowCancelToThinkingRef.current = false;
        setChatIpState("canceltothinking");
        return;
      }
      setChatIpState("thinking");
      return;
    }

    if (wasStreamingForIpRef.current && status === "ready") {
      setChatIpState("thinkingtoresult");
    }
    wasStreamingForIpRef.current = false;
  }, [isNewThread, status]);

  useEffect(() => {
    if (isNewThread || status !== "ready") {
      return;
    }

    let timeout: number | undefined;
    const activityEvents: (keyof WindowEventMap)[] = [
      "pointerdown",
      "keydown",
      "wheel",
      "touchstart",
    ];

    const startIdleTimer = () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }
      timeout = window.setTimeout(() => {
        setChatIpState((current) => current ?? "sleep");
      }, IP_IDLE_TIMEOUT_MS);
    };

    const handleActivity = () => {
      setChatIpState((current) => (current === "sleep" ? null : current));
      startIdleTimer();
    };

    startIdleTimer();
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleActivity, { passive: true });
    });

    return () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleActivity);
      });
    };
  }, [isNewThread, status]);

  useEffect(() => {
    if (chatIpState !== "canceltothinking" || status !== "streaming") {
      return;
    }

    const timeout = window.setTimeout(() => {
      setChatIpState("thinking");
    }, IP_CANCEL_TO_THINKING_DISPLAY_MS);

    return () => window.clearTimeout(timeout);
  }, [chatIpState, status]);

  useEffect(() => {
    if (chatIpState !== "thinkingtoresult") {
      return;
    }

    const timeout = window.setTimeout(() => {
      setChatIpState("good");
    }, IP_THINKING_TO_RESULT_DISPLAY_MS);

    return () => window.clearTimeout(timeout);
  }, [chatIpState]);

  useEffect(() => {
    if (chatIpState !== "good") {
      return;
    }

    const timeout = window.setTimeout(() => {
      setChatIpState(null);
    }, IP_GOOD_DISPLAY_MS);

    return () => window.clearTimeout(timeout);
  }, [chatIpState]);

  useEffect(() => {
    if (!feedbackIpSignal) {
      return;
    }

    setChatIpState(feedbackIpSignal.rating);
    const timeout = window.setTimeout(() => {
      setChatIpState((current) =>
        current === feedbackIpSignal.rating ? null : current,
      );
    }, IP_FEEDBACK_DISPLAY_MS);

    return () => window.clearTimeout(timeout);
  }, [feedbackIpSignal]);

  useEffect(() => {
    if (models.length === 0) {
      return;
    }
    const currentModel = models.find((m) => m.name === context.model_name);
    const fallbackModel = currentModel ?? models[0]!;
    const supportsThinking = fallbackModel.supports_thinking ?? false;
    const nextModelName = fallbackModel.name;
    const nextMode = getResolvedMode(context.mode, supportsThinking);

    if (context.model_name === nextModelName && context.mode === nextMode) {
      return;
    }

    onContextChange?.({
      ...context,
      model_name: nextModelName,
      mode: nextMode,
    });
  }, [context, models, onContextChange]);

  const selectedModel = useMemo(() => {
    if (models.length === 0) {
      return undefined;
    }
    return models.find((m) => m.name === context.model_name) ?? models[0];
  }, [context.model_name, models]);

  const resolvedModelName = selectedModel?.name;

  const supportThinking = useMemo(
    () => selectedModel?.supports_thinking ?? false,
    [selectedModel],
  );

  const supportReasoningEffort = useMemo(
    () => selectedModel?.supports_reasoning_effort ?? false,
    [selectedModel],
  );

  const handleModelSelect = useCallback(
    (model_name: string) => {
      const model = models.find((m) => m.name === model_name);
      if (!model) {
        return;
      }
      onContextChange?.({
        ...context,
        model_name,
        mode: getResolvedMode(context.mode, model.supports_thinking ?? false),
        reasoning_effort: context.reasoning_effort,
      });
      setModelDialogOpen(false);
    },
    [onContextChange, context, models],
  );

  const handleModeSelect = useCallback(
    (mode: InputMode) => {
      onContextChange?.({
        ...context,
        mode: getResolvedMode(mode, supportThinking),
        reasoning_effort:
          mode === "ultra"
            ? "high"
            : mode === "pro"
              ? "medium"
              : mode === "thinking"
                ? "low"
                : "minimal",
      });
    },
    [onContextChange, context, supportThinking],
  );

  const handleReasoningEffortSelect = useCallback(
    (effort: "minimal" | "low" | "medium" | "high") => {
      onContextChange?.({
        ...context,
        reasoning_effort: effort,
      });
    },
    [onContextChange, context],
  );

  // Lumax: 输入区多块入口 JSX 已用块注释关闭；占位引用以避免 no-unused-vars。恢复时请删本表达式并移除 JSX 块注释。
  void [
    CheckIcon,
    FolderOpenIcon,
    GraduationCapIcon,
    LightbulbIcon,
    MessageSquareIcon,
    RocketIcon,
    ZapIcon,
    PromptInputActionMenu,
    PromptInputActionMenuContent,
    PromptInputActionMenuItem,
    PromptInputActionMenuTrigger,
    DropdownMenuGroup,
    DropdownMenuLabel,
    ModelSelector,
    ModelSelectorContent,
    ModelSelectorInput,
    ModelSelectorItem,
    ModelSelectorList,
    ModelSelectorName,
    ModelSelectorTrigger,
    ModeHoverGuide,
    supportReasoningEffort,
    modelDialogOpen,
    handleModelSelect,
    handleModeSelect,
    handleReasoningEffortSelect,
  ];

  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      if (status === "streaming") {
        shouldShowCancelToThinkingRef.current = true;
        onStop?.();
        return;
      }
      if (!message.text) {
        return;
      }
      if (!authSession?.accessToken) {
        requestLoginDialog("required");
        return;
      }
      if (!canUseCapability("aiChat")) {
        return;
      }
      setFollowups([]);
      setFollowupsHidden(false);
      setFollowupsLoading(false);
      setIsInputExpanded(false);

      // Guard against submitting before the initial model auto-selection
      // effect has flushed thread settings to storage/state.
      if (resolvedModelName && context.model_name !== resolvedModelName) {
        onContextChange?.({
          ...context,
          model_name: resolvedModelName,
          mode: getResolvedMode(
            context.mode,
            selectedModel?.supports_thinking ?? false,
          ),
        });
        setTimeout(() => onSubmit?.(message), 0);
        return;
      }

      onSubmit?.(message);
    },
    [
      context,
      onContextChange,
      onSubmit,
      onStop,
      authSession?.accessToken,
      canUseCapability,
      resolvedModelName,
      selectedModel?.supports_thinking,
      status,
    ],
  );

  const requestFormSubmit = useCallback(() => {
    const form = promptRootRef.current?.querySelector("form");
    form?.requestSubmit();
  }, []);

  const handleTextareaChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      setIsInputExpanded(shouldExpandInput(event.currentTarget));
    },
    [],
  );

  const handleSmartDistributionToggle = useCallback(() => {
    setSmartDistributionSelected((selected) => !selected);
  }, []);

  useEffect(() => {
    const textarea = promptRootRef.current?.querySelector<HTMLTextAreaElement>(
      "textarea[name='message']",
    );
    if (!textarea || textInput.value.trim().length === 0) {
      setIsInputExpanded(false);
      return;
    }

    const frame = requestAnimationFrame(() => {
      setIsInputExpanded(shouldExpandInput(textarea));
    });

    return () => cancelAnimationFrame(frame);
  }, [textInput.value]);

  const handlePromptAreaClick = useCallback(
    (event: MouseEvent<HTMLFormElement>) => {
      const target = event.target as HTMLElement;
      if (
        target.closest(
          "button,a,input,select,[role='button'],[data-no-focus-input='true']",
        )
      ) {
        return;
      }
      promptRootRef.current
        ?.querySelector<HTMLTextAreaElement>("textarea[name='message']")
        ?.focus();
    },
    [],
  );

  const handleFollowupClick = useCallback(
    (suggestion: string) => {
      if (status === "streaming") {
        return;
      }
      const current = (textInput.value ?? "").trim();
      if (current) {
        setPendingSuggestion(suggestion);
        setConfirmOpen(true);
        return;
      }
      textInput.setInput(suggestion);
      setFollowupsHidden(true);
      setTimeout(() => requestFormSubmit(), 0);
    },
    [requestFormSubmit, status, textInput],
  );

  const confirmReplaceAndSend = useCallback(() => {
    if (!pendingSuggestion) {
      setConfirmOpen(false);
      return;
    }
    textInput.setInput(pendingSuggestion);
    setFollowupsHidden(true);
    setConfirmOpen(false);
    setPendingSuggestion(null);
    setTimeout(() => requestFormSubmit(), 0);
  }, [pendingSuggestion, requestFormSubmit, textInput]);

  const confirmAppendAndSend = useCallback(() => {
    if (!pendingSuggestion) {
      setConfirmOpen(false);
      return;
    }
    const current = (textInput.value ?? "").trim();
    const next = current
      ? `${current}\n${pendingSuggestion}`
      : pendingSuggestion;
    textInput.setInput(next);
    setFollowupsHidden(true);
    setConfirmOpen(false);
    setPendingSuggestion(null);
    setTimeout(() => requestFormSubmit(), 0);
  }, [pendingSuggestion, requestFormSubmit, textInput]);

  const showFollowups =
    !disabled &&
    !isNewThread &&
    !followupsHidden &&
    (followupsLoading || followups.length > 0);

  const followupsVisibilityChangeRef = useRef(onFollowupsVisibilityChange);

  useEffect(() => {
    followupsVisibilityChangeRef.current = onFollowupsVisibilityChange;
  }, [onFollowupsVisibilityChange]);

  useEffect(() => {
    followupsVisibilityChangeRef.current?.(showFollowups);
  }, [showFollowups]);

  useEffect(() => {
    return () => followupsVisibilityChangeRef.current?.(false);
  }, []);

  useEffect(() => {
    const streaming = status === "streaming";
    const wasStreaming = wasStreamingRef.current;
    wasStreamingRef.current = streaming;
    if (!wasStreaming || streaming) {
      return;
    }

    if (disabled || isMock) {
      return;
    }

    const lastAi = [...thread.messages].reverse().find((m) => m.type === "ai");
    const lastAiId = lastAi?.id ?? null;
    if (!lastAiId || lastAiId === lastGeneratedForAiIdRef.current) {
      return;
    }
    lastGeneratedForAiIdRef.current = lastAiId;

    const recent = thread.messages
      .filter((m) => m.type === "human" || m.type === "ai")
      .map((m) => {
        const role = m.type === "human" ? "user" : "assistant";
        const content = textOfMessage(m) ?? "";
        return { role, content };
      })
      .filter((m) => m.content.trim().length > 0)
      .slice(-6);

    if (recent.length === 0) {
      return;
    }

    const controller = new AbortController();
    setFollowupsHidden(false);
    setFollowupsLoading(true);
    setFollowups([]);

    fetchWithAuth(
      `${getBackendBaseURL()}/api/threads/${threadId}/suggestions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: recent,
          n: 3,
          model_name: context.model_name ?? undefined,
        }),
        signal: controller.signal,
      },
    )
      .then(async (res) => {
        if (!res.ok) {
          return { suggestions: [] as string[] };
        }
        return (await res.json()) as { suggestions?: string[] };
      })
      .then((data) => {
        const suggestions = (data.suggestions ?? [])
          .map((s) => (typeof s === "string" ? s.trim() : ""))
          .filter((s) => s.length > 0)
          .slice(0, 5);
        setFollowups(suggestions);
      })
      .catch(() => {
        setFollowups([]);
      })
      .finally(() => {
        setFollowupsLoading(false);
      });

    return () => controller.abort();
  }, [context.model_name, disabled, isMock, status, thread.messages, threadId]);

  return (
    <div ref={promptRootRef} className="relative flex flex-col gap-3 sm:gap-4">
      {showFollowups && (
        <div className="flex items-center justify-start pb-1 sm:pb-2">
          <div className="flex items-center gap-2">
            {followupsLoading ? (
              <div className="rounded-full border border-[var(--chat-input-border)] bg-[var(--chat-panel-bg)] px-4 py-2 text-xs text-[var(--chat-text-soft)] backdrop-blur-sm">
                {t.inputBox.followupLoading}
              </div>
            ) : (
              <Suggestions className="w-fit items-start">
                {followups.map((s) => (
                  <Suggestion
                    key={s}
                    suggestion={s}
                    onClick={() => handleFollowupClick(s)}
                  />
                ))}
                <Button
                  aria-label={t.common.close}
                  className="cursor-pointer rounded-full border-[var(--chat-input-border)] px-3 text-xs font-normal text-[var(--chat-text-soft)]"
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={() => setFollowupsHidden(true)}
                >
                  <XIcon className="size-4" />
                </Button>
              </Suggestions>
            )}
          </div>
        </div>
      )}
      {isNewThread && searchParams.get("mode") !== "skill" && (
        <div className="relative z-40 -mb-11 flex items-center justify-start pb-12 sm:-mb-13">
          <SuggestionList />
        </div>
      )}
      <PromptInput
        className={cn(
          "relative z-30 rounded-[24px] bg-[var(--chat-input-surface)] backdrop-blur-sm transition-all duration-300 ease-out *:data-[slot='input-group']:h-full *:data-[slot='input-group']:items-stretch *:data-[slot='input-group']:rounded-[24px] *:data-[slot='input-group']:border-0 *:data-[slot='input-group']:bg-transparent *:data-[slot='input-group']:shadow-none",
          "chat-input-rotating-border border-2 border-transparent bg-[linear-gradient(var(--chat-input-surface),var(--chat-input-surface)),conic-gradient(from_var(--chat-input-border-angle),#48CE0A_0deg,#FF9616_112deg,#FF16B9_218deg,#48CE0A_288deg,#44CA06_318deg,#BEFFA0_344deg,#F4FFD8_354deg,#48CE0A_360deg)] [background-clip:padding-box,border-box] bg-origin-border shadow-[0_0_40px_0_#44CA0640] dark:shadow-[0_0_40px_0_#BEFFA040]",
          isInputExpanded
            ? "h-[280px]"
            : hasConversationAttachments
              ? "h-[174px]"
              : isNewThread
                ? "h-[160px]"
                : "h-[118px]",
          className,
        )}
        disabled={disabled}
        globalDrop
        multiple
        onClick={handlePromptAreaClick}
        onSubmit={handleSubmit}
        {...props}
      >
        {!isNewThread && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-44 -right-4 z-20 h-48 w-48 select-none"
          >
            <AnimatePresence mode="sync" initial={false}>
              {chatIpState &&
                (() => {
                  const calibration =
                    CHAT_IP_RENDER_CALIBRATION_BY_STATE[chatIpState];
                  return (
                    <motion.img
                      key={chatIpState}
                      src={CHAT_IP_IMAGE_BY_STATE[chatIpState]}
                      alt=""
                      className="absolute inset-0 h-full w-full object-contain object-right-bottom"
                      initial={
                        shouldReduceMotion
                          ? { opacity: 0, x: calibration.x, y: calibration.y }
                          : {
                              opacity: 0,
                              scale: calibration.scale * 0.995,
                              x: calibration.x,
                              y: calibration.y,
                            }
                      }
                      animate={
                        shouldReduceMotion
                          ? { opacity: 1, x: calibration.x, y: calibration.y }
                          : {
                              opacity: 1,
                              scale: calibration.scale,
                              x: calibration.x,
                              y: calibration.y,
                            }
                      }
                      exit={
                        shouldReduceMotion
                          ? { opacity: 0, x: calibration.x, y: calibration.y }
                          : {
                              opacity: 0,
                              scale: calibration.scale * 1.005,
                              x: calibration.x,
                              y: calibration.y,
                            }
                      }
                      transition={{
                        duration: shouldReduceMotion ? 0.1 : 0.18,
                        ease: [0.22, 1, 0.36, 1],
                      }}
                    />
                  );
                })()}
            </AnimatePresence>
          </div>
        )}
        {extraHeader && (
          <div className="pointer-events-none absolute top-0 right-0 left-0 z-10">
            <div className="absolute right-0 bottom-0 left-0 flex items-center justify-center">
              {extraHeader}
            </div>
          </div>
        )}
        {isNewThread && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 z-[15] rounded-[24px] bg-[var(--chat-input-surface)]"
          />
        )}
        <PromptInputAttachments className="relative z-20 max-h-20 shrink-0 overflow-y-auto px-5 pt-4 pb-0">
          {(attachment) => (
            <PromptInputAttachment
              className="max-w-full bg-[var(--chat-input-surface)]"
              data={attachment}
            />
          )}
        </PromptInputAttachments>
        <PromptInputBody className="relative z-20 flex min-h-0 flex-1">
          <PromptInputTextarea
            className={cn(
              "my-4 block field-sizing-fixed size-full min-h-0 max-w-none self-stretch overflow-y-auto overscroll-contain border-0 px-5 py-0! !text-left text-[16px] leading-[1.5] text-[#181D27] shadow-none outline-none placeholder:!text-left placeholder:text-[var(--chat-placeholder-text)] focus-visible:ring-0 focus-visible:outline-none dark:text-[#FAFAFA]",
            )}
            style={{ textAlign: "left" }}
            disabled={disabled}
            placeholder={t.inputBox.placeholder}
            autoFocus={autoFocus}
            defaultValue={initialValue}
            onChange={handleTextareaChange}
          />
        </PromptInputBody>
        <PromptInputFooter className="relative z-30 flex h-9 items-center gap-2 p-0! px-5! pb-5! text-[#666666] dark:text-[#FAFAFA]">
          <PromptInputTools className="no-scrollbar h-9 flex-1 gap-1 overflow-x-auto whitespace-nowrap">
            <AddAttachmentsButton className="rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-2! dark:!border-[#073803]" />
            {[
              {
                key: "contentFactory" as AgentCapabilityKey,
                icon: FactoryIcon,
                label: t.inputBox.contentFactory,
              },
              {
                key: "smartDistribution" as AgentCapabilityKey,
                icon: TrendingUpIcon,
                label: t.inputBox.smartDistribution,
              },
            ]
              .filter((item) => canUseCapability(item.key))
              .map((item) => (
                <PromptInputButton
                  key={item.key}
                  aria-pressed={
                    item.key === "smartDistribution"
                      ? smartDistributionSelected
                      : undefined
                  }
                  className={cn(
                    "gap-1! rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-3! dark:!border-[#073803]",
                    item.key === "smartDistribution" &&
                      smartDistributionSelected &&
                      "!border-[#16A34A] bg-[#E9FBE7] text-[#15803D] dark:!border-[#37D65C] dark:bg-[#0B3D12] dark:text-[#A7F3D0]",
                  )}
                  onClick={
                    item.key === "smartDistribution"
                      ? handleSmartDistributionToggle
                      : undefined
                  }
                >
                  <item.icon className="size-3" />
                  <span className="text-[16px] leading-none font-medium">
                    {item.label}
                  </span>
                </PromptInputButton>
              ))}
            {/*
             * Lumax: 以下为已隐藏的输入区入口（智能问答、资料整理、模式、推理深度）。
             * 恢复：删除包裹本段的块注释首尾定界符即可。
            <PromptInputButton className="gap-1! rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-3! dark:!border-[#073803]">
              <MessageSquareIcon className="size-3" />
              <span className="text-[16px] leading-none font-medium">
                {t.inputBox.smartQA}
              </span>
            </PromptInputButton>
            <PromptInputButton className="gap-1! rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-3! dark:!border-[#073803]">
              <FolderOpenIcon className="size-3" />
              <span className="text-[16px] leading-none font-medium">
                {t.inputBox.materialOrganizing}
              </span>
            </PromptInputButton>
            <PromptInputActionMenu>
              <ModeHoverGuide
                mode={
                  context.mode === "flash" ||
                  context.mode === "thinking" ||
                  context.mode === "pro" ||
                  context.mode === "ultra"
                    ? context.mode
                    : "flash"
                }
              >
                <PromptInputActionMenuTrigger className="gap-1! rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-3! dark:!border-[#073803]">
                  <div>
                    {context.mode === "flash" && <ZapIcon className="size-3" />}
                    {context.mode === "thinking" && (
                      <LightbulbIcon className="size-3" />
                    )}
                    {context.mode === "pro" && (
                      <GraduationCapIcon className="size-3" />
                    )}
                    {context.mode === "ultra" && (
                      <RocketIcon className="size-3 text-[#dabb5e]" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "text-[16px] leading-none font-normal",
                      context.mode === "ultra" ? "golden-text" : "",
                    )}
                  >
                    {(context.mode === "flash" && t.inputBox.flashMode) ||
                      (context.mode === "thinking" &&
                        t.inputBox.reasoningMode) ||
                      (context.mode === "pro" && t.inputBox.proMode) ||
                      (context.mode === "ultra" && t.inputBox.ultraMode)}
                  </div>
                </PromptInputActionMenuTrigger>
              </ModeHoverGuide>
              <PromptInputActionMenuContent className="w-80">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="text-muted-foreground text-xs">
                    {t.inputBox.mode}
                  </DropdownMenuLabel>
                  <PromptInputActionMenu>
                    <PromptInputActionMenuItem
                      className={cn(
                        context.mode === "flash"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("flash")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <ZapIcon
                            className={cn(
                              "mr-2 size-4",
                              context.mode === "flash" &&
                                "text-accent-foreground",
                            )}
                          />
                          {t.inputBox.flashMode}
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.flashModeDescription}
                        </div>
                      </div>
                      {context.mode === "flash" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                    {supportThinking && (
                      <PromptInputActionMenuItem
                        className={cn(
                          context.mode === "thinking"
                            ? "text-accent-foreground"
                            : "text-muted-foreground/65",
                        )}
                        onSelect={() => handleModeSelect("thinking")}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-1 font-bold">
                            <LightbulbIcon
                              className={cn(
                                "mr-2 size-4",
                                context.mode === "thinking" &&
                                  "text-accent-foreground",
                              )}
                            />
                            {t.inputBox.reasoningMode}
                          </div>
                          <div className="pl-7 text-xs">
                            {t.inputBox.reasoningModeDescription}
                          </div>
                        </div>
                        {context.mode === "thinking" ? (
                          <CheckIcon className="ml-auto size-4" />
                        ) : (
                          <div className="ml-auto size-4" />
                        )}
                      </PromptInputActionMenuItem>
                    )}
                    <PromptInputActionMenuItem
                      className={cn(
                        context.mode === "pro"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("pro")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <GraduationCapIcon
                            className={cn(
                              "mr-2 size-4",
                              context.mode === "pro" &&
                                "text-accent-foreground",
                            )}
                          />
                          {t.inputBox.proMode}
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.proModeDescription}
                        </div>
                      </div>
                      {context.mode === "pro" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      className={cn(
                        context.mode === "ultra"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("ultra")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <RocketIcon
                            className={cn(
                              "mr-2 size-4",
                              context.mode === "ultra" && "text-[#dabb5e]",
                            )}
                          />
                          <div
                            className={cn(
                              context.mode === "ultra" && "golden-text",
                            )}
                          >
                            {t.inputBox.ultraMode}
                          </div>
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.ultraModeDescription}
                        </div>
                      </div>
                      {context.mode === "ultra" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                  </PromptInputActionMenu>
                </DropdownMenuGroup>
              </PromptInputActionMenuContent>
            </PromptInputActionMenu>
            {supportReasoningEffort && context.mode !== "flash" && (
              <PromptInputActionMenu>
                <PromptInputActionMenuTrigger className="gap-1! rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-2! text-[var(--chat-text-soft)] dark:!border-[#073803]">
                  <div className="text-xs font-normal">
                    {t.inputBox.reasoningEffort}:
                    {context.reasoning_effort === "minimal" &&
                      " " + t.inputBox.reasoningEffortMinimal}
                    {context.reasoning_effort === "low" &&
                      " " + t.inputBox.reasoningEffortLow}
                    {context.reasoning_effort === "medium" &&
                      " " + t.inputBox.reasoningEffortMedium}
                    {context.reasoning_effort === "high" &&
                      " " + t.inputBox.reasoningEffortHigh}
                  </div>
                </PromptInputActionMenuTrigger>
                <PromptInputActionMenuContent className="w-70">
                  <DropdownMenuGroup>
                    <DropdownMenuLabel className="text-muted-foreground text-xs">
                      {t.inputBox.reasoningEffort}
                    </DropdownMenuLabel>
                    <PromptInputActionMenu>
                      <PromptInputActionMenuItem
                        className={cn(
                          context.reasoning_effort === "minimal"
                            ? "text-accent-foreground"
                            : "text-muted-foreground/65",
                        )}
                        onSelect={() => handleReasoningEffortSelect("minimal")}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-1 font-bold">
                            {t.inputBox.reasoningEffortMinimal}
                          </div>
                          <div className="pl-2 text-xs">
                            {t.inputBox.reasoningEffortMinimalDescription}
                          </div>
                        </div>
                        {context.reasoning_effort === "minimal" ? (
                          <CheckIcon className="ml-auto size-4" />
                        ) : (
                          <div className="ml-auto size-4" />
                        )}
                      </PromptInputActionMenuItem>
                      <PromptInputActionMenuItem
                        className={cn(
                          context.reasoning_effort === "low"
                            ? "text-accent-foreground"
                            : "text-muted-foreground/65",
                        )}
                        onSelect={() => handleReasoningEffortSelect("low")}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-1 font-bold">
                            {t.inputBox.reasoningEffortLow}
                          </div>
                          <div className="pl-2 text-xs">
                            {t.inputBox.reasoningEffortLowDescription}
                          </div>
                        </div>
                        {context.reasoning_effort === "low" ? (
                          <CheckIcon className="ml-auto size-4" />
                        ) : (
                          <div className="ml-auto size-4" />
                        )}
                      </PromptInputActionMenuItem>
                      <PromptInputActionMenuItem
                        className={cn(
                          context.reasoning_effort === "medium" ||
                            !context.reasoning_effort
                            ? "text-accent-foreground"
                            : "text-muted-foreground/65",
                        )}
                        onSelect={() => handleReasoningEffortSelect("medium")}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-1 font-bold">
                            {t.inputBox.reasoningEffortMedium}
                          </div>
                          <div className="pl-2 text-xs">
                            {t.inputBox.reasoningEffortMediumDescription}
                          </div>
                        </div>
                        {context.reasoning_effort === "medium" ||
                        !context.reasoning_effort ? (
                          <CheckIcon className="ml-auto size-4" />
                        ) : (
                          <div className="ml-auto size-4" />
                        )}
                      </PromptInputActionMenuItem>
                      <PromptInputActionMenuItem
                        className={cn(
                          context.reasoning_effort === "high"
                            ? "text-accent-foreground"
                            : "text-muted-foreground/65",
                        )}
                        onSelect={() => handleReasoningEffortSelect("high")}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-1 font-bold">
                            {t.inputBox.reasoningEffortHigh}
                          </div>
                          <div className="pl-2 text-xs">
                            {t.inputBox.reasoningEffortHighDescription}
                          </div>
                        </div>
                        {context.reasoning_effort === "high" ? (
                          <CheckIcon className="ml-auto size-4" />
                        ) : (
                          <div className="ml-auto size-4" />
                        )}
                      </PromptInputActionMenuItem>
                    </PromptInputActionMenu>
                  </DropdownMenuGroup>
                </PromptInputActionMenuContent>
              </PromptInputActionMenu>
            )}
            */}
          </PromptInputTools>
          <PromptInputTools className="shrink-0 gap-1">
            {/*
             * Lumax: 以下为已隐藏的模型选择器入口。
            <ModelSelector
              open={modelDialogOpen}
              onOpenChange={setModelDialogOpen}
            >
              <ModelSelectorTrigger asChild>
                <PromptInputButton className="rounded-full border !border-[#E9F0E9] bg-[var(--chat-input-surface)] px-3 dark:!border-[#073803]">
                  <div className="flex min-w-0 flex-col items-start text-left">
                    <ModelSelectorName className="text-[16px] leading-none font-normal">
                      {selectedModel?.display_name}
                    </ModelSelectorName>
                  </div>
                </PromptInputButton>
              </ModelSelectorTrigger>
              <ModelSelectorContent>
                <ModelSelectorInput placeholder={t.inputBox.searchModels} />
                <ModelSelectorList>
                  {models.map((m) => (
                    <ModelSelectorItem
                      key={m.name}
                      value={m.name}
                      onSelect={() => handleModelSelect(m.name)}
                    >
                      <div className="flex min-w-0 flex-1 flex-col">
                        <ModelSelectorName>{m.display_name}</ModelSelectorName>
                        <span className="text-muted-foreground truncate text-[10px]">
                          {m.model}
                        </span>
                      </div>
                      {m.name === context.model_name ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </ModelSelectorItem>
                  ))}
                </ModelSelectorList>
              </ModelSelectorContent>
            </ModelSelector>
            */}
            {/* shadow-[0_8px_24px_oklch(0_0_0_/_0.3)] */}
            <PromptInputSubmit
              className={cn(
                "h-9 w-9 rounded-full border !border-[#E9F0E9] text-[#FAFAFA] hover:!text-[#FAFAFA] dark:!border-[#073803] dark:text-[#FAFAFA] dark:hover:!text-[#FAFAFA]",
                hasInputContent
                  ? "bg-[#157575] hover:!bg-[#157575] dark:bg-[#157575] dark:hover:!bg-[#157575]"
                  : "bg-[#CDCECD] hover:!bg-[#CDCECD] dark:bg-[#88AF8F] dark:hover:!bg-[#88AF8F]",
              )}
              disabled={disabled}
              variant="outline"
              status={status}
            />
          </PromptInputTools>
        </PromptInputFooter>
        {!isNewThread && (
          <div className="absolute right-0 -bottom-[17px] left-0 z-0 h-4 bg-[var(--chat-shell-bg)]" />
        )}
      </PromptInput>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.inputBox.followupConfirmTitle}</DialogTitle>
            <DialogDescription>
              {t.inputBox.followupConfirmDescription}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              {t.common.cancel}
            </Button>
            <Button variant="secondary" onClick={confirmAppendAndSend}>
              {t.inputBox.followupConfirmAppend}
            </Button>
            <Button onClick={confirmReplaceAndSend}>
              {t.inputBox.followupConfirmReplace}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SuggestionList() {
  const { t } = useI18n();
  const { textInput } = usePromptInputController();
  const handleSuggestionClick = useCallback(
    (prompt: string | undefined) => {
      if (!prompt) return;
      textInput.setInput(prompt);
      setTimeout(() => {
        const textarea = document.querySelector<HTMLTextAreaElement>(
          "textarea[name='message']",
        );
        if (textarea) {
          const selStart = prompt.indexOf("[");
          const selEnd = prompt.indexOf("]");
          if (selStart !== -1 && selEnd !== -1) {
            textarea.setSelectionRange(selStart, selEnd + 1);
            textarea.focus();
          }
        }
      }, 500);
    },
    [textInput],
  );
  return (
    <Suggestions className="min-h-12 w-full items-start justify-start gap-[10px] overflow-x-auto px-1 sm:w-fit">
      {/* legacy-mismatch(welcome): screenshot quick-prompt area uses three direct chips instead of surprise/create */}
      {/* <ConfettiButton
        className="cursor-pointer rounded-full border-[var(--chat-input-border)] px-4 text-xs font-normal text-[var(--chat-text-soft)] hover:bg-[var(--chat-sidebar-item-hover)] hover:text-[var(--chat-text-title)]"
        variant="outline"
        size="sm"
        onClick={() => handleSuggestionClick(t.inputBox.surpriseMePrompt)}
      >
        <SparklesIcon className="size-4" /> {t.inputBox.surpriseMe}
      </ConfettiButton> */}
      {t.inputBox.suggestions.slice(0, 3).map((suggestion, index) => (
        <Suggestion
          key={`${suggestion.suggestion}-${index}`}
          // icon={suggestion.icon}
          suggestion={suggestion.suggestion}
          onClick={() => handleSuggestionClick(suggestion.prompt)}
          className="h-[36px] rounded-full border border-[#E9F0E9] bg-[var(--chat-input-surface)] px-[13px] py-[7px] text-[14px] text-[#666666] hover:!border-[#E9F0E9] hover:!bg-[var(--chat-input-surface)] hover:!text-[#666666] dark:border-[#073803] dark:text-[#FAFAFA] dark:hover:!border-[#073803] dark:hover:!bg-[var(--chat-input-surface)] dark:hover:!text-[#FAFAFA]"
        />
      ))}
      {/* legacy-mismatch(welcome): screenshot doesn't display create dropdown in quick-prompt row */}
      {/* <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Suggestion icon={PlusIcon} suggestion={t.common.create} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuGroup>
            {t.inputBox.suggestionsCreate.map((suggestion, index) =>
              "type" in suggestion && suggestion.type === "separator" ? (
                <DropdownMenuSeparator key={index} />
              ) : (
                !("type" in suggestion) && (
                  <DropdownMenuItem
                    key={suggestion.suggestion}
                    onClick={() => handleSuggestionClick(suggestion.prompt)}
                  >
                    {suggestion.icon && <suggestion.icon className="size-4" />}
                    {suggestion.suggestion}
                  </DropdownMenuItem>
                )
              ),
            )}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu> */}
    </Suggestions>
  );
}

function AddAttachmentsButton({ className }: { className?: string }) {
  const { t } = useI18n();
  const attachments = usePromptInputAttachments();
  return (
    <Tooltip content={t.inputBox.addAttachments}>
      <PromptInputButton
        className={cn("px-2!", className)}
        onClick={() => attachments.openFileDialog()}
      >
        <PaperclipIcon className="size-3" />
      </PromptInputButton>
    </Tooltip>
  );
}
