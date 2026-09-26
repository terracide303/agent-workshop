#!/usr/bin/env bash
# ./start.sh  --  the only file you need to run. Ask it nothing; it asks you.
#
# First run: sets up the workshop and creates your first project.
# Later runs: just creates another project -- it remembers the rest.
#
# Everything it does is reversible: it writes workshop.json here, and creates one
# new directory beside this one. It never touches an existing project.
set -euo pipefail
SHOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SHOP")"
CFG="$SHOP/workshop.json"
TODAY="$(date +%Y-%m-%d)"

ask() {  # ask "prompt" "default" -> echoes the answer
    local p="$1" d="${2:-}" a=""
    if [ -n "$d" ]; then printf '%s [%s]: ' "$p" "$d" >&2; else printf '%s: ' "$p" >&2; fi
    read -r a || a=""
    printf '%s' "${a:-$d}"
}

echo
echo "  agent-workshop"
echo "  ─────────────────────────────────────────────────────────────"
echo

# ── things we only need once ──────────────────────────────────────────────────
if [ ! -f "$CFG" ]; then
    echo "  First run. Three questions, then it is set up for good."
    echo

    HUMAN="$(ask '  Your name (for the human seat)' "${USER:-you}")"
    echo
    echo "  Do all the agent sessions run on THIS ONE computer, or across several?"
    echo
    echo "    1) one computer  — they can nudge each other directly, and mail"
    echo "                       between them skips git entirely"
    echo "    2) several       — git is the ONLY channel, so mail is committed and"
    echo "                       pushed, and every seat must pull before it starts"
    echo
    case "$(ask '  choice' 1)" in 2) MACHINES=several;; *) MACHINES=one;; esac
    echo
    USEGH=no
    if command -v gh >/dev/null 2>&1; then
        case "$(ask '  Create GitHub repos for your projects automatically? (y/n)' y)" in
            [Nn]*) USEGH=no;; *) USEGH=yes;;
        esac
    else
        echo "  (gh not installed, so projects stay local git only — that is fine)"
    fi

    cat > "$CFG" <<EOF
{
  "human": "$HUMAN",
  "machines": "$MACHINES",
  "use_gh": "$USEGH",
  "configured": "$TODAY"
}
EOF
    echo
    echo "  ok — saved. Re-run this file any time to change it or add a project."
    echo
    if [ "$MACHINES" = one ]; then
        cat <<'EOF'
  ONE COMPUTER, so:
    · mail between seats needs no commit:
        ./board.py msg --to test --frm design --local "the check is ready"
    · two sessions open at once can nudge each other by name — useful for a
      hand-over that should not wait for a push
    · you still commit and push the WORK; only the mail shortcut changes
EOF
    else
        cat <<'EOF'
  SEVERAL COMPUTERS, so — and this bites if you forget:
    · GIT IS THE ONLY CHANNEL. ./board.py msg commits and pushes, and fails
      loudly if it cannot, because a message that was not pushed was not sent
    · EVERY SEAT MUST PULL FIRST. An un-pulled inbox is an empty one, and it
      says "no messages" rather than giving an error
    · a seat reads its brief from ITS OWN checkout, so a stale checkout means a
      stale brief — or none at all
    · seats cannot nudge each other across machines; hand-over is mail
EOF
    fi
    echo
else
    HUMAN="$(python3 -c 'import json;print(json.load(open("'"$CFG"'"))["human"])' 2>/dev/null || echo you)"
    USEGH="$(python3 -c 'import json;print(json.load(open("'"$CFG"'")).get("use_gh","no"))' 2>/dev/null || echo no)"
    echo "  Set up already, $HUMAN. Let us add a project."
    echo
fi

# ── the project ───────────────────────────────────────────────────────────────
NAME=""
while [ -z "$NAME" ]; do
    NAME="$(ask '  Project name (one word, no spaces)' '')"
    case "$NAME" in
        "")            echo "  needs a name.";;
        *[!A-Za-z0-9_-]*) echo "  letters, digits, - and _ only."; NAME="";;
        *) if [ -e "$ROOT/$NAME" ]; then echo "  $ROOT/$NAME already exists — pick another."; NAME=""; fi;;
    esac
done
SUBTITLE="$(ask '  One line: what is it' "$NAME")"
echo
echo "  What kind of project?"
echo "    1) software   a program, a library, a service"
echo "    2) pcb        a circuit board"
echo "    3) fpga       an FPGA core or port"
echo "    4) other      just the board and the four seats"
case "$(ask '  choice' 1)" in 2) KIND=pcb;; 3) KIND=fpga;; 4) KIND=other;; *) KIND=software;; esac

