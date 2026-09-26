#!/usr/bin/env python3
"""The board, as a command line. Same file the Workshop page draws.

A board lives in a project's plan document as Phase -> Feature -> Story:

    ## Phase A - the migration
    ### Stage 2 - the ROM path
    - [ ] Story text - the evidence that closes it @role #model

    [ ] to do   [~] doing   [x] done

Anyone can edit that file by hand. This exists so an AGENT can move a ticket
without inventing its own idea of the format, and so a mistake fails loudly
instead of quietly corrupting the plan: every match is by substring and an
ambiguous match is refused.

    board.py list   <project> [--who build] [--state open]
    board.py add    <project> "story text" --phase "Phase A" --feature "Stage 2"
                    [--who build] [--model sonnet] [--evidence "what closes it"]
    board.py start  <project> "part of the text"
    board.py done   <project> "part of the text" --evidence "the measurement"
    board.py reopen <project> "part of the text"
    board.py edit   <project> "part of the text" [--text ...] [--who ...]
                    [--model ...] [--evidence ...]

<project> is a directory name beside the Workshop, or a path.
Board edits are not committed: make the change, then commit it with the finding.
Mail is the exception -- git is the only route to the other machine, so msg
commits and pushes, and fails loudly when it cannot.
"""
import argparse, json, re, sys
from pathlib import Path

# Plan documents use em-dashes and arrows. A Windows console is cp1252 by
# default, so an unqualified print() of those raises UnicodeEncodeError and the
# command dies. Force UTF-8 out; harmless on a console that already is.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

CANDIDATES = ("docs/PLAN.md", "PLAN.md", "docs/PORT_PLAN.md", "docs/ROADMAP.md", "docs/NEXT.md")


def _write_lines(path, lines):
    """Write the plan back: UTF-8, LF, and ATOMIC. The plain write_text default
    is cp1252 on Windows, which mangled em-dashes and, when an arrow hit the
    encoder mid-write, left the plan document TRUNCATED TO ZERO BYTES. A
    temp-file + os.replace means a failed encode cannot destroy the real file."""
    import os
    data = "\n".join(lines)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


STORY = re.compile(r"^(\s*[-*]\s*)\[([ xX~?cC])\]\s*(.+)$")
MARK = {"backlog": "?", "open": " ", "wip": "~", "check": "c", "done": "x"}
STATE = {"?": "backlog", " ": "open", "~": "wip", "c": "check", "x": "done"}

# Kanban's two rules, as this workshop applies them:
#   1. Only REFINED work is pulled. A story is refined when it has an owner and
#      the evidence that will close it -- i.e. someone can start it without
#      asking a question first. Unrefined stories sit in [?].
#   2. Limit work in progress. One [~] per role at a time.
WIP_LIMIT = 1


def refined(s):
    """A STORY is refined when someone could start it without asking a question."""
    return bool(s.get("evidence")) and bool(s.get("who"))


BLOCK_MARK = "BLOCKED:"


def split_block(body):
    """text, blocked-reason  <-  'text BLOCKED: waiting on the capture'

    Blocked is a flag, not a column. The story keeps its place in the flow --
    losing that place is how a blocked item quietly becomes a forgotten one --
    and it does NOT count against the role's work-in-progress limit, so the
    agent can pull something else while it waits.
    """
    if BLOCK_MARK in body:
        a, b = body.split(BLOCK_MARK, 1)
        return a.strip(), b.strip()
    return body.strip(), ""


FEATURE_MARK = "{refined}"


def feature_name(heading):
    return heading.replace(FEATURE_MARK, "").strip()


def feature_refined(heading):
    """A FEATURE is refined when its stories are all written and someone has said so.

    Story-level refinement is not enough: a feature half-written looks ready
    story by story and is not, and pulling work out of it is how a phase ends up
    part-built. The mark is deliberate, and it is a person's or an agent's call.
    """
    return FEATURE_MARK in heading


def plan_path(project):
    p = Path(project)
    if not p.is_dir():
        p = Path(__file__).resolve().parent.parent / project
    if not p.is_dir():
        sys.exit(f"FAIL  no such project: {project}")
    for c in CANDIDATES:
        if (p / c).exists():
            return p / c
    sys.exit(f"FAIL  {p.name} has no plan document ({', '.join(CANDIDATES)})")


def split_story(body):
    """text, evidence, who, model, prio  <-  'text - evidence @who #model !8'

    Priority is 1..10, ten highest, and it is what decides which story is picked
    up next. No priority means 5.
    """
    body, blocked = split_block(body)
    who = re.search(r"(?<![\w/])@([a-z][\w-]*)", body)
    mdl = re.search(r"(?<![\w/])#([a-z][\w.-]*)", body)
    pri = re.search(r"(?<![\w/])!(10|[1-9])(?![\w])", body)
    # ONLY a leading #NN is this story's own id. Any other #NN in the text is a
    # cross-reference to another ticket and must survive being re-serialised --
    # board.py used to strip every one of them, and since join_story re-adds
    # only the id, the references were deleted from the plan for good. It had
    # already eaten PCEHeroTN #24's "gated on #84 #85 #86 #87" before anyone
    # noticed, in a commit whose stated job was adding a different ticket
    # (@review, 2026-09-06). Found because the missing gate was then reported
    # as a discipline problem: the tool destroyed the record and stayed quiet.
    tid = re.match(r"\s*#(\d+)(?![\w])", body)
    # +role is the CHECKER: one owner does the work, one other confirms it.
    # Two owners would mean neither, so a story has exactly one @ and at most one +.
    chk = re.search(r"(?<![\w/])\+([a-z][\w-]*)", body)
    core = re.sub(r"(?<![\w/])(?:[@#+][a-z][\w.-]*|![0-9]{1,2}(?![\w]))", "", body).strip()
    if tid:
        core = re.sub(r"^#\d+\s*", "", core).strip()   # the id alone; join_story re-adds it
    parts = re.split(r"\s+[—-]{1,2}\s+", core, maxsplit=1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "",
            who.group(1) if who else "", mdl.group(1) if mdl else "",
            int(pri.group(1)) if pri else 5, blocked, chk.group(1) if chk else "",
            int(tid.group(1)) if tid else 0)


