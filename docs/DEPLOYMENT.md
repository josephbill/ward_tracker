# Deploying to Pxxl

[Pxxl](https://pxxl.app/) ("a Nigerian alternative to Vercel/Render/Netlify")
deploys straight from a connected GitHub repo, auto-detecting the stack. This
repo is a monorepo (`backend/`, `mobile-app/`, `ledger-sidecar/`).

Pxxl's own written docs describe a "Multiple Services" toggle for handling a
monorepo as one project with several services — **in practice this wasn't
findable in the actual dashboard** (same story as the "Health Check Path"
field below), so this guide uses the simpler, confirmed-working shape
instead: **two separate Pxxl projects pointed at the same repo**, one per
root directory (`backend`, `mobile-app`). Functionally equivalent for this
app's purposes — the backend just gets its own URL instead of sharing one
with the static site. `ledger-sidecar/` is the third piece and lives on
**Render** instead (section 6) — this workspace ran out of free Pxxl
project slots after the other two.

This guide is dashboard-based deliberately — deploying requires signing in
to *your* Pxxl account, which isn't something to hand a credential for to an
agent (see this session's own safety rules). Everything below is what to
click; nothing here needs your Pxxl password. (Pxxl does have its own MCP
server — see `docs.pxxl.app/mcp/overview` — if you'd rather connect an agent
with a scoped API key than click through the dashboard; untested here for
whether it needs a paid plan, worth checking if you want that route instead.)

**Scope of this launch, matching the decisions made for this deploy**: SQLite
(`DATABASE_URL` left unset) rather than a provisioned database — see step
4's trade-off notes, one env-var change away from upgrading later. The
ledger started on the local stub (`LEDGER_BACKEND=stub`, the default) and is
being upgraded to the real Hedera-backed sidecar per section 6 below — until
that section's step 5 is done on the backend project, `LEDGER_BACKEND`
staying unset/`stub` is still the working fallback.

## 1. Prerequisites (already done in this repo)

- `backend/run.py` binds to `0.0.0.0` and reads `PORT` from the environment
  (Pxxl assigns the port at runtime — a hardcoded port or `127.0.0.1` is the
  most common reason a Flask app that works locally fails to boot on a PaaS).
- `backend/Procfile` (`web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 1`)
  — a production WSGI server; Flask's own dev server explicitly warns
  against production use. **Deliberately `--workers 1`**: `services/otp.py`
  stores OTP codes in an in-memory dict, keyed by phone. With more than one
  worker process, a `request-otp` and the following `verify-otp` can land on
  different workers that don't share that dict, failing verification with
  `invalid_or_expired_code` regardless of the code entered — confirmed live
  (3 of 8 verify attempts failed this way with `--workers 2`). Moving the
  store into the DB would allow more workers again; not done for this PoC.
- `backend/requirements.txt` includes `gunicorn`.

## 2. Connect the repo, deploy the backend service

1. Sign in at [app.pxxl.app](https://app.pxxl.app/).
2. **New Project → Deploy → GitHub** → select the repo.
3. When asked for the **root directory** (this project's first/only service
   so far), set it to `backend`.
4. Pxxl should auto-detect Python + Flask from `backend/requirements.txt`.
   Before the first deploy, open **Build Configuration** and confirm:
   - **Install command**: `pip install -r requirements.txt`
   - **Start command**: set this explicitly to
     `python seed.py && gunicorn run:app --bind 0.0.0.0:$PORT --workers 1` —
     matches `backend/Procfile`. Don't assume auto-detection guessed this right:
     this repo's Flask app factory lives in `run.py` (`app = create_app()`),
     not a top-level `app.py`, and a generic Flask auto-detect commonly
     defaults to `gunicorn app:app`, which would build fine and then fail
     at startup against this repo's actual layout.
   - Confirm **web service** type (long-running, listens on `$PORT`, binds
     `0.0.0.0` — already true of `backend/run.py`, nothing to change there).

## 3. Environment variables

Set these under the project's **Secrets** / environment variables screen —
copy the *names* from `backend/.env.example`, filling in only what you
actually have. Nothing is required to boot; every integration defaults to a
"dummy" client that logs instead of calling out (see docs/ARCHITECTURE.md's
table). At minimum for a real demo:

| Variable | Value |
|---|---|
| `PHONE_HASH_SALT` | any random string — don't leave the placeholder in production |
| `FLASK_DEBUG` | `false` |
| `EMAIL_BACKEND` | `sendbyte` (once you have a SendByte key) |
| `SENDBYTE_API_KEY` | your `sk_test_...` sandbox key |
| `COUNTY_NOTIFICATION_EMAIL` | `josephbill00@gmail.com` for testing |

`PORT` is set by Pxxl itself — don't set it manually.

**Do not set `LEDGER_BACKEND` to `hedera_sidecar` on this project** unless
`ledger-sidecar/` is actually deployed as its own separate Pxxl project with
real testnet credentials, and `LEDGER_SIDECAR_URL` points at *that* project's
live URL. `localhost:4001` (the value in `backend/.env.example`, meant for
local dev where both processes run on one machine) will never resolve inside
this project's own container — confirmed live: every report submission threw
an unhandled `requests.exceptions.ConnectionError` and 500'd before saving,
because `LEDGER_BACKEND` had been set to `hedera_sidecar` with that localhost
URL and nothing was listening on it. Leave `LEDGER_BACKEND` unset (defaults
to `stub`) for this launch, matching the decision in the intro above.

## 4. Database — SQLite for this launch, the trade-off to know about

The backend uses SQLite (`backend/instance/app.db`) by default —
`DATABASE_URL` is left unset. That's the deliberate choice for this launch:
zero setup, and switching later is a pure env-var change (`Flask-SQLAlchemy`
doesn't care which database backend it talks to, no code change needed).
What you're accepting in the meantime:

- **Data can vanish on redeploy.** Pxxl's containers are ephemeral like most
  PaaS — a redeploy or restart can wipe `instance/`. Ward project data
  repopulates itself automatically: `backend/Procfile`'s start command is
  `python seed.py && gunicorn run:app ...`, so every container boot re-runs
  the (idempotent — upserts by id, never duplicates) seed step before
  gunicorn starts serving. **Citizen reports submitted since the last
  deploy are not recoverable this way** — `seed.py` only repopulates
  `Project` rows from `data/ward_projects.json`, it has no knowledge of
  reports/issues a resident submitted; those are genuinely gone once
  `instance/app.db` is wiped.
- No real write-concurrency headroom under genuine multi-citizen traffic,
  and no backups — a provisioned Pxxl database gets both for free.
- Upgrade path when ready: **New Project → Database** on Pxxl (see
  `docs.pxxl.app/database/overview`), then point this project's
  `DATABASE_URL` at it and redeploy. Not part of this launch.

## 5. Deploy the mobile app's web build as its own second project

This is the piece that turns into a public URL — the one to register with
Sabilytics (see the mobile app's own `EXPO_PUBLIC_SABILYTICS_*` vars in
`mobile-app/.env.example`) or hand to anyone testing the app in a browser.

**This workspace's Pxxl dashboard has no distinct "Static Site" deploy
mode** — confirmed the hard way: a project configured with just a build
command and `dist/` as output still got treated as a long-running web
service, checked for a listener on `$PORT`, and timed out forever because
nothing was actually running to bind to it. So this isn't published as flat
files; it runs a real (tiny) server:

1. `mobile-app/package.json` has two scripts:
   - `build:web` → `expo export --platform web`, produces the static bundle
     in `mobile-app/dist/` — confirmed working by running it directly.
   - `start:web` → `node serve-static.js`, a dependency-free static file
     server (`mobile-app/serve-static.js`, uses only Node's built-in
     `http`/`fs`/`path`) that binds to `0.0.0.0:$PORT`, serves `dist/`, and
     falls back to `index.html` for unknown paths (client-side routes —
     otherwise a hard refresh on anything but the root path 404s). Tested
     directly: root returns `200 text/html`, a real asset returns `200`
     with the right content type, an unknown path falls back correctly.
2. **New Project → Deploy → GitHub** → same repo, same branch, same flow as
   step 2 — this is a second, independent Pxxl project, not a second service
   bolted onto the backend one.
   - **Working/base directory**: `mobile-app`
   - **Install command**: `npm install`
   - **Build command**: `npm run build:web`
   - **Start command**: `npm run start:web`
3. **Environment variables for this project** (set *before* the build runs
   — Expo inlines every `EXPO_PUBLIC_*` var into the JS bundle at export
   time; a value changed after the fact needs a rebuild, not just a saved
   variable, to actually take effect):

   | Variable | Value |
   |---|---|
   | `EXPO_PUBLIC_API_BASE_URL` | the backend project's live URL from step 2 |
   | `EXPO_PUBLIC_SABILYTICS_SITE_ID` | from Sabilytics, once you have a site registered (leave unset for now — analytics stays inert, everything else works) |
   | `EXPO_PUBLIC_SABILYTICS_DOMAIN` | this project's own Pxxl URL (below) |
   | `EXPO_PUBLIC_SABILYTICS_SCRIPT_URL` | from Sabilytics |

4. Deploy this project. Pxxl assigns it a live URL — **that URL is your
   Sabilytics domain**, per the decision to use the platform's own subdomain
   rather than a custom one. Register it with Sabilytics, then come back,
   fill in the two Sabilytics vars above, and redeploy this project again so
   the build-time vars actually take effect.

## 6. Ledger sidecar — hosted on Render instead of Pxxl

`ledger-sidecar/` (the Node service that anchors report hashes to a real
Hedera Consensus Service topic — see `LEDGER_BACKEND=hedera_sidecar` in
`docs/ARCHITECTURE.md`) is deployed on **Render**, not Pxxl: this workspace
ran out of free Pxxl project slots after the backend + mobile-app projects.
Render's free tier covers a third small web service fine.

**Prerequisites already sitting in `ledger-sidecar/.env` from local dev**
(never committed — `.gitignore` excludes it): a real Hedera testnet operator
account and a created topic (`0.0.10583604`). Deploying is just handing
those same values to Render; no new Hedera setup needed unless you want a
fresh topic.

1. Push `render.yaml` (repo root) — already in this repo, defines the
   `makueni-ledger-sidecar` service with `rootDir: ledger-sidecar`,
   `npm install` / `npm start`, and a `/healthz` health check path (already
   implemented in `ledger-sidecar/index.js`).
2. In the [Render dashboard](https://dashboard.render.com/): **New + →
   Blueprint** → connect this repo → Render reads `render.yaml` and
   proposes the one service. Confirm and create it.
3. Render will prompt for the two vars marked `sync: false` in
   `render.yaml` (it won't pull secrets from a committed file, by design) —
   paste in your local `ledger-sidecar/.env` values:

   | Variable | Value |
   |---|---|
   | `HEDERA_OPERATOR_ID` | from `ledger-sidecar/.env` |
   | `HEDERA_OPERATOR_KEY` | from `ledger-sidecar/.env` |

   `HEDERA_NETWORK` and `HEDERA_TOPIC_ID` are already set as plain values in
   `render.yaml`. `PORT` is injected by Render itself.
4. Deploy. Render assigns a live URL like
   `https://makueni-ledger-sidecar.onrender.com` — sanity-check it:
   `GET <that-url>/healthz` should return `{"status":"ok"}`.
5. **Back on Pxxl**, in the **backend** project's environment variables:
   - `LEDGER_BACKEND` = `hedera_sidecar`
   - `LEDGER_SIDECAR_URL` = the Render URL from step 4 (not
     `localhost:4001` — that value only ever worked for two processes on
     one machine, and caused every report submission to 500 with
     `ConnectionRefusedError` when it was set on the deployed backend
     pointing at nothing — see the live-testing notes above). Redeploy the
     backend after changing this.
6. Verify: submit a report through the app and check `ledger_ref` — it
   should now read `0.0.10583604/<n>` (a real HCS sequence number) instead
   of `stub-topic-0.0.0/<n>`, and the message should show up on
   [HashScan testnet](https://hashscan.io/testnet/topic/0.0.10583604).

**Render free-tier trade-off to know about**: a free web service spins down
after 15 minutes of no traffic and takes a cold-start (~30–60s) to wake back
up on the next request. The first report submission after a quiet period
will be slow (the Flask backend's `requests.post(..., timeout=10.0)` in
`hedera_sidecar_client.py` may even time out on a cold start) — acceptable
for a demo, worth knowing if a live walkthrough hits it. Upgrading off the
free plan removes the spin-down.

## 7. CLI / MCP alternatives

Pxxl also has a CLI (`pxxl deploy --name ... --domain pxxl.pro`,
`pxxl redeploy proj_123`, `pxxl inspect`) and an MCP server
(`docs.pxxl.app/mcp/overview`) if you'd rather deploy from a terminal, or
have an agent drive it with a scoped API key instead of the dashboard — see
[docs.pxxl.app](https://docs.pxxl.app/) for setup on either.
