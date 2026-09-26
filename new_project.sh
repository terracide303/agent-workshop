#!/usr/bin/env bash
# Start a new project with the board, the roles and the documents already in place.
#
#   ./new_project.sh MyThing "what it is" [--kind software|pcb|fpga] [--private] [--no-push]
#
# Creates ../MyThing beside this workshop, so ../workshop/ resolves from inside it.
# Refuses if it already exists.
#
# WHAT IT DOES NOT DO: pick your skills for you. It writes ticket #1 asking
# @scout to find and JUDGE them, because the judging is the part that matters --
# see CATALOGUE.md for five candidates that all matched a keyword search and four
# of which had to be rejected for reasons no search could see.
set -euo pipefail
SHOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SHOP")"

NAME="${1:-}"; shift || true
SUBTITLE="${1:-}"; case "${SUBTITLE:-}" in --*) SUBTITLE="";; *) shift || true;; esac
KIND=""; VIS="--private"; PUSH=1
while [ $# -gt 0 ]; do
    case "$1" in
        --kind)    KIND="$2"; shift 2;;
        --public)  VIS="--public"; shift;;
        --private) VIS="--private"; shift;;
        --no-push) PUSH=0; shift;;
        *) echo "unknown option: $1" >&2; exit 2;;
    esac
done
[ -n "$NAME" ] || { echo "usage: new_project.sh <Name> [\"subtitle\"] [--kind K] [--public] [--no-push]" >&2; exit 2; }

[ -f "$SHOP/workshop.json" ] || { echo "First run -- setting up the workshop."; "$SHOP/setup.sh"; echo; }

if [ -z "$KIND" ]; then
    echo "What kind of project is this?"
    echo "  1) software   a program, a library, a service"
    echo "  2) pcb        a circuit board"
    echo "  3) fpga       an FPGA core or port"
    echo "  4) other      just the board and the four seats"
    printf 'choice [1]: '; read -r c || c=1
    case "${c:-1}" in 1|"") KIND=software;; 2) KIND=pcb;; 3) KIND=fpga;; *) KIND=other;; esac
fi

DEST="$ROOT/$NAME"
[ -e "$DEST" ] && { echo "FAIL  $DEST already exists." >&2; exit 1; }
[ -n "$SUBTITLE" ] || SUBTITLE="$NAME"
TODAY="$(date +%Y-%m-%d)"

echo "== new $KIND project: $NAME"
mkdir -p "$DEST/docs"
cd "$DEST"

cat > README.md <<EOF
# $NAME

$SUBTITLE

Worked with the [agent-workshop](../workshop/README.md) method: one ticket per
session, evidence required to close, and the rules in
[\`../workshop/RULES.md\`](../workshop/RULES.md).

- **\`RESUME_HERE.md\`** — the live state. Read it first.
- **\`docs/PLAN.md\`** — the board. Phase → Feature → Story.
EOF

cat > RESUME_HERE.md <<EOF
# RESUME HERE — $TODAY

**One page. The live state. Every claim carries how it was measured.**
If a detail is not here, it is history, not current truth.

## Read these first — they do not decay

1. **This project is new.** Nothing is built and nothing is proven.
2. **The rules are in \`../workshop/RULES.md\`.** They grow by retrospective, not
   by having good ideas.

## Where we stand

Nothing yet. The board's first card is the skills survey.

## Next action

\`../workshop/board.py next $NAME --who scout\`
EOF

cat > docs/PLAN.md <<EOF
# Plan — $NAME

**Phase → Feature → Story. A story closes on evidence, never on opinion.**

\`\`\`
### A feature, in plain words
- [ ] The story — what closes it @role #model
\`\`\`

\`@role\` assigns it (see \`../workshop/roles.json\`), \`#model\` overrides that
role's default, and everything after the dash is the evidence required to tick
the box. **Unticked and unevidenced are the same thing.**

---

## Phase 0 — Know what exists before writing anything

### The ground is surveyed {refined}
- [ ] #1 The working examples for a $KIND project are found and judged — at least three candidates read (not just their READMEs), each with licence, maturity, what it is proven on and **what it does not do**; verdict recorded in \`../workshop/CATALOGUE.md\`; ends in use-it / adapt-it / write-our-own with a reason @scout
  **This is rule 1 as the first card.** Something already does most of this and works. The job is to find it before we invent a worse one.
- [ ] #2 The one thing this project must do is written down, with how we will know it works — one paragraph, and a measurement @you
  Not a feature list. The single outcome that makes the project worth doing, and the observation that would prove it.
EOF

cat > docs/DECISIONS.md <<EOF
# Decisions

**Dated, with the reason. A decision without its reason gets re-litigated.**
A reversal gets recorded too — it is the most useful kind of entry.

## $TODAY — project started
Kind: $KIND. Nothing else decided yet.
EOF

git init -q .
git add -A
git commit -q -m "Start $NAME: the board, the live-state page, and the first two cards

Card #1 is the skills survey, assigned to @scout: find and JUDGE the working
examples before anything is written. That is rule 1, as the first thing on the
board.

Card #2 is the human's: what must this do, and how will we know."
echo "ok    $DEST created, first commit made"

if [ "$PUSH" = 1 ] && command -v gh >/dev/null 2>&1; then
    gh repo create "$NAME" $VIS --source=. --remote=origin --push >/dev/null 2>&1 \
      && echo "ok    pushed to GitHub ($VIS)" \
      || echo "note  no GitHub repo made -- run: gh repo create $NAME $VIS --source=. --remote=origin --push"
fi

cat <<EOF

NEXT, and paste this into a fresh session from inside $DEST:

  You are @scout on $NAME. Run \`git pull\` in both this project and
  ../workshop first, then read ../workshop/roles/scout.md, then run
  ../workshop/board.py inbox --who scout and ../workshop/board.py next $NAME
  --who scout, and do what it says.

Your rules file is EMPTY except rule 1. That is correct -- see
../workshop/RULES.md. It fills up by retrospective, and that is the mechanism
that makes your second project faster than your first.
EOF
