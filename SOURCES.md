# Where answers come from

**The ladder, and the one question that decides which end of it you start at.**

## First, sort the question

| the question | where it goes |
|---|---|
| **"How does this work?" "What should this do?" "Does this step exist?"** | **climb the ladder** — read something |
| **"Did OUR thing actually happen?"** | **straight to an instrument** — measure something |

**Getting these backwards wastes effort in both directions.** Reading a reference
implementation cannot tell you whether your code did what you think it did; no
amount of documentation answers it. And building an instrument to answer a
question the manual already settles is a day spent proving something that was
written down.

**Say which kind you are answering, and say where the answer came from.**

## The ladder, for design questions

Climb it in order. Each rung is cheaper than the one below it, and stopping early
is the point.

```
1  the thing's own documentation      the manual, the spec, the datasheet
2  the working reference              the upstream project, the vendor's sample
3  the author's own integration       how the library's author uses their library
4  something shipping in our context  a project on the same stack, same constraints
5  YOUR OWN REASONING, labelled       last, and named as reasoning when used
```

**Rung 5 is legitimate and it is last.** In the project this came from, every
answer that came from a source turned out right, and most that came from reasoning
turned out wrong. The reasoning that got caught in time was the reasoning that had
been labelled as such.

## For did-it-happen questions

An instrument, and it needs two properties:

1. **A self-check.** If it reads nothing, how many things could that mean? More
   than one, and add the bit that separates them.
2. **Every outcome enumerated.** Write out each result it can produce and what
   each one means. If any outcome means two things, it is not finished.

**A check that reports clean may not be checking.** Run it against something
known broken and confirm it fails.
