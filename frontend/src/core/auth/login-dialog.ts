"use client";

import { useSyncExternalStore } from "react";

export type LoginDialogReason = "unauthorized" | "rate_limited" | "required";

export type LoginDialogRequest = {
  id: number;
  reason: LoginDialogReason;
};

type Listener = () => void;

let currentRequest: LoginDialogRequest = {
  id: 0,
  reason: "required",
};
let authChallengeActive = false;
const listeners = new Set<Listener>();

function emitChange() {
  listeners.forEach((listener) => listener());
}

export function requestLoginDialog(reason: LoginDialogReason = "required") {
  if (reason !== "required") {
    if (authChallengeActive) {
      return;
    }
    authChallengeActive = true;
  }

  currentRequest = {
    id: currentRequest.id + 1,
    reason,
  };
  emitChange();
}

export function resolveLoginDialogRequest() {
  authChallengeActive = false;
}

export function getLoginDialogRequestSnapshot(): LoginDialogRequest {
  return currentRequest;
}

export function subscribeLoginDialogRequest(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useLoginDialogRequest(): LoginDialogRequest {
  return useSyncExternalStore(
    subscribeLoginDialogRequest,
    getLoginDialogRequestSnapshot,
    getLoginDialogRequestSnapshot,
  );
}
