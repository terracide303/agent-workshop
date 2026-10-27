#!/usr/bin/env python3
"""The other seats, run by @workshop: start them, watch them, talk to them, stop them.

Every agent is one headless Claude Code session (`claude -p`), so every seat gets
the same harness -- tools, skills, CLAUDE.md, permissions -- whichever AI is behind
it. A DeepSeek seat is Claude Code pointed at DeepSeek's Anthropic-compatible
endpoint (models.json, "providers"). The model is picked per story: its #alias, or
the routing kind @workshop names, or the role's default in roles.json.

    agents.py models                         what can run here, and what it costs
    agents.py route  <kind>                  which alias a kind of task goes to
    agents.py start  <project> --role design [--story "part of the text"]
                     [--model ds-flash | --kind routine] [--prompt "..."]
                     [--budget 1.50] [--wait]
    agents.py list   [--all]                 every agent: state, model, tokens, cost, doing
    agents.py next   <project> [--budget 2] [--dry-run]
                                             Workshop's dispatch: start the next ready card of every
                                             seat that has one and is free
    agents.py autopilot <project> [--on | --off] [--daily 5]
                                             Ready cards are picked up by themselves, within a daily
                                             budget; this computer only (.agents/autopilot.json)
    agents.py autopilot --tick               one round for every project that has it on (the page
                                             server runs this every minute; cron can too)
    agents.py status <id>                    one agent in detail, with its last steps
    agents.py tail   <id> [-n 30] [--follow] what it did, readable
    agents.py send   <id> "message"          the next instruction, in the same session
    agents.py wait   <id> [--timeout 600]    block until it has finished its turn
    agents.py stop   <id>                    kill it now (its session can be resumed)
    agents.py clear  <id>|--done             end the session for good: next work starts fresh
    agents.py cost   <project>               the work left, in money: per phase and feature
    agents.py why    <project> <#id>         what a story really cost, against the estimate, and why
    agents.py ais    <project> [--use anthropic,deepseek]
                                             which AIs this project uses, and what the work left
                                             would cost with every other choice
    agents.py report                         cost and outcome per model and per kind
    agents.py selftest                       the checks below, made to fire

<id> may be any unique prefix. State lives in .agents/ beside this file and never
leaves this computer: it is one machine's processes, not shared truth (that is the
board). Costs are this file's arithmetic from the token counts, with models.json's
prices; for Claude it is checked against Claude Code's own figure.
"""
import argparse, json, os, re, signal, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):   # same reason as board.py: em-dashes on a cp1252 console
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SHOP = Path(os.path.abspath(__file__)).parent   # not resolve(): a symlinked workshop keeps its siblings
ROOT = SHOP.parent
STATE = Path(os.environ.get("AGENTS_STATE") or SHOP / ".agents")
LIVE = ("starting", "running")
UNATTENDED = ("You run UNATTENDED: nobody will answer a question. If you need the human, "
              "send it with ../workshop/board.py msg and end your turn. Finish with one short "
              "paragraph: what you did, what proves it, and what is left.")


# ---- configuration ----------------------------------------------------------

def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def models_cfg(project_dir=None):
    """models.json, or the project's docs/models.json when it has one (as roles.json)."""
    if project_dir and (Path(project_dir) / "docs" / "models.json").exists():
        return load_json(Path(project_dir) / "docs" / "models.json")
    cfg = load_json(SHOP / "models.json")
    if not cfg:
        sys.exit("FAIL  models.json is missing or not valid JSON")
    return cfg


def roles_cfg(project_dir=None):
    if project_dir and (Path(project_dir) / "docs" / "roles.json").exists():
        return load_json(Path(project_dir) / "docs" / "roles.json", {})
    return load_json(SHOP / "roles.json", {})


def project_ais(project_dir):
    """The providers a project has chosen (docs/ais.json), or None: all that can run."""
    if not project_dir:
        return None
    return (load_json(Path(project_dir) / "docs" / "ais.json", {}) or {}).get("use")


def provider_ready(cfg, name, project_dir=None):
    """'' when the provider can run here, else why not."""
    p = cfg["providers"].get(name)
    if p is None:
        return f"provider {name!r} is not in models.json"
    chosen = project_ais(project_dir)
    if chosen is not None and name not in chosen:
        return f"this project does not use {p['name']} (docs/ais.json; agents.py ais to change it)"
    shop = load_json(SHOP / "workshop.json", {}) or {}
    have = shop.get("providers")
    if have is not None and name not in have:
        return f"{p['name']} is not in workshop.json's providers (re-run ./start.sh to add it)"
    if p.get("key_env") and not os.environ.get(p["key_env"]):
        return f"{p['name']} needs {p['key_env']} set in the environment"
    return ""


def route(cfg, kind, project_dir=None):
    """The first alias for this kind whose provider can run here."""
    r = cfg["routing"].get(kind)
    if not r or kind.startswith("_"):
        kinds = ", ".join(k for k in cfg["routing"] if not k.startswith("_"))
        sys.exit(f"FAIL  unknown kind {kind!r}; the kinds are: {kinds}")
    why = []
    for alias in r["use"]:
        m = cfg["models"].get(alias)
        if not m:
            why.append(f"{alias}: not in models")
            continue
        no = provider_ready(cfg, m["provider"], project_dir)
        if not no:
            return alias, why
        why.append(f"{alias}: {no}")
    sys.exit(f"FAIL  nothing can run kind {kind!r} here:\n      " + "\n      ".join(why))


def environment(cfg, alias, base=None):
    """The process environment for one agent: the provider's variables filled in."""
    m = cfg["models"][alias]
    p = cfg["providers"][m["provider"]]
    env = dict(os.environ if base is None else base)
    for k in p.get("unset", []):
        env.pop(k, None)
    key = env.get(p["key_env"], "") if p.get("key_env") else ""
    for k, v in p.get("env", {}).items():
        env[k] = v.replace("${key}", key).replace("${model}", m["model"])
    return env


def command(cfg, meta, prompt, resume):
    """The claude command line for one turn."""
    m = cfg["models"][meta["alias"]]
    a = cfg.get("agents", {})
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", m["model"], "--effort", meta.get("effort") or m.get("effort", "medium"),
           "--permission-mode", a.get("permission_mode", "acceptEdits"),
           "--add-dir", str(SHOP)]
    if a.get("allowed_tools"):
        cmd += ["--allowedTools", *a["allowed_tools"]]
    cmd += ["--resume", meta["session"]] if resume else ["--session-id", meta["session"]]
    return cmd


