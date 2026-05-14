import { describe, expect, test } from "vitest";

import {
  formatStructuredClarificationAnswer,
  messageMatchesStructuredClarifications,
  parseStructuredClarificationSubmittedValue,
  parseStructuredClarificationsFromMessage,
  parseStructuredClarificationContent,
  parseStructuredClarification,
  selectMatchingStructuredClarifications,
} from "@/core/messages/clarification";

describe("parseStructuredClarification", () => {
  test("parses wrapped choice card clarification", () => {
    const result = parseStructuredClarification(
      JSON.stringify({
        data: {
          user_visible_text: "营销目的是什么值？",
          clarification: {
            version: "v1",
            reason: "missing_required_parameter",
            field: "marketing_goal",
            field_label: "营销目的",
            question: "营销目的是什么值？",
            input_control: {
              type: "choice_cards",
              selection_mode: "single",
              options: [{ value: "LIVE", label: "直播" }],
            },
          },
        },
      }),
    );

    expect(result).toMatchObject({
      question: "营销目的是什么值？",
      field: "marketing_goal",
      fieldLabel: "营销目的",
      inputControl: {
        type: "choice_cards",
        selectionMode: "single",
        options: [{ value: "LIVE", label: "直播" }],
      },
    });
    expect(result && formatStructuredClarificationAnswer(result, "LIVE")).toBe(
      "营销目的：LIVE（直播）",
    );
  });

  test("parses direct text input clarification with leading text", () => {
    const result = parseStructuredClarification(`@赵珊珊 填写类型
{
  "input_control": {
    "type": "text_input",
    "value_type": "string",
    "placeholder": "请填写项目名称"
  }
}`);

    expect(result).toMatchObject({
      question: "@赵珊珊 填写类型",
      inputControl: {
        type: "text_input",
        valueType: "string",
        placeholder: "请填写项目名称",
      },
    });
    expect(
      result && formatStructuredClarificationAnswer(result, "春季项目"),
    ).toBe("@赵珊珊 填写类型：春季项目");
  });

  test("parses direct text input control without a leading question", () => {
    const result = parseStructuredClarification(
      JSON.stringify({
        input_control: {
          type: "text_input",
          value_type: "string",
          placeholder: "请填写项目名称",
        },
      }),
    );

    expect(result).toMatchObject({
      question: "请填写项目名称",
      inputControl: {
        type: "text_input",
        valueType: "string",
        placeholder: "请填写项目名称",
      },
    });
  });

  test("returns null for invalid JSON", () => {
    expect(
      parseStructuredClarification(
        '{ "input_control": { "type": "text_input" ',
      ),
    ).toBeNull();
  });

  test("returns null for unsupported control type", () => {
    expect(
      parseStructuredClarification(
        JSON.stringify({
          question: "请选择日期",
          input_control: { type: "date_picker" },
        }),
      ),
    ).toBeNull();
  });
});

describe("parseStructuredClarificationContent", () => {
  test("splits markdown and choice card clarification segments", () => {
    const segments = parseStructuredClarificationContent(`请先补充信息：
{
  "data": {
    "user_visible_text": "营销目的是什么值？",
    "clarification": {
      "field": "marketing_goal",
      "field_label": "营销目的",
      "question": "营销目的是什么值？",
      "input_control": {
        "type": "choice_cards",
        "selection_mode": "single",
        "options": [{ "value": "LIVE", "label": "直播" }]
      }
    }
  }
}
确认后继续。`);

    expect(segments).toHaveLength(3);
    expect(segments[0]).toMatchObject({
      type: "markdown",
      content: "请先补充信息：\n",
    });
    expect(segments[1]).toMatchObject({
      type: "clarification",
      clarification: {
        question: "营销目的是什么值？",
        field: "marketing_goal",
        fieldLabel: "营销目的",
      },
    });
    expect(segments[2]).toMatchObject({
      type: "markdown",
      content: "\n确认后继续。",
    });
  });

  test("keeps invalid JSON as markdown fallback", () => {
    expect(
      parseStructuredClarificationContent(
        '前置文本 { "input_control": { "type": "date_picker" } } 后置文本',
      ),
    ).toEqual([
      {
        type: "markdown",
        content:
          '前置文本 { "input_control": { "type": "date_picker" } } 后置文本',
      },
    ]);
  });
});

