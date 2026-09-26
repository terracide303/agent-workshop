#!/bin/sh
# Link this workshop's skills into ~/.claude/skills so every session sees them.
#
#   ./install_skills.sh
#
# Symlinks, not copies: the repo stays the one source, and an edit here is live
# everywhere immediately.
#
# TWO THINGS THAT WILL CATCH YOU OUT:
#   1. Skills are picked up when a session STARTS. The session you run this in
#      will not see them. Start a new one.
#   2. A skill that did not load fails SILENTLY -- the session works normally and
#      quietly lacks the thing you added it for. That is why every role brief
#      says to name which skills you can actually see, first thing.
set -e
SHOP="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/.claude/skills}"
mkdir -p "$DEST"

n=0
for d in "$SHOP"/skills/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    ln -sfn "$d" "$DEST/$name"
    echo "ok    $DEST/$name -> $d"
    n=$((n+1))
done

if [ "$n" = 0 ]; then
    cat <<'MSG'
note  skills/ is empty, so nothing was linked. That is the shipped state.

      Skills come from @scout's survey (card #1 on a new project). When one
      earns its place, put it in skills/<name>/SKILL.md and re-run this. See
      skills/README.md for the format.
MSG
else
    echo "done -- $n linked. START A NEW SESSION for them to be picked up."
fi
