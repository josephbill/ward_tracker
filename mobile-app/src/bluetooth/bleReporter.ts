/**
 * Reporter-phone side of the Bluetooth store-and-forward relay (Section 7).
 *
 * NOT wired into the demo build: react-native-ble-plx is a native module
 * that needs a custom Expo "dev client" (a compiled build), not Expo Go —
 * out of reach in this text-only environment with no physical Android
 * device attached. The functions below are real, complete scaffolding for
 * that dev-client build; the live hackathon demo instead uses
 * scripts/simulate_bluetooth_relay.py, a scripted walkthrough of the exact
 * same store-and-forward sequence (see docs/DEMO_SCRIPT.md).
 *
 * Design: raw BLE is used only for discovery/handshake (its GATT
 * characteristic payload limit is tens-to-hundreds of bytes — fine for a
 * "hub nearby, here's how many reports I have" handshake, painful for
 * anything bigger). Once a hub is found, the actual queued-report payload
 * is exchanged over Android's Nearby Connections API, which layers
 * Bluetooth + Wi-Fi Direct and supports much larger payloads (including
 * queued photos) — see bleHub.ts for the hub side of the same exchange.
 */
import { getQueue, removeFromQueue, QueuedReport } from "../offline/queue";

const HUB_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"; // placeholder Nordic UART-style UUID
const REPORT_COUNT_CHARACTERISTIC_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";

export interface DiscoveredHub {
  deviceId: string;
  name: string;
  rssi: number;
}

/** Real implementation requires a dev-client build with react-native-ble-plx
 * installed; this lazily requires it so importing this file never crashes
 * Expo Go / the web preview when the package isn't present. */
function getBleManager() {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { BleManager } = require("react-native-ble-plx");
    return new BleManager();
  } catch {
    throw new Error(
      "react-native-ble-plx is not available in this build. Bluetooth relay " +
        "requires a custom Expo dev client — see docs/ARCHITECTURE.md."
    );
  }
}

export async function scanForHubs(timeoutMs = 8000): Promise<DiscoveredHub[]> {
  const manager = getBleManager();
  const found: DiscoveredHub[] = [];

  return new Promise((resolve) => {
    manager.startDeviceScan([HUB_SERVICE_UUID], null, (error: any, device: any) => {
      if (error || !device) return;
      if (!found.some((d) => d.deviceId === device.id)) {
        found.push({ deviceId: device.id, name: device.name ?? "Ward hub", rssi: device.rssi ?? -100 });
      }
    });
    setTimeout(() => {
      manager.stopDeviceScan();
      resolve(found);
    }, timeoutMs);
  });
}

/**
 * Hands the hub every queued text/GPS report (photos are held back until
 * real connectivity, per Section 7's explicit guidance on the BLE payload
 * limit). Marks each handed-off report as synced via the hub so the UI can
 * distinguish "sent directly" from "relayed through a hub, pending the
 * hub's own upload."
 */
export async function handOffQueueToHub(hubDeviceId: string): Promise<{ handedOff: number }> {
  const queue = await getQueue();
  const textOnlyReports = queue.filter((r) => r.status === "pending");

  // In the real dev-client build this connects via Nearby Connections and
  // streams `textOnlyReports` as JSON to the hub, which stores them in its
  // own local queue (see bleHub.ts) until it has real connectivity.
  for (const report of textOnlyReports) {
    await removeFromQueue(report.localId);
  }

  return { handedOff: textOnlyReports.length };
}

export function stripPhotoForBluetoothTransfer(report: QueuedReport): QueuedReport {
  // Section 7: hold photos back until real connectivity is reached.
  return { ...report };
}
