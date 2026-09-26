#!/usr/bin/env python3
"""Render the whole workshop into one self-contained HTML file.

No server, no build step, no network: the JSON from collect_all.py is embedded and
the page draws itself. Open it from Finder. Everything it shows is generated from
the projects' own documents, so the page is a VIEW and never a source of truth --
edit the repo, regenerate, never the other way round.

Usage:  python3 render_workshop.py workshop.json > index.html
"""
import json, sys

blob = open(sys.argv[1]).read()

HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workshop</title>
<style>
:root{
  --bg:#F4F6FA; --surface:#FFFFFF; --sunk:#EDF0F6; --ink:#141821; --muted:#5B657C;
  --line:#DCE1EB; --accent:#2563EB;
  --ok:#0E9F6E; --warn:#B45309; --bad:#DC2626; --idle:#64748B;
  --ok-bg:#E3F5EE; --warn-bg:#FBEEDC; --bad-bg:#FCE7E7; --idle-bg:#EAEDF3;
  --c-backlog:#64748B; --c-open:#2563EB; --c-wip:#7C3AED; --c-check:#D97706; --c-done:#0E9F6E;
}
:root:not([data-theme="light"]){
  --bg:#0E1017; --surface:#161A24; --sunk:#11141C; --ink:#E6E9F0; --muted:#8B93A7;
  --line:#252A37; --accent:#60A5FA;
  --ok:#34D399; --warn:#F0A73D; --bad:#F87171; --idle:#8B93A7;
  --ok-bg:#10291F; --warn-bg:#2C2113; --bad-bg:#2E1618; --idle-bg:#1A1E28;
  --c-backlog:#8B93A7; --c-open:#60A5FA; --c-wip:#A78BFA; --c-check:#F0A73D; --c-done:#34D399;
}
:root[data-theme="dark"]{
  --bg:#0E1017; --surface:#161A24; --sunk:#11141C; --ink:#E6E9F0; --muted:#8B93A7;
  --line:#252A37; --accent:#60A5FA;
  --ok:#34D399; --warn:#F0A73D; --bad:#F87171; --idle:#8B93A7;
  --ok-bg:#10291F; --warn-bg:#2C2113; --bad-bg:#2E1618; --idle-bg:#1A1E28;
  --c-backlog:#8B93A7; --c-open:#60A5FA; --c-wip:#A78BFA; --c-check:#F0A73D; --c-done:#34D399;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 "IBM Plex Sans",system-ui,-apple-system,sans-serif}
.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
#app{display:flex;height:100vh;overflow:hidden;position:relative}
#app.navopen aside{display:flex}
main{padding-left:0}
#app:not(.navopen) .head{padding-left:56px}

/* sidebar */
#navbtn{position:fixed;top:14px;left:14px;z-index:40;border:1px solid var(--line);
  background:var(--surface);color:var(--muted);border-radius:7px;width:30px;height:30px;
  font-size:15px;line-height:1;cursor:pointer;padding:0}
#navbtn:hover{color:var(--ink);border-color:var(--accent)}
#app.navopen aside h1{padding-left:46px}   /* the toggle stays put; the title moves */
aside{display:none;width:216px;flex:0 0 216px;background:var(--surface);
  border-right:1px solid var(--line);flex-direction:column;overflow-y:auto}
aside h1{font-size:15px;margin:0;padding:16px 16px 4px;letter-spacing:-.01em}
aside .gen{font-size:11px;color:var(--muted);padding:0 16px 14px}
aside .grp{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);
  padding:12px 16px 6px;border-top:1px solid var(--line)}
aside button{display:block;width:100%;text-align:left;border:0;background:none;color:var(--ink);
  padding:7px 16px;font:inherit;cursor:pointer;border-left:2px solid transparent}
aside button:hover{background:var(--sunk)}
aside button[aria-current="true"]{background:var(--sunk);border-left-color:var(--accent);font-weight:600}
#themebtn{margin-top:auto;border-top:1px solid var(--line);color:var(--muted);font-size:12px;padding:10px 16px}
aside button small{display:block;color:var(--muted);font-size:11px;font-weight:400}

/* main */
main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.head{padding:18px 26px 0;border-bottom:1px solid var(--line);background:var(--surface)}
.head h2{margin:0;font-size:21px;letter-spacing:-.02em;display:inline-block}
#refreshbtn{float:right;border:1px solid var(--line);background:var(--surface);color:var(--muted);
  border-radius:7px;width:30px;height:30px;font-size:15px;line-height:1;cursor:pointer;padding:0}
#refreshbtn:hover{color:var(--ink);border-color:var(--accent)}
#refreshbtn.spin{animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.wait{margin-left:12px;font:inherit;font-size:12px;border:1px solid var(--line);background:var(--surface);
  color:var(--muted);border-radius:99px;padding:2px 10px;cursor:pointer;vertical-align:3px}
.head .hs{vertical-align:4px}
.hs{font-size:11px;font-weight:600;padding:1px 8px;border-radius:99px;margin-left:8px;
  text-transform:none;letter-spacing:0}
.hs-running{background:var(--ok-bg);color:var(--ok)}
.hs-waiting{background:var(--warn-bg);color:var(--warn)}
.hs-halted,.hs-stalled{background:var(--bad-bg);color:var(--bad)}
.hs-idle{background:var(--idle-bg);color:var(--idle)}
.hs-finished{background:var(--ok-bg);color:var(--ok)}
.wait.on{background:var(--warn-bg);color:var(--warn);border-color:transparent;font-weight:600}
.head p{margin:2px 0 0;color:var(--muted);font-size:13px}
nav{display:flex;gap:2px;margin-top:14px}
nav button{border:0;background:none;font:inherit;color:var(--muted);cursor:pointer;
  padding:8px 12px;border-bottom:2px solid transparent}
nav button:hover{color:var(--ink)}
nav button[aria-current="true"]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.unread{display:inline-block;min-width:17px;padding:0 5px;margin-left:5px;border-radius:99px;
  background:var(--warn);color:var(--bg);font-size:10.5px;font-weight:700;line-height:17px;
  text-align:center;vertical-align:1px}
.body{flex:1;overflow-y:auto;padding:22px 26px 60px}
section[hidden]{display:none!important}

h3{font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);
  margin:0 0 10px;font-weight:600}
.card{background:var(--surface);border:1px solid var(--line);border-radius:7px;padding:14px 16px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-bottom:14px}
.lede{font-size:14px;margin:0 0 8px}
.muted{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);
  font-weight:600;padding:4px 10px 4px 0;border-bottom:1px solid var(--line)}
