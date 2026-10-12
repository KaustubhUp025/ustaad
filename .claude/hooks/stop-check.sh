#!/bin/sh
# Stop: finishing is blocked while `make check` fails.
cd "$CLAUDE_PROJECT_DIR" || exit 2
out=$(make check 2>&1) && exit 0
{ echo "make check failed; fix it before finishing:"; echo "$out" | tail -n 20; } >&2
exit 2
