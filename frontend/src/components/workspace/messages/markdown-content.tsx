"use client";

import { Children, useMemo } from "react";
import type { AnchorHTMLAttributes, ComponentProps, ReactNode } from "react";

import {
  MessageResponse,
  type MessageResponseProps,
} from "@/components/ai-elements/message";
import { EChartsArtifactPreview } from "@/components/workspace/artifacts/echarts-artifact-preview";
import { streamdownPlugins } from "@/core/streamdown";
import { cn } from "@/lib/utils";

import { CitationLink } from "../citations/citation-link";

function isExternalUrl(href: string | undefined): boolean {
  return !!href && /^https?:\/\//.test(href);
}

type CodeRendererProps = ComponentProps<"code"> & {
  inline?: boolean;
};

const ECHARTS_MARKDOWN_LANGUAGES = new Set([
  "echarts",
  "echarts-json",
  "echarts.json",
]);

function getCodeBlockLanguage(className: string | undefined): string | null {
  const match = /(?:^|\s)language-([^\s]+)/.exec(className ?? "");
  return match?.[1]?.toLowerCase() ?? null;
}

function codeBlockContentToString(children: ReactNode): string {
  return Children.toArray(children)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") {
        return String(child);
      }
      return "";
    })
    .join("")
    .replace(/\n$/, "");
}

export type MarkdownContentProps = {
  content: string;
  isLoading: boolean;
  rehypePlugins: MessageResponseProps["rehypePlugins"];
  className?: string;
  remarkPlugins?: MessageResponseProps["remarkPlugins"];
  components?: MessageResponseProps["components"];
};

/** Renders markdown content. */
export function MarkdownContent({
  content,
  isLoading,
  rehypePlugins,
  className,
  remarkPlugins = streamdownPlugins.remarkPlugins,
  components: componentsFromProps,
}: MarkdownContentProps) {
  const components = useMemo(() => {
    const codeFromProps = componentsFromProps?.code as
      | ((props: CodeRendererProps) => ReactNode)
      | undefined;

    return {
      a: (props: AnchorHTMLAttributes<HTMLAnchorElement>) => {
        if (typeof props.children === "string") {
          const match = /^citation:(.+)$/.exec(props.children);
          if (match) {
            const [, text] = match;
            return <CitationLink {...props}>{text}</CitationLink>;
          }
        }
        const { className, target, rel, ...rest } = props;
        const external = isExternalUrl(props.href);
        return (
          <a
            {...rest}
            className={cn(
              "text-primary decoration-primary/30 hover:decoration-primary/60 underline underline-offset-2 transition-colors",
              className,
            )}
            target={target ?? (external ? "_blank" : undefined)}
            rel={rel ?? (external ? "noopener noreferrer" : undefined)}
          />
        );
      },
      ...componentsFromProps,
      code: (props: CodeRendererProps) => {
        const language = getCodeBlockLanguage(props.className);
        if (
          !props.inline &&
          language &&
          ECHARTS_MARKDOWN_LANGUAGES.has(language)
        ) {
          return (
            <EChartsArtifactPreview
              content={codeBlockContentToString(props.children)}
              className="my-4 min-h-80 border shadow-sm"
              pending={isLoading}
            />
          );
        }

        if (codeFromProps) {
          return codeFromProps(props);
        }

        const codeProps: ComponentProps<"code"> = { ...props };
        delete (codeProps as CodeRendererProps).inline;
        return <code {...codeProps} />;
      },
    };
  }, [componentsFromProps, isLoading]);

  if (!content) return null;

  return (
    <MessageResponse
      className={className}
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={components}
    >
      {content}
    </MessageResponse>
  );
}
