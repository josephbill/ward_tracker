# API Reference

Base URL: `http://localhost:5055` (dev). All responses are JSON.

## Navigation (language -> county -> ward)

**`GET /api/counties`**
Every county with at least one ingested ward (`{"counties": ["Makueni"]}` in
this PoC — the endpoint itself is county-agnostic, ready for more counties'
PDFs to be dropped in via the same `pdf_ingest.py` pattern).

**`GET /api/wards?county=Makueni`**
Wards with ingested data, optionally scoped to one county.

**`GET /api/languages`**
Supported language codes.

**`GET /api/verification-info`**
The live threshold constants behind "verified"/"disputed" —
`confirmation_threshold`, `dispute_threshold`, `independence_radius_m`
(from `config.py`). The app's Help screen reads these rather than
hardcoding the numbers, so the copy stays accurate if a deployment tunes
them via env vars.

## Projects

**`GET /api/projects?ward=Kasikeu&county=Makueni&lang=en`**
List projects for a ward (optionally scoped to a county, in case two
counties ever share a ward name), each with a `statement` field pre-rendered
in the requested language (`en` / `sw` / `kam`). Also returns
`delivered_count` and `purported_completion_rate` — the share of listed
projects the **county's own record** claims are complete (not citizen
-verified; see each project's `verification_status` for that).

Every project also carries `last_updated_at` (ISO timestamp of the most
recent audit-trail event, or ingestion time if it has none yet — see
`Project.last_updated_at()`) and `source_reference` (the specific
table/section/page it was lifted from in the source document, e.g.
`"..., Section 3 'List of Ward Development Projects', Kasikeu Ward, p.11"`
— narrower than `source_document`/`source_page` alone).

Every project (list and detail) also carries `verification_counts` —
`{agree_count, agree_needed, disagree_count, disagree_needed,
total_active_reports}` — the same independent-report weights
`recompute_verification_status()` uses internally, exposed read-only via
`aggregation.verification_progress()`, so a resident can see e.g. "1 of 2
independent reports needed to confirm" instead of just the end-state label.

**`GET /api/projects/<project_id>?lang=en`**
Single project detail, including its currently-active reports.

**`GET /api/projects/<project_id>/audit-trail?lang=en`**
Full append-only event history for a project, each event carrying
`ledger_ref` and `ledger_verified` (recomputed live against the ledger —
`true` means the stored data still hashes to what was anchored). Event
`description` and `event_type_label` are rendered in the requested language
at read time from the event's own stored payload — see
`backend/app/api/reports.py`'s `_render_event_description`.

When `LEDGER_BACKEND=hedera_sidecar` and an event's `ledger_ref` is a real
Hedera ref (`"<topicId>/<sequenceNumber>"`, not the stub's
`"stub-topic-0.0.0/<n>"`), the app fetches that exact message straight from
Hedera's public mirror-node REST API **from the device itself** — no backend
involved — so a resident can independently confirm the anchored hash
without trusting this API at all. See `mobile-app/src/services/hedera.ts`.

## Reports

**`POST /api/reports`**
```json
{
  "project_id": "KASIKEU-2022-23-001",
  "phone": "+254700000001",
  "claim": "not_delivered",
  "channel": "app",
  "gps_lat": -1.93,
  "gps_lon": 37.56,
  "lang": "en"
}
```
`claim` is one of `confirmed_delivered` / `not_delivered` / `partially_delivered`.
`channel` is one of `app` / `whatsapp` / `sms` / `bluetooth`.
`remarks` is optional free text — typed or voice-transcribed (see
`POST /api/voice/transcribe` below). A photo is never required to submit a
report — the claim alone is a complete, valid submission.
Also accepts `multipart/form-data` with the same fields plus a `photo` file.
`gps_lat`/`gps_lon` are rounded server-side to ~3 decimal places
(~111m/neighbourhood precision — `services/privacy.py`) before being stored,
regardless of the precision the client sent; an uploaded photo has its EXIF
metadata stripped before storage (`services/uploads.py`).

For `channel="app"` or `channel="bluetooth"`, `phone` must belong to a
reporter who has already completed `POST /api/auth/verify-otp` — otherwise
this returns `403 {"error": "phone_not_verified"}`. `whatsapp`/`sms` are
exempt (sending a message from a number is itself proof of controlling that
SIM). This is also what guarantees "one report per citizen": phone numbers
are normalized before hashing (`services/spam_defense.normalize_phone` —
"+254712345678", "254712345678" and "0712345678" all resolve to the same
identity), so the same OTP-verified person can never accumulate more than
one active report per project by varying how they type their number — a
second submission always supersedes the first (see `docs/SPAM_DEFENSE.md`).