# ---- cost -------------------------------------------------------------------

def price_of(cfg, alias):
    m = cfg["models"][alias]
    pin, pout = m["price"]
    # Anthropic's ratios unless models.json states them: a cache read is 0.1x input, and Claude Code
    # writes its cache with the 1-hour lifetime, which is 2x input (the 5-minute one would be 1.25x).
    read, write = m.get("cache", [pin * 0.1, pin * 2.0])
    return pin, pout, read, write


def cost(cfg, alias, tok):
    pin, pout, read, write = price_of(cfg, alias)
    return (tok.get("in", 0) * pin + tok.get("out", 0) * pout +
            tok.get("cache_read", 0) * read + tok.get("cache_write", 0) * write) / 1e6


def add_usage(tok, u):
    tok["in"] = tok.get("in", 0) + (u.get("input_tokens") or 0)
    tok["out"] = tok.get("out", 0) + (u.get("output_tokens") or 0)
    tok["cache_read"] = tok.get("cache_read", 0) + (u.get("cache_read_input_tokens") or 0)
    tok["cache_write"] = tok.get("cache_write", 0) + (u.get("cache_creation_input_tokens") or 0)


# ---- state ------------------------------------------------------------------

def meta_path(aid):
    return STATE / f"{aid}.json"


def save(meta):
    STATE.mkdir(parents=True, exist_ok=True)
    meta["updated"] = datetime.now().isoformat(timespec="seconds")
    tmp = meta_path(meta["id"]).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    os.replace(tmp, meta_path(meta["id"]))


def all_agents():
    if not STATE.exists():
        return []
    out = [load_json(p) for p in sorted(STATE.glob("*.json")) if not p.name.endswith(".tmp")]
    return [m for m in out if m and "id" in m]


def find(prefix):
    hits = [m for m in all_agents() if m["id"].startswith(prefix)]
    if len(hits) > 1:      # a cleared session is history: the prefix means the one still in play
        hits = [m for m in hits if m["status"] != "cleared"] or hits
    if len(hits) != 1:
        sys.exit(f"FAIL  {'no' if not hits else len(hits)} agents match {prefix!r}" +
                 ("" if not hits else ": " + ", ".join(m["id"] for m in hits)))
    return refresh(hits[0])


def alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def refresh(meta):
    """A live state whose supervisor is gone died without saying so: say it."""
    if meta["status"] in LIVE and not alive(meta.get("pid")):
        meta["status"] = "failed"
        meta["why"] = "the supervisor process is gone (machine slept, killed, or crashed)"
        save(meta)
    return meta


