# The board — the full reference

**Read this the first time you move a card, not every session.**
[`../README.md`](../README.md) has what a session needs at startup. This is the rest.

The board *is* `docs/PLAN.md` in each project. Edit it by hand or drive it from
the command line — same file either way, and a mistake fails loudly rather than
quietly corrupting the plan. Every match is by substring, and an ambiguous match
is refused.

## The format

```
## Phase 1 — a phase, in plain words
### A feature, in plain words {refined}
- [ ] #3 The story — the evidence that closes it @design +test !7 #sonnet
```

| | |
|---|---|
| `#3` | the ticket number. Stable — use it in commands and commit messages |
| `[ ]` | to do · `[~]` doing · `[x]` done · `[?]` unrefined · `[c]` needs checking · `[!]` blocked |
| `— ...` | **everything after the dash is the evidence required to tick the box** |
| `@design` | the one owner |
| `+test` | a **checker** — see below |
| `!7` | priority, 1–10 |
| `#sonnet` | overrides that role's default model |

## `{refined}` — the one that will catch you out

**A feature heading needs `{refined}` before any of its stories can be pulled.**
Without it, `board.py next` reports them as unrefined and hands out nothing.

That is deliberate: it is a human saying out loud *"these stories are written, an
owner is named, and someone could start one without asking a question."* An
unrefined story is an idea, and pulling ideas is how a queue becomes whatever the
last agent felt like doing.

```sh
board.py refine <project> "part of the story text" --who design
```

Note that `refine` on a story does not mark the **feature** — add `{refined}` to
the `###` heading yourself. (Both of us got this wrong on the first try.)

## Every command

```sh
board.py next     <project> --who <role>     # the one ticket to pick up, and WHY that one
board.py list     <project> [--who r] [--state open]
board.py health   <project>                  # what the board says about itself, arithmetic only

board.py add      <project> "story text" --phase "Phase 1" --feature "A feature" \
                  [--who design] [--model sonnet] [--evidence "what closes it"]
board.py refine   <project> "text" [--who design] [--evidence "..."]
board.py feature  <project> ...              # add a feature heading
board.py edit     <project> "text" [--text ...] [--who ...] [--evidence ...] [--model ...]
board.py renumber <project>                  # re-sequence ids after heavy editing
board.py move     <project> ...              # move a story between features
board.py idea     <project> "text"           # park a thought without scheduling it

board.py start    <project> "text"           # [ ] -> [~]
board.py check    <project> "text"           # [~] -> [c], for a story with a +checker
board.py done     <project> "text" --evidence "the measurement"   # REFUSES without evidence
board.py reopen   <project> "text"           # [x] -> [ ]
board.py park     <project> "text"           # out of the live board, kept
board.py block    <project> "text" "why"     # [!] with a reason
board.py unblock  <project> "text"
board.py checker  <project> "text" --who r   # add or change the +checker

board.py note     <project> "text" "a dated line" --who <role>
board.py msg      --to <role> --frm <role> "..." [--local] [--file -]
board.py inbox    --who <role>               # messages, AND checks the seat in
board.py checkin  --who <role> --project P --doing "#3"
board.py checkout --who <role>
board.py resume   --who <role> --project P   # prints the start line for that seat
```

**`done` refuses to close a story that has no evidence.** The evidence can be
already written into the story — everything after the `—` is the closing
condition — or supplied now with `--evidence`. What it will not accept is a
story that says nothing about how anyone would know it worked.

```sh
board.py done MyThing "the parser case"            # ok if the story states its condition
board.py done MyThing "a bare story"               # FAIL  a story closes on evidence
board.py done MyThing "a bare story" --evidence "40/40 cases, 0 failures"
```

Not "it works" — the measurement, or what you ran and what it printed.

## One owner, and someone who checks

A story has exactly **one** owner. Two owners means neither, and the
work-in-progress limit stops meaning anything.

When a second pair of eyes is genuinely needed — a reading only a human can take,
or a result nobody should believe unreviewed — that is a **checker**, written
`+role`:

```
- [ ] #8 The parser handles the malformed case — the failing input, and the output it now gives @design +test
```

The owner does the work and moves it to **check**; the checker confirms it and
moves it to **done**. **A story with a checker cannot go straight to done.** That
is the mechanism behind `@review` and `@test` being separate seats — it makes the
separation structural instead of a good intention.

## Notes — a pointer, not a transcript

```sh
board.py note <project> "part of the text" \
  "round 4 run, 3 of 40 cases still failing -> docs/FINDINGS.md" --who test
```

Lands as `- 2026-09-26 @test: ...` under the story.

**Say what happened and where the detail is.** The finding itself belongs in a
document; the ticket points at it. A plan file that grows into a second logbook
is duplication, and duplication goes stale in one of its two copies.

Use it for: why something is on hold beyond the one-line reason, what was tried
and did not work, where the output landed, and what the next session needs to
know before picking the ticket up.

## Who keeps the board

With four seats and a handful of tickets: **you do.** `board.py health` is
arithmetic and costs nothing — run it when the board feels stale.

At about five live tickets, turn on **`@scrum`** (it is in `roles.json`, marked
optional). It runs `health`, chases holds, parks what is not moving and sends
unrefined work back. **It decides nothing about the work** — not priority, which
is yours, and not whether evidence convinces, which is `@review`'s. It notices
that nobody has decided, and says so on the ticket.

## Who assigns

**Nobody assigns work to themselves out of the backlog without refining it
first.** Refining includes naming the owner — picking who does it is part of
deciding that it is ready.

**Anyone may add an unassigned ticket.** Writing it down beats getting it right;
it waits in the backlog for refinement.

**Priority is the human's, and the human's word is final.** Say your reasoning
once, on the ticket, then it is settled.

## Board edits are not committed

`board.py` changes the file and stops. **You commit the board move together with
the work it describes**, in one commit, so the history shows why the card moved.

Mail is the one exception: `msg` commits and pushes by itself, because git is the
only route to another machine and a message that was not pushed was not sent. On
a single machine, `--local` skips that.
