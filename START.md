# START HERE — the line that starts or resumes a seat

**Open this on the machine you are working on and copy the line you need.** Every
seat starts the same way, so coming back after a `/clear` is one paste and never a
reconstruction of what you were doing.

Replace `MyThing` with your project. Run the line from **inside the project
folder**, which sits beside the workshop.

**Every line begins with `git pull`, and it is load-bearing.** The line tells the
session to read its brief — and it reads that from *its own* checkout. A stale
checkout gives a stale brief, or none at all if the role was added elsewhere.
`board.py inbox` has the same problem: mail travels by git, so an un-pulled inbox
is an empty one, and it reports *"no messages"* rather than an error.

## @scout — finds what already exists, before anything is written

```
You are @scout on MyThing. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/scout.md, then run ../workshop/board.py inbox --who scout and ../workshop/board.py next MyThing --who scout, and do what it says.
```

## @design — decides what to change, and implements it

```
You are @design on MyThing. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/design.md, then run ../workshop/board.py inbox --who design and ../workshop/board.py next MyThing --who design, and do what it says.
```

## @test — writes the check, and says what it does NOT prove

```
You are @test on MyThing. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/test.md, then run ../workshop/board.py inbox --who test and ../workshop/board.py next MyThing --who test, and do what it says.
```

## @review — reads it cold and says what the evidence does not support

```
You are @review on MyThing. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/review.md, then run ../workshop/board.py inbox --who review and ../workshop/board.py next MyThing --who review, and do what it says.
```

## @workshop — owns the shared machinery, and runs the retrospective

```
You are @workshop on MyThing. Run `git pull` in both this project and ../workshop first, then read ../workshop/roles/workshop.md, then run ../workshop/board.py inbox --who workshop and ../workshop/board.py next MyThing --who workshop, and do what it says.
```

**This is the seat that makes the rulebook grow.** Without it the retrospective
never runs, `RULES.md` stays at one rule, and the point of the whole thing is
lost. Give it a session at the end of every phase.

**Do not brief `@review` yourself.** Paste the line and nothing else. The moment
you explain what you meant, it is no longer reading cold and the seat is worthless.

---

## Setting up a machine

**Clone from GitHub into one folder, as siblings.** Every line above assumes the
project sits beside the workshop.

```sh
mkdir -p ~/work && cd ~/work
git clone https://github.com/terracide303/agent-workshop.git workshop
cd workshop && ./start.sh
```

`start.sh` is the only file you run. It asks what it needs, creates the project
beside the workshop, and prints the line to paste. Run it again to add another.

```
work/
  workshop/     <- this repo
  MyThing/      <- ../workshop/ resolves from in here
```

**Do not work from a copy on a drive that might not be mounted.** Git is the
source; a machine that depends on a mounted volume stops working when it is not.

If `board.py` says *Permission denied*, the exec bits did not survive: `chmod +x
workshop/*.py workshop/*.sh`.

---

## What every seat does first

1. **`git pull`** — in the project and in the workshop.
2. Read **`../workshop/RULES.md`**, then its own brief in
   [`roles/`](roles/) — what it owns and, more importantly, what it never does.
3. **`board.py inbox --who <role>`** — messages from you. Reading it checks the
   seat in, so you can see who holds what.
4. **`board.py next <project> --who <role>`** — the one ticket to pick up, and
   why that one.
5. **One ticket, one session.** Commit the work and the board move together,
   push, then ask for a clear and stop.

## Why one ticket per session

A session long enough to be summarised has swapped the real state for a summary
of it — and a summary of a repository is not a repository. Clearing is only cheap
if coming back is one paste, which is the whole reason this file exists.

Ask for the clear early if you catch yourself re-reading a file or re-deriving
something already settled. The repo holds the state; the conversation does not
need to.
