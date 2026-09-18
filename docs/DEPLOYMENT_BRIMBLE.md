# Deploying to Brimble

[Brimble](https://brimble.io/) deploys straight from a connected Git repo —
similar model to Pxxl/Render/Heroku, see `docs/DEPLOYMENT.md` for that
alternative. This repo is a monorepo (`backend/`, `mobile-app/`,
`ledger-sidecar/`), so each thing you deploy is its **own Brimble project**
pointed at a different root directory within the same repo.

This guide is dashboard-based deliberately — deploying requires signing in
to *your* Brimble account, which isn't something to hand a credential for to
an agent (see this session's own safety rules). Everything below is what to
click; nothing here needs your Brimble password. (Brimble does offer an
official MCP server at `mcp.brimble.io` that would let an agent drive this
directly with a *scoped* API key instead of a password — ask if you'd
rather do it that way.)

**Scope of this launch, per the decisions made when this doc was written**:
only `backend` and `mobile-app` are deployed. `ledger-sidecar` stays local —
the deployed backend runs on the local stub ledger (`LEDGER_BACKEND=stub`,
already the default, nothing to set) rather than anchoring to real Hedera.
The database stays SQLite (`DATABASE_URL` left unset) rather than a
provisioned Postgres — see the trade-offs called out in step 4. Both are
one env-var change away from upgrading later; nothing below forecloses it.

## 1. Prerequisites (already done in this repo)

- `backend/run.py` binds to `0.0.0.0` and reads `PORT` from the environment
  — Brimble assigns the port at runtime; a hardcoded port or a
  `127.0.0.1`/`localhost` bind returns a 502 (confirmed from Brimble's own
  quickstart docs).
- `backend/Procfile` (`web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2`).
  **This matters more on Brimble than it did on Pxxl**: Brimble
  auto-detects Flask projects and defaults the start command to
  `gunicorn app:app` — wrong for this repo, since the actual app factory
  lives in `run.py` (`app = create_app()`), not a top-level `app.py`. Step
  3 below explicitly overrides the start command so this default never gets
  used; without that override the deploy would build fine and then 502.
- `backend/requirements.txt` includes `gunicorn`.

## 2. Connect the repo, create the backend project

1. Sign in at [app.brimble.io](https://app.brimble.io/).
2. **New project** → connect GitHub if not already linked → pick this repo
   → choose the branch to track (usually `main`).
3. **Root directory**: `backend`.
4. Brimble should auto-detect Python/Flask from `backend/requirements.txt`.

## 3. Configure the build — override the start command

Before the first deploy, open the build configuration and confirm:

| Setting | Value |
|---|---|
| Framework | Flask (auto-detected) |
| Root directory | `backend` |
| Install command | `pip install -r requirements.txt` |
| Build command | *(none)* |
| **Start command** | `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2` — **override the auto-detected `gunicorn app:app`, it's wrong for this repo** |
| Region | whichever is closest to your users |

## 4. Environment variables

Set these on the backend project's Environment tab (bulk-import from a
`.env` file works too — copy the *names* from `backend/.env.example` and
fill in only what you have). Nothing is required to boot; every integration
defaults to a "dummy"/stub client. At minimum for this launch:

| Variable | Value |
|---|---|
| `PHONE_HASH_SALT` | a real random string — don't ship the placeholder |
| `FLASK_DEBUG` | `false` |
| `EMAIL_BACKEND` | `sendbyte` |
| `SENDBYTE_API_KEY` | your `sk_test_...` sandbox key (see docs/ARCHITECTURE.md for what "sandbox" means for delivery) |
| `SENDBYTE_FROM_ADDRESS` | `josephbill00@gmail.com` |
| `COUNTY_NOTIFICATION_EMAIL` | `joseph.mbugua@moringaschool.com` |

**Deliberately not set** (both stay on their defaults for this launch):
- `LEDGER_BACKEND` — stays `stub`. Reports still get a tamper-evident hash
  and a full audit trail; it's just anchored to a local log on the
  backend's own disk instead of the public Hedera network. Revisit by
  deploying `ledger-sidecar` as its own Brimble project later and setting
  `LEDGER_BACKEND=hedera_sidecar` + `LEDGER_SIDECAR_URL` to its URL.
- `DATABASE_URL` — stays unset (SQLite). See the trade-offs above. Revisit
  by provisioning a Brimble Postgres project and setting `DATABASE_URL` to
  its connection string — no code change needed either way.

`PORT` is set by Brimble itself — don't set it manually.

Brimble's own caveat, confirmed from their docs: **adding or changing a
variable doesn't affect an already-running deployment** — you have to
redeploy for it to take effect.

## 5. Deploy the backend, get its URL

Click **Deploy**. Watch the logs drawer (clone → detect → install → start).
On success you're live at `https://<project-name>.brimble.app`. Note this
URL — the mobile app needs it in step 7.

The SQLite caveat from step 4 applies here concretely: after this first
deploy (and after any future one), run `python seed.py` once via Brimble's
shell/CLI access if offered, to (re)populate the real Kasikeu project data.

## 6. Add a build step for the mobile app's web export

`mobile-app/package.json` only has `"web": "expo start --web"` today — a
dev server, not something you deploy. Add a production export script before
creating the Brimble project for it:

```json
"scripts": {
  "build:web": "expo export --platform web"
}
```

This produces `mobile-app/dist/` — a plain static bundle (HTML/JS/CSS) with
no server behind it, which is exactly what a Brimble **Static Site** project
wants.

## 7. Create the mobile-app project (Static Site)

1. **New project** → same repo → **root directory**: `mobile-app`.
2. **Service type**: Static Site.
3. **Build command**: `npm run build:web` (after step 6's script exists).
4. **Output directory**: `dist`.
5. **Environment variables** (these get baked into the JS bundle at build
   time — Expo inlines every `EXPO_PUBLIC_*` var when the export runs, so
   they must be set *before* this first build, and any later change needs a
   rebuild, not just a saved variable):

   | Variable | Value |
   |---|---|
   | `EXPO_PUBLIC_API_BASE_URL` | the backend URL from step 5 |
   | `EXPO_PUBLIC_SABILYTICS_SITE_ID` | from your Sabilytics dashboard, once you have one (leave unset for now — analytics stays inert, everything else still works) |
   | `EXPO_PUBLIC_SABILYTICS_DOMAIN` | this project's own Brimble subdomain (step 8) |
   | `EXPO_PUBLIC_SABILYTICS_SCRIPT_URL` | from your Sabilytics dashboard |

6. Deploy. You're live at `https://<project-name>.brimble.app` — no
   container, no cold start, served from edge cache.

## 8. This is your Sabilytics domain

Per the decision behind this doc: **stay on Brimble's own subdomain**, no
custom domain purchase/DNS work needed. Whatever `<project-name>.brimble.app`
Brimble assigned the mobile-app project in step 7 is the exact string to
register as the "domain" when you create your Sabilytics site — then come
back and fill in `EXPO_PUBLIC_SABILYTICS_SITE_ID`/`_SCRIPT_URL` from what
Sabilytics gives you, and redeploy (rebuild) the mobile-app project so the
build-time vars actually take effect.

## 9. Smoke test

- Open the mobile-app URL, confirm it loads and successfully calls the
  backend (language → county → ward → project list).
- Submit a test report end-to-end, confirm it shows up via
  `GET /api/projects/<id>/audit-trail` on the backend URL.
- Confirm CORS isn't an issue — `Flask-Cors`'s `CORS(app)` in
  `backend/app/__init__.py` is already wide-open (`*`), so the static
  site's origin needs no extra allow-listing.

## Later upgrades (not part of this launch, no code changes needed either)

- **Real Hedera anchoring**: deploy `ledger-sidecar` as a third Brimble
  project (root dir `ledger-sidecar`, Web Service, Node auto-detected via
  `"start": "node index.js"`), set its Hedera env vars, then set
  `LEDGER_BACKEND=hedera_sidecar` + `LEDGER_SIDECAR_URL` on the backend
  project and redeploy it.
- **Managed Postgres**: **New project → Database → PostgreSQL** on Brimble,
  then set the backend's `DATABASE_URL` using Brimble's cross-project
  reference syntax so traffic stays on their private network:
  ```
  DATABASE_URL = postgres://{{@your-db-slug.DB_USER}}:{{@your-db-slug.DB_PASSWORD}}@{{@your-db-slug.PRIVATE_SERVICE_HOST}}:{{@your-db-slug.SERVICE_PORT}}/{{@your-db-slug.DB_NAME}}
  ```
  Redeploy the backend after setting it.
- **Custom domain**: Domains tab on the mobile-app project → add hostname →
  CNAME to `gateway.brimble.app` for a subdomain, or an A record to
  `157.90.225.125` for an apex domain → TLS auto-provisions via Let's
  Encrypt. Update the Sabilytics domain registration to match afterward.
