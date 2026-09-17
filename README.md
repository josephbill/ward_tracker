# County Ward Tracker

Turns any Kenyan county's own published ward budget documents into
plain-language, translated statements, and lets any resident confirm or
dispute whether a promised project actually happened — over an app,
WhatsApp, SMS, or a Bluetooth relay for zero-connectivity areas — with every
report anchored to a tamper-evident ledger. The journey is
language → county → ward → browse/report, so adding another county is a
matter of ingesting its PDF, not rebuilding the app.

This is a generic, any-county tool — **Makueni County's Kasikeu ward is the
one real, ingested pilot dataset** it currently ships with, built from the
actual
[Kasikeu Ward Development Profile, 2025](https://makueni.go.ke/sandbox/site/files/2026/01/Kasikeu.pdf)
(62 real project records, FY2022/23–FY2025/26). `GET /api/counties` /
`GET /api/wards` are what the app itself reads to build the county/ward
picker, so a second county shows up automatically the moment its data is
seeded — no app-side change needed.

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for what's fully real
vs. stubbed pending credentials, **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)**
for a runnable walkthrough, **[docs/SPAM_DEFENSE.md](docs/SPAM_DEFENSE.md)**
for the abuse-defense summary, **[docs/API.md](docs/API.md)** for the REST
API, and **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for deploying the
backend to Pxxl.

## Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
python seed.py            # loads real Kasikeu project data from data/ward_projects.json
python run.py              # http://localhost:5055
python -m pytest tests/    # 91 tests, no external credentials needed

# Mobile app (Expo)
cd ../mobile-app
npm install
npx expo start --web       # or scan the QR in Expo Go on a phone

# Bluetooth relay demo (simulated — see docs/ARCHITECTURE.md)
cd ..
python scripts/simulate_bluetooth_relay.py --api http://localhost:5055
```

Nothing above needs any external account. Copy `backend/.env.example` to
`.env` and `ledger-sidecar/.env.example` to `.env` to layer in real Hedera
testnet / Twilio WhatsApp / Africa's Talking credentials — every integration
point is a config flag, not a code change (see ARCHITECTURE.md's table).

## Repository layout

```
backend/          Flask API — the one shared backend every channel calls
  app/services/pdf_ingest.py     Parses the real Kasikeu PDF into project records
  app/services/aggregation.py    Dispute-threshold / independence / reputation logic
  app/services/spam_defense.py   Rate limiting, burst detection, anomaly flagging
  app/services/ledger/           Hedera-anchoring interface (stub + real sidecar client)
  app/services/whatsapp_bot.py   Full WhatsApp conversation state machine
  app/services/sms_bot.py        SMS keyword flow
  app/services/issue_service.py  Citizen-initiated infrastructure/improvement reports
  app/services/stt.py            Speech-to-text interface (stub + real Whisper client)
  app/services/escalation.py     "What you can do next" contact lookup for disputed projects
  app/services/privacy.py        Shared GPS-rounding helper (neighbourhood-level precision)
  app/locales/{en,sw,kam}.json   Translated UI copy + statement templates
  tests/                          91 pytest tests covering all of the above

data/              Real source PDF + parsed data/ward_projects.json +
                   project_name_translations.json (real Swahili / best-effort
                   Kikamba titles for all 62 projects, merged in by seed.py)
ledger-sidecar/    Node.js service for real Hedera Consensus Service calls
mobile-app/        Expo/React Native app — offline queue, i18n, Bluetooth scaffolding,
                   TTS ("Listen"), voice-to-text, issue reporting, Sabilytics analytics
