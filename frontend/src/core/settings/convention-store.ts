import {
  SESSION_CONVENTIONS_KEY,
  SESSION_CONVENTIONS_VERSION,
  deleteSessionConvention,
  exportSessionConventions,
  getSessionConventions,
  importSessionConventions,
  mergeRepoAndSessionConventions,
  recordConversationConventionDelta,
  saveSessionConventions,
  upsertSessionConvention,
  type ConventionConflictResolution,
  type MergedConventionItem,
  type SessionConventionItem,
  type SessionConventionsSnapshot,
} from "./conventions";

type Listener = () => void;

const listeners = new Set<Listener>();
const EMPTY_MERGED_CONVENTIONS: MergedConventionItem[] = [];

let loaded = false;
let storageListenerRegistered = false;
let sessionSnapshot: SessionConventionsSnapshot = {
  version: SESSION_CONVENTIONS_VERSION,
  lastUpdated: "",
  items: [],
};
let mergedSnapshot: MergedConventionItem[] = EMPTY_MERGED_CONVENTIONS;

function recomputeMergedSnapshot() {
  mergedSnapshot = mergeRepoAndSessionConventions(sessionSnapshot.items);
}

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

function ensureLoaded() {
  if (loaded || typeof window === "undefined") {
    return;
  }
  sessionSnapshot = getSessionConventions();
  recomputeMergedSnapshot();
  loaded = true;
}

function handleStorage(event: StorageEvent) {
  if (event.storageArea && event.storageArea !== localStorage) {
    return;
  }

  if (event.key !== null && event.key !== SESSION_CONVENTIONS_KEY) {
    return;
  }

  sessionSnapshot = getSessionConventions();
  recomputeMergedSnapshot();
  emitChange();
}

function ensureStorageListenerRegistered() {
  if (storageListenerRegistered || typeof window === "undefined") {
    return;
  }

  window.addEventListener("storage", handleStorage);
  storageListenerRegistered = true;
}

function persist(nextSnapshot: SessionConventionsSnapshot) {
  sessionSnapshot = nextSnapshot;
  recomputeMergedSnapshot();
  saveSessionConventions(sessionSnapshot);
  emitChange();
}

export function subscribeConventionStore(listener: Listener): () => void {
  ensureLoaded();
  ensureStorageListenerRegistered();
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function getSessionConventionsSnapshot(): SessionConventionsSnapshot {
  ensureLoaded();
  return sessionSnapshot;
}

export function getMergedConventionsSnapshot(): MergedConventionItem[] {
  ensureLoaded();
  return mergedSnapshot;
}

export function upsertSessionConventionInStore(
  input: Pick<SessionConventionItem, "topic" | "content"> & { id?: string },
): SessionConventionsSnapshot {
  ensureLoaded();
  const nextSnapshot = upsertSessionConvention(sessionSnapshot, input);
  persist(nextSnapshot);
  return nextSnapshot;
}

export function deleteSessionConventionInStore(
  id: string,
): SessionConventionsSnapshot {
  ensureLoaded();
  const nextSnapshot = deleteSessionConvention(sessionSnapshot, id);
  persist(nextSnapshot);
  return nextSnapshot;
}

export function importSessionConventionsInStore(
  incomingSnapshot: SessionConventionsSnapshot,
  resolution: ConventionConflictResolution,
): SessionConventionsSnapshot {
  ensureLoaded();
  const nextSnapshot = importSessionConventions(
    sessionSnapshot,
    incomingSnapshot,
    resolution,
  );
  persist(nextSnapshot);
  return nextSnapshot;
}

export function exportSessionConventionsFromStore(): SessionConventionsSnapshot {
  ensureLoaded();
  return exportSessionConventions(sessionSnapshot);
}

export function recordConversationDeltaInStore(
  summary: string,
): SessionConventionsSnapshot {
  ensureLoaded();
  const nextSnapshot = recordConversationConventionDelta(sessionSnapshot, summary);
  persist(nextSnapshot);
  return nextSnapshot;
}
