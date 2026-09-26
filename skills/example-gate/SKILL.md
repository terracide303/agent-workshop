---
name: example-gate
description: AN EXAMPLE, delete it. The shape of a gate skill — use BEFORE any slow, costly or hard-to-undo action (a deploy, a fab order, a migration, a long run). Enforces the cheap rungs first and names what the check must fail on.
---

# EXAMPLE — delete this skill once you have written your own

**This is here to show the shape, not to be used.** It is not your gate, and a
gate you did not earn is one you will route around. See
[`../README.md`](../README.md).

Replace "the expensive thing" below with the action that actually costs you:
shipping to production, ordering a board, running a four-hour job, migrating a
database, sending something to a customer.

---

# The gate — the expensive thing is the LAST resort

**Who this is for:** whoever decides *whether* to do it — not whoever carries it
out. If you are carrying it out, the decision was made by whoever wrote the
ticket; your job is to do exactly that and report what happened.

## The ladder. Climb it in order, and say which rung answered you

```
1  THE DOCUMENTATION      does the manual, spec or changelog already say?
2  THE WORKING REFERENCE  does something that already works do this?
3  A CHEAP LOCAL CHECK    can a test, a dry run or a smaller case answer it?
4  THE EXPENSIVE THING    only now, and say why 1-3 could not
```

**A rung you skipped is a rung you will pay for.** The three above the last one
cost minutes. The last one costs whatever it costs, and you find out afterwards.

## Answer these out loud, then put them in the commit

1. **Which rung answered this?** If the answer is *"I did the expensive thing to
   find out"*, go back down.
2. **What kind of question is this?** *How does this work* → read something.
   *Did OUR thing actually happen* → measure something. Getting these backwards
   wastes the effort either way.
3. **What does your check FAIL on?** Name it. A check that only passes has not
   been tested — run it against something you know is broken and confirm it says
   so.
4. **Enumerate every result this can produce, and what each one means.** If any
   outcome means two things, it is not finished. Add the bit that separates them.
5. **What would prove me wrong?** If nothing would, it is not a plan.

## What stays human

The decision to spend money, the decision to ship, and reading the result. An
agent can prepare all three and should not perform any of them.