scripts/           simulate_bluetooth_relay.py — demo walkthrough of the relay
docs/              Architecture, API reference, spam-defense summary, demo script
```

## Additional features

- **Traceability**: every project shows *when* it was last updated
  (`Project.last_updated_at()`, derived from the audit trail) and a
  `source_reference` citing the specific table/section/page it was lifted
  from in the source PDF (`app/services/pdf_ingest.py`), not just the
  document name.
- **Accessibility**: reports and issues never require a photo (the
  claim/category buttons alone are enough); a voice note sent over WhatsApp
  is transcribed into the same free-text remarks a typed message would
  produce (`app/services/whatsapp_bot.py`, via the same STT client the
  app's voice button uses); the app's interactive elements carry
  `accessibilityLabel`/`accessibilityRole` and a ≥44px touch target.
- **Privacy hardening**: uploaded photos have EXIF metadata stripped before
  storage, GPS is rounded to ~111m/neighbourhood-level precision before it's
  ever written to the database, and a Data Protection Act 2019/ODPC notice
  is shown where there's room for it (see Known limitations below).
- **"What you can do next"**: a Disputed project shows a short menu (first
  point of contact / financial accountability / suspected corruption /
  service-delivery failure) that resolves to the one matching institution
  and contact, pre-filled with the project reference and the resident's own
  report id — identically on app, WhatsApp (reply `E`), and SMS
  (`NEXT <code> <1-4>`), all rendered from one lookup table
  (`app/services/escalation.py` / `mobile-app/src/services/escalation.ts`).

## Known limitations (see docs/ARCHITECTURE.md for the full table)

- **Kikamba translations are a best-effort draft, not reviewed by a native
  speaker.** Flagged inline in `backend/app/locales/kam.json` and
  `mobile-app/src/i18n/kam.json` — review before any real deployment.
- Hedera, WhatsApp sending, and SMS sending are stubbed by default (logging
  clients) since this PoC was built without those third-party accounts —
  the real clients are fully coded, just need credentials.
- Bluetooth relay is scaffolded but demoed via a script, not two live
  phones — see `mobile-app/src/bluetooth/README.md` for what running it for
  real requires.
- The OTP flow also accepts a phone's own last 6 digits as a valid code (on
  top of the real generated one), purely so a live demo or emulator run
  doesn't need to tail logs. Remove this fallback (`backend/app/services/otp.py`)
  before any real deployment with a live SMS gateway.
- WhatsApp/SMS still browse by ward only (no county-scoping in those two
  conversational flows yet) — the county layer so far lives in the REST API
  and the app's own navigation.
- Voice-to-text and text-to-speech aren't available for Kikamba (no
  standard device voice or recognition locale exists yet) — the app shows
  this plainly rather than mispronouncing it or silently failing.
- Issue reports (the "areas needing improvement" flow) aren't offline-queued
  yet, unlike project reports — they need a live connection to submit.
- Sabilytics (https://www.sabilytics.com/) is a web-only analytics
  platform with no mobile SDK — `trackEvent()` calls are real on the web
  build and no-ops (dev-logged) on native. See ARCHITECTURE.md.
- Several schema changes mid-build (the `remarks` field, the `issue_reports`
  table, `project_name_sw`/`project_name_kam`) mean a pre-existing
  `backend/instance/app.db` from an older version of this repo needs to be
  deleted and re-seeded (`python seed.py`) — SQLite's `create_all()` only
  creates missing tables, it doesn't alter existing ones. Not an issue on a
  fresh clone.
- Only project *titles* and *sectors* are translated as data (not just UI
  chrome) so far — `description` and `county_remarks` (the PDF's longer
  free-text fields) aren't currently rendered anywhere in the UI, so they
  weren't translated; if a future screen starts showing them, they'd need
  the same treatment as `project_name`.
- Email notifications (SendByte) and Pxxl deployment are both stubbed
  pending credentials/account setup, same pattern as everything else — see
  ARCHITECTURE.md's table and `docs/DEPLOYMENT.md`. Every county
  notification currently goes to one hardcoded test address
  (`COUNTY_NOTIFICATION_EMAIL`), since there's no per-county contact lookup
  built yet and this pilot only seeds one county anyway.
- **GPS is capped to ~111m precision** (`backend/app/services/privacy.py`)
  before it's ever written to the database — full precision is never
  retained anywhere. That's a deliberate privacy default, but it means
  there's currently no path to recover a resident's exact original
  coordinates for a future escalation/investigation workflow; that would
  need to capture higher precision explicitly at the time, behind its own
  access control, not recover it from already-rounded historical data.
- The Data Protection Act / ODPC privacy notice is shown on WhatsApp (after
  language selection) and in the app (language-select screen footer). SMS's
  own message bodies are already near the 160-character single-segment
  limit, so the notice isn't repeated there to avoid silently fragmenting
  every reply into multi-part SMS — a production build with room to spare
  should add it to the first-contact SMS reply too.
- EXIF stripping (`backend/app/services/uploads.py`) only runs for
  jpg/jpeg/png/webp uploads (what the app and WhatsApp actually send) and is
  best-effort: a file Pillow can't parse is kept as-is rather than rejecting
  the report over an image-library limitation.
- The "what you can do next" escalation contacts (EACC, Auditor-General,
  Controller of Budget, Ombudsman) are real institutions/hotlines as of this
  writing but are static text in `escalation.py` — a production deployment
  should treat these as content to review periodically, not hardcode-once.
