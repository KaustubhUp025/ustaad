# Contracts changelog

Every change to a file in `shared/contracts/` adds a line here in the same PR (both people approve).

| Date | File | Change | Author | Approved by |
| --- | --- | --- | --- | --- |
| 2026-10-11 | all | v1 drafts: ws-events, rest, firestore, fault_card schema | setup | — |
| 2026-10-13 | ws-events.md | `media_request.kind` and `media_ready.kind` accept `document`; `step_card.source.kind` accepts `manual_photo`; allowed values listed (S7, T37) | A | B (PR #7) |
| 2026-10-13 | firestore.md | `jobs.media[]` gets optional `reason` (`requested`\|`side_issue`\|`manual`); `media[].kind` values listed (`photo`\|`video`\|`document`) (S7, T36/T37) | A | B (PR #7) |