td{padding:6px 10px 6px 0;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
.pill{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;font-weight:600;white-space:nowrap}
.p-ok{background:var(--ok-bg);color:var(--ok)} .p-warn{background:var(--warn-bg);color:var(--warn)}
.p-bad{background:var(--bad-bg);color:var(--bad)} .p-idle{background:var(--idle-bg);color:var(--idle)}
.front{border-left:3px solid var(--bad);padding-left:12px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.kan{display:grid;grid-template-columns:repeat(var(--ncols,4),1fr);gap:10px;margin-top:12px}
.story.st-check{border-left:3px solid var(--c-check)}
.story.blocked{border-left:3px solid var(--bad);background:var(--bad-bg)}
.blockline{display:block;color:var(--bad);font-size:12px;font-weight:600;margin-top:2px}
.story.st-backlog{border-left:3px solid var(--c-backlog);border-left:3px solid var(--idle);opacity:.85}
.kan .col{background:var(--sunk);border:1px solid var(--line);border-top:2px solid var(--cc,var(--line));
  border-radius:7px;padding:10px;min-height:70px}
.kan .col h4{color:var(--cc,var(--muted));letter-spacing:.08em}
.kan .col h4 .mono{color:var(--muted);font-weight:400}
.col-backlog{--cc:var(--c-backlog)} .col-open{--cc:var(--c-open)} .col-wip{--cc:var(--c-wip)}
.col-check{--cc:var(--c-check)} .col-done{--cc:var(--c-done)}
.kan .col.over{border-color:var(--accent);background:var(--ok-bg)}
.phhead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.phnum{font-size:12px;color:var(--muted)}
.bar{height:5px;background:var(--sunk);border:1px solid var(--line);border-radius:99px;overflow:hidden;margin:8px 0 0}
.bar.big{height:8px;margin:10px 0 14px}
.bar i{display:block;height:100%;background:var(--accent)}
.fstrip{display:grid;gap:7px;margin-bottom:4px}
.frow{display:grid;grid-template-columns:minmax(120px,1fr) 110px 44px;gap:10px;align-items:center;font-size:12.5px}
.frow .bar{margin:0}
.feat-link{cursor:pointer;border-radius:5px;padding:2px 4px;margin:0 -4px}
.feat-link:hover{background:var(--sunk)}
.feat-link.on{background:var(--ok-bg)}
.scoped{font-size:12px;color:var(--muted);align-self:center}
tr.frontrow td{background:var(--bad-bg)}
tr.ladrow{cursor:pointer}
tr.ladrow:hover td{background:var(--sunk)}
.frow .mono{font-size:11.5px;color:var(--muted);text-align:right}
.story{cursor:grab}
.story:active{cursor:grabbing}
.story.dragging{opacity:.45}
.story.st-wip{border-left:3px solid var(--c-wip)}
.story.st-open{border-left:3px solid var(--c-open)}
.story.st-done{border-left:3px solid var(--c-done)}
.mini{font:inherit;font-size:11px;border:1px solid var(--line);background:var(--surface);
  color:var(--muted);border-radius:5px;padding:1px 8px;cursor:pointer;margin-left:8px}
.mini:hover{color:var(--ink);border-color:var(--accent)}
.tform{display:grid;gap:8px;margin:10px 0 4px;padding:12px;background:var(--sunk);
  border:1px solid var(--line);border-radius:7px}
.tform input,.tform select{font:inherit;font-size:13px;background:var(--surface);color:var(--ink);
  border:1px solid var(--line);border-radius:5px;padding:5px 8px;width:100%}
.tform button{font:inherit;font-size:13px;border:1px solid var(--line);border-radius:5px;
  padding:5px 12px;cursor:pointer;background:var(--surface);color:var(--ink)}
.tform button[type=submit]{background:var(--accent);color:var(--bg);border-color:transparent;font-weight:600}
.tform label{display:block;font-size:12px;color:var(--muted)}
.tform label input{margin-top:3px}
.tform label.chk{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--ink)}
.tform label.chk input{width:auto;margin:0}
.frow2{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.frow2 select,.frow2 input{flex:1;min-width:120px}
.resume{background:var(--sunk);border:1px solid var(--line);border-radius:6px;padding:6px 9px;
  font-size:11.5px;display:inline-block;max-width:640px;line-height:1.45}
.ideagrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.ideacard{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--c-wip);
  border-radius:8px;padding:12px 14px}
.ideacard b{display:block;font-size:13.5px;line-height:1.4;margin-bottom:4px}
.ideacard .ihead{display:flex;justify-content:space-between;font-size:10.5px;color:var(--muted);
  margin-bottom:7px}
.ideacard .iwhy{display:block;color:var(--muted);font-size:12px;line-height:1.45}
.ideacard .notes{font-size:11.5px}
.notes{margin-top:6px;padding-left:8px;border-left:2px solid var(--line);font-size:11.5px;color:var(--muted)}
.notes div{margin-bottom:2px}
.story .noev{color:var(--bad);font-size:12px}
.story .feat{display:block;font:inherit;font-size:11px;color:var(--muted);margin-top:4px;
  background:var(--sunk);border:1px solid var(--line);border-radius:99px;padding:1px 8px;cursor:pointer}
.story .feat:hover{color:var(--ink);border-color:var(--accent)}
.col h4{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.story{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:9px 11px;margin-bottom:8px}
.story.done{opacity:.72}
.story b{font-weight:600;display:block}
.tid{color:var(--muted);font-weight:400;font-size:11.5px}
.story .tags{display:flex;gap:6px;align-items:center;margin-top:6px;flex-wrap:wrap}
.tag{font-size:10.5px;font-weight:600;padding:1px 6px;border-radius:99px;background:var(--sunk);
  color:var(--muted);border:1px solid var(--line)}
.tag.who{background:var(--ok-bg);color:var(--ok);border-color:transparent}
.tag.age{background:transparent;color:var(--muted);border-color:var(--line)}
.tag.prio{background:var(--idle-bg);color:var(--idle)}
select.priosel{font:inherit;font-size:10.5px;font-weight:600;padding:0 2px;border:0;border-radius:99px;
  cursor:pointer;-webkit-appearance:none;appearance:none;text-align:center}
.tag.prio.p10,.tag.prio.p9,.tag.prio.p8{background:var(--bad-bg);color:var(--bad)}
.tag.prio.p7,.tag.prio.p6{background:var(--warn-bg);color:var(--warn)}
.tag.chk{background:var(--warn-bg);color:var(--warn)}
.tag.mdl{background:var(--warn-bg);color:var(--warn);border-color:transparent}
.copy{margin-left:auto;font:inherit;font-size:11px;border:1px solid var(--line);background:var(--surface);
  color:var(--muted);border-radius:5px;padding:1px 8px;cursor:pointer}
.copy:hover{color:var(--ink);border-color:var(--accent)}
.filters{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.filters button{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--surface);
  color:var(--muted);border-radius:99px;padding:3px 11px;cursor:pointer}
select{font:inherit;font-size:12.5px;background:var(--surface);color:var(--ink);
  border:1px solid var(--line);border-radius:5px;padding:3px 7px}
.filters button.zero{opacity:.5}
.mail{display:grid;grid-template-columns:172px 320px 1fr;grid-template-rows:auto 1fr;gap:0;
  height:calc(100vh - 190px);border:1px solid var(--line);border-radius:8px;overflow:hidden;
  background:var(--surface)}
.mail .mcompose{grid-column:1 / -1;grid-row:1;margin:0;border:0;border-bottom:1px solid var(--line);
  border-radius:0}
.mfolders{grid-row:2;border-right:1px solid var(--line);background:var(--sunk);padding:8px 0;overflow-y:auto}
.mothers{margin:6px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.mothers summary{cursor:pointer;font-size:11px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);padding:7px 12px}
.mothers summary .mono{text-transform:none;letter-spacing:0}
.mothers .mfolder{font-size:12.5px;padding-left:20px}
.mread h3{border-bottom:1px solid var(--line);padding-bottom:10px}
.mread .acts{border-top:1px solid var(--line);padding-top:12px;margin-top:14px}
.mlist{background:var(--surface)}
.mfolder{display:block;width:100%;text-align:left;border:0;background:none;color:var(--ink);
  font:inherit;font-size:13px;padding:6px 12px;cursor:pointer;border-left:2px solid transparent}
.mfolder:hover{background:var(--surface)}
.mfolder[aria-current="true"]{background:var(--surface);border-left-color:var(--accent);font-weight:600}
.mfolder .mono{color:var(--muted);font-size:11px}
.compose{margin:10px 12px 0;width:calc(100% - 24px);font:inherit;font-size:12.5px;
  background:var(--accent);color:var(--bg);border:0;border-radius:6px;padding:5px 10px;
  cursor:pointer;font-weight:600}
.mlist{grid-row:2;border-right:1px solid var(--line);overflow-y:auto}
.mitem{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);
  background:none;color:var(--ink);font:inherit;padding:9px 12px;cursor:pointer}
.mitem:hover{background:var(--sunk)}
.mitem.on{background:var(--sunk);box-shadow:inset 2px 0 0 var(--accent)}
.mitem.un b{color:var(--warn)}
.mitem b{display:block;font-size:12.5px}
.mitem .mono{float:right;font-size:11px;color:var(--muted);font-weight:400}
.mitem span:last-child{display:block;color:var(--muted);font-size:12px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.mread{grid-row:2;padding:18px 20px;overflow-y:auto}
.mread .brief{background:transparent;border:0;padding:0;font-size:13.5px}
@media (max-width:900px){.mail{grid-template-columns:1fr;height:auto}}
#qbox{font:inherit;font-size:12.5px;background:var(--surface);color:var(--ink);
  border:1px solid var(--line);border-radius:99px;padding:3px 12px;min-width:180px}
.filters button[aria-pressed="true"]{background:var(--accent);color:var(--bg);border-color:transparent;font-weight:600}
.story span{color:var(--muted);font-size:12px}
.empty{color:var(--muted);font-size:13px;padding:10px 0}
details{margin-top:10px}
summary{cursor:pointer;color:var(--accent);font-size:12.5px}
pre.brief{background:var(--sunk);border:1px solid var(--line);border-radius:6px;padding:12px 14px;
  overflow-x:auto;font-size:12px;line-height:1.55;white-space:pre-wrap;margin:8px 0 0}
pre.cmd{background:var(--sunk);border:1px solid var(--line);border-radius:6px;padding:10px 12px;
  overflow-x:auto;font-size:12.5px;margin:8px 0}
.spark{display:block;width:100%;height:64px;margin:6px 0 2px}
a{color:var(--accent)}
#sheet{position:fixed;inset:0;background:rgba(0,0,0,.42);display:flex;justify-content:flex-end;z-index:50}
#sheet[hidden]{display:none}
.sheetbox{background:var(--surface);width:min(560px,100%);height:100%;overflow-y:auto;padding:26px 26px 60px;
  border-left:1px solid var(--line);position:relative}
.sheetclose{position:absolute;top:14px;right:16px;border:0;background:none;color:var(--muted);
  font-size:24px;line-height:1;cursor:pointer}
.sheetclose:hover{color:var(--ink)}
#sheet h2{font-size:19px;margin:0 0 4px;letter-spacing:-.01em;padding-right:30px}
#sheet .path{color:var(--muted);font-size:12.5px;margin:0 0 14px}
#sheet dl{display:grid;grid-template-columns:110px 1fr;gap:7px 12px;margin:0 0 16px;font-size:13px}
#sheet dt{color:var(--muted)}
#sheet dd{margin:0}
#sheet .acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
#sheet .acts select{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);
  color:var(--ink);border-radius:6px;padding:5px 10px;cursor:pointer}
#sheet .acts button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);
  color:var(--ink);border-radius:6px;padding:5px 12px;cursor:pointer}
#sheet .acts button:hover{border-color:var(--accent)}
#sheet .notelist div{border-left:2px solid var(--line);padding:2px 0 2px 10px;margin-bottom:8px;font-size:13px}
kbd{background:var(--sunk);border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:12px}
</style></head><body>
<div id="app">
  <button id="navbtn" title="projects (⌘K)">☰</button>
  <aside>
    <h1>Workshop</h1>
    <div class="gen mono" id="gen"></div>
    <div class="grp">Projects</div>
    <div id="plist"></div>
    <div class="grp">Workshop</div>
    <div id="wlist"></div>
    <button id="themebtn" title="light / dark">◐ theme</button>
  </aside>
  <main>
    <div class="head">
      <h2 id="title"></h2><button id="refreshbtn" title="refresh">⟳</button><p id="sub"></p>
      <nav id="tabs"></nav>
    </div>
    <div class="body" id="view"></div>
  </main>
  <div id="sheet" hidden><div class="sheetbox"><button class="sheetclose" title="close">×</button>
    <div id="sheetbody"></div></div></div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const SERVED = location.protocol === "http:" || location.protocol === "https:";
const $ = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cls = (s) => { s = (s||"").toUpperCase();
  if (s.startsWith("PROVEN")||s.startsWith("CLEARED")||s==="OK") return "p-ok";
  if (s.startsWith("BROKEN")||s.startsWith("NEVER")||s.startsWith("VOID")) return "p-bad";
  if (s.startsWith("INHERITED")||s.startsWith("PARTIAL")||s.startsWith("FIXED")) return "p-warn";
  return "p-idle"; };

document.getElementById("gen").textContent = "generated " + D.generated;

document.getElementById("refreshbtn").onclick = () => {
  if (!SERVED) { alert("Opened as a file, so there is nothing to refresh from.\n\nRun Workshop/serve.py."); return; }
  refresh();
};
document.addEventListener("keydown", e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "r" && SERVED) { e.preventDefault(); refresh(); }
});

(function nav(){
  const app = document.getElementById("app"), KEY = "workshop.nav";
  let open = false;
  try { open = localStorage.getItem(KEY) === "1"; } catch {}
  const set = v => { open = v; app.classList.toggle("navopen", v);
                     try { localStorage.setItem(KEY, v ? "1" : "0"); } catch {} };
  set(open);
  document.getElementById("navbtn").onclick = () => set(!open);
  document.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); set(!open); }
  });
  // picking a project is the reason it was open; close it again
  document.querySelectorAll("#plist button, #wlist button").forEach(b =>
    b.addEventListener("click", () => set(false)));
})();

(function theme(){
  const KEY = "workshop.theme";
  const apply = v => { if (v) document.documentElement.setAttribute("data-theme", v);
                       else document.documentElement.removeAttribute("data-theme"); };
  let cur_t = null;
  try { cur_t = localStorage.getItem(KEY); } catch {}
  apply(cur_t);
  document.getElementById("themebtn").onclick = () => {
    cur_t = (cur_t === "light") ? "dark" : "light";
    apply(cur_t);
    try { localStorage.setItem(KEY, cur_t); } catch {}
  };
})();

let cur = D.projects.find(p => p.builds && p.builds.length) || D.projects[0];
let curTab = "Status";   // the page opens on the standing report, not on a project
let boardFilter = "";
let boardView = "stories";
let boardFeature = "";
let boardPhase = "";
let boardQ = "";
const MK = "workshop.models";
function loadModels(){ try { return JSON.parse(localStorage.getItem(MK)) || {}; } catch { return {}; } }
function saveModels(m){ try { localStorage.setItem(MK, JSON.stringify(m)); } catch {} }
let MODEL_OVERRIDE = loadModels();
function modelFor(roleId, storyModel){
  if (storyModel) return storyModel;
  if (MODEL_OVERRIDE[roleId]) return MODEL_OVERRIDE[roleId];
  const r = role(roleId); return r ? r.model : "";
}
const PTABS = ["Overview","Board","Progress","Builds","Rules","Messages","Ideas","Log"];
const WTABS = {Status:"status", Usage:"usage", Agents:"agents", Rules:"rules", Skills:"skills", "How to":"howto", "New project":"new"};

/* ---------------- sidebar ---------------- */
const plist = document.getElementById("plist");
D.projects.forEach(p => {
  const last = (p.log && p.log[0]) ? p.log[0].date : "";
  const b = $(`<button data-p="${esc(p.name)}">${esc(p.name)}<small>${esc(last)}</small></button>`).firstChild;
  b.onclick = () => { cur = p; if (!PTABS.includes(curTab)) curTab = "Overview"; draw(); };
  plist.appendChild(b);
});
const wlist = document.getElementById("wlist");
Object.keys(WTABS).forEach(k => {
  const b = $(`<button data-w="${esc(k)}">${esc(k)}</button>`).firstChild;
  b.onclick = () => { curTab = k; draw(); };
  wlist.appendChild(b);
});

