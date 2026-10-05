#!/usr/bin/env bash
# Install the hyperproc agent skill for Claude Code, Codex, or both.
#
#   ./install.sh --claude              into ~/.claude/skills/hyperproc
#   ./install.sh --codex               into ./skills/hyperproc + an AGENTS entry
#   ./install.sh --both
#
# Copies files and, for Codex, writes a routing file whose paths match where
# the skill actually landed. An existing AGENTS.md is never overwritten.
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hyperproc"
CLAUDE=0; CODEX=0; PROJECT=0; FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --claude)  CLAUDE=1 ;;
    --codex)   CODEX=1 ;;
    --both)    CLAUDE=1; CODEX=1 ;;
    --project) PROJECT=1 ;;
    --force)   FORCE=1 ;;
    -h|--help) sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

[ "$CLAUDE" = 0 ] && [ "$CODEX" = 0 ] && {
  echo "nothing to do: pass --claude, --codex or --both (--help for the rest)" >&2
  exit 2
}
[ -d "$SOURCE" ] || { echo "cannot find the skill at $SOURCE" >&2; exit 1; }

copy_skill() {                       # $1 destination directory
  local dest="$1"
  if [ -e "$dest" ] && [ "$FORCE" = 0 ]; then
    echo "  $dest already exists; pass --force to replace it"
    return 1
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$SOURCE" "$dest"
  rm -rf "$dest/__pycache__" "$dest/scripts/__pycache__"
  echo "  installed to $dest"
}

if [ "$CLAUDE" = 1 ]; then
  if [ "$PROJECT" = 1 ]; then dest="$PWD/.claude/skills/hyperproc"
  else dest="$HOME/.claude/skills/hyperproc"; fi
  echo "Claude Code:"
  copy_skill "$dest" || true
  echo "  start a new session; the skill loads when a task matches its description"
fi

if [ "$CODEX" = 1 ]; then
  dest="$PWD/skills/hyperproc"
  echo "Codex:"
  if [ "$(cd "$(dirname "$dest")" 2>/dev/null && pwd)/hyperproc" = "$SOURCE" ]; then
    echo "  the skill is already at $dest"
  else
    copy_skill "$dest" || true
  fi
  # Paths inside the routing file must match where the skill actually is.
  rendered="$(sed 's|{{SKILL_ROOT}}|skills/hyperproc|g' "$dest/AGENTS.hyperproc.md" \
              | sed '/^<!--/,/^-->/d')"
  if [ -e "$PWD/AGENTS.md" ]; then
    printf '%s\n' "$rendered" > "$PWD/AGENTS.hyperproc.md"
    echo "  AGENTS.md already exists and was left alone"
    echo "  wrote AGENTS.hyperproc.md instead - paste its contents into your AGENTS.md"
  else
    printf '%s\n' "$rendered" > "$PWD/AGENTS.md"
    echo "  wrote AGENTS.md at the project root"
  fi
fi

echo
echo "Check the environment the skill will run against:"
echo "  python ${SOURCE}/scripts/env_report.py"
