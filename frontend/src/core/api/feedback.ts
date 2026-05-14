import { AuthRequiredError, fetchWithAuth } from "../auth/request";
import { getBackendBaseURL } from "../config";

export type FeedbackRating = "positive" | "negative";

export interface FeedbackData {
  id?: string;
  feedback_id?: string;
  message_id?: string | null;
  run_id?: string | null;
  rating?: FeedbackRating | number;
  /** 服务端回显极性（UI 仅用此字段映射点赞/踩状态）。 */
  result?: FeedbackRating;
  comment?: string | null;
  tags?: string[];
  created_at?: number | string;
  updated_at?: number | string;
  [key: string]: unknown;
}

/** 列表回显：只认 `result`，不读 `rating`。 */
export function feedbackDisplayPolarity(
  entry: Pick<FeedbackData, "result">,
): FeedbackRating | null {
  const r = entry.result;
  return r === "positive" || r === "negative" ? r : null;
}

export type ThreadFeedbackEntry = FeedbackData & {
  id: string;
  thread_id: string;
};

type ThreadFeedbackListResponse = {
  feedback?: ThreadFeedbackEntry[];
  count?: number;
};

export type ThreadFeedbackRequest = {
  messageId?: string;
  runId: string;
  rating: FeedbackRating;
  comment?: string;
  tags?: string[];
};

class FeedbackRequestError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "FeedbackRequestError";
    this.status = status;
  }
}

export function isFeedbackUnauthorizedError(error: unknown): boolean {
  return error instanceof AuthRequiredError && error.status === 401;
}

export function isFeedbackStatusError(error: unknown, status: number): boolean {
  return error instanceof FeedbackRequestError && error.status === status;
}

export async function submitThreadFeedback(
  threadId: string,
  feedback: ThreadFeedbackRequest,
): Promise<FeedbackData> {
  const res = await fetchWithAuth(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/feedback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: feedback.messageId ?? "",
        run_id: feedback.runId,
        rating: feedback.rating,
        comment: feedback.comment ?? "",
        tags: feedback.tags ?? [],
      }),
    },
  );
  if (!res.ok) {
    throw new FeedbackRequestError(
      `Failed to submit feedback: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function listThreadFeedback(
  threadId: string,
): Promise<ThreadFeedbackEntry[]> {
  const res = await fetchWithAuth(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/feedback`,
  );
  if (!res.ok) {
    throw new FeedbackRequestError(
      `Failed to list feedback: ${res.status}`,
      res.status,
    );
  }
  const data = (await res.json()) as ThreadFeedbackListResponse;
  return Array.isArray(data.feedback) ? data.feedback : [];
}

export async function upsertFeedback(
  threadId: string,
  runId: string,
  rating: number,
  comment?: string,
): Promise<FeedbackData> {
  return submitThreadFeedback(threadId, {
    runId,
    rating: rating < 0 ? "negative" : "positive",
    comment,
  });
}

export async function deleteFeedback(
  threadId: string,
  runId: string,
): Promise<void> {
  const res = await fetchWithAuth(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/runs/${encodeURIComponent(runId)}/feedback`,
    { method: "DELETE" },
  );
  if (!res.ok && res.status !== 404) {
    throw new FeedbackRequestError(
      `Failed to delete feedback: ${res.status}`,
      res.status,
    );
  }
}
