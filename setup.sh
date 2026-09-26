#!/usr/bin/env bash
# One-time setup. Asks the few things that change how the workshop behaves, and
# writes workshop.json. Re-run it any time to change the answers.
set -euo pipefail
SHOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$SHOP/workshop.json"

echo "== agent-workshop setup"
echo
echo "Do all the seats run on THIS ONE computer, or across several?"
echo
echo "  1) one computer   -- seats can nudge each other directly, and mail does"
echo "                       not need a git round-trip (board.py msg --local)"
echo "  2) several        -- git is the ONLY channel between them, so mail is"
echo "                       committed and pushed, and every seat must pull"
echo
printf 'choice [1]: '; read -r c || c=1
case "${c:-1}" in 2) MACHINES=several;; *) MACHINES=one;; esac

printf 'Your name, for the human seat [%s]: ' "${USER:-you}"; read -r who || who=""
WHO="${who:-${USER:-you}}"

cat > "$CFG" <<EOF
{
  "machines": "$MACHINES",
  "human": "$WHO",
  "configured": "$(date +%Y-%m-%d)"
}
EOF
echo
echo "ok    wrote workshop.json"
echo

if [ "$MACHINES" = one ]; then
cat <<'EOF'
ONE COMPUTER. What that changes:

  * Mail between seats does not need git. Use --local, which writes it without
    committing:
        ./board.py msg --to test --frm design --local "the check is ready"

  * Seats can nudge each other directly. Two sessions open on the same machine
    can message each other by name -- ask your agent to list the other sessions
    and send to one. Use it to hand work over without waiting for a commit.

  * checkin/checkout still matter, so you can see who holds which ticket:
        ./board.py checkin  --who design --project MyThing --doing "#3"
        ./board.py checkout --who design

  * You still commit and push the WORK. Only the mail shortcut changes.
EOF
else
cat <<'EOF'
SEVERAL COMPUTERS. What that changes, and it bites if you forget:

  * GIT IS THE ONLY CHANNEL. board.py msg commits and pushes, and it fails
    loudly if it cannot -- because a message that is not pushed has not been
    sent. Do not use --local; it stays on the machine that wrote it.

  * EVERY SEAT MUST PULL BEFORE IT STARTS. An un-pulled inbox is an empty one,
    and it reads as "no messages" rather than as an error. That is why every
    start line in START.md begins with git pull.

  * A seat reads its own brief from ITS OWN checkout. A stale checkout means a
    stale brief -- or a missing one, if the role was added on the other machine.

  * Seats CANNOT nudge each other directly across machines. Hand-over is mail,
    and mail is a commit.
EOF
fi
echo
echo "Next:  ./new_project.sh MyThing \"what it is\""
