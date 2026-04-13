#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"

[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$FILE_PATH" >/dev/null 2>&1 || true
    fi
    ;;
  *.md|*.json|*.yml|*.yaml)
    if command -v prettier >/dev/null 2>&1; then
      prettier --write "$FILE_PATH" >/dev/null 2>&1 || true
    fi
    ;;
  *)
    ;;
 esac

exit 0