DEST="$ROOT/$NAME"
echo
echo "  Creating $DEST …"
mkdir -p "$DEST/docs"
cd "$DEST"

cat > README.md <<EOF
# $NAME

$SUBTITLE

Worked with the [agent-workshop](../workshop/README.md) method: one ticket per
session, evidence required to close, and the rules in
[\`../workshop/RULES.md\`](../workshop/RULES.md).

- **\`RESUME_HERE.md\`** — the live state. Read it first.
- **\`docs/PLAN.md\`** — the board.
EOF

cat > RESUME_HERE.md <<EOF
# RESUME HERE — $TODAY

**One page. The live state. Every claim carries how it was measured.**
If a detail is not here, it is history, not current truth.

## Read these first — they do not decay

1. **This project is new.** Nothing is built and nothing is proven.
2. **The rules are in \`../workshop/RULES.md\`** and there is currently one. They
   grow by retrospective, not by having good ideas.

## Where we stand

Nothing yet. The first card is the survey of what already exists.

## Next action

\`../workshop/board.py next $NAME --who scout\`
EOF

cat > docs/PLAN.md <<EOF
# Plan — $NAME

**Phase → Feature → Story. A story closes on evidence, never on opinion.**

\`\`\`
### A feature, in plain words {refined}
- [ ] The story — what closes it @role #model
\`\`\`

\`@role\` assigns it (see \`../workshop/roles.json\`), \`#model\` overrides that
role's default model, and everything after the dash is the evidence required to
tick the box. **Unticked and unevidenced are the same thing.** Full reference:
\`../workshop/docs/BOARD.md\`.

---

## Phase 0 — Know what exists before writing anything

### The ground is surveyed {refined}
- [ ] #1 The working examples for a $KIND project are found and judged — at least three candidates read (not just their READMEs), each with licence, maturity, what it is proven on and **what it does not do**; verdict recorded in \`../workshop/CATALOGUE.md\`; ends in use-it / adapt-it / write-our-own, with a reason @scout
  **This is rule 1 as the first card.** Something already does most of this and works. Find it before inventing a worse one.
- [ ] #2 The one thing this project must do is written down, with how we will know it works — one paragraph, and a measurement @you
  Not a feature list. The single outcome that makes it worth doing, and the observation that would prove it.
EOF

cat > docs/DECISIONS.md <<EOF
# Decisions

**Dated, with the reason. A decision without its reason gets re-litigated.**
Record reversals too — they are the most useful kind of entry.

## $TODAY — project started
Kind: $KIND. Nothing else decided yet.
EOF

git init -q .
git add -A
git commit -q -m "Start $NAME: the board, the live-state page, and the first two cards

Card #1 is the survey, assigned to @scout: find and JUDGE what already exists
before anything is written. That is rule 1 as the first thing on the board.
Card #2 is the human's: what must this do, and how will we know."

echo "  ok — created and committed."
if [ "${USEGH:-no}" = yes ] && command -v gh >/dev/null 2>&1; then
    if gh repo create "$NAME" --private --source=. --remote=origin --push >/dev/null 2>&1; then
        echo "  ok — pushed to GitHub (private)."
    else
        echo "  note — no GitHub repo made. To do it yourself:"
        echo "         gh repo create $NAME --private --source=. --remote=origin --push"
    fi
fi

cat <<EOF

  ─────────────────────────────────────────────────────────────
  DONE. Now start your first agent.

  1.  cd $DEST
  2.  open a FRESH agent session in that folder
  3.  paste exactly this, and nothing else:

You are @scout on $NAME. Run \`git pull\` in both this project and ../workshop first, then read ../workshop/roles/scout.md, then run ../workshop/board.py inbox --who scout and ../workshop/board.py next $NAME --who scout, and do what it says.

  It will read its brief, pick up card #1, do it, commit the work and the board
  move together, and ask you to /clear. Then paste the next seat's line —
  they are all in ../workshop/START.md, or run:

      ./board.py resume --who design --project $NAME

  ONE TICKET, ONE SESSION, THEN CLEAR. A session long enough to be summarised
  has swapped the real state for a summary of it.

  Your rules file has ONE rule, and that is correct — see ../workshop/RULES.md.
  It fills up by retrospective, and that is the mechanism that makes your second
  project faster than your first.
  ─────────────────────────────────────────────────────────────

EOF
