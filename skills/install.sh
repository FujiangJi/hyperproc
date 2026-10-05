#!/usr/bin/env bash
# Install the hyperproc agent skill for Claude Code, Codex, or both.
#
#   ./install.sh --claude              into ~/.claude/skills/hyperproc
#   ./install.sh --codex               into ~/.codex/skills/hyperproc + ~/.codex/AGENTS.md
#   ./install.sh --both
#
# Both are global: they apply in every project on this machine. Add --project
# to scope an install to the current directory instead. An AGENTS.md that is
# already there is never overwritten.
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
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

[ "$CLAUDE" = 0 ] && [ "$CODEX" = 0 ] && {
  echo "nothing to do: pass --claude, --codex or --both (--help for the rest)" >&2
  exit 2
}
[ -d "$SOURCE" ] || { echo "cannot find the skill at $SOURCE" >&2; exit 1; }

copy_skill() {                       # $1 destination; 0 when it put files there
  local dest="$1"
  if [ "$(cd "$(dirname "$dest")" 2>/dev/null && pwd)/$(basename "$dest")" = "$SOURCE" ]; then
    echo "  the skill is already here: $dest"
    return 0
  fi
  if [ -e "$dest" ] && [ "$FORCE" = 0 ]; then
    echo "  $dest already exists; pass --force to replace it"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$SOURCE" "$dest"
  find "$dest" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
  echo "  installed to $dest"
}

# The routing file is read from wherever Codex happens to be running, so a
# global one needs absolute paths; a project one stays relative to its root.
write_agents() {                     # $1 routing file, $2 path to substitute
  local target="$1" root="$2" rendered
  rendered="$(sed "s|{{SKILL_ROOT}}|${root}|g" "$SOURCE/AGENTS.hyperproc.md" | sed '/^<!--/,/^-->/d; /./,$!d')"
  if [ -e "$target" ]; then
    if grep -q 'hyperproc' "$target" 2>/dev/null; then
      echo "  $target already mentions hyperproc; left alone"
      return 0
    fi
    printf '%s\n' "$rendered" > "$(dirname "$target")/AGENTS.hyperproc.md"
    echo "  $target already exists and was left alone"
    echo "  wrote $(dirname "$target")/AGENTS.hyperproc.md - paste its contents into $target"
  else
    mkdir -p "$(dirname "$target")"
    printf '%s\n' "$rendered" > "$target"
    echo "  wrote $target"
  fi
}

if [ "$CLAUDE" = 1 ]; then
  echo "Claude Code:"
  if [ "$PROJECT" = 1 ]; then copy_skill "$PWD/.claude/skills/hyperproc"
  else copy_skill "$HOME/.claude/skills/hyperproc"; fi
  echo "  start a new session; the skill loads when a task matches its description"
fi

if [ "$CODEX" = 1 ]; then
  echo "Codex:"
  if [ "$PROJECT" = 1 ]; then
    copy_skill "$PWD/skills/hyperproc"
    write_agents "$PWD/AGENTS.md" "skills/hyperproc"
  else
    copy_skill "$HOME/.codex/skills/hyperproc"
    write_agents "$HOME/.codex/AGENTS.md" "$HOME/.codex/skills/hyperproc"
  fi
fi

echo
echo "Check the environment the skill will run against:"
echo "  python ${SOURCE}/scripts/env_report.py"
