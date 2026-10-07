#!/usr/bin/env bash
# Install the bpmn, bpmn-coach and bpmn-to-figjam skills for Claude Code.
#
#   ./install.sh                     copy into ~/.claude/skills/ (all sessions)
#   ./install.sh --project <dir>     copy into <dir>/.claude/skills/ (one project)
#   ./install.sh --link              symlink instead of copy, so `git pull` updates the skills
#
# The three skills are installed side by side: bpmn uses ../bpmn-coach/scripts/validate.py to check its output.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/skills"
DEST="$HOME/.claude/skills"
LINK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project) DEST="$(cd "${2:?--project needs a directory}" && pwd)/.claude/skills"; shift 2 ;;
    --link) LINK=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (see --help)" >&2; exit 1 ;;
  esac
done

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || echo "warning: Python 3.9+ not found. bpmn-coach falls back to checking diagrams by hand without it." >&2

mkdir -p "$DEST"
for skill in bpmn bpmn-coach bpmn-to-figjam; do
  target="$DEST/$skill"
  if [ "$LINK" = 1 ]; then
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      echo "$target already exists as a folder; remove it and rerun with --link." >&2
      exit 1
    fi
    ln -sfn "$SRC/$skill" "$target"
    echo "linked    $skill -> $target"
  else
    if [ -L "$target" ]; then rm "$target"; fi
    mkdir -p "$target"
    (cd "$SRC/$skill" && find . -type f ! -path '*/__pycache__/*' -print0) |
      while IFS= read -r -d '' f; do
        mkdir -p "$target/$(dirname "$f")"
        cp -p "$SRC/$skill/$f" "$target/$f"
      done
    echo "installed $skill -> $target"
  fi
done

if [ -n "$PY" ]; then
  "$PY" "$DEST/bpmn-coach/scripts/validate.py" "$DEST/bpmn/templates/purchase-approval.bpmn" >/dev/null \
    && echo "validator ok ($PY)"
fi

echo
echo "Done. Start a new Claude Code session and try: /bpmn Create a BPMN for <your process>"
