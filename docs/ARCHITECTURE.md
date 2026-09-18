# Architecture

## What's real vs. stubbed

This is a hackathon PoC. Per an explicit scope decision, external network
integrations are built as clean, swappable interfaces with a working "dummy"
implementation as the default — so the actual logic (aggregation, spam
defense, translation, audit trail) is 100% real and tested, while calls that
need a third-party account (Hedera testnet, WhatsApp Business/Twilio,
Africa's Talking) are stubbed until real credentials are dropped in.

| Piece | Status | Notes |
|---|---|---|
| PDF ingestion | **Real** | Parses the actual [Kasikeu Ward Development Profile, 2025](https://makueni.go.ke/sandbox/site/files/2026/01/Kasikeu.pdf) PDF from Makueni County's own site — 62 real project records, FY2022/23–FY2025/26. |
| Translation | **Real** | Covers all three layers: UI chrome (`locales/*.json`), the statement template's own grammar, and — since Section 15/09's report caught a real gap — the underlying data itself: each of the 62 project titles has a real Swahili translation and a best-effort Kikamba one in `data/project_name_translations.json`, and the 14 recurring sector/department names + the "Cross-cutting" subward label are translated via a lookup in `services/translation.py`. Every project-facing string (REST API, WhatsApp, SMS) resolves through `Project.display_name(lang)`, so a channel can never show a mix of translated chrome around an untranslated title. English and Kiswahili are solid throughout. **Kikamba is a best-effort draft, not reviewed by a native speaker** — see `backend/app/locales/kam.json`'s `_meta.translator_note` and the same note in `project_name_translations.json`. Do not ship Kikamba copy to real users before a native-speaker review pass. |
| Dispute aggregation & spam defense | **Real** | Fully implemented and unit-tested — no external dependency at all. |
| Ledger (Hedera) | **Live in production**, stub available as a local fallback | `LedgerClient` interface with a `StubLedgerClient` (local, deterministic, fully testable) and a complete `HederaSidecarClient` + Node.js sidecar (`ledger-sidecar/`). The sidecar is deployed on **Render** (not Pxxl — see `docs/DEPLOYMENT.md` section 6; Pxxl's free tier only had room for two projects) with real testnet credentials and topic `0.0.10583604`. The production backend runs with `LEDGER_BACKEND=hedera_sidecar` pointed at that Render URL — confirmed live: a submitted report anchors to the real HCS topic, is independently visible via the public mirror node (`testnet.mirrornode.hedera.com`) within seconds, and the audit trail's `ledger_verified` recomputes true against it. `HederaSidecarClient` raises `LedgerUnavailableError` (not a raw exception) on a connection failure or timeout — caught by `api/reports.py`/`api/issues.py` as a clean `503 ledger_unavailable` instead of an opaque 500, with the request's DB writes explicitly rolled back so a failed ledger call never leaves a half-saved report. The sidecar's request timeout is 45s (`LEDGER_SIDECAR_TIMEOUT_S`) to absorb Render's free-tier cold-start delay after idling. Local dev defaults back to the stub unless `backend/.env` sets `LEDGER_BACKEND=hedera_sidecar` with a locally-running sidecar. |
| Ledger mirror-node viewer (app) | **Real** | The audit-trail screen fetches directly from Hedera's public mirror-node REST API from the device itself (CORS-open, no credentials, no backend proxy — confirmed via `access-control-allow-origin: *`) so a resident can independently verify a report's anchored hash without trusting this app's backend at all. Falls back to a plain explanatory note for events still anchored to the local stub ledger (`mobile-app/src/services/hedera.ts`, `src/components/LedgerRecordView.tsx`). |
| Report-count progress + Help screen | **Real** | `aggregation.verification_progress()` exposes the same independent-report weights `recompute_verification_status()` uses (never just the end label) via `verification_counts` on every project response and a `GET /api/verification-info` endpoint for the threshold constants. The app shows "X of Y independent reports needed" progress bars on each project and a dedicated Help screen explaining what Reported/Confirmed/Disputed mean and what it takes, using the live threshold numbers rather than hardcoding them. |
| WhatsApp bot | **Real conversation logic, stubbed sending** | The full state machine (language select, browse, report, photo, location) is real and tested via direct webhook calls. Outbound sending defaults to `DummyWhatsAppClient` (logs instead of calling Twilio); flip `WHATSAPP_BACKEND=twilio` with real Twilio WhatsApp sandbox credentials to actually send. |
| SMS bot | **Real conversation logic, stubbed sending** | Same pattern — `SMS_BACKEND=africas_talking` once you have a sandbox account. |
| React Native app | **Real** | Full screens, offline queue (AsyncStorage), auto-sync on reconnect, i18n, phone OTP, photo capture, location-at-point-of-use, a once-only story-framed onboarding walkthrough shown after language selection (`OnboardingScreen.tsx`), and client-side search filtering on every list screen (ward projects, local issues, my reports — `ListSearchInput.tsx`). Runs via Expo, verified on both an Android emulator and the web target. |
| Bluetooth relay | **Scaffolded, demo is simulated** | `react-native-ble-plx`-based hub/reporter code in `mobile-app/src/bluetooth/` is complete but needs a compiled Expo dev-client build + two physical Android devices to run for real (Expo Go can't load native BLE modules). The demo instead runs `scripts/simulate_bluetooth_relay.py`, which plays out the identical store-and-forward sequence against the real backend. |
| Text-to-speech ("Listen") | **Real** | `expo-speech` wraps the OS/browser's own TTS engine — works in Expo Go, no dev client needed. English and Kiswahili speak for real (verified: `window.speechSynthesis.speaking` observed `true` on web). Kikamba has no standard device/browser voice, so the button deliberately shows "not available" rather than mispronouncing it. |
| Voice-to-text (reporting) | **Real on web, stubbed on native** | Web uses the browser's built-in Web Speech API directly — a genuine live-transcription experience, no server round trip. Native records audio (`expo-av`) and uploads to `POST /api/voice/transcribe`, which is real, tested plumbing but returns an empty transcript by default (`STT_BACKEND=dummy` — never fabricates words); flip to `STT_BACKEND=openai_whisper` with `OPENAI_API_KEY` for a real one. Kikamba has no recognition locale either, so voice input is disabled there too, same reasoning as TTS. |
| Issue reporting (infrastructure not tied to a project) | **Real, not offline-queued** | Full backend (`IssueReport` model, ledger-anchored submission, listing) and app screens. Unlike project reports, issue submissions require a live connection at submit time — the offline queue is scoped to project reports only; extending it to a second payload shape is straightforward future work. |
| Analytics (Sabilytics) | **Web-only by design, native no-op** | [Sabilytics](https://www.sabilytics.com/) is a web analytics platform with no React Native SDK and no server-ingestion API — confirmed by checking its own site before integrating anything. `trackEvent()` calls throughout the app forward to it on web (once `EXPO_PUBLIC_SABILYTICS_SITE_ID`/`_DOMAIN`/`_SCRIPT_URL` are configured from your [dashboard](https://www.sabilytics.com/dashboard) — its script URL is account-specific) and are dev-logged no-ops on native. See `mobile-app/src/services/analytics.ts`. |
| Email notifications (SendByte) | **Stubbed by default, real client fully coded, verified working in sandbox mode** | Confirmed against [SendByte's own docs](https://docs.sendbyte.africa/): `POST https://api.sendbyte.africa/v1/emails`, `Authorization: Bearer sk_test_...` in sandbox. Fires as a best-effort side notification whenever a report or issue is captured (`services/notifications.py`) — deliberately unable to affect the submission it's attached to; a broken/absent email integration never rolls back or fails a report (tested explicitly). Defaults to `DummyEmailClient` (logs only); flip `EMAIL_BACKEND=sendbyte` with a real `SENDBYTE_API_KEY` to actually send. **A `sk_test_...` key never delivers to a real inbox** — SendByte's sandbox mode returns `201`/`"status":"queued"`/`"sandbox":true` for every call (confirmed by calling the live API directly) and only surfaces the email in SendByte's own dashboard; a `sk_live_...` key is what turns on real SMTP delivery. `python run.py` now calls `logging.basicConfig()` so this is actually visible — every send logs `[SendByte -> <to>] ... (status=..., sandbox=...)`, which previously went nowhere since nothing configured the root logger and "nothing seems to happen" looked identical whether the call succeeded, failed, or was sandboxed. Every notification currently goes to one configured test address (`COUNTY_NOTIFICATION_EMAIL`, defaults to `josephbill00@gmail.com`) since this pilot only seeds one county — a real deployment would look up each county's own contact address. |
| Cloud deployment | **Live**: backend + mobile web on Pxxl, ledger sidecar on Render | `run.py` reads `PORT`/binds `0.0.0.0` (required for most PaaS hosts), plus a `Procfile` (`python seed.py && gunicorn run:app --bind 0.0.0.0:$PORT --workers 1` — see below for why `--workers 1`) and `gunicorn` for a real production server. `ledger-sidecar/` deploys separately via `render.yaml` at the repo root (Render Blueprint). See `docs/DEPLOYMENT.md` — deployment itself happens through your own dashboards (GitHub-connected), since logging into your accounts isn't something to hand to an agent. SQLite's ephemeral-filesystem caveat on most PaaS hosts is documented there too, as is the `--workers 1` reasoning: `services/otp.py` keeps OTP codes in an in-memory dict, and more than one gunicorn worker means a `request-otp` and the following `verify-otp` can land on different worker processes that don't share that dict — confirmed live before the fix (intermittent `invalid_or_expired_code` regardless of the code entered). |
| Traceability (last-updated + source reference) | **Real** | `Project.last_updated_at()` derives from the audit trail (falls back to ingestion time if no reports yet); `source_reference` is populated by `pdf_ingest.py` per record (e.g. "...Section 3 'List of Ward Development Projects', Kasikeu Ward, p.11") and surfaced in the REST API, WhatsApp browse view, and the app's project-detail screen. |
| Accessibility | **Real** | A photo/media attachment is optional everywhere (confirmed, not just assumed — see `test_submit_report_stores_optional_remarks` and the equivalent issue test); a WhatsApp voice note is transcribed via the same `STT` client the app's voice button uses and submitted as report remarks (`whatsapp_bot._handle_report_photo`); app interactive elements carry `accessibilityLabel`/`accessibilityRole` and a ≥44px touch target. |
| Privacy hardening | **Real** | `services/uploads.py` strips EXIF from jpg/png/webp uploads by re-encoding the image (best-effort — an unparseable file is kept as-is rather than rejecting the report); `services/privacy.py` rounds all stored GPS to ~111m/neighbourhood precision before it's written, on both reports and issues; a Data Protection Act 2019/ODPC notice is shown after WhatsApp language selection and on the app's language-select screen. |
| "What you can do next" (escalation) | **Real** | `services/escalation.py` is a small config table (situation → institution/contact) rendered through the normal template/locale system — identical on app (`EscalationPanel` on a Disputed project), WhatsApp (reply `E`), and SMS (`NEXT <code> <1-4>`); pre-fills the project reference and, when one exists, the resident's own most recent active report id (`report_service.latest_active_report_id`). |

## Data flow

```
                    ┌─────────────────────────────────────────────┐
                    │        Kasikeu Ward Development Profile      │
                    │        PDF (Makueni County, real doc)        │
                    └───────────────────┬───────────────────────────┘
                                         │ backend/app/services/pdf_ingest.py
                                         ▼
                              data/ward_projects.json
                                         │ backend/seed.py
                                         ▼
                              ┌────────────────────┐
                              │   Flask backend      │◄──── React Native app (REST)
                              │   (one shared API)    │◄──── WhatsApp webhook
                              │                        │◄──── SMS webhook
                              │  services/              │◄──── Bluetooth hub sync
                              │   - translation.py       │      (same REST API,
                              │   - aggregation.py       │       channel="bluetooth")
                              │   - spam_defense.py      │
                              │   - report_service.py ───┼──► services/ledger/
                              │        (every write        (StubLedgerClient or
                              │         goes through here)   HederaSidecarClient)
                              └──────────┬────────────────┘
                                         │
                                         ▼
                              SQLite (Project, Reporter,
                              Report, StatusEvent — the
                              append-only audit trail)
```

Every channel calls the same `submit_report()` in
`backend/app/services/report_service.py`, so the spam-defense gate, ledger
anchoring, and status aggregation behave identically no matter which of the
four channels a report came in on.

## Citizen-facing status vs. county-claimed status

Two separate fields on `Project`, deliberately not merged:

- `county_claimed_status` — what the PDF says (`delivered` / `ongoing` /
  `not_started` / `planned`). Immutable once seeded; it's the historical
  record.
- `verification_status` — what citizens collectively say
  (`reported` / `confirmed` / `partially_delivered` / `not_delivered` /
  `disputed`). Starts at `reported` and is recomputed by
  `services/aggregation.py` on every new report.

`Disputed` only happens when independent citizen reports actively
*disagree* with the county's own claim — see `docs/SPAM_DEFENSE.md` and
`aggregation.py`'s `_AGREEMENT_MATRIX` for the exact rule.
