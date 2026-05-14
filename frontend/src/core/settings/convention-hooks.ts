import { useCallback, useSyncExternalStore } from "react";

import {
  deleteSessionConventionInStore,
  exportSessionConventionsFromStore,
  getMergedConventionsSnapshot,
  getSessionConventionsSnapshot,
  importSessionConventionsInStore,
  recordConversationDeltaInStore,
  subscribeConventionStore,
  upsertSessionConventionInStore,
} from "./convention-store";
import type {
  ConventionConflictResolution,
  MergedConventionItem,
  SessionConventionsSnapshot,
} from "./conventions";

const EMPTY_SESSION_SNAPSHOT: SessionConventionsSnapshot = {
  version: "1.0.0",
  lastUpdated: "",
  items: [],
};

const EMPTY_MERGED_CONVENTIONS: MergedConventionItem[] = [];

export function useSessionConventions() {
  const sessionSnapshot = useSyncExternalStore(
    subscribeConventionStore,
    getSessionConventionsSnapshot,
    () => EMPTY_SESSION_SNAPSHOT,
  );

  const mergedConventions = useSyncExternalStore(
    subscribeConventionStore,
    getMergedConventionsSnapshot,
    () => EMPTY_MERGED_CONVENTIONS,
  );

  const upsertConvention = useCallback(
    (input: { id?: string; topic: string; content: string }) =>
      upsertSessionConventionInStore(input),
    [],
  );

  const deleteConvention = useCallback(
    (id: string) => deleteSessionConventionInStore(id),
    [],
  );

  const importConventions = useCallback(
    (
      snapshot: SessionConventionsSnapshot,
      resolution: ConventionConflictResolution,
    ) => importSessionConventionsInStore(snapshot, resolution),
    [],
  );

  const exportConventions = useCallback(
    () => exportSessionConventionsFromStore(),
    [],
  );

  const recordConversationDelta = useCallback(
    (summary: string) => recordConversationDeltaInStore(summary),
    [],
  );

  return {
    sessionSnapshot,
    sessionConventions: sessionSnapshot.items,
    mergedConventions,
    upsertConvention,
    deleteConvention,
    importConventions,
    exportConventions,
    recordConversationDelta,
  };
}
