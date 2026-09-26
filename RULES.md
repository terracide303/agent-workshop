# The rules

**1 rule, started 2026-09-26.**

This file ships nearly empty **on purpose**. The rules that make a workshop fast
are the ones that cost you something first — and they have to cost *you*
something, not someone else. A rulebook inherited from another project's
accidents is a rulebook you do not believe and will not maintain.

**They get added by the retrospective, not by having a good idea.** See
[`RETROSPECTIVE.md`](RETROSPECTIVE.md) — that ritual is the actual mechanism, and
it is the reason this file will not stay this short.

## How a rule earns its place

1. **It cost something.** A real loss — hours, a wasted build, a wrong decision
   shipped. Not a thing that sounds prudent.
2. **It carries its incident.** The rule and the story go on the same line. A
   rule whose reason is invisible gets deleted by the next person, correctly,
   because they cannot tell it from someone's opinion.
3. **When you add, ask what comes out.** The rulebook this was extracted from
   grew to 39 rules and had to be tiered before anyone could read it. **A
   rulebook too large to maintain cannot propagate its own corrections** — a
   retracted false premise sat in a live document for a day because the surface
   was too big to sweep.

---

## 1. LOOK AT THE WORKING EXAMPLE BEFORE YOU INVENT ANYTHING

> **Something already does this and works. Find it, read it, and diff your
> version against it — before you reason about what it ought to do.**

Whatever you are building, someone has built the working version: the reference
implementation, the upstream project, the vendor's own example, the library
author's own integration of their library. Read that first. Your own reasoning
goes **last**, and gets labelled as reasoning when you use it.

**What this cost, in the project this came from:**

- **Every answer that came from a source was right. Most that came from reasoning
  were wrong.** Not most-ish — that was the measured pattern across a project's
  whole debugging history.
- **Reading is not enough; diff.** Diffing our copy of a borrowed component
  against the original found **228 changed lines** — debugging hacks from one
  session that had silently become the design a week later. Reading it had not
  caught that, twice.
- **Ask whether the original even has the step you are adding.** Twice the answer
  was no, and the invented step was exactly where the thing hung.

**And the trap inside the rule:** reusing something built for a *different*
purpose is building new, with extra steps and a misleading air of safety. A
memory controller reused from a sibling project — proven, on the same hardware —
cost four bugs and a week, because it had been written for a different processor.
The one written for the actual target passed on the first build. **So search
wide, and search your own shelf LAST:** it gets found by accident anyway, and it
is the one whose assumptions slip past unread.

### The counter-rule, and it matters as much

**This applies to design questions — "how does this work", "what should this
do", "does this step exist".**

It does **not** apply to *did-our-thing-actually-happen*. No amount of reading
the original tells you whether **your** code did what you think it did. That
question goes straight to an instrument: a test, a log, a measurement, a probe.
Getting these two backwards wastes effort in both directions — reading a
reference to answer a question only your own system can answer, or building an
instrument to answer a question the documentation already settled.

**Say which one you are answering, and where the answer came from.**