def join_story(indent, mark, text, evidence, who, model, prio=5, blocked="", checker="", tid=0):
    body = (f"#{tid} " if tid else "") + text
    if evidence:
        body += " — " + evidence
    if who:
        body += " @" + who
    if checker:
        body += " +" + checker
    if model:
        body += " #" + model
    if prio and int(prio) != 5:
        body += " !" + str(int(prio))
    if blocked:
        body += f" {BLOCK_MARK} {blocked}"
    return f"{indent}[{mark}] {body}"


NOTE = re.compile(r"^(\s+)[-*]\s+(\d{4}-\d{2}-\d{2})\s+@([\w-]+):\s*(.+)$")


def load(project):
    path = plan_path(project)
    lines = path.read_text(encoding="utf-8").split("\n")
    out, phase, feature, feat_ok = [], "", "", False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            phase, feature, feat_ok = line[3:].strip(), "", False
        elif line.startswith("### "):
            feature = feature_name(line[4:])
            feat_ok = feature_refined(line)
        m = STORY.match(line)
        if m and phase:
            text, ev, who, model, prio, blocked, checker, tid = split_story(m.group(3))
            notes = []
            for j in range(i + 1, len(lines)):
                nm = NOTE.match(lines[j])
                if not nm:
                    if lines[j].strip() == "":
                        continue
                    break
                notes.append({"i": j, "date": nm.group(2), "who": nm.group(3), "text": nm.group(4)})
            out.append({"i": i, "notes": notes, "indent": m.group(1), "mark": m.group(2).lower(),
                        "feature_refined": feat_ok,
                        "state": STATE.get(m.group(2).lower(), "open"),
                        "phase": phase, "feature": feature, "text": text,
                        "evidence": ev, "who": who, "model": model, "prio": prio,
                        "blocked": blocked, "checker": checker, "id": tid})
    return path, lines, out


def find_one(stories, needle):
    n = needle.lower().strip()
    if re.fullmatch(r"#?\d+", n):
        want = int(n.lstrip("#"))
        hit = [s for s in stories if s["id"] == want]
        if len(hit) > 1:
            # Two tickets can carry one number: both machines pick "next free"
            # from their own copy, so concurrent seats collide. Returning the
            # first silently wrote a note onto the wrong ticket on 2026-09-04.
            # The text branch below has always refused ambiguity; this one did not.
            print(f"FAIL  {len(hit)} tickets are numbered #{want} -- renumber one, "
                  f"or match on text:", file=sys.stderr)
            for h in hit:
                print(f"        [{h['mark']}] {h['phase']}: {h['text'][:70]}", file=sys.stderr)
            sys.exit(1)
        if hit:
            return hit[0]
        sys.exit(f"FAIL  no ticket #{want}")
    hits = [s for s in stories if n in s["text"].lower()]
    if not hits:
        hits = [s for s in stories if n in (s["text"] + " " + s["evidence"]).lower()]
    if not hits:
        sys.exit(f"FAIL  no story matches {needle!r}")
    if len(hits) > 1:
        print(f"FAIL  {len(hits)} stories match {needle!r} -- be more specific:", file=sys.stderr)
        for h in hits:
            print(f"        [{h['mark']}] {h['text']}", file=sys.stderr)
        sys.exit(1)
    return hits[0]


def write(path, lines):
    _write_lines(path, lines)
    print(f"ok    {path}")


def cmd_list(a):
    _, _, stories = load(a.project)
    if not stories:
        print("(no stories)")
        return
    phase = None
    stories = sorted(stories, key=lambda s: (s["phase"], -s["prio"]))
    for s in stories:
        if a.who and s["who"] != a.who:
            continue
        if a.state and s["state"] != a.state:
            continue
        if s["phase"] != phase:
            phase = s["phase"]
            print(f"\n{phase}")
        tag = " ".join(x for x in (f"@{s['who']}" if s["who"] else "",
                                   f"+{s['checker']}" if s["checker"] else "",
                                   f"#{s['model']}" if s["model"] else "") if x)
        print(f"  #{s['id'] or '-':<3} [{s['mark']}] !{s['prio']:<2} {'[BLOCKED] ' if s['blocked'] else ''}{s['text']}"
              + (f"  — {s['evidence']}" if s["evidence"] else "")
              + (f"  {tag}" if tag else ""))


