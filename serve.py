#!/usr/bin/env python3
"""Serve the workshop page, and let it write back.

    ./serve.py            # http://127.0.0.1:8765

Opened as a file, index.html is read-only -- nothing is listening. Served, the
same page can move a ticket, and the move is written into the project's own plan
document. The page stays a VIEW of the repo either way: it never holds state of
its own, it edits the file and regenerates.

Local only, on purpose: it binds 127.0.0.1, and the one command it can run --
new_project.sh, from the New project form -- is invoked as an argument list with
a validated name, never through a shell. Stop it with Ctrl-C.

Board edits are never committed: they sit in the working tree until you commit
them with the finding, which is where they belong. Creating a project is the
exception, because a repository has to be committed to exist.
"""
import json, os, pathlib, re, subprocess, sys, tempfile, threading, importlib.util
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

SHOP = Path(__file__).resolve().parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

spec = importlib.util.spec_from_file_location("boardlib", SHOP / "board.py")


def board_module():
    """board.py is a script; import just its helpers without running its parser."""
    src = (SHOP / "board.py").read_text()
    src = src[:src.index("ap = argparse.ArgumentParser")]
    ns = {"__name__": "boardlib", "__file__": str(SHOP / "board.py")}
    exec(compile(src, str(SHOP / "board.py"), "exec"), ns)
    return ns


B = board_module()


_building = threading.Lock()


def regenerate():
    """Rebuild the data and the page. ONE AT A TIME, and never destructively.

    Two bugs lived here, both found 2026-09-24 while chasing what looked like a
    broken page and was in fact a rebuild in progress.

    1. It streamed collect_all.py straight into workshop.json with
       open(..., "w"), which truncates on the spot. A full collect takes ~4
       minutes on the external drive, so for those 4 minutes the live file was
       0 bytes or half-written -- /api/state served an empty body and anything
       reading it got invalid JSON. A collect that FAILED left it empty for
       good: check=True raised, but the old data was already gone.

    2. rebuild_behind() serialised itself with _building, but the two direct
       callers (GET / on the no-cache path, and the POST handlers) called
       regenerate() with NO lock. Two collects then ran at once and shared one
       temp path: the first one's os.replace() published the very inode the
       second was still writing into, so the live file went to 0 bytes in the
       middle of an apparently healthy rebuild, then healed itself.

    So: the lock is taken HERE, by everyone, and the temp file is unique per
    call. A reader sees the whole old file or the whole new one, never a
    partial, no matter how many rebuilds are triggered.
    """
    with _building:
        return _regenerate_locked()


def _regenerate_locked():
    jpath = SHOP / "dashboard" / "workshop.json"
    fd, tmpname = tempfile.mkstemp(dir=str(jpath.parent), prefix="workshop.", suffix=".json.tmp")
    tmp = pathlib.Path(tmpname)
    try:
        with os.fdopen(fd, "w") as fh:
            subprocess.run([sys.executable, str(SHOP / "dashboard" / "collect_all.py"), str(SHOP)],
                           stdout=fh, check=True)
        os.replace(tmp, jpath)                     # atomic: same filesystem
    except BaseException:
        tmp.unlink(missing_ok=True)                # leave the last good data alone
        raise
    html = subprocess.run([sys.executable, str(SHOP / "dashboard" / "render_workshop.py"),
                           str(jpath)],
                          capture_output=True, text=True, check=True).stdout
    hfd, htmpname = tempfile.mkstemp(dir=str(SHOP), prefix="index.", suffix=".html.tmp")
    htmp = pathlib.Path(htmpname)
    try:
        with os.fdopen(hfd, "w") as fh:
            fh.write(html)
        os.replace(htmp, SHOP / "index.html")
    except BaseException:
        htmp.unlink(missing_ok=True)
        raise
    return html


