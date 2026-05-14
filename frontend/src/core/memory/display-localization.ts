import type { Locale } from "@/core/i18n/locale";

const CJK_RE = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/;

const EXACT_EN_TO_ZH: Record<string, string> = {
  "user is comfortable communicating in chinese, as indicated by the initial test message.":
    "用户更习惯使用中文沟通，这一点可从初始测试消息中看出。",
  "user is in an initial exploratory phase, testing the system's capabilities and available features.":
    "用户目前处于初步探索阶段，正在测试系统能力和可用功能。",
  "they are likely evaluating the assistant's functionality and determining how it can be useful for their needs.":
    "用户很可能正在评估助手功能，并判断其如何满足自身需求。",
  "no specific projects or tasks are currently active.":
    "当前暂无明确正在进行的项目或任务。",
  "the user has just initiated a new interaction with the system, starting with a simple test message to begin the conversation.":
    "用户刚刚开始与系统进行新一轮交互，并以一条简单测试消息开启了对话。",
};

const PHRASE_EN_TO_ZH: Array<[RegExp, string]> = [
  [/\buser\b/gi, "用户"],
  [/\bassistant\b/gi, "助手"],
  [/\bsystem\b/gi, "系统"],
  [/\bconversation\b/gi, "对话"],
  [/\binteractions?\b/gi, "交互"],
  [/\bmemory\b/gi, "记忆"],
  [/\bprojects?\b/gi, "项目"],
  [/\btasks?\b/gi, "任务"],
  [/\bfeatures?\b/gi, "功能"],
  [/\bcapabilities\b/gi, "能力"],
  [/\bcurrently\b/gi, "当前"],
  [/\binitial\b/gi, "初始"],
  [/\bphase\b/gi, "阶段"],
  [/\bevaluating\b/gi, "评估"],
  [/\bexploratory\b/gi, "探索"],
  [/\bactive\b/gi, "活跃"],
  [/\bwith\b/gi, "与"],
  [/\band\b/gi, "和"],
];

function normalizeForLookup(text: string): string {
  return text.trim().replace(/\s+/g, " ").toLowerCase();
}

function translateSingleSentence(text: string): string {
  const normalized = normalizeForLookup(text);
  const exact = EXACT_EN_TO_ZH[normalized];
  if (exact) {
    return exact;
  }

  let translated = text;
  for (const [pattern, replacement] of PHRASE_EN_TO_ZH) {
    translated = translated.replace(pattern, replacement);
  }
  return translated;
}

export function localizeMemoryTextForDisplay(text: string, locale: Locale): string {
  if (locale !== "zh-CN" || !text.trim()) {
    return text;
  }
  if (CJK_RE.test(text)) {
    return text;
  }

  const normalized = normalizeForLookup(text);
  const exact = EXACT_EN_TO_ZH[normalized];
  if (exact) {
    return exact;
  }

  const parts = text.split(/(?<=[.!?])\s+/);
  const localized = parts.map((part) => translateSingleSentence(part));
  return localized.join(" ");
}
