# Skills

**This ships empty. That is the shipped state, not an oversight.**

A skill is a set of instructions your agent loads when a particular kind of work
comes up — a gate to pass before an expensive action, a checklist for a review, a
procedure that has to happen in a fixed order. Like [`../RULES.md`](../RULES.md),
they are only worth having when they came from something that cost you.

## Installing

```sh
./install_skills.sh          # macOS / Linux
.\install_skills.ps1         # Windows
```

Symlinks (junctions on Windows) into `~/.claude/skills`, so this repo stays the
one source and an edit here is live everywhere.

**Two things that will catch you out:**

1. **Skills load when a session STARTS.** The session you run the installer in
   will not see them. Start a new one.
2. **A skill that did not load fails silently.** The session works normally and
   quietly lacks the thing you added it for. **That is why every role brief says
   to name the skills you can actually see, first thing.** Do not assume.

## Where skills come from

Card `#1` on every new project asks `@scout` to survey what exists and record a
verdict in [`../CATALOGUE.md`](../CATALOGUE.md). Some of what it finds will be
third-party skill collections; some of what you need will be yours, written after
a retrospective.

**Third-party skills propose. Your checks verify.** In the survey this method came
from, five candidate skill collections matched the search and **four had to be
rejected** — one forbade the component package the project used, one shipped a
rival ticket tracker, one's benchmarks were self-published, one only worked on
projects that did not exist. A keyword search would have installed all five. So a
skill earns its place by being *tried*, with a verdict written down.

## The format

One directory per skill, containing `SKILL.md` with YAML frontmatter:

```
skills/
  my-skill/
    SKILL.md
```

```markdown
---
name: my-skill
description: Use BEFORE <the expensive or irreversible thing>. Says what must be true first, and what the check has to fail on.
---

# The gate — <the expensive thing> is the LAST resort

**Who this is for:** whoever decides *whether* to do it.

## The ladder. Climb it in order, and say which rung answered you

1  the documentation
2  the working reference
3  a cheap local check
4  the expensive thing   -- only now

## Answer these out loud, then put them in the commit

1. Which rung answered this? If it was "I did the expensive thing to find
   out", go back down.
2. What does your check FAIL on? A check that only passes is untested.
3. What would prove me wrong? If nothing would, it is not a plan.
```

**What makes a skill worth loading, rather than being a document nobody opens:**

- **Its `description` says WHEN to use it**, in terms of an action about to be
  taken — "before running X", "before ordering Y". That is what gets it pulled in
  at the right moment instead of never.
- **It carries the incident.** The same rule as `RULES.md`: a gate whose reason is
  invisible gets skipped by someone in a hurry.
- **It names what the check must fail on.** A gate that only ever says yes is a
  formality.

## A worked example

`example-gate/SKILL.md` is a real, minimal gate — read it for the shape, then
**delete it.** It is not your gate, and a skill you did not earn is one you will
route around.
