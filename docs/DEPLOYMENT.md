# Deploying the backend to Pxxl

[Pxxl](https://pxxl.app/) ("a Nigerian alternative to Vercel/Render/Netlify")
deploys straight from a connected GitHub repo, auto-detecting the stack. This
repo is a monorepo (`backend/`, `mobile-app/`, `ledger-sidecar/`), so Pxxl
needs to be told the backend lives in `backend/`, not the repo root.

This guide is dashboard-based deliberately — deploying requires signing in
to *your* Pxxl account, which isn't something to hand a credential for to an
agent (see this session's own safety rules). Everything below is what to
click; nothing here needs your Pxxl password.

## 1. Prerequisites (already done in this repo)

- `backend/run.py` binds to `0.0.0.0` and reads `PORT` from the environment
  (Pxxl assigns the port at runtime — a hardcoded port or `127.0.0.1` is the
  most common reason a Flask app that works locally fails to boot on a PaaS).
- `backend/Procfile` (`web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2`)
  — a production WSGI server; Flask's own dev server explicitly warns
  against production use.
- `backend/requirements.txt` includes `gunicorn`.

## 2. Connect the repo

1. Sign in at [app.pxxl.app](https://app.pxxl.app/).
2. **New Project → Deploy → GitHub** → select `josephbill/ward_tracker`.
3. When asked for the **root directory**, set it to `backend` — this is the
   part Pxxl's auto-detection can't infer on its own in a monorepo.
4. Pxxl should auto-detect Python + Flask from `backend/requirements.txt`.
   Before the first deploy, open **Build Configuration** and confirm:
   - **Start command**: `gunicorn run:app --bind 0.0.0.0:$PORT` (should be
     picked up from the `Procfile` automatically; set it explicitly here if
     the detected command looks wrong)
   - **Install command**: `pip install -r requirements.txt`

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

## 4. Database — the one real caveat

The backend uses SQLite (`backend/instance/app.db`) by default. Most PaaS
platforms, Pxxl included unless it offers a persistent volume or managed
database for this project type, have an **ephemeral filesystem** — a
redeploy or restart can wipe `instance/`. For this pilot/demo that means:

- After every deploy, run `python seed.py` once (via Pxxl's shell/CLI
  access, if offered) to repopulate the real Kasikeu project data.
- Citizen reports submitted between deploys would be lost on a restart —
  fine for a demo, not for a real rollout.
- A real deployment should point `DATABASE_URL` at a managed Postgres
  instead (Pxxl's own search listing mentions database hosting) — swapping
  it in is a config change only, `Flask-SQLAlchemy` doesn't care which
  database backend it talks to.

## 5. Point the mobile app at the deployed backend

Once you have a live URL (e.g. `https://ward-tracker.pxxl.pro`), set
`EXPO_PUBLIC_API_BASE_URL` to it in `mobile-app/.env` (or wherever you build
the app for demo) instead of `http://localhost:5055`.

## 6. CLI alternative

Pxxl also has a CLI (`pxxl deploy --name ... --domain pxxl.pro`,
`pxxl redeploy proj_123`, `pxxl inspect`) if you'd rather deploy from a
terminal than the dashboard — see [docs.pxxl.app](https://docs.pxxl.app/)
for the install/login steps, which weren't in the public docs excerpt this
guide was written from.
