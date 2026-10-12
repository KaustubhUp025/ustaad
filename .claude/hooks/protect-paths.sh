#!/bin/sh
# PreToolUse (Edit|Write): human-approved files stay read-only unless ALLOW_PROTECTED=1.
[ "$ALLOW_PROTECTED" = "1" ] && exit 0
path=$(jq -r '.tool_input.file_path // empty')
case "$path" in
  */shared/contracts/*|*/docs/SAFETY.md|*/docs/DECISIONS.md|*/backend/agent/instruction.md|*/backend/agent/callbacks.py)
    echo "Blocked: $path is protected (AGENTS.md > Never). A human must start the session with ALLOW_PROTECTED=1." >&2
    exit 2 ;;
esac
