# agent-workshop

**A way of working with coding agents that does not lose the thread.** Tickets
live in a markdown file, every seat has one job and a list of things it must not
do, and nothing closes without evidence.

It came out of a year of FPGA and PCB projects where the expensive failures were
never *"the agent could not write the code."* They were: building something that
already existed, testing what we already believed, trusting a check that was not
checking, and a decision taken on Monday still being wrong in a document on
Friday. **Every rule here exists because one of those cost a day.**

> **This ships with almost no rules, and that is the point.** See
> [`RULES.md`](RULES.md). The rules that make a workshop fast have to cost *you*
> something first. What ships is the machinery and the ritual that grows them.

---

## Start in three commands

```sh
git clone https://github.com/<you>/agent-workshop.git workshop
cd workshop
./setup.sh                              # asks two questions, once
./new_project.sh MyThing "what it is"
```

`new_project.sh` runs `setup.sh` for you if you skip it.

It asks what kind of project it is, then creates `../MyThing` beside the
workshop, with a board, a live-state page, a decisions log, a git repo, and
**two cards already on it**:

- `#1` **find and judge the working examples** → `@scout`
- `#2` **what must this do, and how will we know** → you

Then it prints the line that starts your first session. That layout matters:
projects sit **beside** the workshop, so `../workshop/` resolves from inside any
of them.

```
dhs-agent/
  workshop/     <- this repo
  MyThing/      <- ../workshop/ resolves from in here
  OtherThing/
```

---

## How to start an agent

Every seat starts the same way. Open a fresh session **inside the project
folder** and paste one line:

```
You are @scout on MyThing. Run `git pull` in both this project and ../workshop
first, then read ../workshop/roles/scout.md, then run ../workshop/board.py inbox
--who scout and ../workshop/board.py next MyThing --who scout, and do what it says.
```

Swap `scout` for `design`, `test` or `review`. All the lines are in
[`START.md`](START.md).

**Why the line is shaped like that:**

- **`git pull` first**, because the session reads its brief from *its own*
  checkout. A stale checkout gives a stale brief — or none at all.
- **`inbox`** delivers messages from you *and checks the seat in*, so you can see
  who is working on what.
- **`next`** hands it exactly one ticket and says **why that one**.

Then: it does the one thing, commits the work and the board move together,
pushes, and **asks you to `/clear`**. One ticket, one session. A session long
enough to be summarised has swapped the real state for a summary of it.

---

## One computer, or several?

**`setup.sh` asks this first, because it changes how the seats reach each other.**

**One computer** — seats can nudge each other directly. Two sessions open on the
same machine can message each other by name, so a hand-over does not wait for a
commit. Mail skips git entirely:

```sh
./board.py msg --to test --frm design --local "the check is ready"
```

**Several computers** — **git is the only channel.** `board.py msg` commits and
pushes, and fails loudly when it cannot, because a message that was not pushed
was not sent. Every seat must `git pull` before it starts: an un-pulled inbox is
an empty one, and it reports *"no messages"* rather than an error. Seats cannot
nudge each other across machines — hand-over is mail, and mail is a commit.

Either way, use `checkin` so you can see who holds which ticket:

```sh
./board.py checkin  --who design --project MyThing --doing "#3"
./board.py checkout --who design
```

---

## The board

Tickets are lines in `docs/PLAN.md`. Edit them by hand or drive them from the
command line — same file either way.

```sh
../workshop/board.py next   MyThing --who design    # what to pick up, and why
../workshop/board.py start  MyThing "part of the text"
../workshop/board.py done   MyThing "part of the text" --evidence "the measurement"
../workshop/board.py health MyThing                 # what the board says about itself
```

```
## Phase 1 — the thing works
### A feature, in plain words {refined}
- [ ] The story — the evidence that closes it @design
```

`[ ]` to do · `[~]` doing · `[x]` done · `[?]` unrefined · `[c]` needs checking

Three properties do the real work:

- **`done` refuses without evidence.** Not "it works" — the measurement.
- **Unrefined work cannot be pulled.** A story with no owner and no closing
  condition is not ready, and `{refined}` is a human saying so out loud.
- **`next` explains its choice**, so a session never opens with "what now".

---

## The seats, and why these ones

**They are split by what goes wrong when one seat does two jobs — not by skill.**
That is the whole idea. "Designer, Coder, Tester" is a skill split, and a coder
who also tests writes tests that pass.

| seat | exists to prevent |
|---|---|
| **`@scout`** | building what already exists |
| **`@design`** | typing before deciding |
| **`@test`** | the author testing what they already believe |
| **`@review`** | the author judging their own evidence |
| **you** | scope drifting to whatever is interesting |

Two more are defined but off by default — add them when they earn it:
**`@build`** once there is CI worth reporting, **`@scrum`** at about five live
tickets.

**Each brief's most important section is "what you never do."** A brief that
only lists responsibilities is a job title. One that lists prohibitions is a
check. `@test` may not fix what it tests; `@review` may not be told the answer
first; `@build` may not re-open the design decision.

---

## The files

| file | what it is | when to read it |
|---|---|---|
| **[`RULES.md`](RULES.md)** | **the rulebook.** Ships with one rule; grows by retrospective | every session |
| **[`SOURCES.md`](SOURCES.md)** | where answers come from, and the one question that decides which end of the ladder you start at | before answering anything |
| **[`CATALOGUE.md`](CATALOGUE.md)** | what already exists and whether to use it — **including the rejections and their reasons** | before writing anything |
| **[`RETROSPECTIVE.md`](RETROSPECTIVE.md)** | **the ritual that fills `RULES.md`.** This is the actual product | end of every phase |
| **[`START.md`](START.md)** | the line that starts or resumes each seat | coming back after a clear |
| [`roles/`](roles/) | one brief per seat: what it owns, what it never does | your own, every session |
| [`board.py`](board.py) | the board, as a command line | daily |
| [`check.sh`](check.sh) | the mechanical checks — **a pattern to fill in, not a rule set** | before every commit |
| [`new_project.sh`](new_project.sh) | start a project with all of the above in place | once per project |

---

## The four ideas, if you read nothing else

**1. Look at the working example before you invent anything.** Rule 1, and the
only rule that ships. Every answer that came from a source was right; most that
came from reasoning were wrong.

**2. A check that has never failed has not been tested.** Run it against
something broken and confirm it says so. A checker in the original project
printed *"all mechanical checks passed"* for a day with three of its checks dead
inside an unterminated `echo`. It was not checking. It was reporting.

**3. One source of truth, and generate the rest.** Any number that appears in two
places is two places to be wrong. A hand-maintained summary of a machine-readable
file goes stale silently — one such table was wrong in five rows at once and
looked correct because the errors cancelled.

**4. Evidence, or it did not happen.** "Verified" with no measurement behind it
is the most expensive sentence in a repository.

---

## What this is not

**Not a project-management tool, and not an agent framework.** There is no
server, no database and no daemon — it is markdown, a Python script and a set of
briefs. If you remove the discipline, what is left is a folder of files.

**Not a substitute for knowing your own domain.** It ships with no domain rules
on purpose. Your first project runs without the rules that make it fast, and
nothing can shortcut that except doing the retrospectives.

## Licence

MIT. Fork it, strip what does not fit, and keep your own `RULES.md` — it is the
half that is actually yours.
