export type ClarificationChoiceOption = {
  value: string;
  label: string;
};

export type ClarificationInputControl =
  | {
      type: "choice_cards";
      selectionMode: "single";
      options: ClarificationChoiceOption[];
    }
  | {
      type: "text_input";
      valueType?: string;
      placeholder?: string;
    };

export type StructuredClarification = {
  question: string;
  userVisibleText?: string;
  field?: string;
  fieldLabel?: string;
  inputControl: ClarificationInputControl;
};

export type StructuredClarificationContentSegment =
  | {
      type: "markdown";
      content: string;
    }
  | {
      type: "clarification";
      clarification: StructuredClarification;
      rawContent: string;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

type ExtractedJsonObject = {
  jsonText: string;
  prefix: string;
  start: number;
  end: number;
};

function extractJsonObjects(content: string): ExtractedJsonObject[] {
  const objects: ExtractedJsonObject[] = [];
  let searchStart = 0;

  for (
    let start = content.indexOf("{", searchStart);
    start >= 0;
    start = content.indexOf("{", searchStart)
  ) {
    let depth = 0;
    let inString = false;
    let escaped = false;

    for (let index = start; index < content.length; index += 1) {
      const char = content[index];
      if (escaped) {
        escaped = false;
        continue;
      }
      if (char === "\\") {
        escaped = true;
        continue;
      }
      if (char === '"') {
        inString = !inString;
        continue;
      }
      if (inString) {
        continue;
      }
      if (char === "{") {
        depth += 1;
      } else if (char === "}") {
        depth -= 1;
        if (depth === 0) {
          objects.push({
            jsonText: content.slice(start, index + 1),
            prefix: content.slice(0, start).trim(),
            start,
            end: index + 1,
          });
          searchStart = index + 1;
          break;
        }
      }
    }

    if (searchStart <= start) {
      searchStart = start + 1;
    }
  }
  return objects;
}

function extractFirstJsonObject(content: string) {
  return extractJsonObjects(content)[0] ?? null;
}

function parseInputControl(value: unknown): ClarificationInputControl | null {
  if (!isRecord(value)) {
    return null;
  }

  if (value.type === "choice_cards") {
    const selectionMode =
      value.selection_mode === undefined ? "single" : value.selection_mode;
    if (selectionMode !== "single" || !Array.isArray(value.options)) {
      return null;
    }

    const options = value.options
      .map((option): ClarificationChoiceOption | null => {
        if (!isRecord(option)) {
          return null;
        }
        const optionValue = stringValue(option.value);
        const label = stringValue(option.label);
        if (!optionValue || !label) {
          return null;
        }
        return { value: optionValue, label };
      })
      .filter((option): option is ClarificationChoiceOption => option !== null);

    if (options.length === 0 || options.length !== value.options.length) {
      return null;
    }

    return {
      type: "choice_cards",
      selectionMode: "single",
      options,
    };
  }

  if (value.type === "text_input") {
    return {
      type: "text_input",
      valueType: stringValue(value.value_type),
      placeholder: stringValue(value.placeholder),
    };
  }

  return null;
}

function parseStructuredClarificationObject(
  parsed: Record<string, unknown>,
  prefix?: string,
): StructuredClarification | null {
  const data = isRecord(parsed.data) ? parsed.data : undefined;
  const clarification = isRecord(data?.clarification)
    ? data.clarification
    : isRecord(parsed.clarification)
      ? parsed.clarification
      : parsed;
  const inputControl =
    parseInputControl(clarification.input_control) ??
    parseInputControl(clarification);
  if (!inputControl) {
    return null;
  }

  const userVisibleText =
    stringValue(data?.user_visible_text) ??
    stringValue(clarification.user_visible_text) ??
    stringValue(parsed.user_visible_text);
  const fieldLabel = stringValue(clarification.field_label);
  const question =
    stringValue(clarification.question) ??
    userVisibleText ??
    stringValue(parsed.question) ??
    stringValue(parsed.user_visible_text) ??
    fieldLabel ??
    stringValue(prefix) ??
    (inputControl.type === "text_input" ? inputControl.placeholder : undefined);
  if (!question) {
    return null;
  }

  return {
    question,
    userVisibleText,
    field: stringValue(clarification.field),
    fieldLabel,
    inputControl,
  };
}

export function parseStructuredClarification(
  content: string,
): StructuredClarification | null {
  const extracted = extractFirstJsonObject(content);
  return extracted ? parseStructuredClarificationJson(extracted) : null;
}

function parseStructuredClarificationJson(
  extracted: Pick<ExtractedJsonObject, "jsonText" | "prefix">,
): StructuredClarification | null {
  if (!extracted) {
    return null;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(extracted.jsonText);
  } catch {
    return null;
  }
  if (!isRecord(parsed)) {
    return null;
  }
  return parseStructuredClarificationObject(parsed, extracted.prefix);
}

function parseStructuredClarificationItems(
  items: unknown[],
): StructuredClarification[] {
  return items
    .map((item) =>
      isRecord(item) ? parseStructuredClarificationObject(item) : null,
    )
    .filter((item): item is StructuredClarification => item !== null);
}

export function parseStructuredClarificationsFromMessage(
  messageLike: unknown,
): StructuredClarification[] {
  const clarifications: StructuredClarification[] = [];
  const visited = new Set<unknown>();

  const pushClarifications = (value: unknown) => {
    if (Array.isArray(value)) {
      clarifications.push(...parseStructuredClarificationItems(value));
    }
  };

  const scan = (value: unknown) => {
    if (!value || typeof value !== "object" || visited.has(value)) {
      return;
    }
    visited.add(value);

    if (Array.isArray(value)) {
      for (const item of value) {
        scan(item);
      }
      return;
    }

    if (!isRecord(value)) {
      return;
    }

    pushClarifications(value.structured_clarifications);
    if (isRecord(value.additional_kwargs)) {
      pushClarifications(value.additional_kwargs.structured_clarifications);
    }

    // Some payloads wrap clarifications under nested objects (e.g. `data`).
    scan(value.data);
    scan(value.payload);
    scan(value.message);
    scan(value.messages);
  };

  scan(messageLike);

  if (clarifications.length <= 1) {
    return clarifications;
  }

  const seen = new Set<string>();
  return clarifications.filter((clarification) => {
    const key = JSON.stringify(clarification);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function normalizeClarificationMatchText(value: string) {
  return value
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[：:，,。.!！?？；;、/\\*#`_\-—]/g, "");
}

export function messageMatchesStructuredClarifications(
  content: string,
  clarifications: StructuredClarification[],
) {
  return selectMatchingStructuredClarifications(content, clarifications).length > 0;
}

export function selectMatchingStructuredClarifications(
  content: string,
  clarifications: StructuredClarification[],
) {
  const normalizedContent = normalizeClarificationMatchText(content);
  if (!normalizedContent || clarifications.length === 0) {
    return [];
  }

  return clarifications.filter((clarification) => {
    const directMatches = [
      clarification.question,
      clarification.userVisibleText,
      clarification.fieldLabel,
    ]
      .map((value) =>
        value ? normalizeClarificationMatchText(value) : undefined,
      )
      .filter((value): value is string => Boolean(value));

    if (
      directMatches.some(
        (value) =>
          normalizedContent.includes(value) ||
          (value.length >= 8 && value.includes(normalizedContent)),
      )
    ) {
      return true;
    }

    if (clarification.inputControl.type !== "choice_cards") {
      return false;
    }

    const optionLabels = clarification.inputControl.options
      .map((option) => normalizeClarificationMatchText(option.label))
      .filter(Boolean);
    const fieldLabel = clarification.fieldLabel
      ? normalizeClarificationMatchText(clarification.fieldLabel)
      : "";

    return (
      optionLabels.length > 0 &&
      optionLabels.every((label) => normalizedContent.includes(label)) &&
      (!fieldLabel || normalizedContent.includes(fieldLabel))
    );
  });
}

export function parseStructuredClarificationContent(
  content: string,
): StructuredClarificationContentSegment[] {
  const extractedObjects = extractJsonObjects(content);
  if (extractedObjects.length === 0) {
    return [{ type: "markdown", content }];
  }

  const segments: StructuredClarificationContentSegment[] = [];
  let cursor = 0;

  for (const extracted of extractedObjects) {
    if (extracted.start > cursor) {
      segments.push({
        type: "markdown",
        content: content.slice(cursor, extracted.start),
      });
    }

    const clarification = parseStructuredClarificationJson({
      jsonText: extracted.jsonText,
      prefix: content.slice(0, extracted.start).trim(),
    });
    if (clarification) {
      segments.push({
        type: "clarification",
        clarification,
        rawContent: extracted.jsonText,
      });
    } else {
      segments.push({
        type: "markdown",
        content: extracted.jsonText,
      });
    }
    cursor = extracted.end;
  }

  if (cursor < content.length) {
    segments.push({ type: "markdown", content: content.slice(cursor) });
  }

  return mergeAdjacentMarkdownSegments(segments);
}

function mergeAdjacentMarkdownSegments(
  segments: StructuredClarificationContentSegment[],
) {
  const merged: StructuredClarificationContentSegment[] = [];
  for (const segment of segments) {
    const previous = merged[merged.length - 1];
    if (segment.type === "markdown" && previous?.type === "markdown") {
      previous.content += segment.content;
    } else {
      merged.push(segment);
    }
  }
  return merged;
}

export function formatStructuredClarificationAnswer(
  clarification: StructuredClarification,
  value: string,
) {
  const label = clarification.fieldLabel ?? clarification.question;
  if (clarification.inputControl.type === "choice_cards") {
    const selected = clarification.inputControl.options.find(
      (option) => option.value === value,
    );
    return selected
      ? `${label}：${selected.value}（${selected.label}）`
      : `${label}：${value}`;
  }
  return `${label}：${value.trim()}`;
}

export function parseStructuredClarificationSubmittedValue(
  clarification: StructuredClarification,
  answer: string | undefined,
) {
  const trimmedAnswer = answer?.trim();
  if (!trimmedAnswer) {
    return undefined;
  }

  const labelCandidates = [
    clarification.fieldLabel,
    clarification.question,
  ].filter((value): value is string => Boolean(value?.trim()));
  let submittedValue = trimmedAnswer;
  for (const label of labelCandidates) {
    const normalizedLabel = label.trim();
    for (const separator of ["：", ":"]) {
      const prefix = `${normalizedLabel}${separator}`;
      if (trimmedAnswer.startsWith(prefix)) {
        submittedValue = trimmedAnswer.slice(prefix.length).trim();
        break;
      }
    }
  }

  if (clarification.inputControl.type === "choice_cards") {
    const option = clarification.inputControl.options.find(
      (option) =>
        submittedValue === option.value ||
        submittedValue === option.label ||
        submittedValue.includes(option.value) ||
        submittedValue.includes(option.label),
    );
    return option?.value;
  }

  return submittedValue;
}
