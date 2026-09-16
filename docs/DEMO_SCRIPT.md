# Hackathon Demo Script

## 0. Setup (do this before judges arrive)

```bash
cd backend
pip install -r requirements.txt
python seed.py                 # loads the real Kasikeu ward data
python run.py                  # serves on :5055 (see run.py — avoid :5000, often taken)
```

In a second terminal, for the mobile app:
```bash
cd mobile-app
npm install
npx expo start --web           # or scan the QR with Expo Go on a phone
```

## 1. Core loop — real data, plain language, 2+ languages (Section 9, tier 1)

```bash
curl "http://localhost:5055/api/projects?ward=Kasikeu&lang=en" | jq '.projects[0].statement'
curl "http://localhost:5055/api/projects?ward=Kasikeu&lang=sw" | jq '.projects[0].statement'
curl "http://localhost:5055/api/projects?ward=Kasikeu&lang=kam" | jq '.projects[0].statement'
```
Point out: this is the real [Kasikeu Ward Development Profile, 2025](https://makueni.go.ke/sandbox/site/files/2026/01/Kasikeu.pdf)
PDF from Makueni County's own site, table-parsed into 62 structured project
records — not sample data.

## 2. WhatsApp bot (Section 9, tier 3)

```bash
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=1"
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=2"
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=Kasikeu"
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=1"
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=2"   # not delivered
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=SKIP"
curl -X POST localhost:5055/webhooks/whatsapp -d "From=whatsapp:+254700111222" -d "Body=SKIP"
```
Each response's `replies` array is exactly what a resident would see in
WhatsApp. Swap `WHATSAPP_BACKEND=twilio` with real sandbox creds to show it
landing in an actual WhatsApp thread.

## 3. React Native app (Section 9, tier 4)

In the Expo web preview (or a phone via Expo Go): pick a language → browse
Kasikeu → open a project → submit a report → toggle the device/browser
offline (devtools network throttling) and submit again → watch the "N
report(s) waiting to sync" banner → go back online → banner clears
automatically. This demonstrates the offline-first design end to end.

## 4. SMS (Section 9, tier 5)

```bash
curl -X POST localhost:5055/webhooks/sms -d "from=+254700333444" -d "text=KASIKEU-2022-23-001 2"
```
Wire `SMS_BACKEND=africas_talking` with sandbox credentials to show it over
a real SMS number.

## 5. Bluetooth relay (Section 9, tier 6 — simulated)

```bash
python scripts/simulate_bluetooth_relay.py --api http://localhost:5055
```
Narrate each printed step against the real mechanics it stands in for: a
reporter phone with no signal queues locally → walks into range of a ward
hub → hub holds it until it gets its own connectivity → hub pushes to the
same `/api/reports` every other channel uses, tagged `channel=bluetooth`.
The real (uncompiled-for-demo) implementation is in `mobile-app/src/bluetooth/`.

## 6. The moment: push a project to Disputed, live, with its audit trail

```bash
curl -X POST localhost:5055/api/reports -d '{"project_id":"KASIKEU-2022-23-001","phone":"+254700100001","claim":"not_delivered","channel":"app","gps_lat":-1.0,"gps_lon":37.0}' -H "Content-Type: application/json"
curl -X POST localhost:5055/api/reports -d '{"project_id":"KASIKEU-2022-23-001","phone":"+254700100002","claim":"not_delivered","channel":"app","gps_lat":-1.5,"gps_lon":37.5}' -H "Content-Type: application/json"
curl -X POST localhost:5055/api/reports -d '{"project_id":"KASIKEU-2022-23-001","phone":"+254700100003","claim":"not_delivered","channel":"app","gps_lat":-1.9,"gps_lon":37.9}' -H "Content-Type: application/json"
# the 3rd response has "new_status": "disputed"

curl "http://localhost:5055/api/projects/KASIKEU-2022-23-001/audit-trail" | jq
```
Point out: every `submission` and the `status_change` event carries a
`ledger_ref` and `ledger_verified: true` — recomputed live from the exact
payload Flask stored, proving it hasn't been altered since it was anchored.
This is the strongest "trust and verification" story for judges, per
Section 9's own framing — the audit trail is explainable, not a black box.

## 7. Spam defense, in one breath

Read `docs/SPAM_DEFENSE.md` aloud — it's the required one-paragraph
explanation, already written to match exactly what the code does.
