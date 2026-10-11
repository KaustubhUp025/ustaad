# Playbook: review a pull request

Rule: **the reviewer is a different model from the one that wrote the PR** (recorded in the PR template). If only
one model is available, use a fresh session that did not write the code and say so in the PR.
Any tool can do it. Start it with: "Follow docs/playbooks/review.md for PR #<N>".
If your tool has a built-in GitHub PR review, you can use it instead, as long as it follows the checks below.

## Steps for the agent
1. `gh pr view <N>`, `gh pr diff <N>`, `gh pr checks <N>`.
2. Read `AGENTS.md`, the SPEC sections the PR names, `shared/contracts/`, and `docs/DESIGN.md` if `web/` changed.
3. Check, most important first:
   - contract breaks against `shared/contracts/` or `backend/models/`
   - safety: can a hazardous step be reached without a passed gate; refrigerant handling
   - secrets, phone numbers, AI Studio keys, hard-coded model IDs
   - missing or empty tests for new tools
   - bugs: async misuse, unhandled errors, non-idempotent webhook handling, timezones
   - UI: tokens and i18n only, 360 px width, 48 px targets, DESIGN.md word rules
4. Report only findings tied to a file and line in the diff, most severe first. Say "no blocking issues" if none.
5. Post it: `gh pr review <N> --comment --body "<review>"`, starting with "Review (<tool/model>):" and ending with
   Approve / Approve with nits / Changes needed.

## Rules for humans
- CI is the referee: a red `make check` blocks merge whatever a review says.
- PRs touching `shared/contracts/` need both humans' approval plus one model review.
- The author fixes findings in the same PR; don't argue with the reviewer model, verify the finding.