def set_state(a, state):
    path, lines, stories = load(a.project)
    s = find_one(stories, a.match)
    ev = getattr(a, "evidence", None) or s["evidence"]
    who = getattr(a, "who", None) or s["who"]
    if state == "done" and not ev:
        sys.exit("FAIL  a story closes on evidence. Pass --evidence \"the measurement\".")
    if state == "done" and s["checker"] and s["state"] not in ("check", "done"):
        sys.exit(f"FAIL  +{s['checker']} has to check this one. Move it to check first:\n"
                 f"      board.py check <project> <match>")
    if state in ("open", "wip", "check") and not (ev and who):
        sys.exit("FAIL  unrefined: a story needs an owner (@role) and the evidence that closes it "
                 "before anyone pulls it. Pass --who and --evidence, or leave it in [?].")
    if state == "wip" and s.get("blocked"):
        sys.exit(f"FAIL  that story is blocked: {s['blocked']}\n"
                 f"      Clear it first: board.py unblock <project> <match>")
    if state == "wip" and not s.get("feature_refined"):
        sys.exit(f"FAIL  the feature {s['feature']!r} is not refined. Write its stories, then "
                 f"mark it: board.py feature <project> {s['feature']!r} --refined")
    if state == "wip":
        mine = [x for x in stories if x["state"] == "wip" and x["who"] == who
                and x["i"] != s["i"] and not x["blocked"]]
        if len(mine) >= WIP_LIMIT:
            sys.exit(f"FAIL  @{who} already has {len(mine)} story in progress. Finish or park it "
                     f"first -- limiting work in progress is the point.")
    s["evidence"], s["who"] = ev, who
    lines[s["i"]] = join_story(s["indent"], MARK[state], s["text"], ev, s["who"], s["model"], s["prio"], s["blocked"], s["checker"], s["id"])
    write(path, lines)
    print(f"      [{MARK[state]}] {s['text']}")


class BoardError(Exception):
    """Something the caller asked for cannot be done, with the reason."""


def next_id(stories):
    return max([s["id"] for s in stories] or [0]) + 1


def _insert_after(lines, ft, stop):
    """Index to insert a new story after: the last story in the feature AND the
    notes hanging off it. Inserting between a story and its notes silently hands
    those notes to the newcomer -- that is how #87's brief ended up under #86 and
    how four cancelled tickets' notes piled up under #85.
    """
    last = max((i for i in range(ft + 1, stop) if STORY.match(lines[i])), default=ft)
    while last + 1 < stop and NOTE.match(lines[last + 1]):
        last += 1
    return last


