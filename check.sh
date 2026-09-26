#!/bin/sh
# The mechanical half of the rules, as a script. Run it before every commit.
#
# THIS SHIPS ALMOST EMPTY ON PURPOSE. It is a PATTERN, not a rule set -- what to
# check depends entirely on your project, and a check copied from someone else's
# project is a check nobody here believes.
#
# THE TWO THINGS THE PATTERN IS FOR:
#
#   1. FAIL LOUDLY. A check that prints a warning gets ignored. Exit non-zero.
#   2. A CHECK THAT HAS NEVER FAILED HAS NOT BEEN TESTED. Every check below must
#      have a case in --selftest that makes it fire. Run ./check.sh --selftest
#      whenever you add one.
#
# The incident behind rule 2: a checker in the project this came from printed
# "all mechanical checks passed" for a DAY while three of its checks sat dead
# inside an unterminated echo. It was not checking. It was reporting.
set -eu
FAIL=0
say() { printf '%s\n' "$*"; }
bad() { say "FAIL  $*"; FAIL=1; }
ok()  { say "ok    $*"; }

# ---- checks -----------------------------------------------------------------
# Replace this example with your own. Keep the shape: a condition, a loud
# failure, and a matching selftest case below.

check_no_todo_in_committed_docs() {
    hits=$(git grep -ln 'FIXME(urgent)' -- '*.md' 2>/dev/null || true)
    if [ -n "$hits" ]; then
        bad "FIXME(urgent) left in committed docs: $hits"
    else
        ok "no FIXME(urgent) markers in committed docs"
    fi
}

# ---- selftest ---------------------------------------------------------------
# Each check gets a case here that MAKES IT FIRE. If a check cannot be made to
# fail, you do not know that it works.
selftest() {
    say "SELFTEST -- every line must say CAUGHT"
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    ( cd "$tmp" && git init -q . && printf 'FIXME(urgent) x\n' > a.md && git add a.md &&
      out=$(FAIL=0; hits=$(git grep -ln 'FIXME(urgent)' -- '*.md' || true)
            [ -n "$hits" ] && echo fired)
      if [ "$out" = fired ]; then say "  CAUGHT  FIXME(urgent) in a committed doc"
      else say "  MISSED  FIXME(urgent) in a committed doc"; exit 1; fi )
    say ""
    say "selftest passed: every check fires when it should."
}

if [ "${1:-}" = "--selftest" ]; then selftest; exit 0; fi

say "== check.sh =="
check_no_todo_in_committed_docs
say ""
[ "$FAIL" = 0 ] || { say "SOMETHING FAILED -- do not commit until it is fixed or explained."; exit 1; }
say "all mechanical checks passed"
say ""
say "THE JUDGEMENT HALF -- no script can check these. Answer them in the commit:"
say "  1. Which rung of SOURCES.md answered this? If the answer is 'I built it"
say "     to find out', go back down."
say "  2. What does your check FAIL on? A check that only passes is untested."
say "  3. What is generated, and what did someone type twice?"
say "  4. What would prove me wrong? If nothing would, it is not a plan."
