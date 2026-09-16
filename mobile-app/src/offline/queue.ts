/**
 * Local-first report queue (Section 7). A submitted report is ALWAYS written
 * here first, regardless of connectivity — the UI never blocks on a network
 * call. syncManager.ts drains this queue whenever connectivity (cellular,
 * Wi-Fi, or a completed Bluetooth hub sync) becomes available.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { ReportPayload } from "../api/client";

const QUEUE_KEY = "@makueni/report_queue/v1";
const PROJECT_CACHE_PREFIX = "@makueni/projects_cache/";

export interface QueuedReport extends ReportPayload {
  localId: string;
  queuedAt: string;
  status: "pending" | "syncing" | "failed";
  attempts: number;
  // Set when this report reached the backend via the Bluetooth hub relay
  // rather than this device's own connection (Section 7).
  syncedVia?: "direct" | "bluetooth_hub";
}

function makeLocalId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function enqueueReport(payload: ReportPayload): Promise<QueuedReport> {
  const queue = await getQueue();
  const entry: QueuedReport = {
    ...payload,
    localId: makeLocalId(),
    queuedAt: new Date().toISOString(),
    status: "pending",
    attempts: 0,
  };
  queue.push(entry);
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  return entry;
}

export async function getQueue(): Promise<QueuedReport[]> {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function removeFromQueue(localId: string): Promise<void> {
  const queue = await getQueue();
  const next = queue.filter((r) => r.localId !== localId);
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(next));
}

export async function markAttempt(localId: string, status: QueuedReport["status"]): Promise<void> {
  const queue = await getQueue();
  const next = queue.map((r) =>
    r.localId === localId ? { ...r, status, attempts: r.attempts + (status === "failed" ? 1 : 0) } : r
  );
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(next));
}

export async function pendingCount(): Promise<number> {
  const queue = await getQueue();
  return queue.filter((r) => r.status !== "syncing").length;
}

// --- Ward project list cache: browsing works fully offline after first load ---
// Keyed by county+ward+lang since two different counties could share a ward
// name — county isn't optional here to avoid that collision.

function projectCacheKey(county: string, ward: string, lang: string): string {
  return `${PROJECT_CACHE_PREFIX}${county}:${ward}:${lang}`;
}

export async function cacheProjects(county: string, ward: string, lang: string, projects: unknown): Promise<void> {
  await AsyncStorage.setItem(projectCacheKey(county, ward, lang), JSON.stringify({
    cachedAt: new Date().toISOString(),
    projects,
  }));
}

export async function getCachedProjects(county: string, ward: string, lang: string): Promise<{ cachedAt: string; projects: any[] } | null> {
  const raw = await AsyncStorage.getItem(projectCacheKey(county, ward, lang));
  return raw ? JSON.parse(raw) : null;
}
