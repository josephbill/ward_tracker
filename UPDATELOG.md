# Update Log

Plain-language record of what changed, when, and why. Newest work first.
For the technical "what's real vs. stubbed" reference, see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); for hosting/deploy steps, see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 2026-09-18 — Full QA pass: local + production

Went through every screen and flow twice — once against a local backend
running on your own machine, once against the live deployed site — to
confirm everything actually works, not just that the code looks right.

**Backend**: full automated test suite (106 tests) passing. Spot-checked
every read-only endpoint (`/api/counties`, `/api/wards`,
`/api/verification-info`, `/api/issues/*`) and both bot webhooks
(`/webhooks/whatsapp`, `/webhooks/sms`) directly.

**Mobile app, both locally and on the live site**: language selection →
onboarding (all 5 cards, plus Skip) → county → ward → project list with
search → project detail → phone verification (OTP) → report submission →
audit trail → local issues list with search → issue submission → my reports
with search → help screen → every menu destination → changing language
mid-session.

**Headline result**: submitted a real report on the live production site
end to end — phone verified, report saved, and anchored to the real Hedera
ledger (`ledger_ref: 0.0.10583604/25`), confirmed by querying the live
backend directly afterward. This is the original bug this whole update
session started from ("reports cannot be submitted / never reach the
ledger") — it's now fixed and independently verified working.

Everything tested came back clean except one single OTP verification
attempt on the live site that failed once and then succeeded immediately on
retry — a one-off blip, not reproducible (confirmed via 6/6 successful
direct API calls afterward). Noted here for completeness, not something
that needed a code change.

**Not covered in this pass** (pre-existing scope, not new gaps): native
Android/iOS builds (this app is tested as an Expo web export, which is how
it's actually deployed), the Bluetooth relay (by design demoed via
`scripts/simulate_bluetooth_relay.py`, not two physical phones), and the
deeper WhatsApp/SMS conversation flows beyond the opening message (already
covered by the backend's own automated tests in
`backend/tests/test_whatsapp_bot.py`/`test_sms_bot.py`).

---

## 2026-09-18 — Search filters on every list screen

**What changed**: added a live search box to the ward projects list, the
local issues list, and the my-reports list. Typing filters the list
instantly (by name/description/category/claim) — no round trip to the
server, matching the pattern the language/county/ward pickers already used.

**Files**: new `mobile-app/src/components/ListSearchInput.tsx`, wired into
`WardProjectsScreen.tsx`, `IssuesListScreen.tsx`, `MyReportsScreen.tsx`. New
`searchPlaceholder`/`noSearchResults` copy in all three languages.

---

## 2026-09-18 — Onboarding walkthrough + language-selection fixes

**What changed**: added a 5-card story-framed onboarding screen, shown once
right after a resident picks their language, before they get to
county/ward selection. It walks through: the county's yearly promise → what
the app lets you see → your voice / reporting → the tamper-evident ledger →
access for everyone (WhatsApp/SMS/Bluetooth, for residents without a
smartphone or signal) → "Let's see your ward." Skippable, shown only once
per device (tracked in local storage), illustrated with abstract
geometric color blocks rather than depicted people (no way to source or
generate real photos responsibly here).

**Bug found and fixed while wiring this up**: the language-selection screen
is also reachable later as "change language" from the main menu, for a
resident who's already set up and browsing. That path was unconditionally
forced through the *entire onboarding story again* and then dumped the
resident back on the county-selection screen — discarding their place in
the app even though their county/ward were still saved underneath. This is
almost certainly what looked like "always ending up on onboarding or the
project screens" when testing. Fixed: onboarding now only triggers on a
genuine first-time language pick; changing language later just applies it
and returns you to where you were.

**Wording fix**: the onboarding text used to name "Kikamba" explicitly as
one of three languages content is available in. Changed to "your local
dialect" so the copy doesn't assume Kikamba specifically (the language
*picker* itself still lists Kĩkamba as an actual selectable option — only
the descriptive onboarding sentence changed).