def ledger(meta):
    row = {k: meta.get(k) for k in ("id", "role", "project", "alias", "kind", "story", "story_id",
                                     "size", "status", "cost_usd", "turns")}
    row["date"] = datetime.now().strftime("%Y-%m-%d")
    row["tokens"] = sum(meta.get("tokens", {}).values())
    with open(STATE / "ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


# ---- the board: a story's text and #alias, without importing board.py's CLI ---

_BOARD = None


def board_module():
    """board.py as a module. It parses its command line at import, so give it none and keep its usage
    message quiet; the functions above that line are what we need."""
    global _BOARD
    if _BOARD is None:
        import contextlib, importlib.util, io
        spec = importlib.util.spec_from_file_location("board", SHOP / "board.py")
        _BOARD = importlib.util.module_from_spec(spec)
        saved, sys.argv = sys.argv, ["board.py"]
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    spec.loader.exec_module(_BOARD)
                except SystemExit:
                    pass
        finally:
            sys.argv = saved
    return _BOARD


def story_of(project_dir, match):
    board = board_module()
    _, _, stories = board.load(str(project_dir))
    return board.find_one(stories, match)


# ---- the supervisor: runs one turn of claude and keeps the state current --------

def supervise(aid, prompt, resume):
    meta = load_json(meta_path(aid))
    cfg = models_cfg(meta["project_dir"])
    env = environment(cfg, meta["alias"])
    log = open(STATE / f"{aid}.log", "a", encoding="utf-8")
    log.write(json.dumps({"type": "agents.turn", "prompt": prompt, "resume": resume,
                          "at": datetime.now().isoformat(timespec="seconds")}) + "\n")
    meta.update(status="running", pid=os.getpid(), why="")
    meta["turns"] = meta.get("turns", 0) + 1
    save(meta)
    try:
        child = subprocess.Popen(command(cfg, meta, prompt, resume), cwd=meta["project_dir"], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace")
    except OSError as e:
        meta.update(status="failed", why=f"could not start claude: {e}")
        save(meta)
        return
    meta["child"] = child.pid
    save(meta)
    # Token counts: while the turn runs, the assistant events give a LIVE ESTIMATE (they carry the
    # usage of an answer's first chunk, so output is undercounted); the result event carries the
    # turn's real usage and replaces the estimate. Measured 2026-10-27: 20 live vs 330 real output.
    seen, last_save = set(), 0.0
    before = dict(meta.get("tokens", {}))
    tok = dict(before)
    for line in child.stdout:
        log.write(line)
        log.flush()
        try:
            ev = json.loads(line)
        except ValueError:
            meta["last"] = line.strip()[:200]
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            meta["served_by"] = ev.get("model")
        elif t == "assistant":
            msg = ev.get("message", {})
            if msg.get("id") and msg["id"] not in seen and msg.get("usage"):
                seen.add(msg["id"])          # one API call can arrive as several events
                add_usage(tok, msg["usage"])
            for b in msg.get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    meta["last"] = b["text"].strip()[:300]
                elif b.get("type") == "tool_use":
                    meta["doing"] = tool_line(b)
                    meta["steps"] = meta.get("steps", 0) + 1
        elif t == "result":
            meta["result"] = (ev.get("result") or "")[:4000]
            meta["denials"] = [d.get("tool_name") for d in ev.get("permission_denials") or []]
            meta["status"] = "failed" if ev.get("is_error") else "idle"
            meta["why"] = "" if not ev.get("is_error") else ev.get("subtype", "error")
            if ev.get("usage"):
                tok = dict(before)
                add_usage(tok, ev["usage"])          # this turn only: the real count
            if meta["provider"] == "anthropic" and ev.get("total_cost_usd") is not None:
                # Claude Code's figure is already the whole session's, resumed turns included
                meta["claude_code_cost_usd"] = round(ev["total_cost_usd"], 4)
        meta["tokens"] = tok
        meta["cost_usd"] = round(cost(cfg, meta["alias"], tok), 4)
        if meta["cost_usd"] > meta["budget"]:
            meta.update(status="over-budget",
                        why=f"spent ${meta['cost_usd']:.4g} of a ${meta['budget']:.4g} budget")
            save(meta)
            child.terminate()
            break
        if time.time() - last_save > 1.0:
            save(meta)
            last_save = time.time()
    rc = child.wait()
    if meta["status"] == "running":     # ended without a result event
        meta.update(status="failed", why=f"claude exited {rc} without a result; see tail")
    meta["pid"] = meta["child"] = None
    # One agent per card: when its card is closed (done, or handed to its checker) the agent is
    # cleared, and the next card gets a new one with that card's own AI. A card that is NOT closed
    # keeps its agent, so the human can still send it the missing piece.
    if meta["status"] == "idle" and meta.get("story_id"):
        try:
            st = next((x for x in load_board(meta["project_dir"]) if x["id"] == meta["story_id"]), None)
        except (Exception, SystemExit):
            st = None
        if st and st["state"] in ("done", "check"):
            meta.update(status="cleared", why=f"card #{meta['story_id']} is {st['state']}: agent cleared")
    save(meta)
    if meta["status"] != "idle":
        ledger(meta)


def tool_line(b):
    i = b.get("input", {})
    what = i.get("command") or i.get("file_path") or i.get("pattern") or i.get("description") or ""
    return f"{b.get('name')} {str(what).splitlines()[0][:120] if what else ''}".strip()


def spawn(aid, prompt, resume):
    """The supervisor in its own process group, so stop can take the whole tree."""
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(SHOP))
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008   # DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    args = [sys.executable, str(Path(__file__).resolve()), "_run", aid, "--prompt", prompt]
    p = subprocess.Popen(args + (["--resume"] if resume else []), **kw)
    meta = load_json(meta_path(aid))
    meta.update(pid=p.pid, status="starting")
    save(meta)


# ---- commands ---------------------------------------------------------------

def project_dir(name):
    p = Path(name)
    if not p.is_absolute() and not p.exists():
        p = ROOT / name
    if not p.is_dir():
        sys.exit(f"FAIL  no project directory {name!r} (beside the workshop, or a path)")
    return p.resolve()


def cmd_models(a):
    cfg = models_cfg()
    print(f"{'alias':<14}{'tier':<6}{'in/out $ per 1M':<18}{'effort':<8}{'model':<22}can run here")
    for alias, m in cfg["models"].items():
        no = provider_ready(cfg, m["provider"])
        print(f"{alias:<14}{m['tier']:<6}{m['price'][0]:>6.2f} / {m['price'][1]:<8.2f}"
              f"{m.get('effort',''):<8}{m['model']:<22}{'yes' if not no else 'no -- ' + no}")
    print("\nkinds (cheapest acceptable first; the first that can run is used):")
    for k, r in cfg["routing"].items():
        if not k.startswith("_"):
            print(f"  {k:<11} {' > '.join(r['use']):<32} {r['what']}")


def cmd_route(a):
    cfg = models_cfg()
    alias, skipped = route(cfg, a.kind)
    for s in skipped:
        print(f"skip  {s}")
    print(alias)


def cmd_start(a):
    pdir = project_dir(a.project)
    cfg = models_cfg(pdir)
    story = story_of(pdir, a.story) if a.story else None
    source, alias, kind = "", None, a.kind
    if a.model:
        alias, source = a.model, "--model"
    elif story and story.get("model") and story["model"] in cfg["models"]:
        alias, source = story["model"], f"the story's #{story['model']}"
    elif kind:
        alias, _ = route(cfg, kind, pdir)
        source = f"kind {kind}"
    else:
        role = next((r for r in roles_cfg(pdir).get("roles", []) if r["id"] == a.role), None)
        alias = role and role.get("model")
        source = f"@{a.role}'s default in roles.json"
    if alias not in cfg["models"]:
        sys.exit(f"FAIL  model {alias!r} ({source}) is not an alias in models.json -- see agents.py models")
    m = cfg["models"][alias]
    no = provider_ready(cfg, m["provider"], pdir)
    if no:
        sys.exit(f"FAIL  {alias}: {no}")
    for o in all_agents():
        o = refresh(o)
        if o["status"] in LIVE and o["project"] == pdir.name and o["role"] == a.role:
            sys.exit(f"FAIL  @{a.role} already runs on {pdir.name} as {o['id']}: one seat, one session")
    if a.prompt:
        prompt = a.prompt
    else:
        prompt = (f"You are @{a.role} on {pdir.name}. Run `git pull` in both this project and ../workshop "
                  f"first, then read ../workshop/roles/{a.role}.md, then run ../workshop/board.py inbox "
                  f"--who {a.role} and ../workshop/board.py next {pdir.name} --who {a.role}, and do what it says.")
        if story:
            prompt += f" Work on #{story['id']}: {story['text']} -- it closes on: {story['evidence']}."
    prompt += " " + UNATTENDED
    aid = f"{a.role}-{pdir.name}-{datetime.now().strftime('%m%d-%H%M%S')}"
    meta = dict(id=aid, role=a.role, project=pdir.name, project_dir=str(pdir), alias=alias,
                provider=m["provider"], model=m["model"], effort=a.effort or m.get("effort"),
                kind=kind or "", story=(f"#{story['id']} {story['text']}" if story else ""),
                story_id=(story["id"] if story else 0), size=(story.get("size", "") if story else ""),
                session=str(uuid.uuid4()), budget=a.budget if a.budget is not None
                else cfg.get("agents", {}).get("default_budget_usd", 2.0),
                started=datetime.now().isoformat(timespec="seconds"), status="starting",
                tokens={}, cost_usd=0.0, turns=0, chosen_by=source)
    save(meta)
    spawn(aid, prompt, resume=False)
    print(f"started {aid}\n        {alias} = {m['model']} at effort {meta['effort']} ({source}), "
          f"budget ${meta['budget']:.3g}\n        agents.py tail {aid[:20]} --follow")
    if a.wait:
        wait_for(aid, a.timeout)


def dispatch(project, budget=None, dry_run=False, skip=("you", "workshop")):
    """The next ready card for every seat that is free: what board.py next would hand each role,
    one agent per role per project. Returns [(role, story, alias, why-not-or-'')]. Seats that are
    the human's, or Workshop itself, are never started."""
    pdir = project_dir(project)
    cfg, roles = models_cfg(pdir), roles_cfg(pdir)
    stories = load_board(pdir)
    busy = {m["role"] for m in map(refresh, all_agents()) if m["project"] == pdir.name and m["status"] in LIVE}
    plan = []
    for role in sorted({s["who"] for s in stories if s.get("who")}):
        if role in skip:
            continue
        mine = [s for s in stories if s["who"] == role]
        if role in busy:
            continue
        if any(s["state"] == "wip" and not s["blocked"] for s in mine):
            continue        # the seat has something in progress: finishing it is a person's call
        ready = sorted([s for s in mine if s["state"] == "open" and not s["blocked"] and s["feature_refined"]],
                       key=lambda s: (-s.get("feature_prio", 5), -s["prio"]))
        if not ready:
            continue
        st = ready[0]
        alias = planned_alias(cfg, roles, st)
        no = provider_ready(cfg, cfg["models"][alias]["provider"], pdir) if alias else "no AI planned"
        plan.append((role, st, alias, no))
    if dry_run:
        return plan
    for role, st, alias, no in plan:
        if no:
            continue
        a = argparse.Namespace(project=str(pdir), role=role, story=f"#{st['id']}", model=alias, kind=None,
                               effort=None, prompt=None, budget=budget, wait=False, timeout=0)
        try:
            cmd_start(a)
        except SystemExit as e:
            print(f"skip  @{role} #{st['id']}: {e}")
    return plan


def cmd_next(a):
    plan = dispatch(a.project, a.budget, a.dry_run)
    if not plan:
        print("nothing to start: every seat is busy, waiting, or has no ready card")
        return
    for role, st, alias, no in plan:
        print(f"{'would start' if a.dry_run and not no else 'cannot start' if no else 'started'}  "
              f"@{role} on #{st['id']} {st['text'][:50]} with {alias}" + (f" -- {no}" if no else ""))


AUTOPILOT = "autopilot.json"


def autopilot_cfg():
    return load_json(STATE / AUTOPILOT, {}) or {}


def spent_today(project_name):
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(m.get("cost_usd") or 0 for m in all_agents()
               if m.get("project") == project_name and (m.get("started") or "").startswith(today))


def autopilot_log(text):
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / "autopilot.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}  {text}\n")