/* ---------------- panels ---------------- */
function overview(p){
  const ladder = (p.components||[]).filter(c => /ladder|stage/i.test(c.section));
  const front = ladder.find(c => !/CLEARED|PROVEN/i.test(c.status_full||c.status));
  const gate = p.gate||[];
  return `
  ${p.headline ? `<div class="card"><h3>Where it stands · ${esc(p.headline_doc)}</h3>
     <p class="lede">${esc(p.headline)}</p></div>` : ""}
  ${front ? `<div class="card front"><h3>Front line</h3>
     <p class="lede"><b>${esc(front.name)}</b> — <span class="pill ${cls(front.status)}">${esc(front.status)}</span></p>
     <p class="muted" style="margin:0">${esc(front.evidence)}</p></div>` : ""}
  <div class="grid">
    <div class="card"><h3>Identity</h3><table>
      <tr><td class="muted">Repo</td><td>${p.repo ? `<a href="https://github.com/${esc(p.repo)}">${esc(p.repo)}</a>` : "—"}</td></tr>
      <tr><td class="muted">Chip</td><td>${esc(p.chip||"—")}</td></tr>
      <tr><td class="muted">Clock floor</td><td>${p.clock_floor_mhz ? esc(p.clock_floor_mhz)+" MHz" : "—"}</td></tr>
      <tr><td class="muted">Head</td><td class="mono">${esc(p.head||"—")}</td></tr>
    </table></div>
    <div class="card"><h3>Machines</h3>${(p.machines||[]).length
      ? `<table>${p.machines.map(m=>`<tr><td><b>${esc(m.name)}</b></td><td class="muted">${esc(m.role)}</td></tr>`).join("")}</table>`
      : `<p class="empty">No <span class="mono">docs/project.json</span> yet.</p>`}</div>
  </div>
  ${gate.length ? `<div class="card"><h3>The gate — a build is the last resort</h3><table>
     <tr><th>Rung</th><th>Source</th><th>Where</th></tr>
     ${gate.map(g=>`<tr><td class="mono">${esc(g.rung)}</td><td><b>${esc(g.source)}</b><br><span class="muted">${esc(g.note||"")}</span></td>
       <td class="mono muted">${esc(g.where||"")}</td></tr>`).join("")}</table></div>` : ""}
  <div class="card"><h3>Documents</h3><p class="mono muted" style="margin:0">${
     (p.docs_present||[]).map(esc).join(" · ") || "—"}</p></div>`;
}

function board(p){
  if (!(p.board||[]).length) return `<div class="card"><h3>Board</h3>
    <p class="empty">No stories found${p.board_doc ? ` in <span class="mono">${esc(p.board_doc)}</span>` : ""}.
    The board is drawn from a plan document written as <b>Phase → Feature → Story</b>:</p>
    <pre class="cmd">## Phase 2 — ROM path on the CPU port

### CPU reads its own ROM from SDRAM
- [x] Reset vector reads back correct — GAO round 4a, $001FFE → $27,$E1 @design
- [~] Data matches game.pce over 256 fetches — 0 mismatches to close @build #sonnet
- [ ] Not started yet — what would close it @sim</pre>
    <p class="muted">Everything after the dash is the evidence, and a story cannot be
    ticked without one. <span class="mono">[ ]</span> to do · <span class="mono">[~]</span> doing ·
    <span class="mono">[x]</span> done.</p></div>`;

  const all = p.board.flatMap(ph=>ph.features.flatMap(f=>f.stories));
  // every role is offered, not only the ones that happen to own something today --
  // a role you cannot see is a role you will not assign
  // a closed ticket is not somebody's work any more -- only live tickets count
  const counts = {};
  all.filter(s => s.state !== "done")
     .forEach(s => { const k = s.who || "unassigned"; counts[k] = (counts[k]||0) + 1; });
  const liveN = all.filter(s => s.state !== "done").length;
  const roleIds = ((D.roles&&D.roles.roles)||[]).map(r=>r.id);
  const whos = [...new Set([...roleIds, ...Object.keys(counts)])]
    .filter(w => w !== "unassigned" || counts["unassigned"]);
  const filters = `<div class="filters">
      <button data-f="" aria-pressed="${boardFilter===""}">everyone <span class="mono">${liveN}</span></button>
      ${whos.map(w=>`<button data-f="${esc(w)}" aria-pressed="${boardFilter===w}"
         class="${counts[w]?"":"zero"}">@${esc(w)} <span class="mono">${counts[w]||0}</span></button>`).join("")}
    </div>`;

  const anyCheck = p.board.some(ph=>ph.features.some(f=>f.stories.some(s=>s.checker||s.state==="check")));
  const COLS = anyCheck
    ? [["backlog","Backlog"],["open","Ready"],["wip","Doing"],["check","Check"],["done","Done"]]
    : [["backlog","Backlog"],["open","Ready"],["wip","Doing"],["done","Done"]];
  const bar = (pct, big) => `<div class="bar${big?" big":""}"><i style="width:${pct}%"></i></div>`;

  const card = (p, s) => `<div class="story st-${s.state}${s.blocked?" blocked":""}" draggable="true"
      data-line="${esc(s.line)}" data-state="${s.state}" data-ev="${esc(s.evidence)}"
      data-who="${esc(s.who)}" data-checker="${esc(s.checker||"")}" data-feat="${esc(s.feature||"")}"
      data-featok="${s.featok?1:0}" data-story="${esc(JSON.stringify(s))}">
      <b>${s.id?`<span class="tid mono">#${s.id}</span> `:""}${esc(s.text)}</b>
      ${s.blocked?`<span class="blockline">on hold — ${esc(s.blocked)}</span>`:""}
      ${s.evidence?`<span>${esc(s.evidence)}</span>`:'<span class="noev">no evidence stated</span>'}
      ${(s.notes||[]).length?`<div class="notes">${s.notes.slice(-3).map(n=>
          `<div><span class="mono">${esc(n.date)} @${esc(n.who)}</span> ${esc(n.text)}</div>`).join("")}</div>`:""}
      ${s.feature?`<button class="feat feat-link" data-f="${esc(s.feature)}"
         title="show this feature">${esc(s.feature)}${s.featok?"":" · not refined"}</button>`:""}
      <div class="tags">
        ${SERVED?`<select class="priosel tag prio p${s.prio||5}" title="priority, 10 highest">
          ${[10,9,8,7,6,5,4,3,2,1].map(n=>`<option value="${n}"${n===(s.prio||5)?" selected":""}>!${n}</option>`).join("")}
        </select>`:`<span class="tag prio p${s.prio||5}" title="priority, 10 highest">!${s.prio||5}</span>`}
        ${s.who?`<span class="tag who">@${esc(s.who)}</span>`:'<span class="tag">unassigned</span>'}
        ${s.checker?`<span class="tag chk">+${esc(s.checker)} checks</span>`:""}
        ${modelFor(s.who,s.model)?`<span class="tag mdl">${esc(modelFor(s.who,s.model))}</span>`:""}
        ${SERVED?`<button class="mini note">note</button>`:""}
        ${SERVED?`<button class="mini edit">edit</button>`:""}
        ${SERVED&&s.state!=="done"?`<button class="mini block">${s.blocked?"unblock":"hold"}</button>`:""}
        ${s.state==="done"?"":`<button class="copy" data-brief="${esc(brief(p,s))}">copy brief</button>`}
      </div></div>`;

  // view: all stories, or the features list; clicking a feature scopes to it
  const PARKED = /^(ideas|cancelled|archive)\b/i;
  const phases = p.board.map(ph=>ph.phase);
  if (boardPhase && !phases.includes(boardPhase)) boardPhase = "";
  const controls = `<div class="filters">
      <select id="phasesel" title="epic">
        <option value=""${boardPhase===""?" selected":""}>All live phases</option>
        ${phases.map(ph=>`<option value="${esc(ph)}"${boardPhase===ph?" selected":""}>${esc(ph)}</option>`).join("")}
      </select>
      <input id="qbox" type="search" placeholder="search tickets…" value="${esc(boardQ)}">
      <select id="viewsel">
        <option value="stories"${boardView==="stories"?" selected":""}>Stories</option>
        <option value="features"${boardView==="features"?" selected":""}>Features</option>
      </select>
      ${boardFeature?`<button class="backbtn" data-f="">← all features</button>
        <span class="scoped mono">feature: ${esc(boardFeature)}</span>`:""}
    </div>`;

  if (boardView === "features" && !boardFeature) {
    return controls + filters + p.board.filter(ph=>boardPhase ? ph.phase===boardPhase : !PARKED.test(ph.phase)).map(ph => {
      const fts = ph.features.filter(f=>f.total);
      if (!fts.length) return "";
      return `<div class="card">
        <div class="phhead"><h3 style="margin:0">${esc(ph.phase)}</h3>
          <div class="phnum mono">${ph.features_done}/${ph.features_total} features · <b>${ph.pct}%</b></div></div>
        ${bar(ph.pct, true)}
        <div class="fstrip">${fts.map(f=>`
          <div class="frow feat-link" data-f="${esc(f.feature)}" title="show its stories">
            <span>${esc(f.feature)}
              ${f.refined?'<span class="tag who">refined</span>':'<span class="tag">not refined</span>'}
            </span>${bar(f.pct)}
            <span class="mono">${f.done_n}/${f.total}</span></div>`).join("")}</div>
      </div>`;
    }).join("") + `<p class="muted">Click a feature to see the stories attached to it.</p>`;
  }

  const body = p.board.filter(ph=>boardPhase ? ph.phase===boardPhase : !PARKED.test(ph.phase)).map(ph => {
    let fts = ph.features
      .filter(f => !boardFeature || f.feature === boardFeature)
      .map(f => ({...f, stories: f.stories.filter(s =>
        (!boardFilter || (s.who||"unassigned") === boardFilter) && matchQ(s))}));
    let st = fts.flatMap(f => f.stories.map(s => ({...s, phase: ph.phase, feature: f.feature, featok: f.refined})));
    if (!st.length) return "";
    return `<div class="card">
      <div class="phhead">
        <h3 style="margin:0">${esc(ph.phase)}</h3>
        <div class="phnum mono">${ph.features_done}/${ph.features_total} features ·
          ${ph.done_n}/${ph.total} stories · <b>${ph.pct}%</b>
          ${SERVED?`<button class="mini addbtn" data-phase="${esc(ph.phase)}">+ ticket</button>`:""}</div>
      </div>
      ${SERVED?`<form class="tform" hidden data-phase="${esc(ph.phase)}">
        <div class="frow2">
          <select name="feature">
            ${ph.features.map(f=>`<option value="${esc(f.feature)}">${esc(f.feature)}</option>`).join("")}
            <option value="__new">+ new feature…</option>
          </select>
          <input name="newfeature" placeholder="new feature name" hidden>
        </div>
        <div class="frow2">
          <input name="text" placeholder="What has to happen" required style="flex:3">
          <select name="prio" title="priority, 10 highest">
            ${[10,9,8,7,6,5,4,3,2,1].map(n=>`<option value="${n}"${n===5?" selected":""}>!${n}</option>`).join("")}
          </select>
        </div>
        <input name="evidence" placeholder="What closes it — the measurement">
        <div class="frow2">
          <select name="who">${((D.roles&&D.roles.roles)||[]).map(r=>
            `<option value="${esc(r.id)}">@${esc(r.id)}</option>`).join("")}</select>
          <select name="checker"><option value="">nobody checks</option>
            ${((D.roles&&D.roles.roles)||[]).map(r=>`<option value="${esc(r.id)}">+${esc(r.id)} checks</option>`).join("")}</select>
          <select name="model"><option value="">role default</option>
            ${Object.keys((D.roles&&D.roles.models)||{}).map(k=>
              `<option value="${esc(k)}">#${esc(k)}</option>`).join("")}</select>
          <button type="submit">Add</button>
          <button type="button" class="cancel">Cancel</button>
        </div>
      </form>`:""}
      ${bar(ph.pct, true)}
      <div class="fstrip">${ph.features.filter(f=>f.total).map(f=>`
        <div class="frow feat-link${boardFeature===f.feature?" on":""}" data-f="${esc(f.feature)}"
             title="show only its stories">
          <span>${esc(f.feature)}</span>${bar(f.pct)}
          <span class="mono">${f.done_n}/${f.total}</span></div>`).join("")}</div>
      <div class="kan" style="--ncols:${COLS.length}">${COLS.map(([k,label])=>{
        const list = st.filter(s=>s.state===k)
          .sort((a,b)=>(a.blocked?1:0)-(b.blocked?1:0) || (b.prio||5)-(a.prio||5));
        return `<div class="col drop col-${k}" data-to="${k}" data-project="${esc(p.name)}">
          <h4>${label} <span class="mono">${list.length}</span></h4>
          ${list.map(s=>card(p,s)).join("") || '<p class="empty">—</p>'}
        </div>`; }).join("")}</div>
    </div>`;
  }).join("");

  const ideaBox = (SERVED && /^ideas\b/i.test(boardPhase)) ? `<form class="tform" id="ideaform">
      <input name="text" placeholder="An idea worth keeping — not something to do yet" required>
      <input name="about" placeholder="Why it might matter, in a line (optional)">
      <div class="frow2"><button type="submit">Keep it</button>
        <span class="muted">Nothing is pulled from Ideas. To act on one, move it to a real phase —
        it needs an owner and a closing measurement like any other work.</span></div>
    </form>` : "";
  const note = SERVED
    ? `<p class="muted" style="margin:-4px 0 14px">Drag a ticket between columns and the plan file is
       rewritten. Moving one to <b>Done</b> asks for the evidence, because a story cannot be ticked
       without it.</p>`
    : `<p class="muted" style="margin:-4px 0 14px">Read-only: this page was opened as a file. Run
       <span class="mono">Workshop/serve.py</span> to drag tickets and have
       <span class="mono">${esc(p.board_doc||"the plan")}</span> rewritten.</p>`;
  return controls + filters + ideaBox + note + (body || `<p class="empty">Nothing here yet.</p>`);
}