**Defensive guard**: onboarding now redirects to language selection if
somehow reached without a language set, instead of silently defaulting to
Swahili copy — same pattern the app already uses elsewhere (e.g. redirecting
to phone verification if you try to report without one).

**Files**: new `mobile-app/src/screens/OnboardingScreen.tsx`,
`src/state/AppContext.tsx` (new `onboardingSeen` flag), `App.tsx` (routing),
`LanguageSelectScreen.tsx` (the fix), new `onboarding1–5Title/Body` copy in
all three languages.

---

## 2026-09-18 — Sabilytics analytics wasn't tracking anything

**Symptom reported**: Sabilytics dashboard showed "No visitors yet" despite
the site being live and getting traffic.

**Diagnosis**: fetched the live deployed JavaScript bundle directly and
confirmed it contained no trace of the Sabilytics site ID or script URL —
meaning the three `EXPO_PUBLIC_SABILYTICS_*` environment variables were
never actually baked into that build. Expo inlines these at *build* time,
not runtime, so saving them in the Pxxl dashboard alone does nothing until
the project is rebuilt.

**Fix**: no code change needed — the analytics wiring
(`mobile-app/src/services/analytics.ts`) was already correct. Confirmed all
three env vars were genuinely set on the Pxxl project, then had the mobile
app redeployed. Verified afterward, directly on the live site: the
Sabilytics `<script>` tag is now present with the correct site ID and
domain, and it fired a real pageview request to
`sabilytics.com/api/e` — confirmed via the browser's own performance
timing API, independent of dashboard reporting.

---

## 2026-09-18 — Ledger sidecar deployed for real (Render)

**Context**: Pxxl (where the backend and mobile web app are hosted) ran out
of free project slots, so the Hedera ledger sidecar (`ledger-sidecar/`) —
previously only ever run locally — is now deployed on **Render** instead,
as its own separate service.

**What changed**: added `render.yaml` at the repo root (a Render Blueprint)
defining the sidecar service, reusing the real Hedera testnet credentials
and topic (`0.0.10583604`) already set up during local development rather
than creating a new one. Documented the full walkthrough in
`docs/DEPLOYMENT.md` section 6, including the Render free-tier cold-start
trade-off (a service idle for 15+ minutes takes up to ~60s to wake back up
on its next request).

**Bug found and fixed as a direct result of going live with this**: the
backend's `LEDGER_SIDECAR_URL` had been left as `localhost:4001` (the local
dev value) even after `LEDGER_BACKEND` was switched to `hedera_sidecar` on
the deployed backend — meaning every single report submission tried to
connect to nothing and crashed with an unhandled 500. Separately, once
pointed at the real Render URL, the sidecar's cold-start delay exceeded the
original 10-second timeout. Both are fixed — see the next entry.

---

## 2026-09-18 — Report submission was failing in production (the original bug)

This is the fix for the original report: *"reports cannot be submitted /
never reach the ledger on Hedera."* Three separate, compounding bugs, found
by testing the live site directly rather than guessing from the code:

**1. OTP verification was flaky** (~40% failure rate, confirmed by
repeated live testing). `backend/app/services/otp.py` keeps verification
codes in a plain in-memory dictionary. The production backend was running
2 separate worker processes (`gunicorn --workers 2`); a code requested
through one worker often wasn't visible to the worker that handled the
following verification request, since they don't share memory. Fixed by
running a single worker (`--workers 1`) — the simplest fix at this
traffic scale. A phone number now verifies reliably every time.

**2. The ledger was pointed at nothing.** Covered above — `LEDGER_BACKEND`
was set to `hedera_sidecar` in production, but `LEDGER_SIDECAR_URL` still
pointed at `localhost:4001`, which doesn't exist inside that container.
Every report submission crashed trying to reach it. Fixed by deploying a
real sidecar (see previous entry) and pointing the backend at its real URL.

