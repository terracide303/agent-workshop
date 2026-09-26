# Board rules — the detail

**Read this the first time you move a card, not every session.**
[`README.md`](README.md) has what a session needs at startup; this is the rest.

## Who keeps the board

**`@scrum`.** Not a manager and not a meeting: it runs `board.py health`, chases
holds, parks what is not moving, sends unrefined work back to `@design`, and
escalates anything needing a person.

**It decides nothing about the work.** Not priority — that is Dennis's. Not
whether evidence convinces — that is `@review`'s. It notices that nobody has
decided, and says so on the ticket.

Everything it checks is arithmetic, which is why it is a script first and an agent
second: `board.py health <project>` prints the whole list, deterministically, for
nothing.

## Who assigns

**`@scrum` places unassigned tickets and sets the working priority, asking
`@design` who should hold it** — design knows the work, scrum makes sure it does
not sit unowned. On the workshop's own board `@workshop` does both.

**Dennis is the product owner. On priority and scope his word is final.** Scrum
sets a working order so nothing stalls; when Dennis disagrees, the number changes.
Say your reasoning once, on the ticket, then it is settled.

**Nobody assigns work to themselves out of the backlog without refining it first**
— that is how a queue becomes whatever the last agent felt like doing.

**Anyone may add an unassigned ticket** — writing it down beats getting it right.
It lands in the backlog and waits for refinement.

## Notes on a ticket — a pointer, not a transcript

Any role can write a dated line on a story:

```sh
../Workshop/board.py note <project> "part of the text" \
    "round 4 built, 44.138 MHz; capture pending -> docs/BUILD_NOTES.md" --who build
```

It lands under the ticket as `- 2026-09-02 @build: ...` and shows on the card.

**Say what happened and where the detail is.** The finding itself belongs in
`docs/BUILD_NOTES.md`, `docs/SIM_NOTES.md` or the live-state page — the ticket
points at it. A plan file that grows into a second logbook is the duplication this
workshop already paid for once.

Use it for: why something is on hold beyond the one-line reason, what was tried
and did not work, where a capture or a report landed, and what the next session
needs to know before it picks the ticket up.

## One owner, and someone who checks

A story has exactly **one** owner, `@role`. Two owners means neither, and the
work-in-progress limit stops meaning anything.

When a second pair of eyes or a pair of hands is genuinely needed — a reading only
Dennis can take, a review before something is believed — that is a **checker**,
written `+role`:

```
- [ ] Stage 2 closed — 64 rom_do values byte-identical to game.pce @design +dennis !9
```

The owner does the work and moves it to **Check**. The checker confirms it and
moves it to **Done**. Neither the page nor the CLI will let a story with a checker
go straight to Done, and the Check column only appears when some story has one.

