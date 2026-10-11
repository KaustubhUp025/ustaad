# Setup — both laptops, tonight (about 60–90 minutes)

## 1. Both people
1. Install: git, `gh` (GitHub CLI), Python 3.12 + `uv`, Node 22 + `pnpm`, `make`, `gcloud`, `firebase-tools`
   (`npm i -g firebase-tools`), ffmpeg. Playwright comes with the web dev dependencies.
2. `gh auth login`, `gcloud auth login`, `gcloud auth application-default login`, `firebase login`.
3. Clone the repo, `cp .env.example backend/.env` and `cp web/.env.example web/.env.local`; fill the project ID and
   bucket (unit tests need no secrets). Put the project ID in `.firebaserc`.
4. `make setup && make check` — passes on a fresh clone.

## 2. Your AI coding agent (any tool)
1. Use whichever AI coding agent or model you prefer; you can switch at any time.
2. Open it at the repo root. Confirm it has picked up `AGENTS.md` (ask it "what are this repo's rules?").
   If your tool reads a different filename, add a one-line adapter like `CLAUDE.md` / `GEMINI.md` that points to
   AGENTS.md — never copy the rules.
3. Give it permission to run `make`, `uv`, `pnpm`, `git` and `gh` in the repo (package installs need network).
   Keep `gcloud`, `firebase` and `make deploy-*` for humans unless a task says otherwise.
4. Optional: if your tool has a GitHub PR-review integration, connect it to this repo; it must follow
   `docs/playbooks/review.md`.
5. Optional: a design skill or plugin in your tool is fine for UI work, as long as `docs/DESIGN.md` wins.
6. Use: "Follow docs/playbooks/task.md for: <card>", "…review.md for PR #N", "…ui-pass.md for /w/job".

## 3. GitHub (B)
1. Create a **public** repo `ustaad`, push this starter as the first commit, add A as a collaborator.
2. Branch protection on `main`: require the `ci` checks; CODEOWNERS (`.github/CODEOWNERS`, replace the
   placeholder usernames) requires both of you on `shared/contracts/`.
3. Labels: `A`, `B`, `contracts`, `ui`, `blocked`. Optional: one issue per task card.

## 4. Google Cloud (B, then A)
1. B: `PROJECT_ID=… BILLING_ACCOUNT=… ./infra/setup.sh`, then `./infra/firestore.sh`, then `./infra/budgets.sh`.
2. B: add both people as project Editors.
3. A: `make agent-engine` → put the ID in `backend/.env` as `AGENT_ENGINE_ID`.
4. A: `LIVE_MODEL=gemini-3.8-live make smoke-live`; if it fails, try `gemini-live-2.5-flash-native-audio`.
   Record the result in `docs/STATUS.md` and `docs/DECISIONS.md`.
5. A: export `PROJECT_ID`, `LIVE_MODEL`, `MEDIA_BUCKET`, `ALLOWED_ORIGINS`; run `make deploy-dev`, then once
   `git tag v0-skeleton && make deploy-demo MIN_INSTANCES=0` (the Hosting rewrite needs `ustaad-api` to exist),
   then `make deploy-hosting`.
6. Day 2: Billing → Reports, check which credit each SKU draws from.

## 5. WhatsApp (B)
Meta developer app → WhatsApp product → test number → add the 5 team phones as recipients → webhook URL
`https://<ustaad-api-dev-url>/webhook/whatsapp` with the verify token from Secret Manager → subscribe to
`messages`. Create a system-user token for anything that must outlive 24 hours.