def add_story(project, phase, feature, text, who="", model="", evidence="",
              new_feature=False, prio=5, checker=""):
    """Insert a story under a phase's feature. Returns the line written."""
    if not (text or "").strip():
        raise BoardError("a story needs text")
    path, lines, existing = load(project)
    tid = next_id(existing)
    ph = next((i for i, l in enumerate(lines)
               if l.startswith("## ") and phase.lower() in l.lower()), None)
    if ph is None:
        raise BoardError(f"no phase heading matching {phase!r}")
    end = next((i for i in range(ph + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    ft = next((i for i in range(ph + 1, end)
               if lines[i].startswith("### ") and feature.lower() in lines[i].lower()), None)
    if ft is None:
        if not new_feature:
            raise BoardError(f"no feature heading matching {feature!r} in that phase -- "
                             f"a story belongs to a feature")
        while end > ph + 1 and not lines[end - 1].strip():
            end -= 1
        lines[end:end] = ["", f"### {feature}"]
        ft = end + 1
        end = ft + 1
    stop = next((i for i in range(ft + 1, end) if lines[i].startswith("### ")), end)
    last = _insert_after(lines, ft, stop)
    mark = " " if ((evidence or "").strip() and who) else "?"
    line = join_story("- ", mark, text.strip(), (evidence or "").strip(), who or "",
                      model or "", prio, "", checker or "", tid)
    lines.insert(last + 1, line)
    _write_lines(path, lines)
    return line


def edit_story(project, match, text=None, evidence=None, who=None, model=None,
               exact=False, prio=None, blocked=None, checker=None):
    path, lines, stories = load(project)
    if exact:
        hits = [s for s in stories if lines[s["i"]].strip() == match.strip()]
        if len(hits) != 1:
            raise BoardError(f"{len(hits)} lines match that ticket -- reload the page")
        s = hits[0]
    else:
        s = find_one(stories, match)
    lines[s["i"]] = join_story(s["indent"], s["mark"],
                               (text or s["text"]).strip(),
                               s["evidence"] if evidence is None else evidence.strip(),
                               s["who"] if who is None else who,
                               s["model"] if model is None else model,
                               s["prio"] if prio is None else int(prio),
                               s["blocked"] if blocked is None else blocked,
                               s["checker"] if checker is None else checker, s["id"])
    _write_lines(path, lines)
    return path, lines[s["i"]]


def delete_story(project, line_text):
    path, lines, stories = load(project)
    hits = [s for s in stories if lines[s["i"]].strip() == line_text.strip()]
    if len(hits) != 1:
        raise BoardError(f"{len(hits)} lines match that ticket -- reload the page")
    del lines[hits[0]["i"]]
    _write_lines(path, lines)


def set_feature(project, feature, is_refined):
    path, lines, _ = load(project)
    hits = [i for i, l in enumerate(lines)
            if l.startswith("### ") and feature.lower() in feature_name(l[4:]).lower()]
    if len(hits) != 1:
        raise BoardError(f"{len(hits)} feature headings match {feature!r}")
    i = hits[0]
    name = feature_name(lines[i][4:])
    lines[i] = f"### {name} {FEATURE_MARK}" if is_refined else f"### {name}"
    _write_lines(path, lines)
    return lines[i]


def add_note(project, match, who, text, exact=False):
    """A line under the ticket saying what happened and WHERE the detail is.

    A pointer, not a transcript: findings belong in the project's notes files and
    the ticket links to them. One line, dated, attributed.
    """
    if not (text or "").strip():
        raise BoardError("a note needs text")
    path, lines, stories = load(project)
    if exact:
        hits = [s for s in stories if lines[s["i"]].strip() == match.strip()]
        if len(hits) != 1:
            raise BoardError(f"{len(hits)} lines match that ticket -- reload the page")
        s = hits[0]
    else:
        s = find_one(stories, match)
    at = s["notes"][-1]["i"] if s["notes"] else s["i"]
    day = __import__("datetime").date.today().isoformat()
    line = f"  - {day} @{who or 'design'}: {text.strip()}"
    lines.insert(at + 1, line)
    _write_lines(path, lines)
    return line


# Text that arrives through a shell argument has already been through the shell.
# 2026-09-06 (#112): a message naming a BAT range as a dollar-hex address landed
# in .inbox/sim.md with the leading dollar-zero replaced by /bin/bash, because
# the sender wrote it inside double quotes and the shell expanded it before
# board.py saw it. Same expansion ate the addresses out of PCEHeroTN c029faa
# (#104) -- check_commit_msg.sh guards that route, this guards the other.
#
# The empty expansions ($E231 -> nothing) are gone before we can look; $0 is the
# one that leaves a footprint. So: refuse on the footprint, BEFORE anything is
# written -- the sender still has the text, the recipient would not -- and offer
# the route that cannot be mangled: --file (or --file - for stdin).
SHELL_ATE = re.compile(r"(/usr)?/bin/(ba|z|da)?sh")


def take_text(a, what):
    """The text of a msg or note: from --file (- is stdin), else the argument.
    Refuses text the shell has visibly expanded."""
    if getattr(a, "file", None):
        text = (sys.stdin.read() if a.file == "-"
                else Path(a.file).read_text(encoding="utf-8", errors="replace"))
    else:
        text = a.text or ""
    if a.text and getattr(a, "file", None):
        sys.exit(f"FAIL  {what}: give the text OR --file, not both")
    if not text.strip():
        sys.exit(f"FAIL  {what} needs text -- as an argument, or --file <path> (- for stdin)")
    m = SHELL_ATE.search(text)
    if m:
        sys.exit(f"FAIL  {what} NOT written: the text contains '{m.group(0)}', which "
                 f"is almost certainly $0 expanded where a hex address should be "
                 f"($0138 -> /bin/bash138). Every other $NAME in it is already "
                 f"gone. Put the text in a file and send it with --file <path>, "
                 f"or --file - and pipe it on stdin (#112).")
    return text


def cmd_note(a):
    try:
        line = add_note(a.project, a.match, a.who, take_text(a, 'note'))
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {line.strip()}")


SHOP = Path(__file__).resolve().parent
SESSIONS = SHOP / ".sessions"
INBOX = SHOP / ".inbox"


def mail_sync(paths, what):
    """Commit and push a mail change, and report what actually happened.

    #95: .inbox/ was gitignored, so a message left on the Mac sat in a file the
    PC could never open while msg printed 'ok' every time -- cross-machine mail
    had never once arrived. Git is the only channel between the two machines, so
    a message is not SENT until it is pushed, and a push that fails has to be
    said out loud rather than swallowed.

    Commits by pathspec, so it takes the mail files and nothing else: the tree
    normally holds unrelated work in progress and that is not ours to sweep up.

    Returns (delivered, one line saying so)."""
    import subprocess
    rel = []
    for x in paths:
        try:
            rel.append(str(Path(x).resolve().relative_to(SHOP)))
        except ValueError:
            return False, f"not sent -- {x} is outside the workshop"

    def git(*a):
        return subprocess.run(["git", "-C", str(SHOP), *a],
                              capture_output=True, text=True)

    if git("rev-parse", "--git-dir").returncode:
        return False, "not sent -- the workshop is not a git repository"
    # a path can be legitimately absent -- reading an inbox deletes the unread
    # file -- but git add refuses a pathspec that is neither on disk nor tracked,
    # and one such path would sink the whole send
    known = set(git("ls-files", "--", *rel).stdout.split("\n"))
    rel = [x for x in rel if (SHOP / x).exists() or x in known]
    if not rel:
        return True, "nothing to send -- no mail file to commit"
    add = git("add", "-A", "--", *rel)
    if add.returncode:
        return False, f"not sent -- git add failed: {add.stderr.strip()[:120]}"
    if git("diff", "--cached", "--quiet", "--", *rel).returncode == 0:
        return True, "nothing to send -- no change to the mail"
    c = git("commit", "-q", "-m", f"mail: {what}", "--", *rel)
    if c.returncode:
        return False, f"not sent -- commit failed: {(c.stderr or c.stdout).strip()[:160]}"
    u = git("push")
    if u.returncode and "[rejected]" in (u.stderr + u.stdout):
        # Behind only because the other machine has been busy, which is now the
        # normal case. inbox pulls before it reads; sending has to do the same or
        # every message sent while the other seat was working needs a human.
        r = git("pull", "--rebase", "--autostash", "-q")
        if r.returncode:
            git("rebase", "--abort")   # never leave the repo mid-rebase
            return False, ("committed but NOT PUSHED: the remote moved and the "
                           "rebase would not apply cleanly (mail files can collide, "
                           "#113). Pull by hand, keep BOTH messages, then push")
        u = git("push")
    if u.returncode:
        # git's last line is boilerplate advice ("...and the repository exists.");
        # the line that says what went wrong is the rejection or the first fatal
        lines = [l.strip() for l in (u.stderr + "\n" + u.stdout).splitlines() if l.strip()]
        why = next((l for l in lines if "[rejected]" in l),
                   next((l for l in lines if l.startswith(("fatal", "error"))),
                        lines[0] if lines else "no output"))
        return False, ("committed but NOT PUSHED, so it has not left this machine: "
                       f"{why[:140]} -- pull, then push")
    return True, "committed and pushed -- it will arrive on the other machine at its next pull"


# Mail crosses machines, so it crosses encodings. A seat on the PC writes with
# Windows' cp1252 default unless told otherwise, and a bare read_text() here
# then dies on the first em-dash -- which is exactly how @workshop's own inbox
# became unreadable the day after mail started working (#110). Write UTF-8
# explicitly at every end, and read tolerantly: a mangled character is a bad
# day, an unreadable inbox is a lost message.
def mail_read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def mail_append(p, text):
    with p.open("a", encoding="utf-8") as fh:
        fh.write(text)


def cmd_msg(a):
    """Leave a message for a seat. Not a live nudge -- nothing can type into a
    running session from outside -- so it waits until that seat next reads its
    inbox. The seats are on the other machine, so it is committed and pushed:
    until it is, it has not been sent, and the exit code says which."""
    import time as _t
    text = take_text(a, "message")
    INBOX.mkdir(exist_ok=True)
    p = INBOX / f"{a.to}.md"
    stamp = _t.strftime("%Y-%m-%d %H:%M")
    mail_append(p, f"\n## {stamp} — from @{a.frm}\n\n{text.strip()}\n")
    if a.local:
        print(f"ok    written to {p}\n      NOT SENT (--local): it stays on this machine.")
        return
    sent, how = mail_sync([p], f"to @{a.to} from @{a.frm}")
    print(f"{'ok   ' if sent else 'FAIL '} message for @{a.to} — {how}")
    if not sent:
        sys.exit(1)


def mail_fetch(who):
    """Bring the inbox up to date before claiming it is empty.

    msg pushes but inbox used to do nothing, so half the channel was automatic:
    a seat could run inbox straight after a clear, read whatever its clone last
    had, and be told '(no messages)' while the message sat on the remote. That
    is the original bug wearing a different hat -- it used to print ok and never
    send, this printed empty and never looked. Found 2026-09-07 when @build
    looked, saw nothing, and found the mail after a pull (#114).

    Returns a line to print, or "" when there was nothing to do."""
    import subprocess
    SHOP_ = SHOP

    def git(*c, **kw):
        return subprocess.run(["git", "-C", str(SHOP_), *c],
                              capture_output=True, text=True, **kw)

    if git("rev-parse", "--git-dir").returncode:
        return ""
    rel = f".inbox/{who}.md"
    try:
        if git("fetch", "-q", timeout=30).returncode:
            return ("WARN  could not reach the remote, so this is only what this "
                    "machine already had -- '(no messages)' may be wrong")
    except Exception:
        return ("WARN  the fetch did not finish, so this is only what this machine "
                "already had -- '(no messages)' may be wrong")
    # rev-parse echoes its argument back on stdout when the path is not there,
    # so a seat with no inbox at all compared two DIFFERENT strings and looked
    # permanently behind. Absent has to mean absent.
    def blob(rev):
        r = git("rev-parse", "--verify", "--quiet", f"{rev}:{rel}")
        return r.stdout.strip() if r.returncode == 0 else ""

    here, there = blob("HEAD"), blob("origin/main")
    if here == there:
        return ""
    u = git("pull", "--rebase", "--autostash", "-q")
    if u.returncode:
        return (f"WARN  there IS newer mail for @{who} on the remote and the pull "
                f"failed: {(u.stderr or u.stdout).strip().splitlines()[0][:110] if (u.stderr or u.stdout).strip() else 'no output'}"
                " -- resolve it and read again, do not trust what follows")
    return f"(pulled newer mail for @{who} before reading)"


def cmd_inbox(a):
    """Read a seat's messages, and check in while you are at it."""
    import time as _t
    note = mail_fetch(a.who)
    if note:
        print(note)
    p = INBOX / f"{a.who}.md"
    SESSIONS.mkdir(exist_ok=True)
    sp = SESSIONS / f"{a.who}.json"
    prev = {}
    if sp.exists():
        try:
            prev = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    prev.update({"who": a.who, "at": int(_t.time())})
    prev.setdefault("machine", __import__("socket").gethostname())
    sp.write_text(json.dumps(prev, indent=1), encoding="utf-8")

    if not p.exists() or not mail_read(p).strip():
        print(f"(no messages for @{a.who})")
        return
    print(mail_read(p).strip())
    if not a.keep:
        done = INBOX / f"{a.who}.read.md"
        mail_append(done, mail_read(p))
        p.unlink()
        print(f"\n---\nmarked read (kept in {done.name}). Act on it, or say on the "
              f"ticket why not.")
        # read state crosses too, or the same message is unread again on the
        # other machine and gets acted on twice
        sent, how = mail_sync([p, done], f"@{a.who} read {p.name}")
        if not sent:
            print(f"NOTE  read state stayed here — {how}")


def cmd_resume(a):
    """Print the line that starts or resumes a seat. Same shape for every role,
    so coming back after a clear is one paste and never a reconstruction."""
    print(f"You are @{a.who} on {a.project}. Read ../Workshop/roles/{a.who}.md, then run "
          f"../Workshop/board.py inbox --who {a.who} and "
          f"../Workshop/board.py next {a.project} --who {a.who}, and do what it says.")


def cmd_checkin(a):
    """Say a seat is open. Nothing can detect a session from outside, so it is
    self-reported: a session that dies without saying so goes stale rather than
    showing green forever."""
    import socket, time as _t
    SESSIONS.mkdir(exist_ok=True)
    p = SESSIONS / f"{a.who}.json"
    prev = {}
    if p.exists():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    p.write_text(json.dumps({
        "who": a.who,
        "machine": a.machine or prev.get("machine") or socket.gethostname(),
        "project": a.project or prev.get("project", ""),
        "doing": a.doing or prev.get("doing", ""),
        "at": int(_t.time()),
    }, indent=1))
    print(f"ok    @{a.who} checked in")


def cmd_checkout(a):
    p = SESSIONS / f"{a.who}.json"
    if p.exists():
        p.unlink()
    print(f"ok    @{a.who} signed off")


def cmd_health(a):
    """Everything wrong with the board that a machine can see without judgement."""
    _, _, stories = load(a.project)
    live = [s for s in stories if not re.match(r"^(Ideas|Cancelled|Archive)\b", s["phase"], re.I)]
    out = []

    wip = collections_defaultdict()
    for s in live:
        if s["state"] == "wip" and not s["blocked"]:
            wip.setdefault(s["who"] or "unassigned", []).append(s)
    for who, ss in wip.items():
        if len(ss) > WIP_LIMIT:
            out.append(("WIP", f"@{who} has {len(ss)} in progress: " +
                        ", ".join(f"#{x['id']}" for x in ss)))

    for s in live:
        if s["blocked"]:
            out.append(("HOLD", f"#{s['id']} @{s['who'] or '-'} — {s['blocked']}"))
    for s in live:
        if s["state"] in ("open", "wip") and not (s["evidence"] and s["who"]):
            out.append(("UNREFINED", f"#{s['id']} is pullable but has no "
                        + ("owner" if not s["who"] else "closing measurement")))
    for s in live:
        if s["state"] == "check":
            out.append(("WAITING", f"#{s['id']} needs +{s['checker'] or '?'} to confirm it"))
    for s in live:
        if s["state"] == "wip" and s["feature"] and not s["feature_refined"]:
            out.append(("PULLED EARLY", f"#{s['id']} is in progress inside an unrefined feature"))

    counts = {}
    for s in live:
        if s["state"] in ("open", "wip", "check"):
            counts[s["who"] or "unassigned"] = counts.get(s["who"] or "unassigned", 0) + 1
    for who, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n >= 6:
            out.append(("QUEUE", f"@{who} has {n} live tickets — is that really one seat's work?"))
    for s in live:
        if not s["id"]:
            out.append(("NO ID", f"a story has no number: {s['text'][:60]} "
                        f"-- run board.py renumber"))
    if counts.get("unassigned"):
        out.append(("UNOWNED", f"{counts['unassigned']} live tickets have no owner"))

    if not out:
        print("ok    nothing a machine can see is wrong with this board")
        return
    width = max(len(k) for k, _ in out)
    for k, msg in out:
        print(f"{k.ljust(width)}  {msg}")
    print(f"\n{len(out)} things to look at. None of this is a judgement -- it is "
          f"what the board says about itself.")


def collections_defaultdict():
    return {}


def unplaced_banner(stories):
    """Tickets nobody owns, shown to every seat on every `next`.

    cmd_next only ever looks at `who == me`, so an UNASSIGNED ticket is invisible
    to everybody -- which is exactly what @review is told to file. Five review
    findings sat untouched for a day because of it, and two were then rediscovered
    from scratch by another seat that had no idea they existed. Placing them is
    @scrum's job; being unable to SEE them was the tool's.
    """
    loose = [s for s in stories
             if not s["who"] and s["state"] in ("backlog", "open", "wip")
             and not re.match(r"^(Ideas|Cancelled|Archive)\b", s["phase"], re.I)]
    if not loose:
        return
    print(f"\nUNPLACED     {len(loose)} ticket(s) nobody owns. Until @scrum places them,"
          f" no seat's `next` will offer them:")
    for s in sorted(loose, key=lambda s: -s["prio"])[:6]:
        print(f"               #{s['id']} !{s['prio']} {s['text'][:66]}")
    if len(loose) > 6:
        print(f"               ... and {len(loose) - 6} more")


def cmd_next(a):
    """The one story this role should pick up, and why it is that one."""
    _, _, stories = load(a.project)
    try:
        _next_body(a, stories)
    finally:
        unplaced_banner(stories)


def _next_body(a, stories):
    mine = [s for s in stories if s["who"] == a.who]
    doing = [s for s in mine if s["state"] == "wip" and not s["blocked"]]
    if doing:
        print(f"IN PROGRESS  [{doing[0]['mark']}] {doing[0]['text']}")
        print(f"             closes on: {doing[0]['evidence'] or '(no evidence stated -- fix that first)'}")
        print("             Finish or park it before pulling anything else.")
        return
    checks = [s for s in stories if s["checker"] == a.who and s["state"] == "check"]
    for s in sorted(checks, key=lambda s: -s["prio"]):
        print(f"TO CHECK     !{s['prio']} {s['text']}")
        print(f"             confirm: {s['evidence']}")
    ready = sorted([s for s in mine if s["state"] == "open" and not s["blocked"]
                    and s["feature_refined"]], key=lambda s: -s["prio"])
    if not ready:
        held = [s for s in mine if s["blocked"]]
        unref = [s for s in mine if s["state"] == "open" and not s["feature_refined"]]
        print(f"NOTHING READY for @{a.who}.")
        for s in held:
            print(f"  on hold    {s['text']}  ({s['blocked']})")
        for s in unref:
            print(f"  unrefined  {s['text']}  (feature {s['feature']!r} is not marked refined)")
        if not (held or unref or checks):
            print("  Nothing assigned. Ask for work, or add the story you know is missing.")
        return
    s = ready[0]
    print(f"NEXT         #{s['id']} !{s['prio']} {s['text']}")
    print(f"             phase:   {s['phase']}")
    print(f"             feature: {s['feature']}")
    print(f"             closes:  {s['evidence']}")
    if s["checker"]:
        print(f"             then +{s['checker']} has to check it before it is done")
    for n in s["notes"][-2:]:
        print(f"             note:    {n['date']} @{n['who']}: {n['text']}")
    print(f"\n             board.py start {a.project} \"{s['text'][:40]}\"")
    if len(ready) > 1:
        print("\n             after that:")
        for o in ready[1:4]:
            print(f"               !{o['prio']} {o['text']}")


PARKED_PHASES = ("Ideas", "Cancelled", "Archive")


def move_story(project, match, phase, feature=None, exact=False):
    """Move a story, with its notes, under another phase (and feature)."""
    path, lines, stories = load(project)
    if exact:
        hits = [s for s in stories if lines[s["i"]].strip() == match.strip()]
        if len(hits) != 1:
            raise BoardError(f"{len(hits)} lines match that ticket -- reload the page")
        s = hits[0]
    else:
        s = find_one(stories, match)
    block = [lines[s["i"]]] + [lines[n["i"]] for n in s["notes"]]
    for i in sorted([s["i"]] + [n["i"] for n in s["notes"]], reverse=True):
        del lines[i]

    ph = next((i for i, l in enumerate(lines)
               if l.startswith("## ") and phase.lower() in l.lower()), None)
    if ph is None:
        raise BoardError(f"no phase heading matching {phase!r}")
    end = next((i for i in range(ph + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    ft = None
    if feature:
        ft = next((i for i in range(ph + 1, end)
                   if lines[i].startswith("### ") and feature.lower() in feature_name(lines[i][4:]).lower()), None)
    if ft is None:
        ft = next((i for i in range(ph + 1, end) if lines[i].startswith("### ")), None)
    if ft is None:
        raise BoardError(f"{phase!r} has no feature heading to put it under")
    stop = next((i for i in range(ft + 1, end) if lines[i].startswith("### ")), end)
    last = _insert_after(lines, ft, stop)
    # a story leaving the flow keeps its history but stops claiming a state
    if phase.lower().startswith(("cancel", "archiv", "idea")) and block[0].strip().startswith("- ["):
        block[0] = re.sub(r"^(\s*[-*]\s*)\[.\]", r"\1[?]", block[0])
    lines[last + 1:last + 1] = block
    _write_lines(path, lines)
    return block[0]


def renumber(project):
    path, lines, stories = load(project)
    nxt = next_id(stories)
    given = 0
    for s in stories:
        if s["id"]:
            continue
        lines[s["i"]] = join_story(s["indent"], s["mark"], s["text"], s["evidence"],
                                   s["who"], s["model"], s["prio"], s["blocked"],
                                   s["checker"], nxt)
        nxt += 1
        given += 1
    if given:
        _write_lines(path, lines)
    return given


def cmd_renumber(a):
    n = renumber(a.project)
    print(f"ok    gave {n} stories an id" if n else "ok    every story already has an id")


def cmd_idea(a):
    """Park a thought where it will not be mistaken for work."""
    try:
        line = add_story(a.project, "Ideas", "Ideas", a.text, "", "", a.about or "",
                         new_feature=True, prio=1)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {line.strip()}")


def cmd_move(a):
    try:
        line = move_story(a.project, a.match, a.phase, a.feature)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    moved to {a.phase}")
    print(f"      {line.strip()}")


def cmd_checker(a):
    try:
        path, line = edit_story(a.project, a.match, checker=a.who)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {line.strip()}")


def cmd_block(a, reason):
    try:
        path, line = edit_story(a.project, a.match, blocked=reason)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {path}")
    print(f"      {line.strip()}")


def cmd_feature(a):
    try:
        line = set_feature(a.project, a.feature, not a.unrefine)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {line}")


def cmd_add(a):
    try:
        line = add_story(a.project, a.phase, a.feature, a.text, a.who or "",
                         a.model or "", a.evidence or "", prio=a.prio or 5)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {plan_path(a.project)}")
    print(f"      {line}")


def cmd_edit(a):
    try:
        path, line = edit_story(a.project, a.match, a.text, a.evidence, a.who, a.model,
                                prio=a.prio)
    except BoardError as e:
        sys.exit(f"FAIL  {e}")
    print(f"ok    {path}")
    print(f"      {line.strip()}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)

p = sub.add_parser("list"); p.add_argument("project")
p.add_argument("--who"); p.add_argument("--state", choices=("backlog", "open", "wip", "check", "done"))
p.set_defaults(fn=cmd_list)

p = sub.add_parser("add"); p.add_argument("project"); p.add_argument("text")
p.add_argument("--phase", required=True); p.add_argument("--feature", required=True)
p.add_argument("--who"); p.add_argument("--model"); p.add_argument("--evidence")
p.add_argument("--prio", type=int, choices=range(1, 11), metavar="1-10",
               help="10 is highest and is picked up first; default 5")
p.set_defaults(fn=cmd_add)

for name, state in (("refine", "open"), ("start", "wip"), ("check", "check"),
                    ("done", "done"), ("reopen", "open"), ("park", "backlog")):
    p = sub.add_parser(name); p.add_argument("project"); p.add_argument("match")
    p.add_argument("--evidence"); p.add_argument("--who")
    p.set_defaults(fn=(lambda st: (lambda a: set_state(a, st)))(state))

p = sub.add_parser("note"); p.add_argument("project"); p.add_argument("match")
p.add_argument("text", nargs="?"); p.add_argument("--who", default="design")
p.add_argument("--file", help="read the text from this file (- for stdin) -- "
               "the only route that keeps $-addresses intact")
p.set_defaults(fn=cmd_note)

p = sub.add_parser("msg"); p.add_argument("--to", required=True)
p.add_argument("--frm", default="dennis"); p.add_argument("text", nargs="?")
p.add_argument("--file", help="read the text from this file (- for stdin) -- "
               "the only route that keeps $-addresses intact")
p.add_argument("--local", action="store_true",
               help="write it without committing -- it will not reach the other machine")
p.set_defaults(fn=cmd_msg)

p = sub.add_parser("inbox"); p.add_argument("--who", required=True)
p.add_argument("--keep", action="store_true", help="do not mark it read")
p.set_defaults(fn=cmd_inbox)

p = sub.add_parser("resume"); p.add_argument("--who", required=True)
p.add_argument("--project", default=None)
p.set_defaults(fn=cmd_resume)

p = sub.add_parser("checkin"); p.add_argument("--who", required=True)
p.add_argument("--machine"); p.add_argument("--project"); p.add_argument("--doing")
p.set_defaults(fn=cmd_checkin)

p = sub.add_parser("checkout"); p.add_argument("--who", required=True)
p.set_defaults(fn=cmd_checkout)

p = sub.add_parser("health"); p.add_argument("project")
p.set_defaults(fn=cmd_health)

p = sub.add_parser("next"); p.add_argument("project")
p.add_argument("--who", required=True, help="the role asking")
p.set_defaults(fn=cmd_next)

p = sub.add_parser("renumber"); p.add_argument("project")
p.set_defaults(fn=cmd_renumber)

p = sub.add_parser("idea"); p.add_argument("project"); p.add_argument("text")
p.add_argument("--about", help="why it might matter, in a line")
p.set_defaults(fn=cmd_idea)

p = sub.add_parser("move"); p.add_argument("project"); p.add_argument("match")
p.add_argument("--phase", required=True); p.add_argument("--feature")
p.set_defaults(fn=cmd_move)

p = sub.add_parser("checker"); p.add_argument("project"); p.add_argument("match")
p.add_argument("--who", default="", help="the role that confirms it; empty to clear")
p.set_defaults(fn=lambda a: cmd_checker(a))

p = sub.add_parser("block"); p.add_argument("project"); p.add_argument("match")
p.add_argument("--reason", required=True, help="what it is waiting on")
p.set_defaults(fn=lambda a: cmd_block(a, a.reason))

p = sub.add_parser("unblock"); p.add_argument("project"); p.add_argument("match")
p.set_defaults(fn=lambda a: cmd_block(a, ""))

p = sub.add_parser("feature"); p.add_argument("project"); p.add_argument("feature")
p.add_argument("--unrefine", action="store_true",
               help="take the refined mark off again")
p.set_defaults(fn=cmd_feature)

p = sub.add_parser("edit"); p.add_argument("project"); p.add_argument("match")
p.add_argument("--text"); p.add_argument("--who"); p.add_argument("--model"); p.add_argument("--evidence")
p.add_argument("--prio", type=int, choices=range(1, 11), metavar="1-10")
p.set_defaults(fn=cmd_edit)

a = ap.parse_args()
a.fn(a)