**3. No graceful handling of a slow/unreachable ledger.** Even once pointed
at a real sidecar, a `ConnectionError` or timeout from it was an *unhandled*
exception — a raw, unhelpful 500 error, and (a bug found while testing the
fix) the already-half-written report row was left sitting in the database,
uncommitted but not cleaned up either, because Flask doesn't automatically
roll that back for a request that returns a normal response instead of
crashing all the way out. Fixed with:
  - A new `LedgerUnavailableError`, raised instead of letting the raw
    network exception escape — caught by the API layer and turned into a
    clean `503 {"error": "ledger_unavailable"}`.
  - Explicit `db.session.rollback()` on every error path in
    `api/reports.py`/`api/issues.py`, so a failed submission never leaves
    partial data behind (this also fixed the same latent issue on the
    unrelated `phone_not_verified` error path).
  - The sidecar request timeout raised from 10s to 45s
    (`LEDGER_SIDECAR_TIMEOUT_S`, configurable) to comfortably absorb
    Render's free-tier cold-start delay instead of timing out on it.
  - The mobile app's own error messages for these cases were also fixed to
    show real, translated sentences instead of the raw error code
    (`ledger_unavailable`, `phone_not_verified`, etc.) verbatim.

**Verified fixed**: 6/6 OTP request→verify cycles succeeded directly
against the live backend, and a live report submission through the actual
app landed with a real Hedera ledger reference
(`ledger_ref: 0.0.10583604/25`).

**Files**: `backend/Procfile`, `backend/app/config.py`,
`backend/app/services/ledger/base.py` + `hedera_sidecar_client.py` +
`__init__.py`, `backend/app/api/reports.py` + `issues.py`,
`mobile-app/src/screens/ReportScreen.tsx` + `PhoneVerifyScreen.tsx` +
`ReportIssueScreen.tsx`, `mobile-app/src/i18n/i18n.ts` (new
`translateApiError()` helper) plus new `error_*` copy in all three
languages.

---

## 2026-09-18 — Report/issue submission stopped lying about success

**Symptom**: the app would show "Report submitted and logged to the
tamper-proof audit trail" even when the submission had actually failed
(e.g. the incident above) — because the submit button fired the sync
attempt and navigated away immediately, without ever checking whether it
actually worked.

**Fix**: `ReportScreen.submit()` now waits for the real outcome and shows
one of three honestly distinct messages: synced successfully (green),
genuinely offline and safely queued for automatic retry (blue), or
attempted but failed, will keep retrying (amber) — instead of one green
message regardless of what actually happened. Issue submission
(`ReportIssueScreen.tsx`) was already correct on this front (it doesn't use
the offline queue), so no change was needed there beyond the error-message
translation fix above.

**Files**: `mobile-app/src/screens/ReportScreen.tsx`,
`mobile-app/src/screens/WardProjectsScreen.tsx` (the flash banner now
supports three visual styles, not just success-green), new
`reportQueuedOffline` copy in all three languages.

---

## Earlier this session — deployment groundwork

Condensed summary of foundational fixes made earlier the same day, before
the items above:

- **Backend deploy readiness**: added a `/` health route (platforms
  commonly probe `/` by default, and the app only had `/healthz`), and
  fixed a crash-on-boot caused by the deploy container's read-only
  filesystem rejecting `instance/`/upload directory creation — now falls
  back to a writable temp directory automatically.
- **Mobile web hosting**: Pxxl's workspace has no distinct "static site"
  mode, so `mobile-app/serve-static.js` (a small dependency-free Node
  server) was added to actually serve the Expo web export as a proper
  long-running web service.
- **Data persistence across redeploys**: `backend/Procfile` now runs
  `python seed.py` before starting the server on every boot, so ward
  project data reliably repopulates after a redeploy (citizen-submitted
  reports are not affected by this — they were never wiped by redeploys in
  the first place, only the seed data was).
- Deliberately stayed on SQLite (no Postgres) and, at that point, the local
  stub ledger — both per explicit decisions at the time, later revisited
  (see the ledger entries above).
