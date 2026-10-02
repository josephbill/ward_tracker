# I Built an App to Fact-Check My County's Budget — Here's What It Took

Every financial year, Kenyan counties publish a document most residents
will never open: the Programme Based Budget. Buried in it are real
promises — a borehole here, a market shed there, a bursary fund for this
ward's students. The document says the money is allocated. What it doesn't
say is whether any of it actually happened.

That gap — between a line in a budget book and water flowing from a tap —
is what I set out to close with **County Ward Tracker**, a civic
transparency app built around one real, published dataset: the Kasikeu
Ward Development Profile from Makueni County, Kenya. Any resident can
browse what their ward was promised, in their own language, and say
plainly whether it happened — confirmed, not delivered, or partially done.
Every one of those reports gets anchored to a tamper-evident ledger, so
the record can't be quietly rewritten later, by anyone, including me.

## What it actually does

A resident picks a language (English, Kiswahili, or Local dialect), picks their
ward, and sees every budgeted project translated into plain language —
not government jargon. If they've seen a project with their own eyes, they
verify their phone once and report what they observed. Once three
independent reports disagree with the county's own claim, the project
flips to **Disputed** — not because I decided it, but because enough
independent people said so.

Because a lot of rural Kenya doesn't have a smartphone and constant data,
reporting also works over WhatsApp, plain SMS, and — for genuinely
offline pockets — a Bluetooth relay where one neighbor's phone carries
queued reports to the nearest connection. One backend, four doors in.

## The stack, and why

- **Flask + SQLite** for the backend — deliberately boring, because the
  interesting problems here were never the database.
- **Expo/React Native**, exported to web, for the resident-facing app —
  one codebase, works in a browser without installing anything.
- **Hedera Consensus Service** for the ledger. Every report's hash gets
  submitted to a real Hedera testnet topic; anyone can independently
  verify it on a public mirror node without trusting my backend at all.
- **Three languages**, translated at every layer — not just UI chrome, but
  the actual project titles and the statement templates that assemble
  them.

And here's the part I want to spend a real paragraph on: **Pxxl (hosting),
Sabilytics (analytics), and SendByte (email)** — the three services running
this thing in production — are all African-built products. That wasn't
an accident; when I went looking for infrastructure to run a Kenyan civic
app, finding solid tooling built on the continent, by people solving for
this context, was genuinely one of the best parts of this build. It's easy
to reach for the usual global defaults; it was better to not have to. It's
also why this project is shipping as part of
[Africa Is Building's Ship 2026](https://www.africaisbuilding.com/ship/aib-ship-2026).

## Keeping reporters anonymous — and safe

A resident reporting that a county contract wasn't delivered is, in a
small way, contradicting an official record. That shouldn't cost them
anything personally, so anonymity isn't an afterthought here — it's load-
bearing:

- A phone number is only ever used to prove "this is a real person, not a
  bot," once, at verification. It's hashed before it ever touches the
  database, and every report is attributed to an anonymous reporter ID —
  nobody, including me, can trace a report back to a phone number.
- Location, when a resident chooses to share it, is rounded to roughly
  111 meters before it's ever written to the database — precise enough to
  help establish that two reports came from genuinely different people,
  never precise enough to point at a specific house.
- Photos attached to a report have their EXIF metadata stripped before
  storage. Most phone cameras silently embed the exact GPS coordinates a
  photo was taken at inside the image file itself — invisible unless you
  know to look for it, and a far more precise leak than anything the
  report form itself ever asks for. Stripping happens automatically, on
  every upload, whether or not the resident chose to share their location.
- None of this is a UI-level hide: full-precision GPS and original EXIF
  data are never written to the database in the first place, so there's
  nothing sitting around to leak later either.

## The challenges — the honest version

The core logic — dispute thresholds, spam defense, translation, ledger
anchoring — came together cleanly and stayed well-tested throughout. The
real challenges showed up exactly where they always do: at the seam
between "works on my machine" and "works for a stranger on the internet."

A few that taught me the most:

**The OTP verification that worked half the time.** Once deployed, phone
verification started failing intermittently — right code, still rejected.
The cause: the backend ran two worker processes, and the code was stored
in memory in whichever process happened to answer the first request. If a
different worker answered the second request, it simply didn't know the
code existed. Nothing was wrong with the code the user typed; the two
halves of the conversation just weren't talking to each other. Running a
single worker fixed it instantly — the kind of bug that's invisible until
real traffic hits real infrastructure.

**The ledger pointed at nothing.** When I moved from a local ledger stub to
the real Hedera-anchored sidecar, one environment variable still pointed
at `localhost` — which means nothing at all inside a deployed container.
Every report crashed trying to reach a door that only existed on my own
laptop. Once I actually deployed the sidecar as its own live service and
pointed the backend at its real address, reports started landing on
Hedera for real, verifiable independently within seconds on a public
mirror node.

**The analytics that silently never turned on.** I'd added a third-party
analytics snippet, saved the config, and watched a dashboard insist "no
visitors yet" for days. The fix had nothing to do with the dashboard: the
values only get baked into the app at *build* time, and I'd never
triggered an actual rebuild after saving them. Configuration that's
correct but never actually shipped looks identical to configuration
that's wrong — until you check.

Every one of these was invisible from reading the code — only from
clicking through the live, deployed thing.

## What's actually working today

- Real reports, anchored to a real Hedera testnet topic, independently
  verifiable — not a demo of the idea, the idea itself, running.
- A resident-facing onboarding walkthrough explaining what the app is for
  and why, before dropping someone into a ward picker with no context.
- Honest status messaging: the app now only says "logged to the audit
  trail" once that's actually true, instead of assuming success the
  moment a button is tapped.
- Search across every list in the app, three fully translated languages,
  and four independent ways to file a report.

## What's still unfinished, on purpose

- **Kikamba translations are a best-effort draft**, flagged as such
  everywhere they appear, and need a native speaker's review before this
  goes anywhere near a real deployment.
- **The Bluetooth relay is demoed via a script**, not two physical phones
  passing data hand to hand — that's the next real-world test.
- **WhatsApp and SMS sending are still stubbed** pending real Twilio/Africa's
  Talking credentials — the conversation logic is real and tested; the
  actual outbound message isn't yet.
- SQLite works for a pilot; a real multi-county rollout needs a
  provisioned database with actual write concurrency and backups.

## What I'd tell someone starting this tomorrow

Build the stub first, always — every external integration here (ledger,
WhatsApp, SMS, email) shipped behind a clean interface with a working fake
before any real credential existed, so the actual logic was tested and
solid long before deployment day. But a passing test suite isn't a working
product. The bugs that mattered — the ones that actually blocked a real
resident from filing a real report — were only ever found by treating the
deployed app as a black box and clicking through it like a stranger would.

That, and: build for the infrastructure that's actually built for where
you're building. It made this project feel like it belonged to the place
it's for.

---

*County Ward Tracker is a work-in-progress pilot for Kasikeu ward,
Makueni County. Feedback, and especially a Kikamba speaker willing to
review a few dozen lines of translation, very welcome.*
