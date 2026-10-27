#!/usr/bin/env python3
"""Collect every project in the workshop into one JSON blob.

Discovery, not configuration: any sibling directory of the Workshop that is a git
repository is a project, so a project created tomorrow appears without editing
this file. Each one is passed through collect.py, which reads whatever Workshop
conventions that project happens to follow and tolerates the ones it does not.

Usage:  python3 collect_all.py <workshop-dir> > workshop.json
"""
import json, re, subprocess, sys, os
from pathlib import Path

shop = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
root = shop.parent
here = Path(__file__).resolve().parent
# The Workshop is a project too: it has work, decisions and history like any
# other, and until it was on the board none of that was ever written down.
SKIP = set()

projects = []
for d in sorted((p for p in root.iterdir() if p.is_dir()),
                key=lambda p: (p.name != shop.name, p.name.lower())):
    if d.name in SKIP or d.name.startswith((".", "_")) or not (d / ".git").exists():
        continue
    r = subprocess.run([sys.executable, str(here / "collect.py"), str(d), str(shop)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        projects.append({"name": d.name, "error": r.stderr.strip()[-400:], "components": [],
                         "builds": [], "board": [], "log": [], "rules": [], "freshness": []})
        continue
    projects.append(json.loads(r.stdout))

# --- the work left, in money: agents.py's own arithmetic, so the page and `agents.py cost` agree ---
def price_projects(projects):
    """Annotate every open story with the AI it will run on and its estimated cost, and every
    feature, phase and project with planned / all-on-opus / spent. Nothing here if models.json or
    agents.py is missing: the page then simply has no money in it."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("agents", shop / "agents.py")
        A = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(A)
        cfg0 = A.models_cfg()
    except (Exception, SystemExit):
        return {}
    spent = {}
    for m in A.all_agents():
        if m.get("story_id"):
            k = (m.get("project"), m["story_id"])
            spent[k] = spent.get(k, 0) + (m.get("cost_usd") or 0)
    parked = re.compile(r"^(Ideas|Cancelled|Archive)\b", re.I)
    for p in projects:
        pdir = root / p["name"]
        if not p.get("board") or not pdir.is_dir():
            continue
        cfg, roles = A.models_cfg(pdir), A.roles_cfg(pdir)
        top = "opus" if "opus" in cfg["models"] else max(cfg["models"], key=lambda k: cfg["models"][k]["tier"])
        tot = {"plan": 0.0, "top": 0.0, "spent": 0.0}
        for ph in p["board"]:
            pt = {"plan": 0.0, "top": 0.0, "spent": 0.0}
            for ft in ph["features"]:
                ftc = {"plan": 0.0, "top": 0.0, "spent": 0.0}
                for st in ft["stories"]:
                    ftc["spent"] += spent.get((p["name"], st.get("id")), 0)
                    alias = A.planned_alias(cfg, roles, st) or top
                    st["alias"] = alias
                    st["runs_here"] = not A.provider_ready(cfg, cfg["models"][alias]["provider"], pdir)
                    real = A.explain(cfg, roles, st, A.runs_of(p["name"], st.get("id"))) if st.get("id") else None
                    if real:
                        st["real"] = real         # what it really cost, the estimate, and why
                    if st["state"] == "done":
                        continue
                    st["est"] = round(A.story_cost(cfg, alias, st.get("size") or "M"), 2)
                    ftc["plan"] += st["est"]
                    ftc["top"] += A.story_cost(cfg, top, st.get("size") or "M")
                ft["cost"] = {k: round(v, 2) for k, v in ftc.items()}
                for k in pt:
                    pt[k] += ftc[k]
            ph["cost"] = {k: round(v, 2) for k, v in pt.items()}
            if not parked.match(ph["phase"]):
                for k in tot:
                    tot[k] += pt[k]
        p["cost"] = {**{k: round(v, 2) for k, v in tot.items()}, "top_alias": top,
                     "ais": A.project_ais(pdir)}
    shopcfg = json.loads((shop / "workshop.json").read_text()) if (shop / "workshop.json").exists() else {}
    mine = shopcfg.get("providers")
    providers = {n: {"name": pr["name"], "how": pr.get("how", ""),
                     "mine": mine is None or n in mine,
                     "key_env": pr.get("key_env", ""),
                     "key_ok": not pr.get("key_env") or bool(A.api_key(pr["key_env"]))}
                 for n, pr in cfg0["providers"].items()}
    models = {k: {"model": m["model"], "provider": m["provider"], "price": m["price"], "tier": m["tier"],
                  "effort": m.get("effort", ""), "good_for": m.get("good_for", ""),
                  "runs_here": not A.provider_ready(cfg0, m["provider"])}
              for k, m in cfg0["models"].items()}
    return {"models": models, "providers": providers, "sizes": cfg0.get("sizes", {}),
            "cache": {k: m.get("cache") for k, m in cfg0["models"].items()},
            "budget": cfg0.get("agents", {}).get("default_budget_usd", 2.0)}


priced = price_projects(projects)
models = priced.get("models", {})

rules = projects[0]["rules"] if projects else []
for p in projects:
    p.pop("rules", None)

roles = {}
for cand in (shop / "roles.json",):
    if cand.exists():
        roles = json.loads(cand.read_text())
        for r in roles.get("roles", []):
            b = shop / r.get("brief", "")
            r["brief_text"] = b.read_text() if r.get("brief") and b.exists() else ""

# a one-line-per-project standing report: what is next, what waits on a person
def days_since(datestr):
    try:
        import datetime
        d = datetime.date.fromisoformat(datestr)
        return (datetime.date.today() - d).days
    except Exception:
        return None


def digest(p):
    live = [s for ph in p.get("board", [])
            for f in ph["features"] for s in f["stories"]
            if not re.match(r"^(Ideas|Cancelled|Archive)\b", ph["phase"], re.I)]
    lad = next((ph for ph in p.get("board", []) if re.search(r"ladder", ph["phase"], re.I)), None)
    ladder_st = [s for f in lad["features"] for s in f["stories"]] if lad else []
    front = next((s for s in ladder_st if s["state"] != "done"), None)
    # is this project moving, and if not, why not
    held = [s for ph in p.get("board", []) for f in ph["features"] for s in f["stories"]
            if s.get("blocked") and not re.match(r"^(Ideas|Cancelled|Archive)\b", ph["phase"], re.I)]
    return {
        "name": p["name"],
        "last": (p.get("log") or [{}])[0].get("date", ""),
        "last_subject": (p.get("log") or [{}])[0].get("subject", ""),
        "front": front["text"] if front else "",
        "ladder": f"{sum(1 for s in ladder_st if s['state']=='done')}/{len(ladder_st)}" if ladder_st else "",
        "doing": [s for s in live if s["state"] == "wip"],
        "check": [s for s in live if s["state"] == "check"],
        "held": [s for s in live if s.get("blocked")],
        # waiting on him NOW: his own live tickets, plus checks that have actually
        # arrived. Being the checker on something design has not started yet is not
        # waiting -- counting it made ten tickets look like his queue when three were.
        "dennis": [s for s in live
                   if (s.get("who") == "dennis" and s["state"] in ("open", "wip"))
                   or (s.get("checker") == "dennis" and s["state"] == "check")],
        "later": [s for s in live if s.get("checker") == "dennis"
                  and s["state"] in ("open", "wip")],
        "open_n": sum(1 for s in live if s["state"] in ("open", "wip", "check")),
        "days_quiet": days_since((p.get("log") or [{}])[0].get("date", "")),
        "done_n": sum(1 for s in live if s["state"] == "done"),
    }

import re as _re
# skills: what exists in the repo, and whether it is linked into ~/.claude/skills
skills = []
skdir = shop / "skills"
installed = Path.home() / ".claude" / "skills"
if skdir.is_dir():
    for d in sorted(p for p in skdir.iterdir() if p.is_dir()):
        sk = d / "SKILL.md"
        if not sk.exists():
            continue
        body = sk.read_text(errors="replace")
        m = re.search(r"^---\s*\n(.*?)\n---", body, re.S)
        meta = {}
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
        link = installed / d.name
        skills.append({
            "roles": [x.strip() for x in meta.get("roles", "").split(",") if x.strip()],
            "name": meta.get("name", d.name),
            "description": meta.get("description", ""),
            "file": f"skills/{d.name}/SKILL.md",
            "words": len(body.split()),
            "installed": link.exists(),
            "body": body,
        })

# who says they are working. Self-reported: board.py checkin writes these.
sessions, git_seen = {}, {}
sdir = shop / ".sessions"
if sdir.is_dir():
    import time as _t
    for j in sdir.glob("*.json"):
        try:
            s = json.loads(j.read_text())
            s["mins"] = int((_t.time() - s.get("at", 0)) // 60)
            sessions[s["who"]] = s
        except Exception:
            pass

# a seat that has been committing is obviously alive, whether or not it checked
# in. Weaker than a check-in -- it says "was working", not "is open" -- so it is
# reported as such rather than dressed up as presence.
import subprocess as _sp
for p in projects:
    for e in (p.get("log") or []):
        m = re.search(r"@([a-z][\w-]*)", e.get("subject", ""))
        if not m:
            continue
        who = m.group(1)
        if who in sessions:
            continue
        prev = git_seen.get(who)
        if not prev or e["date"] > prev["date"]:
            git_seen[who] = {"date": e["date"], "what": e["subject"][:90], "project": p["name"]}

# what Dennis has sent, newest last
outbox = ""
op = shop / ".outbox.md"
if op.exists():
    outbox = op.read_text(errors="replace").strip()[-4000:]

# messages, parsed into items so the page can be a mail client rather than a
# wall of text. One store: .inbox/<seat>.md unread, <seat>.read.md read,
# .outbox.md what Dennis sent.
def parse_mail(text, folder, seat, unread):
    out = []
    for chunk in re.split(r"\n(?=## )", text.strip()):
        h = re.match(r"##\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[—-]{1,2}?\s*(?:from @([\w-]+)|→ ([\w-]+))?",
                     chunk)
        if not h:
            continue
        body = chunk.split("\n", 1)[1].strip() if "\n" in chunk else ""
        out.append({
            "when": h.group(1),
            "frm": h.group(2) or "dennis",
            "to": h.group(3) or seat,
            "folder": folder,
            "seat": seat,
            "unread": unread,
            "subject": (body.split("\n", 1)[0] or "(no text)")[:120],
            "body": body,
        })
    return out


mail, inbox = [], {}
idir = shop / ".inbox"
if idir.is_dir():
    for m in sorted(idir.glob("*.md")):
        seat = m.name[:-8] if m.name.endswith(".read.md") else m.stem
        unread = not m.name.endswith(".read.md")
        body = m.read_text(errors="replace")
        items = parse_mail(body, "in", seat, unread)
        mail += items
        if unread and items:
            inbox[seat] = {"n": len(items), "text": body.strip()[-4000:]}
op = shop / ".outbox.md"
if op.exists():
    mail += parse_mail(op.read_text(errors="replace"), "out", "dennis", False)
mail.sort(key=lambda x: x["when"], reverse=True)
history = {}

# what Dennis has sent, newest last
outbox = ""
op = shop / ".outbox.md"
if op.exists():
    outbox = op.read_text(errors="replace").strip()[-4000:]

# token volume on this machine -- see dashboard/usage.py for what it is and is not
usage = {}
try:
    usage = json.loads(_sp.run([sys.executable, str(here / "usage.py"), "14"],
                               capture_output=True, text=True, timeout=120).stdout or "{}")
except Exception:
    usage = {}

# unread messages per seat
inbox = {}
idir = shop / ".inbox"
if idir.is_dir():
    for m in idir.glob("*.md"):
        if m.name.endswith(".read.md"):
            continue
        body = m.read_text(errors="replace").strip()
        if body:
            inbox[m.stem] = {"n": body.count("\n## ") + (1 if body.startswith("## ") else 0),
                             "text": body[-4000:]}
# what has already been read, newest first, so a thread can be looked back at
history = {}
if idir.is_dir():
    for m in idir.glob("*.read.md"):
        body = m.read_text(errors="replace").strip()
        if body:
            history[m.name[:-8]] = body[-4000:]

howto = []
for md in sorted((shop / "howto").glob("*.md")) if (shop / "howto").is_dir() else []:
    body = md.read_text(errors="replace")
    title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), md.stem)
    lead = next((l.strip() for l in body.splitlines()
                 if l.strip() and not l.startswith("#")), "")
    howto.append({"file": f"howto/{md.name}", "title": title,
                  "lead": lead.replace("**", ""), "body": body})

print(json.dumps({
    "code_sig": str(int((here / "render_workshop.py").stat().st_mtime)),
    "generated": subprocess.run(["date", "+%Y-%m-%d %H:%M"], capture_output=True,
                                text=True).stdout.strip(),
    "root": str(root),
    "rules": rules,
    "roles": roles,
    "models": models,
    "providers": priced.get("providers", {}),
    "agent_budget": priced.get("budget", 2.0),
    "sizes": priced.get("sizes", {}),
    "cache": priced.get("cache", {}),
    "status": [digest(p) for p in projects if p.get("board")],
    "howto": howto,
    "skills": skills,
    "sessions": sessions,
    # which machine drew this page. A check-in cannot cross machines (#95), so
    # the page has to name where it is standing before it says who is absent.
    "machine": __import__("socket").gethostname(),
    "git_seen": git_seen,
    "inbox": inbox,
    "inbox_history": history,
    "mail": mail,
    "usage": usage,
    "outbox": outbox,
    "skills_dir": str(installed),
    "projects": projects,
}, indent=1))
