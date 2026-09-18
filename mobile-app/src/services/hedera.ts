/**
 * Reads directly from Hedera's free, public mirror-node REST API — no
 * backend involved, no credentials needed, CORS-open (verified:
 * access-control-allow-origin: * on testnet.mirrornode.hedera.com). That's
 * the entire point of anchoring to a public ledger: a resident (or a
 * journalist, or an auditor) can independently confirm a report's hash was
 * really anchored at a given time WITHOUT trusting this app's backend at
 * all — the backend could vanish tomorrow and this would still work.
 *
 * `ledger_ref` has two possible shapes, and this module has to handle both:
 *   - Real Hedera (LEDGER_BACKEND=hedera_sidecar): "0.0.<topic>/<sequence>",
 *     e.g. "0.0.10583604/1" — see ledger-sidecar/hedera.js's submitEvent().
 *   - The local stub (LEDGER_BACKEND=stub, the default with no Hedera
 *     credentials configured): "stub-topic-0.0.0/<sequence>" — nothing to
 *     look up on a public network, since it never left this machine.
 */

export type HederaNetwork = "testnet" | "mainnet";

export interface MirrorMessage {
  topicId: string;
  sequenceNumber: number;
  consensusTimestamp: string;
  payloadHash: string | null;
  eventType: string | null;
  runningHash: string;
}

const MIRROR_BASE: Record<HederaNetwork, string> = {
  testnet: "https://testnet.mirrornode.hedera.com",
  mainnet: "https://mainnet-public.mirrornode.hedera.com",
};

/** Real Hedera topic ids are shaped "0.0.<digits>" — the stub's fake topic
 * id ("stub-topic-0.0.0") never matches this, which is exactly the
 * distinction the UI needs to decide whether a live mirror-node lookup is
 * even possible for a given report. */
const REAL_TOPIC_RE = /^0\.0\.\d+$/;

export function parseLedgerRef(ledgerRef: string | null | undefined): { topicId: string; sequenceNumber: string } | null {
  if (!ledgerRef || !ledgerRef.includes("/")) return null;
  const [topicId, sequenceNumber] = ledgerRef.split("/");
  return { topicId, sequenceNumber };
}

export function isRealHederaRef(ledgerRef: string | null | undefined): boolean {
  const parsed = parseLedgerRef(ledgerRef);
  return !!parsed && REAL_TOPIC_RE.test(parsed.topicId);
}

/** The public HashScan explorer's page for this topic — human-browsable,
 * for a resident who wants the full official Hedera UI rather than this
 * app's own summary of the same data. */
export function hashscanTopicUrl(ledgerRef: string, network: HederaNetwork = "testnet"): string | null {
  const parsed = parseLedgerRef(ledgerRef);
  if (!parsed) return null;
  return `https://hashscan.io/${network}/topic/${parsed.topicId}`;
}

function base64Decode(b64: string): string {
  if (typeof atob === "function") return atob(b64);
  // eslint-disable-next-line no-undef
  return Buffer.from(b64, "base64").toString("utf-8");
}

/** Fetches one message straight from the mirror node and decodes the JSON
 * payload the sidecar submitted ({event_type, payload_hash} — see
 * ledger-sidecar/hedera.js's submitEvent()). Throws on a stub ref or a
 * network/lookup failure — callers should catch and show an explanatory
 * state rather than a raw error, since "not on Hedera yet" is an expected,
 * common case (the default LEDGER_BACKEND is the local stub), not a bug. */
export async function fetchMirrorMessage(ledgerRef: string, network: HederaNetwork = "testnet"): Promise<MirrorMessage> {
  const parsed = parseLedgerRef(ledgerRef);
  if (!parsed || !REAL_TOPIC_RE.test(parsed.topicId)) {
    throw new Error("not_on_hedera");
  }
  const url = `${MIRROR_BASE[network]}/api/v1/topics/${parsed.topicId}/messages/${parsed.sequenceNumber}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(resp.status === 404 ? "not_found_on_mirror_node" : `mirror_node_error_${resp.status}`);
  }
  const data = await resp.json();
  let payloadHash: string | null = null;
  let eventType: string | null = null;
  try {
    const decoded = JSON.parse(base64Decode(data.message));
    payloadHash = decoded.payload_hash ?? null;
    eventType = decoded.event_type ?? null;
  } catch {
    // Message wasn't JSON in the shape we expect — still show what the
    // mirror node gave us rather than failing the whole lookup.
  }
  return {
    topicId: data.topic_id,
    sequenceNumber: data.sequence_number,
    consensusTimestamp: data.consensus_timestamp,
    payloadHash,
    eventType,
    runningHash: data.running_hash,
  };
}

/** Hedera consensus timestamps are "<seconds>.<nanoseconds>" since epoch. */
export function formatConsensusTimestamp(ts: string): string {
  const seconds = Number(ts.split(".")[0]);
  if (!Number.isFinite(seconds)) return ts;
  return new Date(seconds * 1000).toLocaleString();
}