def autopilot_tick():
    """One round: for every project with the autopilot on, start the next ready card of every free
    seat (dispatch), each agent's budget capped by what is left of today's. Quiet when there is
    nothing to do, so a minute-by-minute loop costs nothing."""
    import contextlib, io
    for name, c in autopilot_cfg().items():
        if not c.get("on"):
            continue
        try:
            pdir = project_dir(name)
        except SystemExit:
            continue
        left = float(c.get("daily", 5)) - spent_today(pdir.name)
        if left <= 0.01:
            if not c.get("_said_spent") == datetime.now().strftime("%Y-%m-%d"):
                autopilot_log(f"{name}: today's budget is spent, waiting for tomorrow")
                cfg = autopilot_cfg(); cfg[name]["_said_spent"] = datetime.now().strftime("%Y-%m-%d")
                save_autopilot(cfg)
            continue
        per = min(models_cfg(pdir).get("agents", {}).get("default_budget_usd", 2.0), left)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            plan = dispatch(str(pdir), budget=round(per, 2))
        for role, st, alias, no in plan:
            if not no:
                autopilot_log(f"{name}: started @{role} on #{st['id']} {st['text'][:50]} with {alias} (budget ${per:.2f})")


def save_autopilot(cfg):
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = STATE / (AUTOPILOT + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    os.replace(tmp, STATE / AUTOPILOT)


def cmd_autopilot(a):
    if a.tick:
        autopilot_tick()
        return
    if not a.project:
        sys.exit("FAIL  autopilot needs a project, or --tick")
    pdir = project_dir(a.project)
    cfg = autopilot_cfg()
    c = cfg.setdefault(pdir.name, {"on": False, "daily": 5.0})
    if a.on or a.off:
        c["on"] = bool(a.on)
        autopilot_log(f"{pdir.name}: autopilot {'ON' if a.on else 'off'}")
    if a.daily is not None:
        if not 0 < a.daily <= 500:
            sys.exit("FAIL  a daily budget is between $0 and $500")
        c["daily"] = a.daily
    save_autopilot(cfg)
    print(f"{pdir.name}: autopilot {'ON' if c['on'] else 'off'}, daily budget ${c['daily']:.2f}, "
          f"spent today ${spent_today(pdir.name):.2f}")


def ago(iso):
    try:
        s = (datetime.now() - datetime.fromisoformat(iso)).total_seconds()
    except (TypeError, ValueError):
        return "?"
    return f"{int(s)}s" if s < 90 else f"{int(s/60)}m" if s < 5400 else f"{s/3600:.1f}h"


def cmd_list(a):
    rows = [refresh(m) for m in all_agents()]
    if not a.all:
        rows = [m for m in rows if m["status"] != "cleared"]
    if not rows:
        print("no agents" + ("" if a.all else " (agents.py list --all shows cleared ones)"))
        return
    print(f"{'id':<34}{'state':<12}{'model':<13}{'tokens':>9}{'cost':>8}  {'quiet':<6}doing")
    for m in rows:
        tk = sum(m.get("tokens", {}).values())
        print(f"{m['id'][:33]:<34}{m['status']:<12}{m['alias']:<13}{tk:>9}{m.get('cost_usd',0):>8.3f}  "
              f"{ago(m.get('updated')):<6}{(m.get('doing') or m.get('why') or '')[:60]}")
    live = sum(1 for m in rows if m["status"] in LIVE)
    print(f"\n{live} running, total ${sum(m.get('cost_usd', 0) for m in rows):.2f} on this list")


def cmd_status(a):
    m = find(a.id)
    for k in ("id", "status", "why", "role", "project", "story", "alias", "model", "served_by", "effort",
              "chosen_by", "session", "turns", "budget", "cost_usd", "claude_code_cost_usd", "tokens",
              "denials", "started", "updated", "doing", "last"):
        if m.get(k) not in (None, "", [], {}):
            print(f"{k:<22}{m[k]}")
    if m.get("result") and m["status"] not in LIVE:
        print("\nresult:\n" + m["result"])
    print()
    show_tail(m["id"], 8)


def readable(ev):
    t = ev.get("type")
    if t == "agents.turn":
        return f"── turn ({'resumed' if ev.get('resume') else 'new session'}) {ev.get('at','')}: {ev.get('prompt','')[:160]}"
    if t == "assistant":
        out = []
        for b in ev.get("message", {}).get("content", []):
            if b.get("type") == "text" and b.get("text", "").strip():
                out.append("say   " + b["text"].strip().replace("\n", " ")[:300])
            elif b.get("type") == "tool_use":
                out.append("do    " + tool_line(b))
        return "\n".join(out) or None
    if t == "user":
        for b in ev.get("message", {}).get("content", []) if isinstance(ev.get("message", {}).get("content"), list) else []:
            if b.get("type") == "tool_result" and b.get("is_error"):
                c = b.get("content")
                c = c if isinstance(c, str) else json.dumps(c)
                return "error " + c.replace("\n", " ")[:200]
        return None
    if t == "result":
        return f"── {ev.get('subtype')} after {ev.get('num_turns')} steps, {ev.get('duration_ms', 0)//1000}s"
    return None


def show_tail(aid, n, follow=False):
    path = STATE / f"{aid}.log"
    if not path.exists():
        print("(no log yet)")
        return
    def lines_from(text):
        out = []
        for line in text.splitlines():
            try:
                r = readable(json.loads(line))
            except ValueError:
                r = line.strip() and "raw   " + line.strip()[:200]
            if r:
                out.extend(r.split("\n"))
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        print("\n".join(lines_from(f.read())[-n:]))
        while follow:
            chunk = f.read()
            if chunk:
                for l in lines_from(chunk):
                    print(l, flush=True)
            elif refresh(load_json(meta_path(aid)))["status"] not in LIVE:
                break
            else:
                time.sleep(1)


def cmd_tail(a):
    show_tail(find(a.id)["id"], a.n, a.follow)


def cmd_send(a):
    m = find(a.id)
    if m["status"] in LIVE:
        sys.exit(f"FAIL  {m['id']} is still working. agents.py wait {a.id}, or stop it first.")
    if m["status"] == "cleared":
        sys.exit(f"FAIL  {m['id']} was cleared: its session is over. Start a new one.")
    spawn(m["id"], a.message + " " + UNATTENDED, resume=True)
    print(f"sent to {m['id']} (turn {m.get('turns', 0) + 1}, same session)")
    if a.wait:
        wait_for(m["id"], a.timeout)


def kill_tree(m):
    """The supervisor's whole process group, and claude itself: claude shuts down gracefully and can
    outlive its supervisor by a second or more (measured), so wait for both, then force."""
    pids = [p for p in (m.get("pid"), m.get("child")) if alive(p)]
    if not pids:
        return False
    if os.name == "nt":
        for pid in pids:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
        return True
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
    for _ in range(50):
        if not any(alive(p) for p in pids):
            return True
        time.sleep(0.1)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    return True


def cmd_stop(a):
    m = find(a.id)
    was = kill_tree(m)
    m = load_json(meta_path(m["id"]))
    m.update(status="stopped", why="stopped by agents.py stop", pid=None, child=None)
    save(m)
    ledger(m)
    print(f"{'stopped' if was else 'was not running:'} {m['id']}  (agents.py send resumes its session)")


def cmd_clear(a):
    targets = ([m for m in map(refresh, all_agents()) if m["status"] in ("idle", "stopped", "failed", "over-budget")]
               if a.done else [find(a.id)])
    for m in targets:
        kill_tree(m)
        m = load_json(meta_path(m["id"]))
        if m["status"] == "idle":
            ledger(m)            # a finished turn that nobody stopped: its outcome still counts
        m.update(status="cleared", pid=None, child=None)
        save(m)
        print(f"cleared {m['id']}")
    if not targets:
        print("nothing to clear")


def wait_for(aid, timeout):
    end = time.time() + timeout
    while time.time() < end:
        m = refresh(load_json(meta_path(aid)))
        if m["status"] not in LIVE:
            print(f"{aid}: {m['status']}  ${m.get('cost_usd', 0):.3f}  {m.get('why') or ''}")
            if m.get("result"):
                print(m["result"])
            return m
        time.sleep(2)
    sys.exit(f"TIMEOUT  {aid} still {load_json(meta_path(aid))['status']} after {timeout}s")


def cmd_wait(a):
    wait_for(find(a.id)["id"], a.timeout)


def load_board(project):
    return board_module().load(str(project))[2]


def story_cost(cfg, alias, size):
    z = cfg["sizes"][size]
    return cost(cfg, alias, {"in": z["in"], "out": z["out"], "cache_read": z["cache_read"],
                             "cache_write": z["cache_write"]})


def planned_alias(cfg, roles, s):
    """The model a story will run on: its #alias, else its owner's default in roles.json."""
    if s.get("model") in cfg["models"]:
        return s["model"]
    role = next((r for r in roles.get("roles", []) if r["id"] == s.get("who")), None)
    return role.get("model") if role and role.get("model") in cfg["models"] else None


def steps_of(meta):
    """How many actions an agent took: counted live since 2026-10-27, from its log before that."""
    if meta.get("steps") is not None:
        return meta["steps"]
    n, log = 0, STATE / f"{meta['id']}.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"tool_use"' in line:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                n += sum(1 for b in ev.get("message", {}).get("content", []) if b.get("type") == "tool_use")
    return n


def runs_of(project_name, story_id):
    return [m for m in all_agents() if m.get("project") == project_name and m.get("story_id") == story_id]


def explain(cfg, roles, story, runs):
    """What a story really cost against its estimate, and the reasons, in plain words. None when
    no agent has worked on it. One copy: the page and `agents.py why` both call this."""
    if not runs:
        return None
    top = "opus" if "opus" in cfg["models"] else max(cfg["models"], key=lambda k: cfg["models"][k]["tier"])
    planned = planned_alias(cfg, roles, story) or top
    size = story.get("size") or "M"
    est = story_cost(cfg, planned, size)
    spent = sum(m.get("cost_usd") or 0 for m in runs)
    why = []
    if not story.get("size"):
        why.append("the card has no size, so it was estimated as a medium (~M)")
    ran = sorted({m["alias"] for m in runs})
    if ran != [planned]:
        r = ran[0]
        alt = story_cost(cfg, r, size)
        why.append(f"it ran on {', '.join(ran)} instead of the planned {planned}"
                   + (f": a typical ~{size} costs ${alt:.3f} there, ${est:.3f} on {planned}" if len(ran) == 1 else ""))
    z = cfg["sizes"][size]
    expect = z["in"] + z["out"] + z["cache_read"] + z["cache_write"]
    used = sum(sum((m.get("tokens") or {}).values()) for m in runs)
    steps = sum(steps_of(m) for m in runs)
    ratio = used / expect if expect else 1
    words = f"{steps} steps, {used/1000:.0f}k tokens where a typical ~{size} uses {expect/1000:.0f}k"
    if ratio < 0.5:
        why.append(f"less work than a typical ~{size}: {words}")
    elif ratio > 1.5:
        why.append(f"more work than a typical ~{size}: {words}")
    else:
        why.append(f"about the work of a typical ~{size}: {words}")
    if len(runs) > 1:
        why.append(f"it took {len(runs)} runs: every new run reads the project again from the start")
    bad = [m["status"] for m in runs if m["status"] in ("failed", "over-budget", "stopped")]
    if bad:
        why.append(f"{len(bad)} run(s) ended {', '.join(sorted(set(bad)))}: that money is spent, the work may not be")
    delta = spent - est
    pct = round(100 * delta / est) if est else 0
    verdict = ("about as estimated" if abs(pct) < 25 else
               f"{abs(pct)}% {'less' if delta < 0 else 'more'} than estimated")
    return {"spent": round(spent, 4), "estimate": round(est, 4), "delta": round(delta, 4), "pct": pct,
            "verdict": verdict, "why": why, "runs": len(runs), "ran_on": ran, "planned": planned}


def cmd_why(a):
    pdir = project_dir(a.project)
    cfg, roles = models_cfg(pdir), roles_cfg(pdir)
    s = story_of(pdir, a.story)
    e = explain(cfg, roles, s, runs_of(pdir.name, s["id"]))
    print(f"#{s['id']} {s['text']}")
    if not e:
        print("no agent has worked on it yet: nothing spent")
        return
    print(f"spent ${e['spent']:.3f}, estimated ${e['estimate']:.3f} on {e['planned']} -- {e['verdict']}")
    for w in e["why"]:
        print("  - " + w)


def cmd_cost(a):
    pdir = project_dir(a.project)
    cfg, roles = models_cfg(pdir), roles_cfg(pdir)
    stories = load_board(pdir)
    spent = {}       # from every agent's own record: money is spent the moment it is spent, not when cleared
    for m in all_agents():
        if m.get("project") == pdir.name and m.get("story_id"):
            spent[m["story_id"]] = spent.get(m["story_id"], 0) + (m.get("cost_usd") or 0)
    top = max(cfg["models"], key=lambda k: (cfg["models"][k]["tier"] == 4, -cfg["models"][k]["tier"]))
    top = "opus" if "opus" in cfg["models"] else top
    feats, notes = {}, set()
    for s in stories:
        if s["phase"].startswith(("Ideas", "Cancelled", "Archive")):
            continue
        f = feats.setdefault((s["phase"], s["feature"]), dict(prio=s.get("feature_prio", 5),
                             refined=s["feature_refined"], open=0, done=0, plan=0.0, top=0.0, spent=0.0,
                             sizes=[], unknown=0))
        f["spent"] += spent.get(s["id"], 0)
        if s["state"] == "done":
            f["done"] += 1
            continue
        f["open"] += 1
        size = s.get("size") or "M"
        if not s.get("size"):
            f["unknown"] += 1
        f["sizes"].append(size)
        alias = planned_alias(cfg, roles, s)
        if alias is None:
            notes.add(f"#{s['id']} has no model it can be priced on (no #alias, owner {s.get('who') or 'none'})")
            alias = top
        elif provider_ready(cfg, cfg["models"][alias]["provider"], pdir):
            notes.add(f"#{s['id']} is planned on {alias}, which cannot run here: "
                      + provider_ready(cfg, cfg["models"][alias]["provider"], pdir))
        f["plan"] += story_cost(cfg, alias, size)
        f["top"] += story_cost(cfg, top, size)
    if not feats:
        print("no stories on this board")
        return
    print(f"{pdir.name}: the open work, priced (sizes and prices from models.json; estimates, not quotes)\n")
    print(f"{'feature':<38}{'prio':>5}{'open':>6}{'done':>6}  {'sizes':<14}{'planned $':>10}{'all ' + top + ' $':>12}{'spent $':>9}")
    tot = dict(plan=0.0, top=0.0, spent=0.0)
    phase = None
    for (ph, ft), f in sorted(feats.items(), key=lambda kv: (list(dict.fromkeys(k[0] for k in feats)).index(kv[0][0]),
                                                            -kv[1]["prio"])):
        if ph != phase:
            phase = ph
            pp = [v for (p2, _), v in feats.items() if p2 == ph]
            print(f"\n{ph[:60]}   planned ${sum(v['plan'] for v in pp):.2f}, spent ${sum(v['spent'] for v in pp):.2f}")
        sz = " ".join(f"{n}{z}" if n > 1 else z for z, n in
                      ((z, f["sizes"].count(z)) for z in ("XS", "S", "M", "L", "XL")) if n)
        name = (ft or "(no feature)")[:34] + ("" if f["refined"] else " ?")
        print(f"  {name:<36}{f['prio']:>5}{f['open']:>6}{f['done']:>6}  {sz + ('*' if f['unknown'] else ''):<14}"
              f"{f['plan']:>10.2f}{f['top']:>12.2f}{f['spent']:>9.2f}")
        for k in tot:
            tot[k] += f[k]
    print(f"\n{'total':<38}{'':>17}  {'':<14}{tot['plan']:>10.2f}{tot['top']:>12.2f}{tot['spent']:>9.2f}")
    print("\n? = feature not refined yet    * = some stories have no ~size and are counted as M")
    worked = [(st, explain(cfg, roles, st, runs_of(pdir.name, st["id"]))) for st in stories if st.get("id")]
    worked = [(st, e) for st, e in worked if e]
    if worked:
        print(f"\nwhat it really cost, against the estimate:")
        for st, e in worked:
            print(f"  #{st['id']:<4}{st['text'][:40]:<42}spent ${e['spent']:.3f}  est ${e['estimate']:.3f}  {e['verdict']}")
            print(f"        why: {e['why'][0]}" + "".join(f"; {w}" for w in e["why"][1:]))
    for n in sorted(notes):
        print("note  " + n)


def cheapest_for(cfg, providers, tier, size):
    """The cheapest alias of at least this tier among these providers, or None."""
    fits = [k for k, m in cfg["models"].items() if m["provider"] in providers and m["tier"] >= tier]
    return min(fits, key=lambda k: story_cost(cfg, k, size)) if fits else None


def cmd_ais(a):
    """Which AIs a project uses, and the what-if: the work left, priced with every choice of AIs.

    A story keeps its STRENGTH, not its model: it needs at least the tier of the model it is planned
    on (models.json "tier"), and each choice gives it the cheapest model of that tier or above. Tiers
    are a judgement, written down in models.json; the measured '$ per ok' in agents.py report is what
    shows whether a cheaper model really holds up."""
    import itertools
    pdir = project_dir(a.project)
    cfg, roles = models_cfg(pdir), roles_cfg(pdir)
    names = list(cfg["providers"])
    if a.use is not None:
        want = [x.strip() for x in a.use.split(",") if x.strip()]
        bad = [x for x in want if x not in names]
        if bad or not want:
            sys.exit(f"FAIL  choose from: {', '.join(names)}" + (f" (unknown: {', '.join(bad)})" if bad else ""))
        (pdir / "docs").mkdir(exist_ok=True)
        (pdir / "docs" / "ais.json").write_text(json.dumps({"use": want}, indent=1) + "\n", encoding="utf-8")
        print(f"ok    {pdir.name} now uses: {', '.join(want)}  (docs/ais.json -- commit it with the plan)\n")
    chosen = project_ais(pdir)
    print(f"{pdir.name} uses: " + (", ".join(chosen) if chosen is not None else "every AI that can run here (no docs/ais.json)"))
    print(f"\n{'AI':<12}{'in this project':<17}can run on this computer")
    for n in names:
        no = provider_ready(cfg, n)
        print(f"{n:<12}{('yes' if chosen is None or n in chosen else 'no'):<17}{'yes' if not no else 'no -- ' + no}")
    open_ = [s for s in load_board(pdir) if s["state"] != "done"
             and not s["phase"].startswith(("Ideas", "Cancelled", "Archive"))]
    if not open_:
        print("\nno open stories to price")
        return
    need = []
    for s in open_:
        al = planned_alias(cfg, roles, s) or "opus"
        need.append((s, cfg["models"][al]["tier"], s.get("size") or "M"))
    current = set(chosen if chosen is not None else names)
    print(f"\nthe work left ({len(open_)} stories), priced with each choice of AIs -- each story on the cheapest model")
    print("at least as strong as the one it is planned on:\n")
    print(f"  {'AIs':<28}{'cost $':>9}{'can do':>9}   cheapest picks")
    rows = []
    for r in range(1, len(names) + 1):
        for combo in itertools.combinations(names, r):
            total, done, picks = 0.0, 0, {}
            for s, tier, size in need:
                al = cheapest_for(cfg, combo, tier, size)
                if al:
                    total += story_cost(cfg, al, size)
                    done += 1
                    picks[al] = picks.get(al, 0) + 1
            rows.append((combo, total, done, picks))
    for combo, total, done, picks in sorted(rows, key=lambda r: (-r[2], r[1])):
        mark = "  <- now" if set(combo) == current else ""
        pk = ", ".join(f"{n}x {k}" for k, n in sorted(picks.items(), key=lambda kv: -kv[1]))
        print(f"  {' + '.join(combo):<28}{total:>9.2f}{done:>6}/{len(need):<3}  {pk}{mark}")
    print("\nA choice that cannot do every story needs another AI for the rest. Cheaper is only cheaper if the")
    print("work holds up: check '$ per ok' in agents.py report before switching a whole project.")


def cmd_report(a):
    rows = [json.loads(l) for l in (STATE / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()] if (STATE / "ledger.jsonl").exists() else []
    if not rows:
        print("no finished agents yet")
        return
    for key in ("alias", "kind", "role"):
        groups = {}
        for r in rows:
            groups.setdefault(r.get(key) or "-", []).append(r)
        print(f"\nper {key}:")
        print(f"  {'':<14}{'runs':>5}{'ok':>5}{'failed':>8}{'cost $':>9}{'$ per ok':>10}")
        for g, rs in sorted(groups.items()):
            ok = sum(1 for r in rs if r["status"] in ("idle", "cleared"))
            c = sum(r.get("cost_usd") or 0 for r in rs)
            print(f"  {g:<14}{len(rs):>5}{ok:>5}{len(rs)-ok:>8}{c:>9.2f}{(c/ok if ok else 0):>10.2f}")
    cfg = models_cfg()
    sized = [r for r in rows if r.get("size") and r["status"] in ("idle", "cleared")]
    if sized:
        print("\nmeasured vs models.json, per size (median cost of a finished story):")
        for z in ("XS", "S", "M", "L", "XL"):
            for al in sorted({r["alias"] for r in sized if r["size"] == z}):
                cs = sorted(r.get("cost_usd") or 0 for r in sized if r["size"] == z and r["alias"] == al)
                print(f"  ~{z:<3}{al:<14}{len(cs):>3} runs   measured ${cs[len(cs)//2]:.3f}"
                      f"   estimate ${story_cost(cfg, al, z):.3f}")
    print("\n'$ per ok' is what the retrospective routes on: a cheap model that fails twice is not cheap.")


# ---- selftest: every check made to fire --------------------------------------

def cmd_selftest(a):
    import tempfile
    fails = []
    def check(name, cond):
        print(("  CAUGHT  " if cond else "  MISSED  ") + name)
        if not cond:
            fails.append(name)
    import tempfile
    print("SELFTEST -- every line must say CAUGHT")
    cfg = models_cfg()
    base = {"PATH": "/bin", "ANTHROPIC_API_KEY": "sk-real-anthropic", "DEEPSEEK_API_KEY": "sk-ds"}
    env = environment(cfg, "ds-flash", base)
    check("a DeepSeek seat is pointed at DeepSeek", env.get("ANTHROPIC_BASE_URL", "").startswith("https://api.deepseek.com"))
    check("a DeepSeek seat carries the DeepSeek key", env.get("ANTHROPIC_AUTH_TOKEN") == "sk-ds")
    check("a DeepSeek seat cannot fall back to the Anthropic key", "ANTHROPIC_API_KEY" not in env)
    check("a DeepSeek seat's subagents stay on DeepSeek", env.get("CLAUDE_CODE_SUBAGENT_MODEL") == "deepseek-flash[1m]")
    env = environment(cfg, "opus", base)
    check("a Claude seat is left on Anthropic", "ANTHROPIC_BASE_URL" not in env and env.get("ANTHROPIC_API_KEY") == "sk-real-anthropic")
    old = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        check("a provider without its key is refused", "DEEPSEEK_API_KEY" in provider_ready(cfg, "deepseek"))
        check("routing skips a provider that cannot run", route(cfg, "mechanical")[0] == "haiku")
    finally:
        if old is not None:
            os.environ["DEEPSEEK_API_KEY"] = old
    try:
        route(cfg, "no-such-kind")
        check("an unknown kind is refused", False)
    except SystemExit:
        check("an unknown kind is refused", True)
    pd = Path(tempfile.mkdtemp())
    (pd / "docs").mkdir()
    (pd / "docs" / "ais.json").write_text('{"use": ["deepseek"]}')
    check("a project that chose other AIs refuses Claude", "does not use" in provider_ready(cfg, "anthropic", pd))
    check("the what-if keeps a story's strength", cheapest_for(cfg, ["deepseek"], 4, "M") is None
          and cheapest_for(cfg, ["anthropic", "deepseek"], 2, "M") == "ds-flash")
    tok = {}
    for u in ({"input_tokens": 1_000_000}, {"output_tokens": 1_000_000}):
        add_usage(tok, u)
    check("cost is input + output at models.json's prices", abs(cost(cfg, "sonnet", tok) - 12.0) < 1e-9)
    meta = {"alias": "ds-flash", "session": "s-1", "effort": "low"}
    c = command(cfg, meta, "go", resume=True)
    check("a follow-up resumes the same session", c[c.index("--resume") + 1] == "s-1" and "--session-id" not in c)
    check("the effort reaches claude", c[c.index("--effort") + 1] == "low")
    check("a headless agent has a permission mode", "--permission-mode" in c)
    ev = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "make test\nmore"}}]}}
    check("tail shows what an agent ran", readable(ev) == "do    Bash make test")
    global STATE
    saved, STATE = STATE, Path(tempfile.mkdtemp())
    try:
        save({"id": "ghost", "status": "running", "pid": 999999, "tokens": {}})
        check("a dead supervisor is reported, not shown as running", refresh(load_json(meta_path("ghost")))["status"] == "failed")
    finally:
        STATE = saved
    print()
    if fails:
        sys.exit(f"selftest FAILED: {len(fails)} check(s) did not fire")
    print("selftest passed: every check fires when it should.")


