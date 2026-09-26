# The retrospective — how the rules get better

**Run this at the end of every phase, and after any day that cost more than it
should have. Fifteen minutes. It is the only mechanism that makes your next
project faster than this one.**

**This is the actual product of this repository.** [`RULES.md`](RULES.md) ships
with one rule and [`CATALOGUE.md`](CATALOGUE.md) ships empty, because the content
has to be yours. This file is how they fill up. In the project this method came
from, every rule, every gate and every catalogue entry got there this way — **none
of it was written in advance.**

## The five questions

**1. What did we assume was working that was not?**

Every time something was switched on and assumed good, it was not. That list is
where the next bug is. → usually a new **gate** in the sequence: a thing that must
be proven before the next step is allowed.

**2. Which check lied, and how would we have caught it sooner?**

Ask what its silence could have meant. A check that reports clean may not be
checking — the most expensive version of this is a checker that passes because it
is broken, not because the thing is right. → usually a new **rule**.

**3. What did we build that already existed?**

Include the glue: taking someone's component and hand-writing the adapter around
it is where the bugs land. Ask specifically **"was the thing I built already an
option on the thing I was wrapping?"** → [`CATALOGUE.md`](CATALOGUE.md).

**4. What did we believe because a comment or a document said so?**

Comments record what someone believed at the time, not what is true now.
Documentation is one source, not the source — **working code outranks a document
that describes it.** → note it wherever the wrong belief was written down, not
just in the rules.

**5. What did we revert, and which constraint did it violate?**

A revert throws away the broken behaviour *and* whatever the fix got right. Write
the specific requirement it broke, in one line, in the revert commit — otherwise
the same thing flip-flops between two half-right versions forever.

## Where each answer goes

| kind of lesson | goes in |
|---|---|
| a rule for while you are working | [`RULES.md`](RULES.md) |
| a gate — something that must be proven before the next step | [`RULES.md`](RULES.md), as a sequence rule |
| a reusable thing, with its licence and what it does not do | [`CATALOGUE.md`](CATALOGUE.md) |
| which source answers which kind of question | [`SOURCES.md`](SOURCES.md) |
| a mechanical check | [`check.sh`](check.sh) — **with a selftest case** |
| project-specific | that project's `docs/` |

## The bar

**If it cost more than one cycle of work, it goes in. If it cost less, it
probably does not** — a rulebook nobody finishes reading protects nobody.

**Write the evidence, not just the rule.** A rule without its incident is
indistinguishable from an opinion, and the next person deletes it. Compare:

- *"Prefer clear signals over fast ones"* — forgettable, and sounds like taste.
- *"A bit toggling at 43 MHz looks dim, not blinking, and was nearly read as a
  dead system"* — nobody deletes that.

**And when you add, ask what comes out.** The rulebook this came from reached 39
rules and had to be tiered before anyone could read it. A rulebook too large to
maintain cannot propagate its own corrections — a retracted false premise sat in
a live document for a day because the surface was too big to sweep.

## Log

**Yours starts empty. Add a row every time you run this.**

| Date | Project | Lesson | Landed in |
|---|---|---|---|
| | | | |

### Three rows from the original project, as examples of the shape

**These are not your lessons — delete them once you have your own.** They are
here because the format is easier to copy than to describe.

| Date | Project | Lesson | Landed in |
|---|---|---|---|
| 2026-08-30 | *(original)* | `grep -c 'class="error"'` counted **0** on a build with **31** errors — the tool wrote `class = "error"`, with spaces | rule: a check that reports clean may not be checking |
| 2026-08-31 | *(original)* | **five rounds of bugs, all inside a hand-written adapter around a borrowed component — the feature we needed was already a parameter on it** | catalogue: read the thing's own options before wrapping it |
| 2026-08-31 | *(original)* | the process hung in a verify step **the reference implementation does not have.** We invented the step, and the step was the bug | rule 1: ask whether the original even has what you are adding |

Notice what all three have in common: **a number, or a specific thing that
happened.** That is what makes a lesson survive being read by someone who was not
there — including you, in four months.