const bar2 = (pct) => `<div class="bar big"><i style="width:${pct}%"></i></div>`;

async function api(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body)});
  if (r.ok) {
    // an endpoint can succeed and still have something the caller must know --
    // mail written but not pushed is the case that made this necessary (#95),
    // because it looked identical to a delivery
    const j = await r.json().catch(() => ({}));
    await refresh();
    if (j && j.warn) alert(j.warn);
    return true;
  }
  alert(await r.text()); return false;
}

// Re-read the repos and redraw in place. Keeps the tab, the project, the filters
// and the scroll position -- a full reload throws all of that away, which is why
// nobody presses one.
let refreshing = false;
async function refresh(){
  if (!SERVED || refreshing) return false;
  refreshing = true;
  const btn = document.getElementById("refreshbtn");
  if (btn) { btn.classList.add("spin"); btn.disabled = true; }
  const view = document.getElementById("view");
  const y = view ? view.scrollTop : 0;
  try {
    const fresh = await (await fetch("/api/state", {cache:"no-store"})).json();
    // the page's own code is whatever was loaded; refreshing data cannot fix a
    // bug fixed since. If the renderer changed, take the whole page again.
    if (fresh.code_sig && D.code_sig && fresh.code_sig !== D.code_sig) {
      location.reload();
      return true;
    }
    Object.assign(D, fresh);
    const name = cur && cur.name;
    cur = D.projects.find(p => p.name === name) || D.projects[0];
    SHEET.hidden = true;
    draw();
    const v2 = document.getElementById("view"); if (v2) v2.scrollTop = y;
    if (btn) btn.title = "refreshed " + new Date().toLocaleTimeString();
  } catch (e) {
    alert("Could not refresh: " + e);
  } finally {
    refreshing = false;
    if (btn) { btn.classList.remove("spin"); btn.disabled = false; }
  }
  return true;
}

const SHEET = document.getElementById("sheet");
const SHEETBODY = document.getElementById("sheetbody");
document.querySelector(".sheetclose").onclick = () => { SHEET.hidden = true; };
SHEET.onclick = e => { if (e.target === SHEET) SHEET.hidden = true; };
document.addEventListener("keydown", e => { if (e.key === "Escape") SHEET.hidden = true; });

