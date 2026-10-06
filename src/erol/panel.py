"""Loopback-only read-only evidence panel with no remote assets or task mutation."""
# ruff: noqa: E501 -- embedded self-contained HTML/CSS/JS assets

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .benchmark import metrics
from .chat import Sessions
from .common import ErolError, canonical
from .runstore import RunStore
from .work import WorkStore

HTML = """<!doctype html><html lang="tr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>EROL · İş ve kanıt</title>
<style>
:root{font-family:system-ui,sans-serif;color:#16313c;background:#f3f6f5}*{box-sizing:border-box}
body{margin:0}header{background:#123640;color:#fff;padding:30px max(24px,calc((100vw - 1160px)/2));display:flex;justify-content:space-between;align-items:center}
h1{font-size:24px;margin:0}header p{color:#9fcbc6;font-size:13px;margin:8px 0 0}main{max-width:1208px;margin:auto;padding:28px 24px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:0 0 28px}.stat,article{background:#fff;border:1px solid #dce5e1;border-radius:12px;padding:22px}
.stat strong{display:block;font-size:30px;margin-top:8px}.label{color:#648078;font-size:13px}nav{display:flex;gap:12px;align-items:center;margin-bottom:18px;flex-wrap:wrap}
input,select,button{font:inherit;border:1px solid #cddcd6;border-radius:7px;background:white;padding:10px 14px}input{flex:1;min-width:180px}button{cursor:pointer}button.active{background:#147467;color:white;border-color:#147467}
article{margin-bottom:12px;padding:18px 22px}article button{padding:0;border:0;text-align:left;color:#16313c;width:100%;display:flex;justify-content:space-between;gap:20px}code{font-family:monospace;font-size:13px;overflow-wrap:anywhere}.badge{border-radius:16px;background:#edf3f0;font-size:12px;padding:5px 10px}.completed{background:#d8eee6;color:#176447}.needs_attention{background:#fff0d5;color:#865b17}.running{background:#ddecf6;color:#275c81}.detail{border-top:1px solid #e5ebe8;margin-top:16px;padding-top:16px}.detail p{line-height:1.6;font-size:13px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:9px;text-align:left;border-bottom:1px solid #edf1ef}.empty{text-align:center;padding:48px;color:#688078}.note{font-size:12px;color:#6b827a;margin-top:24px}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}header{padding:24px}main{padding:20px 16px}.stat{padding:16px}}
</style><header><div><h1>EROL</h1><p>İşler, yürütme ve doğrulama kanıtları</p></div><span id="connection">Bağlanıyor…</span></header>
<main><div class="stats" id="stats"></div><nav><button id="runs" class="active">Yürütmeler</button><button id="chats">Terminal görevleri</button><button id="jobs">Kuyruk</button><button id="benchmarks">Ölçümler</button><input id="query" placeholder="Kimlik veya aşama ara" aria-label="Ara"><select id="status" aria-label="Durum"><option value="">Tüm durumlar</option>completed</option><option>running</option><option>queued</option><option>needs_attention</option><option>cancelled</option></select></nav><div id="items"></div><p class="note">Salt okunur yerel panel · Süreç çıkışları yerel kanıttır. Kaynak erişimi iddianın doğruluğunu onaylamaz. Worktree bir işletim sistemi sandbox’ı değildir.</p></main>
<script src="/panel.js"></script></html>"""

