# -*- coding: utf-8 -*-
"""Rnai Web UI — เซิร์ฟเวอร์ localhost (stdlib ล้วน ไม่ต้องลง dependency เพิ่ม)
เปิดด้วย: rnai ui  →  http://localhost:8765
"""
from __future__ import annotations
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, history
from .providers import get_provider

PORT = 8765

HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>Rnai — Cowork</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --teal:#0B3945; --orange:#D77757; --bg:#F5F7F8; --card:#fff; --line:#E2E9EB; }
* { box-sizing:border-box; margin:0; }
body { font:15px/1.6 -apple-system,'Sarabun',sans-serif; background:var(--bg); color:#1c2b30; display:flex; height:100vh; }
/* ── Sidebar ── */
#side { width:280px; background:var(--teal); color:#dfe9ec; display:flex; flex-direction:column; }
#side h1 { font-size:18px; padding:18px 16px 8px; color:#fff; }
#side h1 span { color:var(--orange); }
#newBtn { margin:8px 16px; padding:10px; border:0; border-radius:10px; background:var(--orange); color:#fff; font-size:14px; font-weight:600; cursor:pointer; }
#recents { flex:1; overflow-y:auto; padding:8px; }
.recent { padding:10px 12px; border-radius:10px; cursor:pointer; font-size:13.5px; margin-bottom:2px;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.recent:hover { background:rgba(255,255,255,.08); }
.recent.active { background:rgba(255,255,255,.16); color:#fff; }
.recent small { display:block; color:#9db6bd; font-size:11px; }
/* ── Main ── */
#main { flex:1; display:flex; flex-direction:column; }
#head { padding:12px 20px; background:var(--card); border-bottom:1px solid var(--line);
        display:flex; align-items:center; gap:12px; }
#head b { font-size:15px; flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
select { padding:7px 10px; border:1px solid var(--line); border-radius:8px; font-size:13px; background:#fff; }
#chat { flex:1; overflow-y:auto; padding:24px 8%; }
.msg { max-width:78%; padding:12px 16px; border-radius:16px; margin-bottom:14px; white-space:pre-wrap; word-break:break-word; }
.user { background:var(--teal); color:#fff; margin-left:auto; border-bottom-right-radius:4px; }
.bot  { background:var(--card); border:1px solid var(--line); border-bottom-left-radius:4px; }
.bot .meta { color:#8aa0a7; font-size:11px; margin-top:6px; }
#empty { text-align:center; color:#8aa0a7; margin-top:18vh; }
#empty .logo { font-size:42px; }
/* ── Composer ── */
#composer { padding:14px 8% 22px; background:linear-gradient(transparent, var(--bg) 30%); }
#box { display:flex; gap:10px; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:10px; }
#input { flex:1; border:0; outline:0; resize:none; font:inherit; max-height:140px; background:transparent; }
#send { border:0; background:var(--orange); color:#fff; border-radius:10px; padding:8px 18px; font-size:14px; font-weight:600; cursor:pointer; }
#send:disabled { opacity:.5; }
.typing { color:#8aa0a7; font-style:italic; }
</style>
</head>
<body>
<div id="side">
  <h1>Rnai <span>Cowork</span></h1>
  <button id="newBtn" onclick="newChat()">＋ สนทนาใหม่</button>
  <div id="recents"></div>
</div>
<div id="main">
  <div id="head">
    <b id="title">สนทนาใหม่</b>
    <label style="font-size:12px;color:#8aa0a7">โมเดล</label>
    <select id="model">
      <option value="rnai">rnai-llm (v3.2)</option>
      <option value="gemini">Gemini</option>
      <option value="groq">Groq</option>
      <option value="openrouter">OpenRouter</option>
    </select>
  </div>
  <div id="chat"><div id="empty"><div class="logo">🤖</div>สวัสดีครับ ผม Rnai<br>พิมพ์ข้อความด้านล่างเพื่อเริ่มคุยได้เลย</div></div>
  <div id="composer">
    <div id="box">
      <textarea id="input" rows="1" placeholder="พิมพ์ข้อความ... (Enter ส่ง / Shift+Enter ขึ้นบรรทัด)"></textarea>
      <button id="send" onclick="send()">ส่ง</button>
    </div>
  </div>
</div>
<script>
let sid = null;
const $ = id => document.getElementById(id);

async function loadRecents() {
  const r = await fetch('/api/sessions'); const list = await r.json();
  $('recents').innerHTML = list.map(s =>
    `<div class="recent ${s.id===sid?'active':''}" onclick="openSession('${s.id}')">${esc(s.title)}
     <small>${s.count} ข้อความ · ${s.model} · ${ago(s.updated)}</small></div>`).join('');
}
async function openSession(id) {
  sid = id;
  const r = await fetch('/api/sessions/' + id); const d = await r.json();
  $('title').textContent = d.title;
  $('chat').innerHTML = '';
  d.messages.forEach(m => addMsg(m.role, m.content, m.model));
  loadRecents(); scrollBottom();
}
function newChat() {
  sid = null; $('title').textContent = 'สนทนาใหม่';
  $('chat').innerHTML = '<div id="empty"><div class="logo">🤖</div>เริ่มสนทนาใหม่ได้เลยครับ</div>';
  loadRecents();
}
function addMsg(role, text, model) {
  const e = $('empty'); if (e) e.remove();
  const div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
  div.textContent = text;
  if (role !== 'user' && model) {
    const meta = document.createElement('div'); meta.className = 'meta';
    meta.textContent = model; div.appendChild(meta);
  }
  $('chat').appendChild(div); return div;
}
async function send() {
  const text = $('input').value.trim(); if (!text) return;
  $('input').value = ''; $('send').disabled = true;
  addMsg('user', text);
  const wait = addMsg('bot', 'กำลังคิด... (ถ้าโมเดลเพิ่งตื่นอาจถึง 2 นาที)'); wait.classList.add('typing');
  scrollBottom();
  try {
    const r = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ session_id: sid, model: $('model').value, message: text }) });
    const d = await r.json();
    wait.remove();
    if (d.error) addMsg('bot', '⚠️ ' + d.error);
    else { sid = d.session_id; addMsg('bot', d.reply, d.model + ' · ' + d.elapsed.toFixed(1) + 's'); }
  } catch (e) { wait.remove(); addMsg('bot', '⚠️ ' + e); }
  $('send').disabled = false; loadRecents(); scrollBottom();
}
function scrollBottom(){ const c = $('chat'); c.scrollTop = c.scrollHeight; }
function esc(s){ return s.replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function ago(ts){ const m = (Date.now()/1000 - ts)/60;
  if (m < 1) return 'เมื่อครู่'; if (m < 60) return Math.floor(m)+' นาที';
  if (m < 1440) return Math.floor(m/60)+' ชม.'; return Math.floor(m/1440)+' วัน'; }
$('input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
loadRecents();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # เงียบ log ปกติ
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/sessions":
            self._json(history.list_sessions())
        elif self.path.startswith("/api/sessions/"):
            d = history.load(self.path.rsplit("/", 1)[1])
            self._json(d if d else {"error": "not found"}, 200 if d else 404)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/chat":
            return self._json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length))
            model_name = req.get("model", "rnai")
            text = (req.get("message") or "").strip()
            if not text:
                return self._json({"error": "ข้อความว่าง"}, 400)

            sid = req.get("session_id") or history.new_session(text, model_name)
            history.append(sid, "user", text)

            # ประกอบ messages จากประวัติทั้งหมดของ session
            data = history.load(sid)
            msgs = [{"role": m["role"], "content": m["content"]} for m in data["messages"]]
            p = get_provider(model_name)
            if p.name == "rnai":
                msgs = [{"role": "system", "content": config.get("RNAI_SYSTEM_PROMPT")}] + msgs

            resp = p.chat(msgs, max_tokens=1500, timeout=200)
            reply = resp["content"] or "(ไม่มีคำตอบ)"
            history.append(sid, "assistant", reply, model=f"{p.name}/{p.model}")
            self._json({"session_id": sid, "reply": reply,
                        "model": f"{p.name}/{p.model}", "elapsed": resp["elapsed"]})
        except SystemExit as e:
            self._json({"error": str(e)}, 200)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"}, 200)


def serve(port: int = PORT, open_browser: bool = True):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"🌐 Rnai Cowork UI เปิดที่ {url}  (กด Ctrl+C เพื่อหยุด)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nปิด UI แล้วครับ")