describe("parseStructuredClarificationsFromMessage", () => {
  test("preserves top-level user_visible_text for fallback matching", () => {
    const result = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "marketing_goal",
          field_label: "营销场景",
          question: "营销场景是什么值？",
          user_visible_text: "营销场景是什么值？可选：直播、短视频/图文。",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "LIVE", label: "直播" },
              { value: "VIDEO_IMAGE", label: "短视频/图文" },
            ],
          },
        },
      ],
    });

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      question: "营销场景是什么值？",
      userVisibleText: "营销场景是什么值？可选：直播、短视频/图文。",
      inputControl: {
        type: "choice_cards",
      },
    });
  });

  test("parses top-level structured_clarifications array", () => {
    const result = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          version: "v1",
          reason: "missing_required_parameter",
          field: "name",
          field_label: "项目名称",
          question: "项目名称是什么值？",
          input_control: {
            type: "text_input",
            value_type: "string",
            placeholder: "请填写项目名称",
          },
        },
        {
          version: "v1",
          reason: "missing_required_parameter",
          field: "marketing_goal",
          field_label: "营销场景",
          question: "营销场景是什么值？",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "LIVE", label: "直播" },
              { value: "VIDEO_IMAGE", label: "短视频/图文" },
            ],
          },
        },
      ],
    });

    expect(result).toHaveLength(2);
    expect(result[0]).toMatchObject({
      field: "name",
      fieldLabel: "项目名称",
      inputControl: {
        type: "text_input",
        valueType: "string",
        placeholder: "请填写项目名称",
      },
    });
    expect(result[1]).toMatchObject({
      field: "marketing_goal",
      fieldLabel: "营销场景",
      inputControl: {
        type: "choice_cards",
        selectionMode: "single",
        options: [
          { value: "LIVE", label: "直播" },
          { value: "VIDEO_IMAGE", label: "短视频/图文" },
        ],
      },
    });
  });

  test("parses from additional_kwargs and filters invalid entries", () => {
    const result = parseStructuredClarificationsFromMessage({
      additional_kwargs: {
        structured_clarifications: [
          {
            field: "name",
            field_label: "项目名称",
            question: "项目名称是什么值？",
            input_control: {
              type: "text_input",
              placeholder: "请填写项目名称",
            },
          },
          {
            field: "unsupported",
            input_control: {
              type: "date_picker",
            },
          },
          "invalid-item",
        ],
      },
    });

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      field: "name",
      fieldLabel: "项目名称",
      inputControl: {
        type: "text_input",
        placeholder: "请填写项目名称",
      },
    });
  });

  test("returns empty array when no structured clarifications found", () => {
    expect(parseStructuredClarificationsFromMessage({})).toEqual([]);
    expect(parseStructuredClarificationsFromMessage("invalid")).toEqual([]);
  });
});

describe("messageMatchesStructuredClarifications", () => {
  test("matches expanded assistant copy against choice card clarification", () => {
    const clarifications = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "marketing_goal",
          field_label: "营销场景",
          question: "营销场景是什么值？可选：直播、短视频/图文。",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "LIVE", label: "直播" },
              { value: "VIDEO_IMAGE", label: "短视频/图文" },
            ],
          },
        },
      ],
    });

    expect(
      messageMatchesStructuredClarifications(
        "创建本地推项目需要指定营销场景，这是必填参数。请告诉我这个项目的营销场景是什么？您可以选择：直播、短视频/图文。1. 直播 2. 短视频/图文",
        clarifications,
      ),
    ).toBe(true);
  });

  test("selects only the clarification matching the current prompt", () => {
    const clarifications = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "marketing_goal",
          field_label: "营销场景",
          question: "营销场景是什么值？可选：直播、短视频/图文。",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "LIVE", label: "直播" },
              { value: "VIDEO_IMAGE", label: "短视频/图文" },
            ],
          },
        },
        {
          field: "local_delivery_scene",
          field_label: "营销目的",
          question:
            "营销目的是什么值？可选：线上互动、线下到店、团购成交、获取线索。",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "CONTENT_HEAT", label: "线上互动" },
              { value: "POI_RECOMMEND", label: "线下到店" },
              { value: "PRODUCT_PAY", label: "团购成交" },
              { value: "EXTERNAL", label: "获取线索" },
            ],
          },
        },
      ],
    });

    expect(
      selectMatchingStructuredClarifications(
        "营销目的是什么值？可选：线上互动、线下到店、团购成交、获取线索。",
        clarifications,
      ),
    ).toMatchObject([
      {
        field: "local_delivery_scene",
      },
    ]);
  });

  test("does not match unrelated assistant copy", () => {
    const clarifications = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "marketing_goal",
          field_label: "营销场景",
          question: "营销场景是什么值？",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "LIVE", label: "直播" },
              { value: "VIDEO_IMAGE", label: "短视频/图文" },
            ],
          },
        },
      ],
    });

    expect(
      messageMatchesStructuredClarifications("项目创建完成。", clarifications),
    ).toBe(false);
  });
});

describe("parseStructuredClarificationSubmittedValue", () => {
  test("extracts submitted text input value", () => {
    const clarification = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "name",
          field_label: "项目名称",
          question: "项目名称是什么值？",
          input_control: {
            type: "text_input",
            value_type: "string",
            placeholder: "请填写项目名称",
          },
        },
      ],
    })[0];

    expect(
      clarification &&
        parseStructuredClarificationSubmittedValue(
          clarification,
          "项目名称：别克1991",
        ),
    ).toBe("别克1991");
  });

  test("extracts submitted choice card value", () => {
    const clarification = parseStructuredClarificationsFromMessage({
      structured_clarifications: [
        {
          field: "local_delivery_scene",
          field_label: "营销目的",
          question:
            "营销目的是什么值？可选：线上互动、线下到店、团购成交、获取线索。",
          input_control: {
            type: "choice_cards",
            selection_mode: "single",
            options: [
              { value: "CONTENT_HEAT", label: "线上互动" },
              { value: "POI_RECOMMEND", label: "线下到店" },
              { value: "PRODUCT_PAY", label: "团购成交" },
              { value: "EXTERNAL", label: "获取线索" },
            ],
          },
        },
      ],
    })[0];

    expect(
      clarification &&
        parseStructuredClarificationSubmittedValue(
          clarification,
          "营销目的：PRODUCT_PAY（团购成交）",
        ),
    ).toBe("PRODUCT_PAY");
  });
});
