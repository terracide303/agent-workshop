# Catalogue — what already exists, and whether we should use it

**0 entries, started 2026-09-26.**

**`@scout` fills this in. Read it before writing anything.** The point is that a
survey happens **once per domain, not once per project** — and that the
rejections are recorded, so nobody re-runs a search that already has an answer.

## The format

| thing | licence | size | what it does | verdict, and why |
|---|---|---|---|---|
| | | | | |

**Every row needs a verdict, and a rejection needs its reason.** "Not suitable"
is not a reason. "Its rules forbid the package we are using" is.

## Why the rejections are the valuable half

A real example from the project this method came from. Five candidate tool
repositories were surveyed for one job. Four had to be rejected, and **not one of
the reasons was visible from a search**:

- one **explicitly forbade the component package the board used** — it matched the
  search terms perfectly
- one shipped a second ticket tracker that collided with this board.py
- one's impressive benchmarks were all published by the company selling it, with
  no independent reproduction
- one only worked on projects that did not exist yet

**A keyword search would have installed all five.** That is why this file is
written by a seat that reads code, and why a verdict is required rather than
optional.

## Adding an entry

A thing earns a row by being **tried**, not by looking good. Record the licence,
the size, what it actually did, and what it does **not** do — and if it is
rejected, the reason, in enough detail that the next person does not have to
check for themselves.