# ---- command line -------------------------------------------------------------

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("models")
s = sub.add_parser("route"); s.add_argument("kind")
s = sub.add_parser("start"); s.add_argument("project"); s.add_argument("--role", required=True)
s.add_argument("--story"); s.add_argument("--model"); s.add_argument("--kind"); s.add_argument("--effort")
s.add_argument("--prompt"); s.add_argument("--budget", type=float)
s.add_argument("--wait", action="store_true"); s.add_argument("--timeout", type=int, default=1800)
s = sub.add_parser("list"); s.add_argument("--all", action="store_true")
s = sub.add_parser("next"); s.add_argument("project"); s.add_argument("--budget", type=float)
s.add_argument("--dry-run", action="store_true")
s = sub.add_parser("autopilot"); s.add_argument("project", nargs="?"); s.add_argument("--on", action="store_true")
s.add_argument("--off", action="store_true"); s.add_argument("--daily", type=float); s.add_argument("--tick", action="store_true")
s = sub.add_parser("status"); s.add_argument("id")
s = sub.add_parser("tail"); s.add_argument("id"); s.add_argument("-n", type=int, default=30)
s.add_argument("--follow", action="store_true")
s = sub.add_parser("send"); s.add_argument("id"); s.add_argument("message")
s.add_argument("--wait", action="store_true"); s.add_argument("--timeout", type=int, default=1800)
s = sub.add_parser("wait"); s.add_argument("id"); s.add_argument("--timeout", type=int, default=1800)
s = sub.add_parser("stop"); s.add_argument("id")
s = sub.add_parser("clear"); s.add_argument("id", nargs="?"); s.add_argument("--done", action="store_true")
s = sub.add_parser("cost"); s.add_argument("project")
s = sub.add_parser("why"); s.add_argument("project"); s.add_argument("story", help="#id or part of the text")
s = sub.add_parser("ais"); s.add_argument("project"); s.add_argument("--use", help="comma-separated providers from models.json")
sub.add_parser("report")
sub.add_parser("selftest")
s = sub.add_parser("_run"); s.add_argument("id"); s.add_argument("--prompt", required=True)
s.add_argument("--resume", action="store_true")

if __name__ == "__main__":
    a = p.parse_args()
    if a.cmd == "clear" and not (a.id or a.done):
        sys.exit("FAIL  clear needs an id, or --done for every finished agent")
    if a.cmd == "_run":
        supervise(a.id, a.prompt, a.resume)
    else:
        globals()["cmd_" + a.cmd](a)
