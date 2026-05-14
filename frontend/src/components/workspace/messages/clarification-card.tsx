import { CheckIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  formatStructuredClarificationAnswer,
  parseStructuredClarificationSubmittedValue,
  type StructuredClarification,
} from "@/core/messages/clarification";
import { cn } from "@/lib/utils";

export type ClarificationSubmitHandler = (
  answer: string,
) => void | Promise<void>;

export function ClarificationCard({
  clarification,
  onSubmit,
  submittedAnswer,
  variant = "standalone",
}: {
  clarification: StructuredClarification;
  onSubmit?: ClarificationSubmitHandler;
  submittedAnswer?: string;
  variant?: "standalone" | "embedded";
}) {
  const submittedValue = parseStructuredClarificationSubmittedValue(
    clarification,
    submittedAnswer,
  );
  const [selectedValue, setSelectedValue] = useState(() =>
    clarification.inputControl.type === "choice_cards"
      ? (submittedValue ?? clarification.inputControl.options[0]?.value ?? "")
      : "",
  );
  const [textValue, setTextValue] = useState(() =>
    clarification.inputControl.type === "text_input"
      ? (submittedValue ?? "")
      : "",
  );
  const [localSubmittedAnswer, setLocalSubmittedAnswer] = useState<string | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const displayedSubmittedAnswer = submittedAnswer ?? localSubmittedAnswer;
  const isReadonly = !onSubmit || displayedSubmittedAnswer !== null;
  const isTextInput = clarification.inputControl.type === "text_input";
  const currentValue = isTextInput ? textValue.trim() : selectedValue;
  const canSubmit = Boolean(onSubmit && currentValue && !isSubmitting);

  useEffect(() => {
    if (!submittedValue) {
      return;
    }
    if (clarification.inputControl.type === "choice_cards") {
      setSelectedValue(submittedValue);
      return;
    }
    setTextValue(submittedValue);
  }, [clarification.inputControl.type, submittedValue]);

  const handleConfirm = async () => {
    if (!onSubmit || !currentValue || isSubmitting) {
      return;
    }

    const answer = formatStructuredClarificationAnswer(
      clarification,
      currentValue,
    );
    setIsSubmitting(true);
    setLocalSubmittedAnswer(answer);
    try {
      await onSubmit(answer);
    } catch (error) {
      setLocalSubmittedAnswer(null);
      console.error("Failed to submit clarification:", error);
      toast.error("提交失败，请重试");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section
      className={cn(
        "relative w-full rounded-[20px] border border-[var(--chat-assistant-bubble-border)] bg-[var(--chat-assistant-bubble)] px-[17px] py-[16px] text-[var(--chat-assistant-bubble-text)]",
        variant === "standalone"
          ? "shadow-[0_13px_34px_oklch(0_0_0_/_0.29)]"
          : "bg-background/30 shadow-none",
      )}
    >
      <div className="flex flex-col gap-4">
        <div>
          <div className="text-muted-foreground mb-1 text-xs font-medium">
            需要补充信息
          </div>
          <div className="text-[16px] leading-6">{clarification.question}</div>
        </div>

        {clarification.inputControl.type === "choice_cards" ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {clarification.inputControl.options.map((option) => {
              const selected = selectedValue === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  disabled={isReadonly || isSubmitting}
                  className={cn(
                    "cursor-pointer rounded-2xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-70",
                    selected
                      ? "border-[#157575] bg-[oklch(0.67_0.13_145_/_0.14)]"
                      : "border-border/60 bg-background/40 hover:border-[#157575]/70",
                  )}
                  onClick={() => setSelectedValue(option.value)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{option.label}</div>
                      <div className="text-muted-foreground mt-1 text-xs">
                        {option.value}
                      </div>
                    </div>
                    {selected && (
                      <CheckIcon className="size-4 text-[#157575]" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <Input
            value={textValue}
            disabled={isReadonly || isSubmitting}
            placeholder={clarification.inputControl.placeholder}
            onChange={(event) => setTextValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleConfirm();
              }
            }}
          />
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-muted-foreground text-xs">
            {displayedSubmittedAnswer
              ? `已提交：${displayedSubmittedAnswer}`
              : "确认后将继续下一步"}
          </div>
          <Button
            type="button"
            size="sm"
            disabled={!canSubmit || displayedSubmittedAnswer !== null}
            onClick={() => void handleConfirm()}
          >
            {isSubmitting
              ? "提交中..."
              : displayedSubmittedAnswer
                ? "已确认"
                : "确认"}
          </Button>
        </div>
      </div>
    </section>
  );
}
