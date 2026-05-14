import { ChevronUpIcon, ListTodoIcon } from "lucide-react";
import { useState } from "react";

import type { Todo } from "@/core/todos";
import { cn } from "@/lib/utils";

import {
  QueueItem,
  QueueItemContent,
  QueueItemIndicator,
  QueueList,
} from "../ai-elements/queue";

export function TodoList({
  className,
  todos,
  collapsed: controlledCollapsed,
  hidden = false,
  onToggle,
}: {
  className?: string;
  todos: Todo[];
  collapsed?: boolean;
  hidden?: boolean;
  onToggle?: () => void;
}) {
  const [internalCollapsed, setInternalCollapsed] = useState(true);
  const isControlled = controlledCollapsed !== undefined;
  const collapsed = isControlled ? controlledCollapsed : internalCollapsed;

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  };

  return (
    <div
      className={cn(
        "mb-3 flex h-fit w-full origin-bottom translate-y-4 flex-col overflow-hidden rounded-t-xl border border-[#157575] bg-[var(--chat-input-surface)] text-[#181D27] backdrop-blur-sm transition-all duration-200 ease-out dark:text-[#FAFAFA]",
        hidden ? "pointer-events-none translate-y-8 opacity-0" : "",
        className,
      )}
    >
      <header
        className={cn(
          "flex min-h-8 shrink-0 cursor-pointer items-center justify-between bg-[var(--chat-input-surface)] px-4 text-sm transition-all duration-300 ease-out",
        )}
        onClick={handleToggle}
      >
        <div className="text-[#181D27] dark:text-[#FAFAFA]">
          <div className="flex items-center justify-center gap-2">
            <ListTodoIcon className="size-4" />
            <div>To-dos</div>
          </div>
        </div>
        <div>
          <ChevronUpIcon
            className={cn(
              "size-4 text-[#181D27] transition-transform duration-300 ease-out dark:text-[#FAFAFA]",
              collapsed ? "" : "rotate-180",
            )}
          />
        </div>
      </header>
      <main
        className={cn(
          "flex grow bg-[var(--chat-input-surface)] px-2 transition-all duration-300 ease-out",
          collapsed ? "h-0 pb-3" : "h-28 pb-4",
        )}
      >
        <QueueList className="mt-0 w-full rounded-t-xl bg-[var(--chat-input-surface)] text-[#181D27] dark:text-[#FAFAFA]">
          {todos.map((todo, i) => (
            <QueueItem key={i + (todo.content ?? "")}>
              <div className="flex items-center gap-2">
                <QueueItemIndicator
                  className={
                    todo.status === "in_progress" ? "bg-primary/70" : ""
                  }
                  completed={todo.status === "completed"}
                />
                <QueueItemContent
                  className={
                    todo.status === "in_progress" ? "text-primary/70" : ""
                  }
                  completed={todo.status === "completed"}
                >
                  {todo.content}
                </QueueItemContent>
              </div>
            </QueueItem>
          ))}
        </QueueList>
      </main>
    </div>
  );
}