JS = """const credential=new URLSearchParams(location.hash.slice(1)).get('token')||'';
history.replaceState(null,'',location.pathname);
let state={runs:[],chats:[],jobs:[],benchmarks:[]},view='runs',expanded=new Set();
const $=id=>document.getElementById(id),el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
function render(){const counts=[['Yürütme',state.runs.length],['Tamamlanan',state.runs.filter(r=>r.status==='completed').length],['İlgi bekleyen',state.runs.filter(r=>r.status==='needs_attention').length],['Kuyruk',state.jobs.filter(j=>j.status==='queued').length]];
$('stats').replaceChildren(...counts.map(([label,n])=>{let d=el('div');d.className='stat';let l=el('span',label);l.className='label';d.append(l,el('strong',n));return d}));
let rows=state[view].filter(r=>(!$('status').value||r.status===$('status').value)&&JSON.stringify([r.id,r.task_id,r.phase,r.status]).toLowerCase().includes($('query').value.toLowerCase()));
$('items').replaceChildren(...rows.slice().reverse().map(r=>{let a=el('article'),b=el('button'),badge=el('span',r.status);badge.className='badge '+r.status;b.append(el('code',r.id),badge);b.onclick=()=>{expanded.has(r.id)?expanded.delete(r.id):expanded.add(r.id);render()};a.append(b,el('p',(r.phase||'')+' · '+(r.harness||r.rule?.harness||'')+' · '+(r.created||'')));
if(expanded.has(r.id)){let d=el('div');d.className='detail';for(const key of ['worktree','tested_digest','reviewed_digest','reason','run_id','duration_seconds','attempts','cost_usd','pairs','report','artifact_directory','next_step'])if(r[key]!==undefined&&r[key]!==null)d.append(el('p',key+': '+r[key]));for(const key of ['routing','selected_skills','phase_timings','model_turns','verification','selection'])if(r[key])d.append(el('p',key+': '+JSON.stringify(r[key])));if(r.usage)d.append(el('p','CLI kullanımı: '+JSON.stringify(r.usage)));if(r.review_summary)d.append(el('p',r.review_summary));let t=el('table'),head=el('tr');['Kontrol / kaynak','Sonuç','Kanıt'].forEach(s=>head.append(el('th',s)));t.append(head);for(const c of r.checks||[]){let tr=el('tr');[c.name,c.passed?'Geçti':'Başarısız',c.evidence_type].forEach(s=>tr.append(el('td',s)));t.append(tr)}for(const c of r.source_access_receipts||[]){let tr=el('tr');[c.source_id,c.status,c.evidence_type].forEach(s=>tr.append(el('td',s)));t.append(tr)}d.append(t);for(const f of r.findings||[])d.append(el('p',f.severity+': '+f.message));a.append(d)}return a}));if(!rows.length){let e=el('div','Bu filtrede kayıt yok.');e.className='empty';$('items').append(e)}}
['runs','chats','jobs','benchmarks'].forEach(id=>$(id).onclick=()=>{view=id;['runs','chats','jobs','benchmarks'].forEach(k=>$(k).classList.toggle('active',k===view));render()});$('query').oninput=render;$('status').onchange=render;
async function refresh(){try{let r=await fetch('/api/state',{cache:'no-store',headers:{Authorization:'Bearer '+credential}});if(!r.ok)throw Error();state=await r.json();$('connection').textContent='● Yerel bağlantı';render()}catch{$('connection').textContent='Bağlantı bekleniyor'}}refresh();setInterval(refresh,3000);
"""


