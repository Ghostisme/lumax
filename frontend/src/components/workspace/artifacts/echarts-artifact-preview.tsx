"use client";

import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

type EChartsOption = Parameters<echarts.ECharts["setOption"]>[0];

export interface EChartsArtifactSpec {
  option?: EChartsOption;
  width?: number;
  height?: number;
}

export function parseEChartsArtifact(content: string):
  | { spec: EChartsArtifactSpec; error?: never }
  | { spec?: never; error: string } {
  try {
    const parsed = JSON.parse(content) as EChartsArtifactSpec | EChartsOption;
    if (parsed && typeof parsed === "object" && "option" in parsed) {
      const spec = parsed as EChartsArtifactSpec;
      if (!spec.option || typeof spec.option !== "object") {
        return { error: "Missing valid `option` object." };
      }
      return { spec };
    }
    if (!parsed || typeof parsed !== "object") {
      return { error: "Root value must be an ECharts option object." };
    }
    return { spec: { option: parsed as EChartsOption } };
  } catch {
    return {
      error:
        "File must be strict JSON. Do not use JavaScript functions, single quotes, comments, or trailing commas.",
    };
  }
}

export function isEChartsArtifact(filepath: string) {
  return filepath.toLowerCase().endsWith(".echarts.json");
}

export function EChartsArtifactPreview({
  className,
  content,
  pending = false,
}: {
  className?: string;
  content?: string;
  pending?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const parsed = useMemo(
    () => (content ? parseEChartsArtifact(content) : null),
    [content],
  );
  const spec = parsed?.spec;
  const height = spec?.height ?? 320;
  const isPending = pending && !spec?.option;

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !spec?.option) return;

    const option = spec.option;
    setRenderError(null);
    const chart = echarts.init(container, null, { renderer: "canvas" });
    chart.showLoading("default", {
      text: "图表正在绘制，请稍后...",
      color: "#157575",
      textColor: "#64748b",
      maskColor: "rgba(255, 255, 255, 0.85)",
    });

    const frameId = requestAnimationFrame(() => {
      try {
        chart.setOption(option, true);
        chart.hideLoading();
      } catch (error) {
        chart.hideLoading();
        setRenderError(
          error instanceof Error ? error.message : "Failed to render chart.",
        );
      }
    });

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [spec]);

  if (!content || isPending) {
    return (
      <div
        className={cn(
          "bg-background/95 flex h-80 w-full items-center justify-center rounded-lg border",
          className,
        )}
      >
        <div className="text-muted-foreground flex items-center gap-3 text-sm">
          <span className="border-primary size-4 animate-spin rounded-full border-2 border-t-transparent" />
          <span>图表正在绘制，请稍后...</span>
        </div>
      </div>
    );
  }

  if (!spec?.option) {
    return (
      <div className={cn("text-muted-foreground rounded-lg border p-4 text-sm", className)}>
        Invalid ECharts artifact: {parsed?.error ?? "missing option."}
      </div>
    );
  }

  if (renderError) {
    return (
      <div className={cn("text-muted-foreground rounded-lg border p-4 text-sm", className)}>
        Invalid ECharts artifact: {renderError}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn("w-full rounded-lg bg-white", className)}
      style={{ height }}
    />
  );
}
