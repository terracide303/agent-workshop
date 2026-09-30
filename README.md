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

# Getting started

**Two commands. The second one asks you everything it needs.**

```sh
git clone https://github.com/terracide303/agent-workshop.git workshop
cd workshop && ./start.sh
```

That is it. `start.sh` asks your name, whether your agent sessions run on one
computer or several, and what your first project is — then creates it, puts two
cards on its board, and prints the single line you paste into an agent session to
begin.

**You need:** `git`, `python3` (any version — `board.py` is pure standard
library), and a coding agent such as Claude Code. `gh` is optional; without it
your projects are local git only.

**Clone it into a folder called `workshop`.** The name matters, because projects
sit *beside* it and every seat's start line uses `../workshop/`:

```
work/
  workshop/     <- this repo
  Blinky/       <- ../workshop/ resolves from in here
  OtherThing/
```

Run `./start.sh` again any time to add another project — it remembers your
answers and only asks about the new one.

## What happens after that

`start.sh` hands you a line like this, and tells you to open a **fresh** agent
session in the project folder and paste it:

```
You are @scout on Blinky. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/scout.md, then run ../workshop/board.py inbox --who scout and ../workshop/board.py next Blinky --who scout, and do what it says.
```

The session reads its brief, picks up card `#1`, does that one thing, commits the
work and the board move together, and **asks you to `/clear`**. Then you paste the
next seat's line — `@design` to build, `@test` to check, `@review` to read it
cold. They are all in [`START.md`](START.md).

**One ticket, one session, then clear.** A session long enough to be summarised
has swapped the real state for a summary of it, and a summary of a repository is
not a repository. Clearing is only cheap because coming back is one paste.

## Talk to @workshop. Seriously.

Every other seat lives inside one project. **@workshop is the one that sees all of
them** — the board tool, the page, the rules, the briefs, the mail between seats.
It is your friend, your interface, your partner in crime, your comrade in arms.
The one who knows where the bodies are buried, because it wrote the burial rules.

Talk to it when:

- **something in the machinery bites** — `board.py` refuses, the page is blank, a
  script is missing. Other seats will quietly work around it. @workshop fixes it,
  so the next friend who clones this does not hit it too.
- **you do not know whose job something is.** It picks the owner. That is the job.
- **a day went badly.** That is a retrospective, and a retrospective is how
  `RULES.md` grows past rule 1. No @workshop, no retrospective, no rules. Just
  vibes. Vibes do not ship.
- **you just want to ask how it is all going.** It reads every board.

Seats can write to it too:

```sh
../workshop/board.py msg --to workshop "board.py next says nothing is refined, but I refined it"
```

Start it like any other seat — its line is in [`START.md`](START.md).

**This is not optional decoration.** A workshop with no @workshop is a kitchen
where nobody ever washes up: it works great for about a week.

## One computer, or several?

**`start.sh` asks this, because it changes how the seats reach each other.**

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

- **`done` refuses to close a story with no evidence** — either the closing
  condition written after the `—`, or `--evidence` now. Not "it works": the
  measurement.
- **A feature needs `{refined}`** before its stories can be pulled — a human
  saying they are written and owned. Without it, `next` hands out nothing.
- **`next` explains its choice**, so a session never opens with "what now".

**Full reference, all 24 commands: [`docs/BOARD.md`](docs/BOARD.md).**

## Seeing the whole board at once

Optional — the command line does everything without it.

```sh
./page.sh              # serve every project's board at http://127.0.0.1:8765
./page.sh 9000         # another port, if 8765 is taken
./page.sh --build      # write index.html once and open the file instead
```

**It holds no state of its own.** It renders the `docs/PLAN.md` files, so if the
page and a plan file ever disagree, **the plan file is right.** The first render
is slow — it replays every revision of every plan file, so give it a minute before
deciding it is broken.

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
| **`@workshop`** | **the retrospective never happening** — so the rulebook stays at one rule |
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
| [`start.sh`](start.sh) | **the only file you run.** Sets up, and adds a project | first, and per project |
| [`board.py`](board.py) | the board, as a command line | daily |
| [`page.sh`](page.sh) | **the board as a web page**, optional — renders the plan files, stores nothing | when you want to see it all |
| [`skills/`](skills/) | agent skills + `install_skills.sh` — **ships one example, delete it** | when a skill earns its place |
| [`check.sh`](check.sh) | the mechanical checks — **a pattern to fill in, not a rule set** | before every commit |
| **[`docs/BOARD.md`](docs/BOARD.md)** | **the board's full reference** — every command, `{refined}`, checkers, notes | first time you move a card |

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

## What is deliberately not here

**No curated skill list.** The *machinery* is here — [`skills/`](skills/) with one
example gate, `install_skills.sh` / `install_skills.ps1` to link them into
`~/.claude/skills`, and a line in every role brief telling the seat to **name the
skills it can actually see**, because one that did not load fails silently. What
is absent is a list of which skills to use: `start.sh` writes cards asking
`@scout` to find, judge and install the ones **your** project needs. Handing you
someone else's skill list is the same mistake as handing you someone else's rules
— in the survey this came from, five candidates matched the search and four had to
be rejected for reasons no search could see.

**No rules for your domain.** [`RULES.md`](RULES.md) has one. **Your first project
runs without the rules that make an established one fast, and nothing shortcuts
that except doing the retrospectives.** A rulebook inherited from someone else's
accidents is one you will neither believe nor maintain.

**And it is not a project-management tool or an agent framework.** No database, no
daemon, and no service you have to keep running — `page.sh` is a renderer you
start when you want it and kill when you do not, and it stores nothing. Underneath
it is markdown, one Python script and a set of briefs. Remove the discipline and
what is left is a folder of files.

## Licence

MIT. Fork it, strip what does not fit, and keep your own `RULES.md` — it is the
half that is actually yours.
