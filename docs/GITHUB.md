# GitHub rules for this repo

How changes reach `main`, for both people and their coding agents. Set up in T02 on Oct 12, 2026.
Repo: https://github.com/KaustubhUp025/ustaad (public). Owners: A = @KaustubhUp025, B = @samyak8796.

## The rules on `main`

| Rule | Setting |
| --- | --- |
| Direct pushes to `main` | Blocked. Every change goes through a pull request. |
| Required checks | `backend` and `web` (the two jobs in `.github/workflows/ci.yml`) must be green. |
| Approvals for ordinary PRs | None required. Self-merge once CI is green. |
| Approvals for code-owner paths | One listed owner other than the author must approve. |
| Admins | The rules apply to admins too. |
| Force pushes and deleting `main` | Blocked. |
| Branch must be up to date before merge | Not required (keeps parallel work fast). Rebase if CI on `main` goes red after a merge. |

## Code-owner paths (`.github/CODEOWNERS`)

| Path | Owners | What it holds |
| --- | --- | --- |
| `shared/contracts/` | A and B | The interface between the two halves: REST shapes (`rest.md`), WebSocket events (`ws-events.md`), Firestore collections (`firestore.md`), the fault-card schema, the generated `openapi.json`, and `CHANGELOG.md`. |
| `backend/agent/instruction.md` | A | The agent's system instruction. |

A PR that touches `shared/contracts/` is approved by the other person: B approves A's, A approves B's.
GitHub does not let anyone approve their own PR.

## Day-to-day flow

1. Branch from `main`: `a/<feature-id>-slug` or `b/<feature-id>-slug` (for example `a/M4-camera-sheet`).
2. Commit with the feature ID first (`M4: …`), or the task ID if there is no feature (`T03: …`).
3. Run `make check` before pushing.
4. Open a PR and fill the template, including which tools wrote and reviewed it.
5. Have a different model from the author review it (`docs/playbooks/review.md`).
6. Merge when `backend` and `web` are green, the same day. Update the task's Status in `docs/TASKS.md` in the PR.

## What coding agents may and may not do

- May: write code, open PRs, review PRs, and merge ordinary PRs once CI is green.
- May not: approve or merge a PR that touches a code-owner path, `docs/SAFETY.md`, `backend/agent/callbacks.py`,
  `docs/DECISIONS.md` or `AGENTS.md`. A human reads the review and approves.
- An agent on your laptop uses your GitHub login, so GitHub cannot tell it from you. Branch protection does not
  enforce the line above; you do, by how you instruct your agent.
- A red CI is final. No model's approval overrides it.

## Labels

`A`, `B` (owner), `contracts` (touches `shared/contracts/`), `ui`, `blocked`.

## Changing these rules

Settings → Branches → `main` (admin only). Agree first, then update this file in the same PR.
If the rule blocks an urgent fix, fix the PR; don't switch the rule off.