def rebuild_behind():
    """Rebuild after the page has already gone out, so a load never waits on it.

    A full rebuild replays every revision of every plan file and shells out per
    project; on the external drive that measured 72 s. Doing it inside GET /
    meant the browser sat on a blank tab long enough to look broken, which is
    how the page came to seem dead when the server was in fact answering.
    One at a time -- a second request just leaves the running build alone.
    """
    if _building.locked():
        return                      # one is already running; leave it alone
    def run():
        try:
            regenerate()            # takes _building itself
        except Exception as e:
            print(f"  background rebuild failed: {e}")
    threading.Thread(target=run, daemon=True).start()


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            # Serve the last build immediately and refresh behind it. The page's
            # own refresh button (/api/state) still rebuilds synchronously, so
            # "show me the truth right now" is one click and never a page load.
            cached = SHOP / "index.html"
            if cached.exists():
                self._send(200, cached.read_text())
                rebuild_behind()
                return
            try:
                self._send(200, regenerate())
            except subprocess.CalledProcessError as e:
                self._send(500, f"<pre>generation failed:\n{e}</pre>")
        elif self.path == "/api/state":
            # regenerate: this is the refresh button, and a stale answer would
            # defeat the point of having one
            try:
                regenerate()
            except subprocess.CalledProcessError as e:
                return self._send(500, str(e), "text/plain")
            self._send(200, (SHOP / "dashboard" / "workshop.json").read_text(),
                       "application/json")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/new":
                return self.new_project(req)
            if self.path == "/api/msg":
                return self.send_msg(req)
            if self.path == "/api/mail_delete":
                seat = (req.get("seat") or "").strip()
                when = (req.get("when") or "").strip()
                folder = req.get("folder") or "in"
                if not re.fullmatch(r"[a-z][\w-]{0,31}", seat) or not when:
                    raise ValueError("bad message reference")
                targets = ([SHOP / ".outbox.md"] if folder == "out"
                           else [SHOP / ".inbox" / f"{seat}.md",
                                 SHOP / ".inbox" / f"{seat}.read.md"])
                gone = 0
                for p in targets:
                    if not p.exists():
                        continue
                    chunks = re.split(r"\n(?=## )", B["mail_read"](p))
                    keep = [c for c in chunks if when not in c.split("\n", 1)[0]]
                    gone += len(chunks) - len(keep)
                    body = "\n".join(keep).strip()
                    if body:
                        p.write_text(body + "\n", encoding="utf-8")
                    else:
                        p.unlink()
                print(f"  deleted {gone} message(s) for {seat}")
                return self._send(200, json.dumps(
                    {"ok": True, "deleted": gone,
                     **self.mail_warn(targets, f"deleted {gone} for @{seat}")}),
                    "application/json")
            if self.path == "/api/inbox_read":
                who = (req.get("who") or "").strip()
                if not re.fullmatch(r"[a-z][\w-]{0,31}", who):
                    raise ValueError("unknown seat")
                p = SHOP / ".inbox" / f"{who}.md"
                done = SHOP / ".inbox" / f"{who}.read.md"
                if p.exists():
                    B["mail_append"](done, B["mail_read"](p))
                    p.unlink()
                return self._send(200, json.dumps(
                    {"ok": True, **self.mail_warn([p, done], f"@{who} read {p.name}")}),
                    "application/json")
            project = req["project"]
            if self.path == "/api/move":
                self.move(project, req)
            elif self.path == "/api/add":
                line = B["add_story"](project, req["phase"], req["feature"], req["text"],
                                      req.get("who", ""), req.get("model", ""),
                                      req.get("evidence", ""), bool(req.get("new_feature")),
                                      int(req.get("prio") or 5), req.get("checker", ""))
                print(f"  {project}: + {line.strip()[:70]}")
            elif self.path == "/api/edit":
                _, line = B["edit_story"](project, req["line"], req.get("text"),
                                          req.get("evidence"), req.get("who"),
                                          req.get("model"), exact=True,
                                          prio=req.get("prio"),
                                          blocked=req.get("blocked"),
                                          checker=req.get("checker"))
                print(f"  {project}: ~ {line.strip()[:70]}")
            elif self.path == "/api/new":
                return self.new_project(req)
            elif self.path == "/api/move_phase":
                line = B["move_story"](project, req["line"], req["phase"],
                                       req.get("feature"), exact=True)
                print(f"  {project}: -> {req['phase']}: {line.strip()[:60]}")
            elif self.path == "/api/msg":
                return self.send_msg(req)
            elif self.path == "/api/note":
                line = B["add_note"](project, req["line"], req.get("who") or "design",
                                     req["text"], exact=True)
                print(f"  {project}: note {line.strip()[:70]}")
            elif self.path == "/api/feature":
                line = B["set_feature"](project, req["feature"], bool(req.get("refined")))
                print(f"  {project}: {line}")
            elif self.path == "/api/delete":
                B["delete_story"](project, req["line"])
                print(f"  {project}: - {req['line'].strip()[:70]}")
            else:
                return self._send(404, "not found", "text/plain")
            self._send(200, json.dumps({"ok": True}), "application/json")
        except Exception as e:
            self._send(400, str(e), "text/plain")

    def send_msg(self, req):
        who = (req.get("to") or "").strip()
        text = (req.get("text") or "").strip()
        if who == "ideas":
            # mailing the ideas box files the idea straight away, so it cannot be
            # lost waiting for someone to read an inbox, and tells @workshop to
            # come and think about it
            if not text:
                raise ValueError("empty idea")
            # an idea is prose: @role and #model in it are words, not tags, so
            # quote them or the parser adopts them as owner and model
            safe = lambda s: re.sub(r"(?<![\w`/])([@#+])([a-z][\w.-]*)", r"`\1\2`", s)
            text = safe(text)
            first, _, rest = text.partition("\n")
            line = B["add_story"]("Workshop", "Ideas", "Ideas", first.strip(),
                                  "", "", rest.strip(), new_feature=True, prio=1)
            import time as _t
            box = SHOP / ".inbox"
            box.mkdir(exist_ok=True)
            B["mail_append"](box / "workshop.md",
                f"\n## {_t.strftime('%Y-%m-%d %H:%M')} — from @dennis\n\n"
                f"New idea filed: {first.strip()}\n\nRead it, add a note on what it "
                f"would cost and what it collides with. Do not act on it.\n")
            self.log_sent("ideas", first.strip())
            print(f"  idea filed: {line.strip()[:70]}")
            return self._send(200, json.dumps(
                {"ok": True, **self.mail_warn([box / "workshop.md", SHOP / ".outbox.md"],
                                              "idea filed for @workshop")}),
                "application/json")
        if not re.fullmatch(r"[a-z][\w-]{0,31}", who):
            raise ValueError("unknown recipient")
        if not text:
            raise ValueError("empty message")
        import time as _t
        box = SHOP / ".inbox"
        box.mkdir(exist_ok=True)
        B["mail_append"](box / f"{who}.md",
            f"\n## {_t.strftime('%Y-%m-%d %H:%M')} — from @dennis\n\n{text}\n")
        self.log_sent(who, text)
        warn = self.mail_warn([box / f"{who}.md", SHOP / ".outbox.md"], f"to @{who} from @dennis")
        print(f"  message for @{who} — {warn.get('warn') or 'sent'}")
        self._send(200, json.dumps({"ok": True, **warn}), "application/json")

    def mail_warn(self, paths, what):
        """Push the mail, and hand the page a warning if it did not leave.

        Every seat but @workshop is on the other machine (#95), so a message is
        only really sent once it is pushed. Silence here is what made the inbox
        look like it worked for a fortnight while nothing ever arrived, so a
        failure is returned to the browser and shown, not logged and forgotten."""
        sent, how = B["mail_sync"](paths, what)
        return {} if sent else {"warn": f"Written here, but NOT SENT — {how}"}

    def log_sent(self, who, text):
        """An outbox: what was sent, to whom, when. Without it a message is a
        thing you did that left no trace, and you cannot tell a delivery from a
        mistyped click."""
        import time as _t
        p = SHOP / ".outbox.md"
        B["mail_append"](p, f"\n## {_t.strftime('%Y-%m-%d %H:%M')} → {who}\n\n{text.strip()}\n")

    def new_project(self, req):
        name = (req.get("name") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
            raise ValueError("name: letters, digits, dot, dash, underscore; no spaces")
        cmd = [str(SHOP / "new_project.sh"), name, (req.get("subtitle") or "").strip() or name]
        if req.get("board"):
            cmd += ["--board", str(req["board"])[:60]]
        if req.get("chip"):
            cmd += ["--chip", str(req["chip"])[:60]]
        if req.get("private"):
            cmd += ["--private"]
        if not req.get("push"):
            cmd += ["--no-push"]
        print(f"  creating {name} ...")
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SHOP))
        out = (r.stdout + r.stderr).strip()
        print("  " + out.replace("\n", "\n  "))
        if r.returncode != 0:
            return self._send(400, out or "new_project.sh failed", "text/plain")
        self._send(200, json.dumps({"ok": True, "log": out}), "application/json")

    def move(self, project, req):
        to = req["to"]
        if to not in B["MARK"]:
            raise ValueError(f"unknown state {to!r}")
        path, lines, stories = B["load"](project)
        hit = [s for s in stories if lines[s["i"]].strip() == req["line"].strip()]
        if len(hit) != 1:
            raise ValueError(f"{len(hit)} lines match that ticket -- reload the page")
        s = hit[0]
        ev = (req.get("evidence") or "").strip() or s["evidence"]
        if to == "done" and not ev:
            raise ValueError("a story closes on evidence")
        lines[s["i"]] = B["join_story"](s["indent"], B["MARK"][to], s["text"],
                                        ev, s["who"], s["model"])
        path.write_text("\n".join(lines))
        print(f"  {project}: [{B['MARK'][to]}] {s['text'][:70]}")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    # Bind first, build after: startup used to spend a minute in regenerate()
    # before the socket existed, so the page was refused rather than slow.
    print(f"workshop on http://127.0.0.1:{PORT}   (Ctrl-C to stop)")
    rebuild_behind()
    print("moves are written to the project's plan file and left uncommitted")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