def panel_state(directory: Path, project_id: str) -> dict:
    with RunStore(directory, project_id) as runs, WorkStore(directory, project_id) as work:
        records = []
        for run in runs.list()[-200:]:
            item = {
                key: run.get(key)
                for key in (
                    "id",
                    "task_id",
                    "status",
                    "phase",
                    "harness",
                    "created",
                    "worktree",
                    "tested_digest",
                    "reviewed_digest",
                    "reason",
                    "phase_timings",
                    "artifact_directory",
                )
            }
            try:
                end = (
                    datetime.fromisoformat(run["completed"])
                    if run.get("completed")
                    else datetime.now(UTC)
                )
                duration = (end - datetime.fromisoformat(run["created"])).total_seconds()
            except (ValueError, TypeError):
                duration = 0
            measured = metrics(run, round(max(0, duration), 3))
            item.update(
                {
                    key: measured[key]
                    for key in ("duration_seconds", "attempts", "usage", "cost_usd")
                }
            )
            item["checks"] = [
                {key: check.get(key) for key in ("name", "passed", "evidence_type")}
                for check in run["checks"]
            ]
            item["source_access_receipts"] = [
                {key: receipt.get(key) for key in ("source_id", "status", "evidence_type")}
                for receipt in run.get("source_access_receipts", [])
            ]
            review = (run.get("review") or {}).get("result") or {}
            item.update(
                {"review_summary": review.get("summary"), "findings": review.get("findings", [])}
            )
            records.append(item)
        chats = []
        sessions = Sessions(directory, project_id)
        for entry in sessions.list():
            record = sessions.load(entry["id"])
            item = {
                key: record.get(key)
                for key in (
                    "id",
                    "task_id",
                    "status",
                    "updated",
                    "selected_skills",
                    "phase_timings",
                    "artifact_directory",
                    "model_turns",
                    "verification",
                    "selection",
                    "error",
                )
            }
            item["created"] = record.get("updated")
            item["duration_seconds"] = record.get("elapsed_seconds")
            item["phase"] = "terminal"
            item["checks"] = [
                {key: check.get(key) for key in ("name", "passed", "evidence_type")}
                for check in record.get("checks", [])
            ]
            diagnostics = record.get("routing_diagnostics", {})
            item["routing"] = {
                key: diagnostics.get(key)
                for key in ("mode", "context_inherited", "unmatched", "ambiguity")
            }
            item["reason"] = record.get("error") or record.get("verification", {}).get(
                "missing_checks_reason"
            )
            item["next_step"] = (
                "None"
                if record.get("status") == "completed"
                else "Inspect verification and configured checks; /tests /usage"
            )
            chats.append(item)
        jobs = [
            {key: item.get(key) for key in ("id", "task_id", "status", "run_id", "created")}
            for item in work.list("jobs")[-200:]
        ]
        benchmarks = [
            {**item, "status": "completed" if item["passed"] else "needs_attention"}
            for item in work.list("benchmarks")[-100:]
        ]
    return {
        "project_id": project_id,
        "runs": records,
        "jobs": jobs,
        "chats": chats,
        "benchmarks": benchmarks,
        "read_only": True,
    }


class PanelServer(HTTPServer):
    def __init__(self, address, handler):
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, handler)

    @property
    def access_url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/#token={self.token}"


def make_server(directory: Path, project_id: str, port: int = 8765) -> PanelServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise ErolError("Invalid panel port")

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *_):
            pass

        def discard_body(self) -> bool:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 4096 or self.headers.get("Transfer-Encoding"):
                    return False
                # Drain a bounded body before closing: unread input causes Windows TCP resets.
                return len(self.rfile.read(size)) == size
            except (ValueError, OSError):
                return False

        def reply(self, status, body: bytes, mime="text/plain; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.discard_body():
                self.reply(413, b"Request body rejected")
                return
            address = self.server.server_address
            assert isinstance(address, tuple)
            expected = {
                f"127.0.0.1:{address[1]}",
                f"localhost:{address[1]}",
            }
            if self.headers.get("Host") not in expected:
                self.reply(403, b"Loopback host required")
            elif self.headers.get("Origin") is not None and self.headers.get("Origin") not in {
                f"http://{host}" for host in expected
            }:
                self.reply(403, b"Same origin required")
            elif self.path == "/":
                self.reply(200, HTML.encode(), "text/html; charset=utf-8")
            elif self.path == "/panel.js":
                self.reply(200, JS.encode(), "text/javascript; charset=utf-8")
            elif self.path == "/api/state":
                assert isinstance(self.server, PanelServer)
                authorization = self.headers.get("Authorization", "")
                if not secrets.compare_digest(
                    authorization.encode("utf-8"), ("Bearer " + self.server.token).encode()
                ):
                    self.reply(401, b"Panel session authorization required")
                    return
                try:
                    body = canonical(panel_state(directory, project_id)).encode()
                    if len(body) > 1048576:
                        raise ErolError("Panel response exceeds budget")
                    self.reply(200, body, "application/json")
                except (ErolError, OSError, json.JSONDecodeError):
                    self.reply(503, b"Evidence unavailable")
            else:
                self.reply(404, b"Not found")

        def do_POST(self):
            if self.discard_body():
                self.reply(405, b"Read-only panel")
            else:
                self.reply(413, b"Request body rejected")

    return PanelServer(("127.0.0.1", port), Handler)
