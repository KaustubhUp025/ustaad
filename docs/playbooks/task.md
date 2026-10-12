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
Out of scope: retake UI, real vision calls, anything not under "Done when"
```

## Steps for the agent
1. Read `AGENTS.md`, then only the files the card lists under "Read".
2. Write a 5-line plan: files to change, tests to add, open questions. If the card contradicts the spec, stop and ask.
3. Red first: write the tests, run them, and see them fail for the right reason. Use fixtures in
   `seed/fixtures/`; no network in unit tests.
4. Write the least code that makes them pass. Nothing listed under "Out of scope".
5. Run `make check` until it passes, then run the thing itself (curl the endpoint, replay the fixture, or
   screenshot the screen).
6. Commit with the feature ID prefix on the card's branch.
7. Final message: what changed (files with line counts), the `make check` summary line and the run evidence,
   what you were unsure about, any new dependency, anything added that the card didn't ask for.

## Steps for the human
- Give each task its own worktree: `git worktree add ../ustaad-T17 -b a/M4-request-media`.
- Run as many sessions in parallel as you can review well; reviewing is usually the bottleneck, not the tool.
- If a session hasn't produced passing tests after about 45 minutes, stop it, split the card, and restart fresh.
- Open the PR with the template; request a review per `docs/playbooks/review.md`.
