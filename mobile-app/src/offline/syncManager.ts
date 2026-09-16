/**
 * Drains the local report queue whenever connectivity is available.
 * Subscribes to NetInfo so a sync runs automatically the moment the device
 * comes back online — no user action needed, per Section 7 ("queue
 * confirm/dispute submissions locally; sync whenever any connectivity...
 * becomes available").
 */
import NetInfo from "@react-native-community/netinfo";
import { submitReport } from "../api/client";
import { getQueue, markAttempt, removeFromQueue, QueuedReport } from "./queue";

const MAX_ATTEMPTS = 5;
let syncing = false;

export type SyncListener = (result: { synced: number; failed: number }) => void;
const listeners = new Set<SyncListener>();

export function onSyncComplete(listener: SyncListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function syncNow(): Promise<{ synced: number; failed: number }> {
  if (syncing) return { synced: 0, failed: 0 };
  syncing = true;
  let synced = 0;
  let failed = 0;

  try {
    const queue = await getQueue();
    for (const entry of queue) {
      if (entry.status === "syncing" || entry.attempts >= MAX_ATTEMPTS) continue;
      try {
        await markAttempt(entry.localId, "syncing");
        await submitReport(toPayload(entry));
        await removeFromQueue(entry.localId);
        synced += 1;
      } catch (err) {
        await markAttempt(entry.localId, "failed");
        failed += 1;
      }
    }
  } finally {
    syncing = false;
  }

  if (synced > 0 || failed > 0) {
    listeners.forEach((l) => l({ synced, failed }));
  }
  return { synced, failed };
}

function toPayload(entry: QueuedReport) {
  const { localId, queuedAt, status, attempts, syncedVia, ...payload } = entry;
  return payload;
}

let unsubscribeNetInfo: (() => void) | null = null;

export function startAutoSync(): () => void {
  if (unsubscribeNetInfo) return unsubscribeNetInfo;
  unsubscribeNetInfo = NetInfo.addEventListener((state) => {
    if (state.isConnected && state.isInternetReachable !== false) {
      syncNow();
    }
  });
  return () => {
    unsubscribeNetInfo?.();
    unsubscribeNetInfo = null;
  };
}
