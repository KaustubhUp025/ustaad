# Playbook: do one task

Works with any coding agent. Start it with: "Follow docs/playbooks/task.md for: <task card>".

## Task card (the human writes this; keep it to one sitting)
```
ID: T17 / M4   Owner: A   Branch: a/M4-request-media
Goal: request_media tool + WebSocket media_request / media_ready flow
Read: SPEC §6 (request_media row), shared/contracts/ws-events.md, backend/AGENTS.md
Done when:
- tests/unit/test_request_media.py passes (upload → vision check faked → findings)
- confidence < 0.6 returns follow_up with a retake reason; max 2 retakes
- declared NON_BLOCKING with WHEN_IDLE
Don't touch: shared/contracts/, backend/agent/instruction.md
```

## Steps for the agent
1. Read `AGENTS.md`, then only the files the card lists under "Read".
2. Write a 5-line plan: files to change, tests to add, open questions. If the card contradicts the spec, stop and ask.
3. Write the tests, then the code. Use fixtures in `seed/fixtures/`; no network in unit tests.
4. Run `make check` until it passes. Paste only the summary line of the output.
5. Commit with the feature ID prefix on the card's branch.
6. Final message: what changed, how to test it, what you were unsure about, any new dependency.

## Steps for the human
- Give each task its own worktree: `git worktree add ../ustaad-T17 -b a/M4-request-media`.
- Run as many sessions in parallel as you can review well; reviewing is usually the bottleneck, not the tool.
- If a session hasn't produced passing tests after about 45 minutes, stop it, split the card, and restart fresh.
- Open the PR with the template; request a review per `docs/playbooks/review.md`.
