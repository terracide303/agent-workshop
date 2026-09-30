#!/usr/bin/env python3
"""Collect one project's state into one JSON blob, for the page (page.sh).

Everything here is parsed from files a project following the workshop
conventions already has -- docs/PLAN.md above all -- and every one of them is
optional: a missing file gives an empty section, never an error. The only
per-project input is docs/project.json, for what cannot be derived (a title,
a subtitle); it is optional too.

Usage:  python3 collect.py <project-dir> <workshop-dir> > state.json
"""
import json, re, subprocess, sys, os
from pathlib import Path

proj = Path(sys.argv[1]).resolve()
shop = Path(sys.argv[2]).resolve()

def read(p, default=""):
    try: return (proj / p).read_text(errors="replace")
    except Exception: return default

state = json.loads(read("docs/project.json", "{}") or "{}")

# --- components, from CAPABILITY.md tables ----------------------------------
components, section = [], "General"
for line in read("docs/CAPABILITY.md").splitlines():
    if line.startswith("## "):
        section = line[3:].strip()
    m = re.match(r"^\|\s*(.+?)\s*\|\s*\*{0,2}([A-Z ]+?)\*{0,2}\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
    if m and m.group(2).strip() not in ("STATUS",):
        name, status, evidence, where = (x.strip() for x in m.groups())
        if name.lower().startswith("component") or set(name) <= set("-| "):
            continue
        components.append({
            "section": section,
            "name": re.sub(r"[`*]", "", name),
            "status": status.strip().split()[0],
            "status_full": status.strip(),
            "evidence": re.sub(r"[`*]", "", evidence),
            "where": re.sub(r"[`*]", "", where),
        })
state["components"] = components

# --- builds, from BUILD_NOTES.md --------------------------------------------
# Every dated entry counts. The old parser required "build N:" in the heading and
# silently dropped everything titled another way -- 37 entries in the file, 10 on
# the page, and all of the recent ones missing.
notes = read("docs/BUILD_NOTES.md")
archived = ""
for extra in (proj / "docs" / "archive").glob("BUILD_NOTES*.md") if (proj / "docs" / "archive").is_dir() else []:
    archived += extra.read_text(errors="replace")
builds = []
for source in (archived, notes):
    for b in re.split(r"\n(?=## )", source):
        h = re.match(r"## (\d{4}-\d{2}-\d{2})\s*[-–—]{1,2}\s*(.*)", b)
        if not h:
            continue
        date, title = h.group(1), h.group(2).strip()
        num = re.search(r"\bbuild (\d+)\b", title, re.I)
        title = re.sub(r"^.*?build \d+\s*:\s*", "", title, flags=re.I)
        builds.append({
            "date": date,
            "n": int(num.group(1)) if num else None,
            "title": title,
            "fmax": None, "tns": None, "lut": None,
            "failed": bool(re.search(r"\bFAIL(?:ED|S)?\b", b)),
            "flashed": bool(re.search(r"\bflashed\b", b, re.I)) and not re.search(r"NOT flashed", b, re.I),
        })
seen, uniq = set(), []
for x in builds:
    k = (x["date"], x["title"][:60])
    if k in seen:
        continue
    seen.add(k)
    uniq.append(x)
builds = uniq
# a stable sequence number, so every build can be named even when the notes did not
for i, x in enumerate(builds, 1):
    x["seq"] = i
state["builds"] = builds

# --- protected files ---------------------------------------------------------
state["protected"] = [l.strip() for l in read(".protected").splitlines()
                      if l.strip() and not l.startswith("#")]

# --- build freshness (only if the workshop has a build_deps.sh) ----------------
fresh = []
script = shop / "build_deps.sh"
if script.exists():
    try:
        out = subprocess.run(["bash", str(script)], cwd=proj, capture_output=True,
                             text=True, timeout=60).stdout
        cur = None
        for line in out.splitlines():
            m = re.match(r"\s*(STALE|ok)\s+(\S+)", line)
            if m:
                cur = {"build": m.group(2), "stale": m.group(1) == "STALE", "files": []}
                fresh.append(cur)
            elif cur and line.strip().startswith("rtl/") or (cur and line.strip().startswith("source/")):
                cur["files"].append(line.strip())
    except Exception:
        pass
state["freshness"] = fresh

# --- the workshop's rules, from RULES.md ---------------------------------------
# A rule is a "## N. TEXT" heading; other "## " headings (the preamble) are not.
rules = []
try:
    for line in (shop / "RULES.md").read_text(errors="replace").splitlines():
        m = re.match(r"^##\s+(\d+[a-z]?)\.\s*(.+)$", line)
        if m:
            rules.append({"id": m.group(1), "text": m.group(2).strip(), "part": "Rules"})
except Exception:
    pass
state["rules"] = rules


# --- identity, when there is no project.json ---------------------------------
state.setdefault("name", proj.name)
if not state.get("subtitle"):
    for line in read("README.md").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            state["subtitle"] = re.sub(r"[*`\[\]]", "", s)[:160]
            break
if not state.get("repo"):
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=proj,
                       capture_output=True, text=True).stdout.strip()
    m = re.search(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", r)
    state["repo"] = m.group(1) if m else ""

# --- the headline: first prose block of the live-state doc -------------------
head_doc = next((d for d in ("RESUME_HERE.md", "docs/NEXT.md", "docs/ROADMAP.md",
                             "docs/DESIGN.md", "NOTES.md", "README.md")
                 if (proj / d).exists()), None)
state["headline_doc"] = head_doc or ""
para = []
if head_doc:
    started = False
    for line in read(head_doc).splitlines():
        s = line.strip()
        if s.startswith("#"):
            if started: break
            started = True; continue
        if not s:
            if para: break
            continue
        if started: para.append(s)
state["headline"] = " ".join(para)[:420]

# --- the board: Phase -> Feature -> Story, from PLAN.md ----------------------
# Phase   = "## Phase ..."          (or any "## " heading in a plan document)
# Feature = "### ..."
# Story   = "- [ ] ..." / "- [x] ..."  with everything after an em-dash as evidence
board, phase, feature = [], None, None
plan_doc = next((d for d in ("docs/PLAN.md", "PLAN.md", "docs/PORT_PLAN.md",
                             "docs/ROADMAP.md", "docs/NEXT.md") if (proj / d).exists()), None)
state["board_doc"] = plan_doc or ""
plan_lines = read(plan_doc or "").splitlines()
note_re = re.compile(r"^\s+[-*]\s+(\d{4}-\d{2}-\d{2})\s+@([\w-]+):\s*(.+)$")
for line in plan_lines:
    nm = note_re.match(line)
    if nm and phase and feature and feature["stories"]:
        feature["stories"][-1].setdefault("notes", []).append(
            {"date": nm.group(1), "who": nm.group(2), "text": nm.group(3)})
        continue
    if line.startswith("## "):
        phase = {"phase": line[3:].strip(), "features": []}
        board.append(phase); feature = None
    elif line.startswith("### ") and phase:
        raw = line[4:].strip()
        feature = {"feature": raw.replace("{refined}", "").strip(),
                   "refined": "{refined}" in raw, "stories": []}
        phase["features"].append(feature)
    else:
        m = re.match(r"^\s*[-*]\s*\[([ xX~?cC])\]\s*(.+)$", line)
        if m and phase:
            if feature is None:
                feature = {"feature": "", "refined": False, "stories": []}
                phase["features"].append(feature)
            body = m.group(2).strip()
            blocked = ""
            if "BLOCKED:" in body:
                body, blocked = (x.strip() for x in body.split("BLOCKED:", 1))
            # @role assigns the story; #model names the model to run it on.
            who = re.search(r"(?<![\w/])@([a-z][\w-]*)", body)
            mdl = re.search(r"(?<![\w/])#([a-z][\w.-]*)", body)
            pri = re.search(r"(?<![\w/])!(10|[1-9])(?![\w])", body)
            tid = re.search(r"(?<![\w/])#(\d+)(?![\w])", body)
            chk = re.search(r"(?<![\w/])\+([a-z][\w-]*)", body)
            body = re.sub(r"(?<![\w/])(?:[@#+][a-z][\w.-]*|![0-9]{1,2}(?![\w])|#\d+(?![\w]))", "", body).strip()
            parts = re.split(r"\s+[\u2014-]{1,2}\s+", body, maxsplit=1)
            mark = m.group(1).lower()
            feature["stories"].append({
                "state": {"x": "done", "~": "wip", "?": "backlog", "c": "check"}.get(mark, "open"),
                "checker": chk.group(1) if chk else "",
                "refined": bool(who) and bool(parts[1].strip() if len(parts) > 1 else ""),
                "done": mark == "x",
                "line": line.rstrip(),
                "text": re.sub(r"[`*]", "", parts[0]).strip(),
                "evidence": re.sub(r"[`*]", "", parts[1]).strip() if len(parts) > 1 else "",
                "id": int(tid.group(1)) if tid else 0,
                "prio": int(pri.group(1)) if pri else 5,
                "blocked": blocked,
                "notes": [],
                "who": who.group(1) if who else "",
                "model": mdl.group(1) if mdl else "",
            })
# Cancelled and Archive are kept even when empty: they are destinations, and a
# destination that disappears when it is empty cannot be moved to.
board = [p for p in board
         if any(f["stories"] for f in p["features"])
         or re.match(r"^(Ideas|Cancelled|Archive)\b", p["phase"], re.I)]
for ph in board:
    for ft in ph["features"]:
        st = ft["stories"]
        ft["done_n"] = sum(1 for s in st if s["state"] == "done")
        ft["total"] = len(st)
        ft["pct"] = round(100 * ft["done_n"] / ft["total"]) if ft["total"] else 0
    st = [s for ft in ph["features"] for s in ft["stories"]]
    fts = [ft for ft in ph["features"] if ft["total"]]
    ph["done_n"] = sum(1 for s in st if s["state"] == "done")
    ph["total"] = len(st)
    ph["pct"] = round(100 * ph["done_n"] / ph["total"]) if ph["total"] else 0
    ph["features_done"] = sum(1 for ft in fts if ft["pct"] == 100)
    ph["features_total"] = len(fts)
state["board"] = board

# --- project-specific rules, from the project's own CLAUDE.md -----------------
# The shared rulebook is the workshop's RULES.md. A project can also have rules
# that are true only there. Those live under a "rules" heading in CLAUDE.md, which is the file
# guaranteed to be read at session start.
prules, grab = [], False
for line in read("CLAUDE.md").splitlines():
    if line.startswith("#"):
        grab = bool(re.search(r"rule", line, re.I))
        continue
    if not grab:
        continue
    s = line.strip()
    if not s:
        continue
    m = re.match(r"^(?:[-*]\s*)?\*\*(.+?)\*\*[.:]?\s*(.*)$", s)
    if m:
        prules.append({"rule": re.sub(r"[`*]", "", m.group(1)).strip(),
                       "detail": re.sub(r"[`*]", "", m.group(2)).strip()})
    elif prules:
        prules[-1]["detail"] = (prules[-1]["detail"] + " " + re.sub(r"[`*]", "", s)).strip()
state["project_rules"] = prules

# --- how old is each ticket ---------------------------------------------------
# One `git blame` over the plan file, mapped line -> when that line last changed.
# Last-touched, not created: a ticket edited today is not stale, and staleness is
# the thing worth seeing.
if plan_doc:
    try:
        bl = subprocess.run(["git", "blame", "--line-porcelain", "--", plan_doc],
                            cwd=proj, capture_output=True, text=True, timeout=60).stdout
        stamps, cur_t = {}, None
        for ln in bl.splitlines():
            if ln.startswith("author-time "):
                cur_t = int(ln.split()[1])
            elif ln.startswith("\t") and cur_t:
                stamps.setdefault(ln[1:].strip(), cur_t)
        import time as _t
        now = _t.time()
        for ph in board:
            for ft in ph["features"]:
                for s in ft["stories"]:
                    ts = stamps.get(s["line"].strip())
                    if ts:
                        s["touched"] = _t.strftime("%Y-%m-%d", _t.localtime(ts))
                        s["age_days"] = int((now - ts) // 86400)
    except Exception:
        pass

# --- when was each ticket first written -------------------------------------
# Walk the plan file's revisions oldest-first and record the first one in which a
# story's text appears. Matching on TEXT, not on the id: ids were assigned in one
# pass long after most of these tickets existed, so an id would date them all to
# that pass. Costs one `git show` per revision of one file.
if plan_doc:
    try:
        revs = subprocess.run(["git", "log", "--reverse", "--format=%H %at", "--", plan_doc],
                              cwd=proj, capture_output=True, text=True, timeout=60).stdout.split()
        pairs = list(zip(revs[0::2], revs[1::2]))
        key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())[:44]
        first = {}
        for sha, ts in pairs:
            blob = subprocess.run(["git", "show", f"{sha}:{plan_doc}"], cwd=proj,
                                  capture_output=True, text=True).stdout
            for line in blob.splitlines():
                m = re.match(r"^\s*[-*]\s*\[[ xX~?cC]\]\s*(.+)$", line)
                if not m:
                    continue
                body = re.sub(r"(?<![\w/])(?:[@#+][a-z][\w.-]*|![0-9]{1,2}(?![\w])|#\d+(?![\w]))",
                              "", m.group(1))
                body = re.split(r"\s+[\u2014-]{1,2}\s+", body, maxsplit=1)[0]
                first.setdefault(key(body), int(ts))
        import time as _t2
        for ph in board:
            for ft in ph["features"]:
                for s in ft["stories"]:
                    ts = first.get(key(s["text"]))
                    if ts:
                        s["created"] = _t2.strftime("%Y-%m-%d", _t2.localtime(ts))
                        s["age_created"] = int((_t2.time() - ts) // 86400)
    except Exception:
        pass

# --- logbook: recent commits -------------------------------------------------
log = subprocess.run(["git", "log", "-40", "--date=short", "--format=%h\x1f%ad\x1f%s"],
                     cwd=proj, capture_output=True, text=True).stdout
state["log"] = [dict(zip(("sha", "date", "subject"), l.split("\x1f")))
                for l in log.splitlines() if l.count("\x1f") == 2]

# --- what documents this project actually has --------------------------------
state["docs_present"] = sorted(p.name for p in (proj / "docs").glob("*.md")) \
    if (proj / "docs").is_dir() else []

state["generated"] = subprocess.run(["date", "+%Y-%m-%d %H:%M"],
                                    capture_output=True, text=True).stdout.strip()
state["head"] = subprocess.run(["git", "log", "-1", "--format=%h %s"], cwd=proj,
                               capture_output=True, text=True).stdout.strip()
print(json.dumps(state, indent=1))
