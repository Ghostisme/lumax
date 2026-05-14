import { cn } from "@/lib/utils";

export function StreamingIndicator({
  className,
  size = "normal",
}: {
  className?: string;
  size?: "normal" | "sm";
}) {
  const dotClass = size === "sm" ? "text-xl" : "text-4xl";

  return (
    <div
      aria-label="Loading"
      className={cn(
        "text-muted-foreground inline-flex items-center leading-none font-bold",
        className,
      )}
    >
      <span
        className={cn(dotClass, "animate-bouncing inline-block opacity-100")}
      >
        .
      </span>
      <span
        className={cn(
          dotClass,
          "animate-bouncing inline-block opacity-100 [animation-delay:0.2s]",
        )}
      >
        .
      </span>
      <span
        className={cn(
          dotClass,
          "animate-bouncing inline-block opacity-100 [animation-delay:0.4s]",
        )}
      >
        .
      </span>
    </div>
  );
}
