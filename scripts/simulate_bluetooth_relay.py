"""
Scripted walkthrough of the Bluetooth store-and-forward relay (Section 7),
for the hackathon demo. A live 2-phone BLE demo needs a compiled Expo
dev-client build and two physical Android devices — out of reach in this
environment (see mobile-app/src/bluetooth/README.md for the real
implementation). This script plays out the exact same sequence of state
transitions against the real backend, so the concept and the data flow are
both genuinely demonstrated, just with the Bluetooth hop simulated.

Sequence:
  1. A "reporter" phone with no cellular signal queues a report locally
     (mirrors mobile-app/src/offline/queue.ts — nothing hits the network).
  2. The reporter walks within Bluetooth range of a ward hub. A handshake
     exchanges the queued report (mirrors bleReporter.ts <-> bleHub.ts).
  3. The hub — which also has no signal yet — holds the report in its own
     local queue.
  4. The hub later gets connectivity (e.g. reaches the shop/chief's office
     it sits in) and pushes everything it's collected to the real Flask
     backend over the normal REST API — indistinguishable, from the
     backend's point of view, from any other "app" channel submission,
     except channel="bluetooth" is recorded so the audit trail shows how
     the report actually reached the server.

Run:
    python scripts/simulate_bluetooth_relay.py --api http://127.0.0.1:5055
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass, field

import requests


@dataclass
class LocalQueue:
    owner_label: str
    items: list[dict] = field(default_factory=list)

    def enqueue(self, report: dict) -> None:
        print(f"  [{self.owner_label}] queued locally (no connectivity): {report['claim']} on {report['project_id']}")
        self.items.append(report)

    def drain_to(self, other: "LocalQueue") -> int:
        count = len(self.items)
        for item in self.items:
            other.enqueue(item)
        self.items.clear()
        return count


def simulate(api_base: str, project_id: str, ward: str = "Kasikeu") -> None:
    reporter_queue = LocalQueue("Reporter phone")
    hub_queue = LocalQueue("Ward hub")

    print("\n=== Step 1: Reporter has no cellular signal, submits via the app ===")
    reporter_phone = f"+2547{uuid.uuid4().int % 10**8:08d}"

    # The app already gates the Report screen behind OTP verification before
    # a report can even be composed (see ReportScreen.tsx) — a Bluetooth-
    # relayed report is queued from that exact same screen, just forwarded
    # over BLE instead of the internet, so it's held to the same bar
    # server-side (report_service.submit_report() rejects an unverified
    # phone for channel="app"/"bluetooth" with 403 phone_not_verified).
    # Mirror that here: verify via the same demo fallback the app's OTP
    # screen documents (last 6 digits of the phone as the code).
    requests.post(f"{api_base}/api/auth/request-otp", json={"phone": reporter_phone}, timeout=10).raise_for_status()
    verify = requests.post(
        f"{api_base}/api/auth/verify-otp",
        json={"phone": reporter_phone, "code": reporter_phone[-6:]},
        timeout=10,
    )
    verify.raise_for_status()
    print(f"  [Reporter phone] verified {reporter_phone} via OTP (demo fallback code)")

    report = {
        "project_id": project_id,
        "phone": reporter_phone,
        "claim": "not_delivered",
        "channel": "bluetooth",
        "gps_lat": -1.9300,
        "gps_lon": 37.5600,
        "lang": "en",
    }
    reporter_queue.enqueue(report)
    time.sleep(0.5)

    print("\n=== Step 2: Reporter walks within Bluetooth range of the ward hub ===")
    print("  [Reporter phone] discovered hub via BLE advertisement (HUB_SERVICE_UUID)")
    print("  [Reporter phone] handshake ok, handing off queued report over Nearby Connections...")
    handed_off = reporter_queue.drain_to(hub_queue)
    print(f"  [Ward hub] received {handed_off} report(s) from reporter phone")
    time.sleep(0.5)

    print("\n=== Step 3: Hub itself has no connectivity yet — holds the report ===")
    print(f"  [Ward hub] local relay queue size: {len(hub_queue.items)}")
    time.sleep(0.5)

    print("\n=== Step 4: Hub reaches connectivity (e.g. back at the shop) and syncs to backend ===")
    for item in hub_queue.items:
        resp = requests.post(f"{api_base}/api/reports", json=item, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        print(f"  [Ward hub -> backend] POST /api/reports -> 201, ledger_ref={body['report']['ledger_ref']}")
    hub_queue.items.clear()

    print("\n=== Done: verifying the report landed with channel=bluetooth ===")
    trail = requests.get(f"{api_base}/api/projects/{project_id}/audit-trail", timeout=10).json()
    last_event = trail["events"][-1]
    print(json.dumps(last_event, indent=2))
    print(f"\nProject verification_status is now: {trail['verification_status']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:5055", help="Flask backend base URL")
    parser.add_argument("--project-id", default="KASIKEU-2023-24-013", help="Project id to report on")
    args = parser.parse_args()
    simulate(args.api, args.project_id)
