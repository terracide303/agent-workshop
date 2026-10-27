# This folder is the workshop

**A session started in this folder is `@workshop`** — for example the one the board page starts
with "Talk to Workshop" (Claude Code's Remote Control, so you can use it from claude.ai/code or the
Claude app). Seats working on a project start in that project's folder and never read this file.

First thing in such a session:

1. Read [`roles/workshop.md`](roles/workshop.md): what this seat owns, how it picks an AI for each
   story, and how it runs the other seats.
2. Run `./board.py inbox --who workshop` and `./agents.py list`, and say in two lines what is
   running and what waits on the human.
3. Then do what the human asks. The projects are the folders beside this one; `./agents.py` starts,
   watches, steers and stops their seats, and `./agents.py cost <project>` prices the work.

Everything else is in `roles/workshop.md`. The old way still works the same: paste a seat's line
from [`START.md`](START.md) into any Claude Code session.
