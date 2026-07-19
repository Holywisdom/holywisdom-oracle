#!/usr/bin/env python3
"""Read-only web dashboard for tmux sessions on arduin.

Renders live `tmux capture-pane` snapshots of every session. Purely read-only:
the server never accepts terminal input and never passes request data to a
shell — the only tmux commands it runs use fixed, validated arguments.

Usage:
    tmux-dashboard.py [--host HOST] [--port PORT]

Defaults: host = the Tailscale IP that owns 100.97.x (private to the tailnet),
port = 7681. Bind to 127.0.0.1 for localhost-only.
"""
import argparse
import html
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


def tmux(*args):
    """Run tmux with fixed argument list (no shell). Returns stdout or ''."""
    try:
        return subprocess.run(
            ["tmux", *args], capture_output=True, text=True, timeout=5
        ).stdout
    except Exception:
        return ""


def list_sessions():
    out = tmux("list-sessions", "-F",
               "#{session_name}\t#{session_windows}\t#{?session_attached,attached,detached}")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if parts and parts[0]:
            rows.append({
                "name": parts[0],
                "windows": parts[1] if len(parts) > 1 else "?",
                "state": parts[2] if len(parts) > 2 else "",
            })
    return rows


def capture(session):
    # Validate against the live session list — never trust the query param.
    valid = {s["name"] for s in list_sessions()}
    if session not in valid:
        return None
    return tmux("capture-pane", "-p", "-t", session)


PAGE = """<!doctype html>
<meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>tmux dashboard · arduin</title>
<style>
  :root{color-scheme:dark}
  body{margin:0;background:#0b0e14;color:#c9d1d9;font:14px/1.5 -apple-system,Segoe UI,sans-serif}
  header{padding:12px 18px;border-bottom:1px solid #1f2430;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  header b{color:#7ee787}
  .muted{color:#6e7681;font-size:12px}
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:14px;padding:14px}
  .card{background:#0d1117;border:1px solid #1f2430;border-radius:10px;overflow:hidden}
  .card h2{margin:0;padding:8px 12px;font-size:13px;background:#11151f;border-bottom:1px solid #1f2430;display:flex;justify-content:space-between}
  .tag{color:#6e7681;font-weight:normal}
  pre{margin:0;padding:10px 12px;overflow:auto;max-height:60vh;white-space:pre;
      font:12px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;color:#adbac7}
  .empty{padding:24px;color:#6e7681;text-align:center}
</style>
<header>
  <b>🖥️ tmux dashboard</b><span class=muted>arduin · read-only · refresh 2s</span>
  <span class=muted id=clock></span>
</header>
<main id=grid><div class=empty>loading…</div></main>
<script>
async function tick(){
  try{
    const sessions = await (await fetch('sessions')).json();
    const grid = document.getElementById('grid');
    if(!sessions.length){ grid.innerHTML='<div class=empty>no tmux sessions</div>'; return; }
    // build cards once, then just update <pre> text
    for(const s of sessions){
      let card = document.getElementById('card-'+s.name);
      if(!card){
        card = document.createElement('div'); card.className='card'; card.id='card-'+s.name;
        card.innerHTML = '<h2><span>'+escapeHtml(s.name)+'</span><span class=tag>'+
          escapeHtml(s.windows)+'w · '+escapeHtml(s.state)+'</span></h2><pre></pre>';
        grid.appendChild(card);
        if(grid.querySelector('.empty')) grid.querySelector('.empty').remove();
      }
      const pane = await (await fetch('pane?s='+encodeURIComponent(s.name))).text();
      const pre = card.querySelector('pre');
      const atBottom = pre.scrollTop+pre.clientHeight >= pre.scrollHeight-4;
      pre.textContent = pane;
      if(atBottom) pre.scrollTop = pre.scrollHeight;
    }
    // remove cards for sessions that disappeared
    for(const card of [...grid.querySelectorAll('.card')]){
      if(!sessions.find(s=>'card-'+s.name===card.id)) card.remove();
    }
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
  }catch(e){ /* keep trying */ }
}
function escapeHtml(x){return (''+x).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));}
tick(); setInterval(tick, 2000);
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/sessions":
            self._send(200, json.dumps(list_sessions()), "application/json")
        elif path == "/pane":
            qs = parse_qs(urlparse(self.path).query)
            name = (qs.get("s") or [""])[0]
            pane = capture(name)
            if pane is None:
                self._send(404, "no such session", "text/plain")
            else:
                self._send(200, pane, "text/plain; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *a):  # quiet
        pass


def default_host():
    """Tailscale IP if we can find one, else localhost."""
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                             text=True, timeout=3).stdout.strip().splitlines()
        if out:
            return out[0].strip()
    except Exception:
        pass
    return "127.0.0.1"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=default_host())
    ap.add_argument("--port", type=int, default=7681)
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"🖥️  tmux dashboard (read-only) on http://{a.host}:{a.port}")
    srv.serve_forever()