function matchQ(s){
  if (!boardQ.trim()) return true;
  const q = boardQ.trim().toLowerCase();
  if (/^#?\d+$/.test(q)) return String(s.id) === q.replace("#","");
  return [s.text, s.evidence, s.who, s.checker, s.blocked, s.feature]
    .filter(Boolean).join(" ").toLowerCase().includes(q);
}

const age = (d) => d === 0 ? "today" : d === 1 ? "yesterday"
  : d < 7 ? d + "d ago" : d < 30 ? Math.floor(d/7) + "w ago" : Math.floor(d/30) + "mo ago";

const STATE_LABEL = {backlog:"Backlog", open:"Ready", wip:"Doing", check:"Waiting for a check", done:"Done"};

function openSheet(projectName, s, line){
  const r = role(s.who);
  D._phases = (cur.board||[]).map(ph=>ph.phase);
  SHEETBODY.innerHTML = `
    <h2>${s.id?`<span class="tid mono">#${s.id}</span> `:""}${esc(s.text)}</h2>
    <p class="path">${esc(s.phase||"")}${s.feature?" › "+esc(s.feature):""}</p>
    ${s.blocked?`<div class="card" style="border-color:var(--bad);background:var(--bad-bg);margin-bottom:14px">
       <b style="color:var(--bad)">On hold</b><br>${esc(s.blocked)}</div>`:""}
    <dl>
      <dt>Status</dt><dd><span class="pill ${s.state==="done"?"p-ok":(s.state==="wip"?"p-warn":"p-idle")}">${STATE_LABEL[s.state]||s.state}</span></dd>
      <dt>Closes when</dt><dd>${s.evidence?esc(s.evidence):'<span style="color:var(--bad)">nothing stated — it is not refined</span>'}</dd>
      <dt>Owner</dt><dd>${s.who?"@"+esc(s.who):"unassigned"}${r?` <span class="muted">· ${esc(r.name)}</span>`:""}</dd>
      ${s.checker?`<dt>Checked by</dt><dd>+${esc(s.checker)} — it cannot be closed without them</dd>`:""}
      <dt>Model</dt><dd>${esc(modelFor(s.who,s.model)||"—")}</dd>
      <dt>Made</dt><dd>${s.created?esc(s.created)+" · "+age(s.age_created)+" old":"—"}</dd>
      <dt>Last changed</dt><dd>${s.touched?esc(s.touched)+" · "+age(s.age_days):"—"}</dd>
      <dt>Priority</dt><dd>!${s.prio||5} <span class="muted">(10 is picked up first)</span></dd>
      <dt>Feature</dt><dd>${esc(s.feature||"—")} ${s.featok?'<span class="tag who">refined</span>':'<span class="tag">not refined — nothing here can be started</span>'}</dd>
    </dl>
    <h3>Notes — what happened, and where the detail is</h3>
    <div class="notelist">${(s.notes||[]).length
      ? s.notes.map(n=>`<div><span class="mono muted">${esc(n.date)} @${esc(n.who)}</span><br>${esc(n.text)}</div>`).join("")
      : '<p class="empty">No notes yet.</p>'}</div>
    ${SERVED?`<div class="acts">
      <select data-a="phase"><option value="">move to phase…</option>
        ${(D._phases||[]).filter(x=>x!==s.phase).map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("")}
      </select>
      <button data-a="note">Add a note</button>
      <button data-a="block">${s.blocked?"Clear the hold":"Put on hold"}</button>
      <button data-a="edit">Edit</button>
    </div>`:'<p class="muted">Read-only — run Workshop/serve.py to edit from here.</p>'}
    ${r&&r.brief?`<p class="muted" style="margin-top:18px">Whoever picks this up reads
      <span class="mono">Workshop/${esc(r.brief)}</span> first.</p>`:""}`;

  const psel = SHEETBODY.querySelector('[data-a="phase"]');
  if (psel) psel.onchange = () => {
    if (psel.value) api("/api/move_phase", {project: projectName, line, phase: psel.value});
  };
  SHEETBODY.querySelectorAll(".acts button").forEach(b => b.onclick = () => {
    const a = b.dataset.a;
    if (a === "note") {
      const txt = prompt("A line saying what happened, and where the detail is");
      if (txt && txt.trim()) api("/api/note", {project: projectName, line, text: txt.trim(), who: s.who||"design"});
    } else if (a === "block") {
      if (s.blocked) api("/api/edit", {project: projectName, line, blocked: ""});
      else { const why = prompt("On hold — what is it waiting on?");
             if (why && why.trim()) api("/api/edit", {project: projectName, line, blocked: why.trim()}); }
    } else {
      const text = prompt("Story", s.text); if (text === null) return;
      const ev = prompt("Closes when", s.evidence || ""); if (ev === null) return;
      api("/api/edit", {project: projectName, line, text, evidence: ev});
    }
  });
  SHEET.hidden = false;
}

// The same three lines for every seat, so a session after a clear starts the
// same way every time and Dennis does not have to remember seven variants.
function resumeLine(id){
  const proj = (cur && cur.name) || "PCEHeroTN";
  return `You are @${id} on ${proj}. Read ../Workshop/roles/${id}.md, then run `
       + `../Workshop/board.py inbox --who ${id} and ../Workshop/board.py next ${proj} --who ${id}, `
       + `and do what it says.`;
}

function role(id){ return ((D.roles&&D.roles.roles)||[]).find(r=>r.id===id) || null; }
function brief(p, s){
  const r = role(s.who);
  const model = modelFor(s.who, s.model);
  const reads = (r ? r.reads : ["CLAUDE.md","RESUME_HERE.md"]).join(", ");
  return [
    r ? `You are the ${r.name} (@${r.id}) for ${p.name}. ${r.does}` : `You are working on ${p.name}.`,
    r && r.brief ? `Read your brief first: ../Workshop/${r.brief}. It says what you own, what you never do, and how to move your own tickets.` : "",
    model ? `Run this on ${model}.` : "",
    `Read first: ${reads}.`,
    `TASK: ${s.text}`,
    s.evidence ? `CLOSES WHEN: ${s.evidence}` : "",
    `The gate applies: manuals, then the working original, then simulation. A hardware build is the last resort and you must say why the cheaper rungs cannot answer it.`,
    `Update the plan and the live state in the same commit as the finding.`
  ].filter(Boolean).join("\n");
}

function agents(){
  const R = (D.roles&&D.roles.roles)||[], M = (D.roles&&D.roles.models)||{};
  if (!R.length) return `<div class="card"><p class="empty">No <span class="mono">Workshop/roles.json</span>.</p></div>`;
  const SES = D.sessions || {};
  const GIT = D.git_seen || {};
  const seen = (m) => m < 15 ? "active" : m < 120 ? `quiet ${m}m` : m < 1440 ? `last seen ${Math.floor(m/60)}h ago` : "gone quiet";
  return `<div class="card"><h3>Who is working</h3>
    <table>${R.map(r=>{const s = SES[r.id];
      const g = GIT[r.id];
      const live = s && s.mins < 15;
      // "no check-in" used to be shown for a seat that simply lives on the other
      // machine, which read as "never deployed" -- three PC seats looked dead
      // from the Mac for a fortnight (#95). A check-in is machine-local and
      // always will be; the page names where it is standing instead.
      const state = s ? seen(s.mins) : (g ? "working, no check-in" : "not open here");
      const ib = (D.inbox||{})[r.id];
      return `<tr>
        <td style="width:120px"><b>@${esc(r.id)}</b>
          ${ib?`<span class="tag mdl" title="unread">${ib.n} unread</span>`:""}</td>
        <td style="width:130px"><span class="hs ${live?"hs-running":(s&&s.mins<120?"hs-waiting":"hs-idle")}">${esc(state)}</span></td>
        <td class="muted">${s ? `${esc(s.machine||"")}${s.project?" · "+esc(s.project):""}${s.doing?" · "+esc(s.doing):""}`
          : (g ? `committed in ${esc(g.project)} on ${esc(g.date)} — ${esc(g.what)}`
               : `seat lives on ${esc(r.machine||"?")} — nothing here can see it, and no commit names it`)}</td>
        <td style="width:90px">${SERVED&&r.id!=="dennis"?`<button class="mini msgbtn" data-to="${esc(r.id)}">message</button>`:""}</td>
      </tr>`;}).join("")}</table>
    <p class="muted" style="margin:10px 0 0"><b>This page is running on
    <span class="mono">${esc(D.machine||"?")}</span>, and a check-in never leaves the machine that
    made it.</b> So <b>"not open here"</b> means exactly that and nothing more — a seat on the other
    machine can be hard at work and still say it. The one signal that does cross is a commit, which
    is what <b>"working, no check-in"</b> is: no session said anything, but its name is on a recent
    commit. Mail crosses too, since <span class="mono">board.py msg</span> pushes it.</p>
    <p class="muted" style="margin:6px 0 0">Self-reported: a session says
    <span class="mono">board.py checkin --who &lt;role&gt;</span> when it starts and when it moves a
    ticket. Nothing can detect a session from outside, so one that dies without signing off goes
    stale rather than showing green forever — which is why this reports elapsed time, not a light.
    Presence is deliberately not in git: it could only ever arrive stale, and it would cost a commit
    every time anyone opened a seat.</p>
  </div>
  <div class="card"><h3>How a task gets an owner</h3>
    <p class="lede">A story carries its owner and its model inline. The board reads them,
    filters by owner, and hands you the brief.</p>
    <pre class="cmd">- [ ] Data matches game.pce over 256 fetches — 0 mismatches to close @build #sonnet</pre>
    <p class="muted" style="margin:0"><span class="mono">@role</span> assigns it ·
    <span class="mono">#model</span> overrides the role's default model ·
    unassigned stories fall to <b>design</b>.</p></div>
  ${R.map(r=>`<div class="card"><h3>@${esc(r.id)} — ${esc(r.name)}</h3>
    <table>
      <tr><td class="muted" style="width:110px">Machine</td><td>${esc(r.machine)}</td></tr>
      ${r.model === "" ? `<tr><td class="muted">Model</td><td class="muted">— human</td></tr>` :
      `<tr><td class="muted">Model</td><td>
        <select class="mdlsel" data-role="${esc(r.id)}">
          ${Object.keys(M).map(k=>`<option value="${esc(k)}"${modelFor(r.id,"")===k?" selected":""}>${esc(k)} — ${esc(M[k])}</option>`).join("")}
        </select>
        ${MODEL_OVERRIDE[r.id] && MODEL_OVERRIDE[r.id] !== r.model
          ? `<span class="tag mdl" style="margin-left:8px">changed here, default is ${esc(r.model)}</span>` : ""}
      </td></tr>`}
      <tr><td class="muted">Does</td><td>${esc(r.does)}</td></tr>
      <tr><td class="muted">Reads first</td><td class="mono muted">${(r.reads||[]).map(esc).join(" · ")}</td></tr>
      ${r.brief?`<tr><td class="muted">Brief</td><td class="mono">Workshop/${esc(r.brief)}</td></tr>`:""}
      ${r.id!=="dennis"?`<tr><td class="muted">Start / resume</td><td>
        <div class="resume mono">${esc(resumeLine(r.id))}</div>
        ${SERVED||true?`<button class="mini copyresume" data-t="${esc(resumeLine(r.id))}">copy</button>`:""}
      </td></tr>`:""}
      <tr><td class="muted">Skills</td><td>${
        (D.skills||[]).filter(s=>(s.roles||[]).includes(r.id)).map(s=>
          `<span class="tag ${s.installed?"who":""}">${esc(s.name)}${s.installed?"":" · not installed"}</span>`).join(" ")
        || '<span class="muted">none tagged for this role</span>'}</td></tr>
    </table>
    ${r.brief_text?`<details><summary>the brief</summary><pre class="brief">${esc(r.brief_text)}</pre></details>`:""}
    </div>`).join("")}
  <div class="card"><h3>Where a model choice lives</h3>
    <p class="lede">Changing a model above takes effect immediately — every brief this page hands you
    will name it — and it is remembered in this browser. It is <b>not</b> written back to the repo,
    because this page is a file and nothing is listening.</p>
    <p class="muted" style="margin:0">To make it the default for everyone, set <span class="mono">"model"</span>
    for that role in <span class="mono">Workshop/roles.json</span> and regenerate. A story can always
    override both with <span class="mono">#model</span> on its own line.</p></div>
  <div class="card"><h3>Starting one</h3>
    <p class="lede">The page cannot launch an agent — it is a file, nothing is listening. What it can do
    is hand you the exact brief: hit <b>copy brief</b> on a card, open a session in that project with the
    model named, and paste.</p>
    <pre class="cmd">cd ${esc(D.root)}/&lt;project&gt; &amp;&amp; claude --model ${esc(Object.values(M)[0]||"claude-opus-5")}</pre>
    <p class="muted" style="margin:0">If you want the page to start them itself, that needs a small local
    server running alongside — say the word and it is an evening's work.</p></div>`;
}

function progress(p){
  // The ladder is not a copy: it is the board's ladder phase, rendered.
  const lad = (p.board||[]).find(ph=>/ladder/i.test(ph.phase));
  let ladderHtml = "";
  if (lad) {
    const st = lad.features.flatMap(f=>f.stories.map(s=>({...s, phase: lad.phase, feature: f.feature, featok: f.refined})));
    const front = st.findIndex(s=>s.state!=="done");
    ladderHtml = `<div class="card">
      <div class="phhead"><h3 style="margin:0">${esc(lad.phase)}</h3>
        <div class="phnum mono">${lad.done_n}/${lad.total} stages · <b>${lad.pct}%</b></div></div>
      ${bar2(lad.pct)}
      <table style="margin-top:12px">
      ${st.map((s,i)=>`<tr class="${i===front?"frontrow":""} ladrow" data-story="${esc(JSON.stringify(s))}" data-line="${esc(s.line)}">
        <td style="width:26px"><span class="pill ${s.state==="done"?"p-ok":(s.state==="wip"?"p-warn":"p-idle")}">
          ${s.state==="done"?"✓":(s.state==="wip"?"~":"·")}</span></td>
        <td><b>${esc(s.text)}</b>${i===front?' <span class="tag" style="background:var(--bad-bg);color:var(--bad)">front line</span>':""}
          ${s.blocked?`<span class="blockline">on hold — ${esc(s.blocked)}</span>`:""}</td>
        <td class="muted">${esc(s.evidence)}</td>
        <td class="mono muted" style="white-space:nowrap">${s.who?"@"+esc(s.who):""}${s.checker?" +"+esc(s.checker):""}</td>
      </tr>`).join("")}</table>
      <p class="muted" style="margin:10px 0 0">Rendered from the board, not kept separately — a stage
      is done when its story is, and a story cannot be ticked without a measurement. Move it on the
      <b>Board</b> tab.</p></div>`;
  }
  const c = p.components||[];
  if (!c.length) return ladderHtml + `<div class="card"><h3>Progress</h3><p class="empty">No
    <span class="mono">docs/CAPABILITY.md</span> in this project. That file is the results layer:
    one row per component or boot stage, each with a status, the evidence, and the build that last
    proved it.</p></div>`;
  const secs = [...new Set(c.map(x=>x.section))];
  return ladderHtml + secs.map(s => `<div class="card"><h3>${esc(s)}</h3><table>
    <tr><th>Item</th><th>Status</th><th>Evidence</th><th>Last read</th></tr>
    ${c.filter(x=>x.section===s).map(x=>`<tr>
      <td><b>${esc(x.name)}</b></td>
      <td><span class="pill ${cls(x.status)}">${esc(x.status)}</span></td>
      <td class="muted">${esc(x.evidence)}</td>
      <td class="mono muted">${esc(x.where)}</td></tr>`).join("")}</table></div>`).join("");
}

function builds(p){
  const b = p.builds||[], f = p.freshness||[];
  let spark = "";
  const pts = b.filter(x=>x.fmax);
  if (pts.length > 1){
    const W=760,H=64, lo=Math.min(...pts.map(x=>x.fmax), p.clock_floor_mhz||Infinity)-1,
          hi=Math.max(...pts.map(x=>x.fmax))+1;
    const X=i=>i*(W-8)/(pts.length-1)+4, Y=v=>H-4-((v-lo)/(hi-lo))*(H-12);
    const floor = p.clock_floor_mhz ? `<line x1="0" y1="${Y(p.clock_floor_mhz)}" x2="${W}" y2="${Y(p.clock_floor_mhz)}"
        stroke="var(--bad)" stroke-width="1" stroke-dasharray="3 3"/>` : "";
    spark = `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${floor}
      <polyline fill="none" stroke="var(--accent)" stroke-width="1.5"
        points="${pts.map((x,i)=>`${X(i)},${Y(x.fmax)}`).join(" ")}"/>
      ${pts.map((x,i)=>`<circle cx="${X(i)}" cy="${Y(x.fmax)}" r="2.5" fill="${x.failed?"var(--bad)":"var(--accent)"}"/>`).join("")}
    </svg><p class="muted" style="margin:0;font-size:12px">clk_sys Fmax by build${
      p.clock_floor_mhz?`, dashed line is the ${esc(p.clock_floor_mhz)} MHz floor`:""}</p>`;
  }
  return `${b.length?`<div class="card"><h3>Timing</h3>${spark}</div>`:""}
  <div class="card"><h3>Builds</h3>${b.length?`<table>
    <tr><th>#</th><th>Date</th><th>What</th><th>Fmax</th><th>TNS</th><th>LUT4</th></tr>
    ${b.slice().reverse().map(x=>`<tr><td class="mono">${x.n?esc(x.n):`b${x.seq}`}</td><td class="mono muted">${esc(x.date)}</td>
      <td>${esc(x.title)} ${x.failed?'<span class="pill p-bad">violated</span>':""}
        ${x.flashed?'<span class="pill p-ok">flashed</span>':""}</td>
      <td class="mono">${x.fmax??"—"}</td><td class="mono">${x.tns??"—"}</td>
      <td class="mono muted">${x.lut??"—"}</td></tr>`).join("")}</table>`
    :`<p class="empty">No <span class="mono">docs/BUILD_NOTES.md</span> entries parsed.</p>`}</div>
  ${f.length?`<div class="card"><h3>Bitstream freshness</h3><table>
    ${f.map(x=>`<tr><td class="mono">${esc(x.build)}</td>
      <td><span class="pill ${x.stale?"p-warn":"p-ok"}">${x.stale?"stale":"ok"}</span></td>
      <td class="mono muted">${(x.files||[]).map(esc).join("<br>")}</td></tr>`).join("")}</table>
    <p class="muted" style="margin:8px 0 0">A shared module belongs to every build that includes it.</p></div>`:""}`;
}

function log(p){
  return `<div class="card"><h3>Logbook — last ${(p.log||[]).length} commits</h3><table>
    ${(p.log||[]).map(l=>`<tr><td class="mono muted">${esc(l.date)}</td>
      <td class="mono muted">${esc(l.sha)}</td><td>${esc(l.subject)}</td></tr>`).join("")}</table></div>`;
}

function projrules(p){
  const R = p.project_rules||[];
  const six = D.rules.filter(r=>/PART II-A|PART II-B/.test(r.part)).slice(0,0); // placeholder
  return `<div class="card"><h3>Rules for ${esc(p.name)} only</h3>
    ${R.length ? `<table>${R.map(r=>`<tr><td style="width:44%"><b>${esc(r.rule)}</b></td>
        <td class="muted">${esc(r.detail)}</td></tr>`).join("")}</table>
      <p class="muted" style="margin:10px 0 0">Source: <span class="mono">${esc(p.name)}/CLAUDE.md</span>
      — the only file guaranteed to be read at the start of a session.</p>`
    : `<p class="empty">No project rules found. Put them under a heading containing the word
       <span class="mono">rules</span> in <span class="mono">CLAUDE.md</span>, one bolded rule per
       paragraph, and they appear here.</p>`}</div>
  ${(p.protected||[]).length ? `<div class="card"><h3>Protected files</h3>
    <p class="lede">Changing one of these needs <span class="mono">UNPROTECT:</span> in the commit
    message, and <span class="mono">check_rules.sh</span> refuses otherwise.</p>
    <p class="mono muted" style="margin:0">${p.protected.map(esc).join(" · ")}</p></div>` : ""}
  <div class="card"><h3>And the shared rulebook</h3>
    <p class="lede">${D.rules.length} rules apply to every project here — the gate, the source ladder,
    diff the original, one variable per build, state the procedure before the trial, and the three
    questions in the commit. They are on the <b>Rules</b> tab under Workshop, and in
    <span class="mono">Workshop/FPGA_WORKFLOW.md</span>.</p>
    <p class="muted" style="margin:0">Project rules never contradict them; they are the local detail
    the shared file cannot know — a pin map, a part that must not be re-added, this board's lamp order.</p></div>`;
}

// Why a project is not moving, said in one line. Waiting on a person is a
// healthy stop; nothing in progress and nothing waiting is not.
function health(p){
  const doing = p.doing.length, check = p.check.length, held = p.held.length;
  const mine = p.dennis.length, quiet = p.days_quiet;
  if (doing)              return ["running", `${doing} in progress`];
  if (mine)               return ["waiting on you", mine === 1 ? "1 ticket needs you" : `${mine} tickets need you`];
  if (check)              return ["waiting on a check", `${check} waiting to be confirmed`];
  if (held && !p.open_n)  return ["halted", `everything is on hold`];
  if (held)               return ["stalled", `${held} on hold, nothing picked up`];
  if (!p.open_n)          return ["finished", "no live tickets"];
  if (quiet !== null && quiet >= 3) return ["idle", `nothing committed for ${quiet} days`];
  return ["idle", "nothing in progress — the queue is waiting for someone to start"];
}

function status(){
  const S = D.status || [];
  const mine = S.flatMap(p => p.dennis.map(s => ({...s, project: p.name})));
  return `<div class="card"><h3>Waiting on you</h3>
    ${mine.length ? `<table>${mine.map(s=>`<tr>
        <td class="mono muted" style="width:90px">${esc(s.project)}</td>
        <td class="mono" style="width:44px">#${s.id}</td>
        <td><b>${esc(s.text)}</b><br><span class="muted">${esc(s.evidence)}</span></td>
        <td><span class="pill ${s.state==="check"?"p-warn":"p-idle"}">${STATE_LABEL[s.state]||s.state}</span></td>
      </tr>`).join("")}</table>`
      : '<p class="empty">Nothing right now. Every ticket is with an agent.</p>'}
    ${S.some(p=>p.later&&p.later.length) ? `<p class="muted" style="margin:10px 0 0">
      Later, when they get there: ${S.flatMap(p=>(p.later||[]).map(s=>`#${s.id}`)).join(", ")}
      — you are the checker, but design has not started them.</p>` : ""}</div>
  ${S.map(p=>{const [state, why] = health(p); return `<div class="card">
    <div class="phhead"><h3 style="margin:0">${esc(p.name)}
      <span class="hs hs-${state.split(" ")[0]}">${esc(state)}</span>
      <span class="muted" style="font-weight:400;text-transform:none;letter-spacing:0">${esc(why)}</span></h3>
      <div class="phnum mono">${p.done_n} done · ${p.open_n} open${p.ladder?` · ladder ${esc(p.ladder)}`:""}</div></div>
    ${frontSentence(p)}
    <table style="margin-top:8px">
      ${p.front?`<tr><td class="muted" style="width:110px">Front line</td><td><b>${esc(p.front)}</b></td></tr>`:""}
      <tr><td class="muted">In progress</td><td>${p.doing.length
        ? p.doing.map(s=>`#${s.id} ${esc(s.text)} <span class="muted">@${esc(s.who)}</span>`).join("<br>")
        : '<span class="muted">nothing</span>'}</td></tr>
      ${p.check.length?`<tr><td class="muted">Waiting on a check</td><td>${
        p.check.map(s=>`#${s.id} ${esc(s.text)} <span class="muted">+${esc(s.checker)}</span>`).join("<br>")}</td></tr>`:""}
      ${p.held.length?`<tr><td class="muted">On hold</td><td>${
        p.held.map(s=>`#${s.id} <span class="muted">${esc(s.blocked)}</span>`).join("<br>")}</td></tr>`:""}
      <tr><td class="muted">Last commit</td><td class="muted">${esc(p.last)} — ${esc(p.last_subject)}</td></tr>
    </table></div>`;}).join("")}
  <p class="muted">Generated ${esc(D.generated)}. Served by <span class="mono">serve.py</span> it is
  rebuilt on every load, so a refresh is the report.</p>`;
}

// The front line in WORDS: the rung the machine is stuck at, what is being worked
// to move it, and what waits on Dennis. All three were already in the digest --
// laid out as a table, which shows the facts without answering "so what do I do".
// Derived on every render, so it cannot go stale the way a hand-kept line would.
function frontSentence(p){
  if(!p.front) return "";
  const cut = t => (t||"").length > 72 ? (t||"").slice(0,72) + "\u2026" : (t||"");
  const bits = ["Stuck at <b>" + esc(p.front) + "</b>."];
  if(p.doing && p.doing.length)
    bits.push("Being worked to move it: " + p.doing.map(s =>
      "#" + s.id + " " + esc(cut(s.text)) + ' <span class="muted">@' + esc(s.who) + "</span>").join(", ") + ".");
  else
    bits.push('<span class="muted">Nothing is being worked to move it.</span>');
  if(p.dennis && p.dennis.length)
    bits.push("<b>Waiting on you:</b> " + p.dennis.map(s =>
      "#" + s.id + " " + esc(cut(s.text))).join(", ") + ".");
  return '<p class="lede">' + bits.join(" ") + "</p>";
}

let mailFolder = "in", mailSel = null;

function ideas(p){
  const wp = (D.projects||[]).find(x=>x.name==="Workshop");
  const iph = wp && (wp.board||[]).find(ph=>/^ideas\b/i.test(ph.phase));
  const list = iph ? iph.features.flatMap(f=>f.stories) : [];
  return `<div class="card"><h3>The ideas box — ${list.length}</h3>
    <p class="lede">Kept, not queued. Nothing is pulled from here; an idea that is going to happen
    moves to a real phase first, where it needs an owner and a closing measurement like any other
    work.</p>
    ${SERVED?`<form class="tform" id="ideaform2">
      <input name="text" placeholder="An idea worth keeping" required>
      <input name="about" placeholder="Why it might matter, in a line (optional)">
      <div class="frow2"><button type="submit">Keep it</button></div>
    </form>`:""}</div>
  <div class="ideagrid">${list.slice().reverse().map(s=>`<div class="ideacard">
    <div class="ihead"><span class="mono">#${s.id}</span>
      <span class="mono">${esc(s.created||s.touched||"")}</span></div>
    <b>${esc(s.text)}</b>
    ${s.evidence?`<span class="iwhy">${esc(s.evidence)}</span>`:""}
    ${(s.notes||[]).length?`<div class="notes">${s.notes.map(n=>
      `<div><span class="mono">@${esc(n.who)}</span> ${esc(n.text)}</div>`).join("")}</div>`:""}
    ${SERVED?`<div class="tags">
      <button class="mini ideaedit" data-line="${esc(s.line)}" data-text="${esc(s.text)}"
        data-ev="${esc(s.evidence||"")}">edit</button>
      <button class="mini ideaadd" data-line="${esc(s.line)}">add</button>
      <button class="mini ideapromote" data-line="${esc(s.line)}" data-text="${esc(s.text)}">make it work</button>
    </div>`:""}</div>`).join("")}</div>
  ${list.length?"":'<div class="card"><p class="empty">Nothing kept yet.</p></div>'}`;
}

function messages(p){
  const M = D.mail || [];
  const roles = ((D.roles&&D.roles.roles)||[]).map(r=>r.id).filter(x=>x!=="dennis");
  const mine = [
    ["in", "Inbox", M.filter(m=>m.folder==="in" && m.to==="dennis")],
    ["out", "Sent", M.filter(m=>m.folder==="out")],
  ];
  const others = roles.map(r=>[r, "@"+r, M.filter(m=>m.folder==="in" && m.seat===r)])
                      .filter(f=>f[2].length);
  const folders = [...mine, ...others];
  const cur_f = folders.find(f=>f[0]===mailFolder) || folders[0];
  const items = cur_f[2];
  if (mailSel === null && items.length) mailSel = 0;
  const open_m = items[mailSel] || null;

  return `<div class="mail">
    <div class="mfolders">
      ${mine.map(([k,label,ms])=>{
        const un = ms.filter(m=>m.unread).length;
        return `<button class="mfolder" data-f="${esc(k)}" aria-current="${k===cur_f[0]}">
          ${esc(label)} <span class="mono">${ms.length}</span>
          ${un?`<span class="unread">${un}</span>`:""}</button>`;}).join("")}
      ${others.length?`<details class="mothers"${others.some(f=>f[0]===cur_f[0])?" open":""}>
        <summary>Other seats <span class="mono">${others.reduce((n,f)=>n+f[2].length,0)}</span></summary>
        ${others.map(([k,label,ms])=>`<button class="mfolder" data-f="${esc(k)}"
            aria-current="${k===cur_f[0]}">${esc(label)} <span class="mono">${ms.length}</span></button>`).join("")}
      </details>`:""}
      ${SERVED?`<button class="compose">Write</button>`:""}
    </div>
    <div class="mlist">
      ${items.length ? items.map((m,i)=>`<button class="mitem${i===mailSel?" on":""}${m.unread?" un":""}" data-i="${i}">
          <b>${esc(m.folder==="out" ? "to @"+m.to : "@"+m.frm)}</b>
          <span class="mono">${esc(m.when.slice(5,16))}</span>
          <span>${esc(m.subject)}</span></button>`).join("")
        : '<p class="empty" style="padding:10px">Nothing here.</p>'}
    </div>
    <div class="mread">
      ${open_m ? `<h3 style="margin:0 0 2px">${esc(open_m.subject)}</h3>
        <p class="path">${open_m.folder==="out" ? "to @"+esc(open_m.to) : "from @"+esc(open_m.frm)}
          · ${esc(open_m.when)}${open_m.unread?' · <span class="tag mdl">unread</span>':""}</p>
        <pre class="brief">${esc(open_m.body)}</pre>
        ${SERVED?`<div class="acts">
          ${open_m.unread && open_m.to==="dennis" ? `<button id="markread">Mark read</button>` : ""}
          <button id="maildel" data-seat="${esc(open_m.seat)}" data-when="${esc(open_m.when)}"
            data-folder="${esc(open_m.folder)}">Delete</button>
        </div>`:""}`
        : '<p class="empty">Nothing selected.</p>'}
    </div>
    ${SERVED?`<form class="tform mcompose" id="msgform" hidden>
      <div class="frow2">
        <select name="to"><option value="ideas">The ideas box</option>
          ${roles.map(x=>`<option value="${esc(x)}">@${esc(x)}</option>`).join("")}</select>
        <button type="submit">Send</button>
        <button type="button" class="ccancel">Cancel</button>
      </div>
      <input name="text" placeholder="What they need to know" required>
      <p class="muted" style="margin:0">It waits until that seat next reads its inbox. The ideas box
      is different: it files the idea straight onto the board.</p>
    </form>`:""}
  </div>`;
}

function usage(){
  const U = D.usage || {}, days = U.days || [], lim = U.limits || {};
  if (!days.length) return `<div class="card"><p class="empty">No local transcripts found.</p></div>`;
  const M = n => (n/1e6).toFixed(n < 1e6 ? 2 : 1) + "M";
  const max = Math.max(...days.map(d=>d.billable), 1);
  const dayPct = lim.daily ? Math.round(100 * U.today / lim.daily) : null;
  const weekPct = lim.weekly ? Math.round(100 * U.week / lim.weekly) : null;
  // how far through the week we are, so pace can be compared with spend
  const dow = (new Date().getDay() + 6) % 7;
  const weekElapsed = Math.round(100 * (dow + 1) / 7);
  return `<div class="card"><h3>What this is</h3>
    <p class="lede">Tokens recorded in this machine's own transcripts under
    <span class="mono">~/.claude/projects/</span> — input plus output, cache reads shown separately.
    <b>It is not Anthropic's limit accounting</b>, which is account-wide and counted differently.
    Read it as what is expensive here, not as how much is left.</p>
    <p class="muted" style="margin:0">Machine: <span class="mono">${esc(U.machine||"?")}</span>.
    Budget in <span class="mono">Workshop/usage_limits.json</span>.</p></div>

  <div class="grid">
    <div class="card"><h3>Today</h3>
      <p class="lede" style="font-size:26px;margin:0">${M(U.today||0)}</p>
      ${dayPct!==null?`${bar2(Math.min(dayPct,100))}
        <p class="muted" style="margin:4px 0 0">${dayPct}% of your ${M(lim.daily)} daily budget</p>`:""}</div>
    <div class="card"><h3>This week — from ${esc(U.week_start||"")}</h3>
      <p class="lede" style="font-size:26px;margin:0">${M(U.week||0)}</p>
      ${weekPct!==null?`${bar2(Math.min(weekPct,100))}
        <p class="muted" style="margin:4px 0 0">${weekPct}% of ${M(lim.weekly)}, and the week is
        ${weekElapsed}% gone —
        <b>${weekPct > weekElapsed + 10 ? "ahead of pace" : weekPct < weekElapsed - 10 ? "behind pace" : "on pace"}</b>.
        ${weekPct > weekElapsed + 10 ? "Cheaper work now — simulation, reading, board tidying — buys back the end of the week." : ""}</p>`:""}</div>
  </div>

  <div class="card"><h3>Last ${days.length} days</h3>
    <table><tr><th>Day</th><th>Billable</th><th></th><th>Cache read</th></tr>
    ${days.slice().reverse().map(d=>`<tr>
      <td class="mono muted" style="width:96px">${esc(d.day)}</td>
      <td class="mono" style="width:70px">${M(d.billable)}</td>
      <td>${bar2(Math.round(100*d.billable/max))}</td>
      <td class="mono muted" style="width:80px">${M(d.cache||0)}</td></tr>`).join("")}</table>
    <p class="muted" style="margin:8px 0 0">Cache reads are the whole conversation being re-sent each
    turn. They dwarf everything else, which is the arithmetic behind one ticket per session.</p></div>

  ${(U.by_project||[]).length?`<div class="card"><h3>Where it went</h3><table>
    ${U.by_project.map(p=>`<tr><td class="mono">${esc(p.project)}</td>
      <td class="mono" style="width:80px">${M(p.tokens)}</td>
      <td>${bar2(Math.round(100*p.tokens/(U.by_project[0].tokens||1)))}</td></tr>`).join("")}
    </table></div>`:""}
  ${(U.by_model||[]).length?`<div class="card"><h3>By model</h3><table>
    ${U.by_model.map(m=>`<tr><td class="mono">${esc(m.model)}</td>
      <td class="mono" style="width:80px">${M(m.tokens)}</td></tr>`).join("")}</table>
    <p class="muted" style="margin:8px 0 0">Mechanical work on a cheaper model is the one lever that
    does not cost quality where it matters — see the model column on the Agents tab.</p></div>`:""}`;
}

function skills(){
  const S = D.skills || [];
  const off = S.filter(s=>!s.installed).length;
  return `<div class="card"><h3>Skills</h3>
    <p class="lede">A brief is read once at the start of a session and gone by the time the decision
    arrives. A skill fires <b>when the work matches</b> — which is the moment the gate is worth
    hearing.</p>
    <p class="muted" style="margin:0">Only each skill's name and description sit in context
    permanently, a line each; the body loads only when it fires. So they cost less than the file they
    save an agent from opening — as long as they <b>point at the canon and never restate it</b>.</p></div>
  ${S.length ? S.map(s=>`<div class="card">
      <div class="phhead"><h3 style="margin:0">${esc(s.name)}
        ${(s.roles||[]).map(x=>`<span class="tag who">@${esc(x)}</span>`).join(" ")}
        <span class="hs ${s.installed?"hs-running":"hs-idle"}">${s.installed?"loaded":"not installed"}</span></h3>
        <div class="phnum mono">${s.words} words</div></div>
      <p class="lede">${esc(s.description)}</p>
      <details><summary>read it</summary><pre class="brief">${esc(s.body)}</pre></details>
      <p class="muted mono" style="margin:8px 0 0">${esc(s.file)}</p></div>`).join("")
    : '<div class="card"><p class="empty">No skills yet.</p></div>'}
  <div class="card"><h3>Installing</h3>
    <p class="lede">Symlinked into <span class="mono">${esc(D.skills_dir||"~/.claude/skills")}</span>,
    not copied — the repo stays the one source and an edit here is live everywhere at once.</p>
    <pre class="cmd">cd ${esc(D.root)}/Workshop && ./install_skills.sh      # Mac, Linux
cd &lt;path&gt;\Workshop; .\install_skills.ps1              # Windows (the build machine)</pre>
    ${off?`<p class="muted" style="margin:0">${off} not installed on this machine. A new session is
    needed before a freshly linked skill is picked up.</p>`
        :'<p class="muted" style="margin:0">All of them are linked on this machine.</p>'}</div>`;
}

function howto(){
  const H = D.howto || [];
  return `<div class="card"><h3>Work instructions</h3>
    <p class="lede">A procedure you follow, not a rule you apply. The rulebook is
    judgement — "a build is the last resort", and you have to think to obey it. These are steps:
    when you see X, do Y.</p>
    <p class="muted" style="margin:0">A finding earns one when it will happen again, the answer is
    mechanical, and getting it wrong costs a build cycle. Otherwise it is a note.
    Source: <span class="mono">Workshop/howto/</span></p></div>
  ${H.filter(h=>!/README/i.test(h.file)).map(h=>`<div class="card">
    <h3>${esc(h.title)}</h3>
    <p class="lede">${esc(h.lead)}</p>
    <details><summary>read it</summary><pre class="brief">${esc(h.body)}</pre></details>
    <p class="muted mono" style="margin:8px 0 0">${esc(h.file)}</p></div>`).join("")
    || '<div class="card"><p class="empty">Nothing yet.</p></div>'}`;
}

function rules(){
  const parts = [...new Set(D.rules.map(r=>r.part))];
  return `<div class="card"><h3>The rulebook</h3>
    <p class="lede">Part I is six rules that always apply. Everything below is the long form,
    grouped by when it bites — look one up, do not read them all.</p>
    <p class="muted" style="margin:0">Source: <span class="mono">Workshop/FPGA_WORKFLOW.md</span></p></div>
    ${parts.map(pt=>`<div class="card"><h3>${esc(pt)}</h3><table>
      ${D.rules.filter(r=>r.part===pt).map(r=>`<tr><td class="mono" style="width:90px">${esc(r.id)}</td>
        <td>${esc(r.text)}</td></tr>`).join("")}</table></div>`).join("")}`;
}

function newproj(){
  const form = SERVED ? `<div class="card"><h3>Start a project</h3>
    <form class="tform" id="npform">
      <label>Name <input name="name" placeholder="MyCoreTN" required
        pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,63}" title="no spaces"></label>
      <label>What it is <input name="subtitle" placeholder="MSX2 on a Tang Nano 20K"></label>
      <div class="frow2">
        <label style="flex:1">Board <input name="board" value="Tang Nano 20K"></label>
        <label style="flex:1">Chip <input name="chip" value="Gowin GW2AR-18C"></label>
      </div>
      <div class="frow2">
        <label class="chk"><input type="checkbox" name="push" checked> create it on GitHub and push</label>
        <label class="chk"><input type="checkbox" name="private"> private repository</label>
        <button type="submit">Create</button>
      </div>
      <p class="muted" style="margin:0">It copies the template, fills the placeholders, writes the
      documents the rules assume exist, installs <span class="mono">check_rules.sh</span> as a
      pre-commit hook, makes the first commit, and creates the repository.</p>
    </form>
    <pre class="cmd" id="nplog" hidden></pre></div>`
  : `<div class="card"><h3>Start a project</h3>
    <p class="lede">This page was opened as a file, so it can only show you the command.
    Run <span class="mono">Workshop/serve.py</span> and this becomes a form.</p>
    <pre class="cmd">cd ${esc(D.root)}/Workshop
./new_project.sh MyCoreTN "MSX2 on a Tang Nano 20K"</pre>
    <p class="muted"><span class="mono">--private</span> for a private repo,
    <span class="mono">--no-push</span> to stop before GitHub.</p></div>`;

  return form + `<div class="card"><h3>What it arrives with</h3><table>
    <tr><td><b>CLAUDE.md</b></td><td class="muted">the reading order — the only file guaranteed to be read at session start</td></tr>
    <tr><td><b>RESUME_HERE.md</b></td><td class="muted">the live state, one page, every claim carrying how it was measured</td></tr>
    <tr><td><b>docs/PLAN.md</b></td><td class="muted">Phase → Feature → Story, pre-filled from the porting playbook's phases</td></tr>
    <tr><td><b>docs/CAPABILITY.md</b></td><td class="muted">the results layer: status, evidence, and which build last proved it</td></tr>
    <tr><td><b>docs/project.json</b></td><td class="muted">identity and the gate — what this page reads</td></tr>
    <tr><td><b>docs/DIAGNOSTICS.md</b>, <b>BUILD_NOTES.md</b>, <b>ARCHITECTURE.md</b></td><td class="muted">the logbooks</td></tr>
    <tr><td><b>rtl/</b></td><td class="muted">clocks with the 270° shifted SDRAM clock, NanoMig's controller, a UART, the memory soak test</td></tr>
    <tr><td><b>pre-commit hook</b></td><td class="muted">check_rules.sh — the mechanical half, wired in automatically</td></tr>
  </table>
  <p class="muted" style="margin:10px 0 0">The rulebook is <b>not</b> copied in. New projects link to
  Workshop, because copies drift — this workshop already made that mistake once.</p></div>
  <div class="card"><h3>Then</h3>
  <p class="lede">Work down <span class="mono">CHECKLIST.md</span>. It has gates in it — points where
  the honest answer may be "this needs a bigger board" or "settle the licence first".</p></div>`;
}

/* ---------------- draw ---------------- */
function draw(){
  const isW = !PTABS.includes(curTab);
  document.querySelectorAll("#plist button").forEach(b =>
    b.setAttribute("aria-current", (!isW && b.dataset.p === cur.name) ? "true" : "false"));
  document.querySelectorAll("#wlist button").forEach(b =>
    b.setAttribute("aria-current", (isW && b.dataset.w === curTab) ? "true" : "false"));

  const tabs = document.getElementById("tabs"); tabs.innerHTML = "";
  const unread = ((D.inbox||{})["dennis"]||{}).n || 0;
  if (!isW) PTABS.forEach(t => {
    const b = $(`<button>${t}${t === "Messages" && unread
      ? ` <span class="unread">${unread}</span>` : ""}</button>`).firstChild;
    b.setAttribute("aria-current", t === curTab ? "true" : "false");
    b.onclick = () => { curTab = t; draw(); };
    tabs.appendChild(b);
  });

  const waiting = (D.status||[]).reduce((n,p)=>n+p.dennis.length,0);
  const hdr = document.getElementById("title");
  hdr.textContent = isW ? curTab : cur.name;
  document.querySelectorAll(".head .hs").forEach(e => e.remove());
  if (!isW) {
    const d = (D.status||[]).find(x=>x.name===cur.name);
    if (d) { const [state, why] = health(d);
      const b = document.createElement("span");
      b.className = "hs hs-" + state.split(" ")[0];
      b.textContent = state + " · " + why;
      b.title = d.front ? "front line: " + d.front : "";
      hdr.after(b); }
  }
  let badge = document.getElementById("waitbadge");
  if (!badge) { badge = document.createElement("button"); badge.id = "waitbadge";
    hdr.after(badge); badge.onclick = () => { curTab = "Status"; draw(); }; }
  badge.textContent = waiting ? `${waiting} waiting on you` : "nothing waiting on you";
  badge.className = waiting ? "wait on" : "wait";
  document.getElementById("sub").textContent = isW
    ? ({Status:"Where everything stands, right now",
        Rules:"Shared across every project in this workshop",
        Skills:"What loads itself when the work matches",
        Usage:"Token volume on this machine",
        Agents:"Who does what, and on which model",
        "How to":"Procedures, not judgement",
        "New project":"Scaffold a new core port"}[curTab] || "")
    : (cur.subtitle || "");
  const v = document.getElementById("view"); v.scrollTop = 0;
  v.innerHTML = isW ? ({Status:status, Usage:usage, Rules:rules, Agents:agents, Skills:skills, "How to":howto, "New project":newproj}[curTab])()
    : ({Overview:overview, Board:board, Progress:progress, Builds:builds, Rules:projrules,
        Messages:messages, Ideas:ideas, Log:log}[curTab])(cur);

  v.querySelectorAll(".addbtn").forEach(b => b.onclick = () => {
    const f = v.querySelector(`form.tform[data-phase="${CSS.escape(b.dataset.phase)}"]`);
    f.hidden = !f.hidden; if (!f.hidden) f.querySelector("[name=text]").focus();
  });
  // only the add-a-ticket forms; the idea, message and new-project forms are also
  // .tform and have no feature dropdown
  v.querySelectorAll("form.tform[data-phase]").forEach(f => {
    const sel = f.querySelector("[name=feature]"), nf = f.querySelector("[name=newfeature]");
    if (!sel || !nf) return;
    sel.onchange = () => { nf.hidden = sel.value !== "__new"; if (!nf.hidden) nf.focus(); };
    f.querySelector(".cancel").onclick = () => { f.hidden = true; };
    f.onsubmit = e => {
      e.preventDefault();
      const isNew = sel.value === "__new";
      api("/api/add", {project: cur.name, phase: f.dataset.phase,
        feature: isNew ? nf.value.trim() : sel.value, new_feature: isNew,
        text: f.text.value, evidence: f.evidence.value, prio: f.prio.value,
        who: f.who.value, model: f.model.value, checker: f.checker.value});
    };
  });
  v.querySelectorAll(".story[data-story]").forEach(el => el.addEventListener("click", e => {
    if (e.target.closest("button,select,input,a")) return;
    openSheet(cur.name, JSON.parse(el.dataset.story), el.dataset.line);
  }));
  v.querySelectorAll(".story .priosel").forEach(sel => {
    sel.onmousedown = e => e.stopPropagation();          // do not start a drag
    sel.onchange = () => api("/api/edit",
      {project: cur.name, line: sel.closest(".story").dataset.line, prio: sel.value});
  });
  v.querySelectorAll(".story .note").forEach(b => b.onclick = () => {
    const el = b.closest(".story");
    const txt = prompt("A line saying what happened, and where the detail is —\ne.g. \"round 4 built, 44.138 MHz -> docs/BUILD_NOTES.md\"");
    if (txt && txt.trim()) api("/api/note",
      {project: cur.name, line: el.dataset.line, text: txt.trim(), who: el.dataset.who || "design"});
  });
  v.querySelectorAll(".story .block").forEach(b => b.onclick = () => {
    const el = b.closest(".story"), was = el.querySelector(".blockline");
    if (was) { api("/api/edit", {project: cur.name, line: el.dataset.line, blocked: ""}); return; }
    const why = prompt("On hold — what is it waiting on?");
    if (why && why.trim()) api("/api/edit", {project: cur.name, line: el.dataset.line, blocked: why.trim()});
  });
  v.querySelectorAll(".story .edit").forEach(b => b.onclick = () => {
    const el = b.closest(".story"), line = el.dataset.line;
    const text = prompt("Story", el.querySelector("b").textContent.trim());
    if (text === null) return;
    if (!text.trim()) { if (confirm("Empty text deletes this ticket. Delete it?"))
        api("/api/delete", {project: cur.name, line}); return; }
    const ev = prompt("Evidence — what closes it", el.dataset.ev || "");
    if (ev === null) return;
    api("/api/edit", {project: cur.name, line, text, evidence: ev});
  });

  let dragged = null;
  v.querySelectorAll(".story[draggable]").forEach(el => {
    el.addEventListener("dragstart", e => {
      if (e.target.closest("select,button,input")) { e.preventDefault(); return; }
      dragged = el; el.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", el.dataset.line);
    });
    el.addEventListener("dragend", () => { el.classList.remove("dragging"); dragged = null; });
  });
  v.querySelectorAll(".drop").forEach(z => {
    z.addEventListener("dragover", e => { e.preventDefault(); z.classList.add("over"); });
    z.addEventListener("dragleave", () => z.classList.remove("over"));
    z.addEventListener("drop", async e => {
      e.preventDefault(); z.classList.remove("over");
      if (!dragged) return;
      const to = z.dataset.to, line = dragged.dataset.line;
      if (to === dragged.dataset.state) return;
      if (!SERVED) { alert("Read-only: this page was opened as a file.\n\nRun Workshop/serve.py to move tickets."); return; }
      if (to === "wip" && dragged.querySelector(".blockline")) {
        alert("That story is on hold. Clear the hold first — the button is on the card.");
        return;
      }
      const feat = dragged.dataset.feat, featOK = dragged.dataset.featok === "1";
      if ((to === "wip") && !featOK) {
        alert(`"${feat}" is not refined yet.\n\nWrite its stories first, then mark the feature refined. ` +
              `Only refined features are pulled -- a half-written feature looks ready story by story and is not.`);
        return;
      }
      let evidence = dragged.dataset.ev || "";
      if ((to === "open" || to === "wip") && !(evidence && dragged.dataset.who)) {
        alert("That story is not refined: it needs an owner and the evidence that closes it.\n\nUse edit, or drag it back to Backlog.");
        return;
      }
      if (to === "done" && dragged.dataset.checker && dragged.dataset.state !== "check") {
        alert(`+${dragged.dataset.checker} has to check this one first. Move it to Check.`);
        return;
      }
      if (to === "done" && dragged.dataset.checker &&
          !confirm(`Has @${dragged.dataset.checker} actually checked this?`)) return;
      if (to === "done") {
        evidence = prompt("A story closes on evidence. What measurement closes this one?", evidence || "");
        if (!evidence) return;
      }
      const r = await fetch("/api/move", {method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({project: z.dataset.project, line, to, evidence})});
      if (r.ok) location.reload();
      else alert("Could not move it: " + (await r.text()));
    });
  });
  const idf = v.querySelector("#ideaform");
  if (idf) idf.onsubmit = e => { e.preventDefault();
    api("/api/add", {project: cur.name, phase: "Ideas", feature: "Ideas", new_feature: true,
      text: idf.text.value, evidence: idf.about.value, prio: 1}); };
  v.querySelectorAll(".mfolder").forEach(b => b.onclick = () => {
    mailFolder = b.dataset.f; mailSel = null; draw(); });
  v.querySelectorAll(".mitem").forEach(b => b.onclick = () => {
    mailSel = +b.dataset.i; draw(); });
  const md = v.querySelector("#maildel");
  if (md) md.onclick = () => { mailSel = null;
    api("/api/mail_delete", {seat: md.dataset.seat, when: md.dataset.when, folder: md.dataset.folder}); };
  const cw = v.querySelector(".compose"), cf = v.querySelector("#msgform");
  if (cw && cf) { cw.onclick = () => { cf.hidden = !cf.hidden; if (!cf.hidden) cf.text.focus(); };
    const cc = cf.querySelector(".ccancel"); if (cc) cc.onclick = () => { cf.hidden = true; }; }
  const if2 = v.querySelector("#ideaform2");
  if (if2) if2.onsubmit = e => { e.preventDefault();
    api("/api/msg", {to: "ideas", text: if2.text.value + (if2.about.value ? "\n" + if2.about.value : "")}); };
  v.querySelectorAll(".ideaedit").forEach(b => b.onclick = () => {
    const text = prompt("The idea", b.dataset.text); if (text === null) return;
    const ev = prompt("Why it might matter", b.dataset.ev || ""); if (ev === null) return;
    api("/api/edit", {project: "Workshop", line: b.dataset.line, text, evidence: ev});
  });
  v.querySelectorAll(".ideaadd").forEach(b => b.onclick = () => {
    const txt = prompt("Something to add — it goes underneath as a dated note");
    if (txt && txt.trim()) api("/api/note",
      {project: "Workshop", line: b.dataset.line, text: txt.trim(), who: "dennis"});
  });
  v.querySelectorAll(".ideapromote").forEach(b => b.onclick = () => {
    const ph = prompt("Move it to which phase? It needs an owner and a closing measurement there.",
                      "Phase W");
    if (ph && ph.trim()) api("/api/move_phase",
      {project: "Workshop", line: b.dataset.line, phase: ph.trim()});
  });
  const mf = v.querySelector("#msgform");
  if (mf) mf.onsubmit = async e => { e.preventDefault();
    const to = mf.to.value, btn = mf.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "sending…";
    const ok = await api("/api/msg", {to, text: mf.text.value});
    if (!ok) { btn.disabled = false; btn.textContent = "Send"; }
  };
  const mr = v.querySelector("#markread");
  if (mr) mr.onclick = () => api("/api/inbox_read", {who: "dennis"});
  const np = v.querySelector("#npform");
  if (np) np.onsubmit = async e => {
    e.preventDefault();
    const log = v.querySelector("#nplog");
    const btn = np.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "creating…";
    log.hidden = false; log.textContent = "working…";
    const r = await fetch("/api/new", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({name: np.name.value.trim(), subtitle: np.subtitle.value.trim(),
        board: np.board.value.trim(), chip: np.chip.value.trim(),
        push: np.push.checked, private: np.private.checked})});
    const txt = await r.text();
    if (r.ok) { log.textContent = JSON.parse(txt).log + "\n\nreloading…"; setTimeout(()=>location.reload(), 1500); }
    else { log.textContent = txt; btn.disabled = false; btn.textContent = "Create"; }
  };
  v.querySelectorAll(".copyresume").forEach(b => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.t); b.textContent = "copied"; }
    catch { alert(b.dataset.t); }
    setTimeout(()=>b.textContent="copy", 1400);
  });
  v.querySelectorAll(".msgbtn").forEach(b => b.onclick = () => {
    const txt = prompt(`Message for @${b.dataset.to} — it waits in their inbox until that seat next reads it`);
    if (txt && txt.trim()) api("/api/msg", {to: b.dataset.to, text: txt.trim()});
  });
  v.querySelectorAll(".mdlsel").forEach(s => s.onchange = () => {
    MODEL_OVERRIDE[s.dataset.role] = s.value; saveModels(MODEL_OVERRIDE); draw();
  });
  v.querySelectorAll("tr.ladrow").forEach(tr => tr.onclick = () =>
    openSheet(cur.name, JSON.parse(tr.dataset.story), tr.dataset.line));
  v.querySelectorAll(".filters button[data-f]").forEach(b =>
    b.onclick = () => { boardFilter = b.dataset.f; draw(); });
  const ps = v.querySelector("#phasesel");
  if (ps) ps.onchange = () => { boardPhase = ps.value; boardFeature = ""; draw(); };
  const qb = v.querySelector("#qbox");
  if (qb) {
    qb.oninput = () => { boardQ = qb.value; draw();
      const n = document.getElementById("qbox"); if (n) { n.focus();
        n.setSelectionRange(n.value.length, n.value.length); } };
  }
  const vs = v.querySelector("#viewsel");
  if (vs) vs.onchange = () => { boardView = vs.value; boardFeature = ""; draw(); };
  v.querySelectorAll(".backbtn").forEach(b =>
    b.onclick = () => { boardFeature = ""; boardView = "features"; draw(); });
  v.querySelectorAll(".reffeat").forEach(b => b.onclick = e => {
    e.stopPropagation();
    api("/api/feature", {project: cur.name, feature: b.dataset.f, refined: b.dataset.to === "1"});
  });
  v.querySelectorAll(".feat-link").forEach(el =>
    el.onclick = () => { boardFeature = (boardFeature === el.dataset.f) ? "" : el.dataset.f;
                         boardView = "stories"; draw(); });
  v.querySelectorAll(".copy").forEach(b => b.onclick = async () => {
    try { await navigator.clipboard.writeText(b.dataset.brief); b.textContent = "copied"; }
    catch { b.textContent = "select & copy below"; alert(b.dataset.brief); }
    setTimeout(() => b.textContent = "copy brief", 1400);
  });
}
draw();
</script></body></html>
"""
sys.stdout.write(HTML.replace("__DATA__", blob.replace("</", "<\\/")))
