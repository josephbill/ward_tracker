/**
 * Hub-mode side of the Bluetooth relay (Section 7): a phone left somewhere
 * with occasional connectivity (a shop, a chief's office, a boda stage)
 * runs the same app with hub mode on. It advertises over BLE so reporter
 * phones can find it, collects their queued reports (see bleReporter.ts),
 * and pushes everything it's collected to the Flask backend once it gets
 * a real connection.
 *
 * Same caveat as bleReporter.ts: real BLE advertising needs a dev-client
 * build, not Expo Go. This is complete scaffolding for that build; the
 * hackathon demo uses scripts/simulate_bluetooth_relay.py instead.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { submitReport, ReportPayload } from "../api/client";

const HUB_QUEUE_KEY = "@makueni/hub_relay_queue/v1";

interface RelayedReport extends ReportPayload {
  relayedFromDeviceId: string;
  receivedAt: string;
}

function getBleManager() {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { BleManager } = require("react-native-ble-plx");
    return new BleManager();
  } catch {
    throw new Error(
      "react-native-ble-plx is not available in this build. Hub mode " +
        "requires a custom Expo dev client — see docs/ARCHITECTURE.md."
    );
  }
}

export async function startAdvertisingAsHub(): Promise<void> {
  // Real implementation: advertise HUB_SERVICE_UUID (bleReporter.ts) so
  // nearby reporter phones can discover this device, then accept incoming
  // Nearby Connections payloads and hand each one to receiveRelayedReport().
  getBleManager();
}

export async function receiveRelayedReport(fromDeviceId: string, payload: ReportPayload): Promise<void> {
  const queue = await getHubQueue();
  queue.push({ ...payload, relayedFromDeviceId: fromDeviceId, receivedAt: new Date().toISOString() });
  await AsyncStorage.setItem(HUB_QUEUE_KEY, JSON.stringify(queue));
}

async function getHubQueue(): Promise<RelayedReport[]> {
  const raw = await AsyncStorage.getItem(HUB_QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

/** Pushes everything the hub has collected to the backend once IT has
 * connectivity — the second leg of the store-and-forward relay. */
export async function pushHubQueueToBackend(): Promise<{ pushed: number; failed: number }> {
  const queue = await getHubQueue();
  let pushed = 0;
  let failed = 0;
  const remaining: RelayedReport[] = [];

  for (const entry of queue) {
    try {
      const { relayedFromDeviceId, receivedAt, ...payload } = entry;
      await submitReport(payload);
      pushed += 1;
    } catch {
      failed += 1;
      remaining.push(entry);
    }
  }

  await AsyncStorage.setItem(HUB_QUEUE_KEY, JSON.stringify(remaining));
  return { pushed, failed };
}

export async function hubQueueSize(): Promise<number> {
  return (await getHubQueue()).length;
}
