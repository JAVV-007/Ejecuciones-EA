#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')"

if [[ "$CMD" =~ (^|[[:space:]])sudo([[:space:]]|$) ]]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Blocked: sudo is not allowed from Claude Code."}}'
  exit 0
fi

if [[ "$CMD" =~ (^|[[:space:]])rm([[:space:]]|$) ]] && [[ "$CMD" =~ -rf ]]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Blocked: rm -rf is not allowed."}}'
  exit 0
fi

if [[ "$CMD" =~ (^|[[:space:]])dd([[:space:]]|$) ]]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Blocked: dd is not allowed from Claude Code."}}'
  exit 0
fi

if [[ "$CMD" =~ (^|[[:space:]])mkfs([[:space:]]|$) ]]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Blocked: mkfs is not allowed from Claude Code."}}'
  exit 0
fi

exit 0