Response includes `status_changed` and `new_status` — the WhatsApp bot uses
this to notify a reporter when their submission just pushed a project into
`disputed`.

A successful submission also fires a best-effort county notification email
(see `services/notifications.py`) — this never affects the response above;
an email-sending failure is logged and swallowed, not surfaced as an error.

**`GET /api/reports/mine?phone=+254700000001&lang=en`**
A resident's own report history (percent-encode the `+` — `URLSearchParams`
or `encodeURIComponent` does this correctly; a raw `+` in a query string
decodes as a space and silently breaks the phone-hash lookup). Requires an
OTP-verified phone — same trust bar as submitting a report — and returns
`403` otherwise. Never exposes another phone's history.

## Auth (phone OTP)

**`POST /api/auth/request-otp`** `{ "phone": "+254700000001" }`
**`POST /api/auth/verify-otp`** `{ "phone": "...", "code": "123456" }`
Demo convenience: the last 6 digits of the phone number itself are also
accepted as a valid code (alongside the real generated one), so a live demo
doesn't need to tail logs — see `backend/app/services/otp.py`'s docstring
for why this is safe only because the SMS channel is already a stub.

## Voice-to-text

**`POST /api/voice/transcribe`** `multipart/form-data`: `audio` (file) + `lang`.
Native-only path (web transcribes client-side via the Web Speech API and
never calls this) — returns `{"transcript": ""}` by default since no STT
credential is configured (`STT_BACKEND=dummy`); never fabricates a
transcript. Flip `STT_BACKEND=openai_whisper` with `OPENAI_API_KEY` for a
real one — see `backend/app/services/stt.py`.

## Issues (infrastructure/improvement reports not tied to a project)

**`GET /api/issues/categories`** — `["roads", "water", "health", "education", "electricity", "security", "sanitation", "other"]`.

**`GET /api/issues?ward=Kasikeu&county=Makueni`** — list open/acknowledged/resolved issues.

**`POST /api/issues`**
```json
{
  "phone": "+254700000001",
  "county": "Makueni",
  "ward": "Kasikeu",
  "category": "roads",
  "title": "Pothole on Kasikeu-Kwale road",
  "description": "Getting worse after the rains."
}
```
Requires an OTP-verified phone (`403` otherwise) and is rate-limited the
same way as project reports (`429` past `BURST_MAX_REPORTS` in
`BURST_WINDOW_MINUTES`). Also accepts `multipart/form-data` with a `photo`.
Anchored to the same ledger as project reports, but doesn't feed the
dispute-aggregation logic — there's no official county claim to compare
against for something the county hasn't published yet. Also fires the same
best-effort county notification email as a project report.

## Channel webhooks

**`POST /webhooks/whatsapp`** — Twilio-style form fields (`From`, `Body`,
`MediaUrl0`, `MediaContentType0`, `Latitude`, `Longitude`). When
`MediaContentType0` starts with `audio/`, the media is treated as a voice
note and transcribed via the configured STT client into the report's
`remarks` instead of being stored as a photo (`whatsapp_bot._handle_report_photo`).

**`POST /webhooks/sms`** — Africa's Talking-style form fields (`from`, `text`).

## "What you can do next" (escalation)

No dedicated REST endpoint — `app/services/escalation.py` is a small,
channel-agnostic lookup table (situation → institution/contact) rendered
through the same locale/template system as everything else, and each
channel calls it directly:

- **App**: `EscalationPanel` renders on a project's detail screen whenever
  `verification_status === "disputed"`, mirroring the same four-situation
  table client-side (`mobile-app/src/services/escalation.ts`).
- **WhatsApp**: reply `E` from a project's detail view (or automatically
  offered right after a report pushes a project into `disputed`) to get the
  4-option menu; replying `1`-`4` returns the matching contact.
- **SMS**: `NEXT <project_code> <1-4>`, e.g. `NEXT KASIKEU-2022-23-001 3`.

All three pre-fill the project reference and, when the resident already has
an active report on that project, their own report id
(`report_service.latest_active_report_id`) — so escalating doesn't mean
re-explaining what they already reported from scratch.
