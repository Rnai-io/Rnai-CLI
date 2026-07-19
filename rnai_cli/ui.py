# -*- coding: utf-8 -*-
"""Rnai Web UI — เซิร์ฟเวอร์ localhost (stdlib ล้วน ไม่ต้องลง dependency เพิ่ม)
เปิดด้วย: rnai ui  →  http://localhost:8765
ดีไซน์: minimal สไตล์ ollama.com — พื้นขาว เส้นบาง เนื้อหากลางจอ
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
<title>Rnai</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
  --ink:#171717; --sub:#737373; --faint:#a3a3a3;
  --line:#e5e5e5; --soft:#f5f5f5; --hover:#fafafa;
  --accent:#D77757; --r:12px;
}
* { box-sizing:border-box; margin:0; padding:0; }
html,body { height:100%; }
body { font:15px/1.7 -apple-system,BlinkMacSystemFont,'Inter','Sarabun',sans-serif;
       color:var(--ink); background:#fff; display:flex; flex-direction:column; }
button { font:inherit; cursor:pointer; }

/* ── Navbar ── */
nav { height:57px; display:flex; align-items:center; gap:24px; padding:0 24px;
      border-bottom:1px solid var(--line); background:#fff; flex-shrink:0; }
.brand { font-weight:700; font-size:17px; letter-spacing:-.02em; display:flex; align-items:center; gap:8px; }
.brand .dot { width:9px; height:9px; border-radius:50%; background:var(--accent); }
nav a { color:var(--sub); text-decoration:none; font-size:14px; }
nav a:hover { color:var(--ink); }
nav .grow { flex:1; }
#model { appearance:none; -webkit-appearance:none; border:1px solid var(--line); border-radius:99px;
         padding:6px 30px 6px 14px; font-size:13.5px; background:#fff url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><path d="M1 1l4 4 4-4" stroke="%23737373" fill="none" stroke-width="1.5" stroke-linecap="round"/></svg>') no-repeat right 12px center; }
#model:hover { border-color:#d4d4d4; }

/* ── Layout ── */
#wrap { flex:1; display:flex; min-height:0; }
#side { width:264px; border-right:1px solid var(--line); display:flex; flex-direction:column; background:#fff; }
#newBtn { margin:16px; padding:9px 14px; border:1px solid var(--line); background:#fff;
          border-radius:var(--r); font-size:14px; font-weight:500; text-align:left;
          display:flex; align-items:center; gap:8px; transition:.15s; }
#newBtn:hover { background:var(--hover); border-color:#d4d4d4; }
#side .label { padding:4px 20px 8px; font-size:11.5px; font-weight:600; color:var(--faint);
               text-transform:uppercase; letter-spacing:.06em; }
#recents { flex:1; overflow-y:auto; padding:0 8px 16px; }
.recent { position:relative; padding:8px 12px; border-radius:8px; cursor:pointer; font-size:13.5px;
          color:#404040; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.recent:hover { background:var(--soft); }
.recent.active { background:var(--soft); color:var(--ink); font-weight:500; }
.recent small { display:block; color:var(--faint); font-size:11px; font-weight:400; }
.recent .del { position:absolute; right:6px; top:8px; display:none; border:0; background:transparent;
               color:var(--faint); font-size:13px; padding:2px 6px; border-radius:6px; }
.recent:hover .del { display:block; }
.recent .del:hover { color:#dc2626; background:#fee; }

/* ── Chat ── */
#main { flex:1; display:flex; flex-direction:column; min-width:0; }
#chat { flex:1; overflow-y:auto; }
#thread { max-width:720px; margin:0 auto; padding:32px 24px 8px; }
.turn { margin-bottom:26px; }
.turn .who { font-size:12px; font-weight:600; color:var(--faint); margin-bottom:4px; }
.turn.user .bubble { background:var(--soft); border-radius:var(--r); padding:10px 16px; display:inline-block; }
.turn .bubble { white-space:pre-wrap; word-break:break-word; }
.turn .meta { font-size:11.5px; color:var(--faint); margin-top:6px; }
.turn.user { text-align:right; }
.turn.user .who { display:none; }

#empty { text-align:center; margin-top:16vh; color:var(--sub); }
#empty .mark { width:52px; height:52px; border-radius:16px; background:var(--ink); color:#fff;
               display:inline-flex; align-items:center; justify-content:center;
               font-size:22px; font-weight:700; margin-bottom:16px; }
#empty h2 { color:var(--ink); font-size:19px; font-weight:600; letter-spacing:-.01em; }
#empty p { font-size:14px; margin-top:4px; }
#empty .chips { margin-top:20px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
#empty .chip { border:1px solid var(--line); background:#fff; border-radius:99px;
               padding:7px 14px; font-size:13px; color:#404040; transition:.15s; }
#empty .chip:hover { background:var(--hover); border-color:#d4d4d4; }

/* ── Composer ── */
#composer { flex-shrink:0; padding:8px 24px 24px; }
#box { max-width:720px; margin:0 auto; display:flex; align-items:flex-end; gap:8px;
       border:1px solid var(--line); border-radius:16px; padding:10px 10px 10px 18px;
       box-shadow:0 1px 3px rgba(0,0,0,.04); transition:.15s; background:#fff; }
#box:focus-within { border-color:#c9c9c9; box-shadow:0 2px 8px rgba(0,0,0,.06); }
#input { flex:1; border:0; outline:0; resize:none; font:inherit; max-height:160px; background:transparent; }
#send { width:34px; height:34px; border:0; border-radius:99px; background:var(--ink); color:#fff;
        display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:.15s; }
#send:hover { background:#000; }
#send:disabled { background:#d4d4d4; }
#hint { max-width:720px; margin:8px auto 0; text-align:center; font-size:11.5px; color:var(--faint); }
.typing { color:var(--faint); }
.typing::after { content:'●'; animation:blink 1s infinite; margin-left:2px; }
@keyframes blink { 50% { opacity:.2 } }
.err { color:#dc2626; }
@media (max-width:760px){ #side{display:none} }
</style>
</head>
<body>
<nav>
  <div class="brand"><span class="dot"></span>Rnai</div>
  <a href="#" onclick="newChat();return false">Chat</a>
  <a href="https://rnai-io.vercel.app" target="_blank">Rnai.io</a>
  <a href="https://github.com/Rnai-io/Rnai-CLI" target="_blank">GitHub</a>
  <div class="grow"></div>
  <select id="model">
    <option value="rnai">rnai-llm v3.2</option>
    <option value="gemini">Gemini</option>
    <option value="groq">Groq</option>
    <option value="openrouter">OpenRouter</option>
  </select>
</nav>
<div id="wrap">
  <div id="side">
    <button id="newBtn" onclick="newChat()"><span style="font-size:16px">＋</span> สนทนาใหม่</button>
    <div class="label">Recents</div>
    <div id="recents"></div>
  </div>
  <div id="main">
    <div id="chat"><div id="thread">
      <div id="empty">
        <div class="mark">R</div>
        <h2>คุยกับ Rnai ได้เลย</h2>
        <p>โมเดลของคุณเอง รันบนเครื่อง ประวัติเก็บในเครื่อง</p>
        <div class="chips">
          <button class="chip" onclick="fill('วางแผนเก็บเงินเดือนละ 5,000 ให้หน่อย')">💰 วางแผนเก็บเงิน</button>
          <button class="chip" onclick="fill('ช่วยร่างอีเมลขอเลื่อนนัดประชุม')">✉️ ร่างอีเมล</button>
          <button class="chip" onclick="fill('สรุปหลัก 50/30/20 สั้นๆ')">📊 ถามความรู้</button>
        </div>
      </div>
    </div></div>
    <div id="composer">
      <div id="box">
        <textarea id="input" rows="1" placeholder="พิมพ์ข้อความถึง Rnai..."></textarea>
        <button id="send" onclick="send()" title="ส่ง">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
      <div id="hint">Enter ส่ง · Shift+Enter ขึ้นบรรทัดใหม่ · ประวัติอยู่ที่ ~/.rnai/history</div>
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
       <small>${s.count} ข้อความ · ${ago(s.updated)}</small>
       <button class="del" title="ลบ" onclick="delSession(event,'${s.id}')">✕</button>
     </div>`).join('');
}
async function openSession(id) {
  sid = id;
  const r = await fetch('/api/sessions/' + id); const d = await r.json();
  $('thread').innerHTML = '';
  d.messages.forEach(m => addMsg(m.role, m.content, m.model));
  loadRecents(); scrollBottom();
}
async function delSession(ev, id) {
  ev.stopPropagation();
  await fetch('/api/sessions/' + id, { method:'DELETE' });
  if (sid === id) newChat(); else loadRecents();
}
function newChat() {
  sid = null;
  location.hash = '';
  window.location.reload();
}
function fill(text){ $('input').value = text; $('input').focus(); }
function addMsg(role, text, model) {
  const e = $('empty'); if (e) e.remove();
  const turn = document.createElement('div');
  turn.className = 'turn ' + (role === 'user' ? 'user' : 'bot');
  const who = document.createElement('div'); who.className = 'who'; who.textContent = 'Rnai';
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  turn.appendChild(who); turn.appendChild(bubble);
  if (role !== 'user' && model) {
    const meta = document.createElement('div'); meta.className = 'meta'; meta.textContent = model;
    turn.appendChild(meta);
  }
  $('thread').appendChild(turn); return bubble;
}
async function send() {
  const text = $('input').value.trim(); if (!text) return;
  $('input').value = ''; autosize(); $('send').disabled = true;
  addMsg('user', text);
  const wait = addMsg('bot', 'กำลังคิด'); wait.classList.add('typing');
  scrollBottom();
  try {
    const r = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ session_id: sid, model: $('model').value, message: text }) });
    const d = await r.json();
    wait.parentElement.remove();
    if (d.error) { const b = addMsg('bot', d.error); b.classList.add('err'); }
    else { sid = d.session_id; addMsg('bot', d.reply, d.model + ' · ' + d.elapsed.toFixed(1) + 's'); }
  } catch (e) { wait.parentElement.remove(); const b = addMsg('bot', String(e)); b.classList.add('err'); }
  $('send').disabled = false; loadRecents(); scrollBottom();
}
function scrollBottom(){ const c = $('chat'); c.scrollTop = c.scrollHeight; }
function esc(s){ return s.replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function ago(ts){ const m = (Date.now()/1000 - ts)/60;
  if (m < 1) return 'เมื่อครู่'; if (m < 60) return Math.floor(m)+' นาทีที่แล้ว';
  if (m < 1440) return Math.floor(m/60)+' ชม.ที่แล้ว'; return Math.floor(m/1440)+' วันที่แล้ว'; }
const input = $('input');
function autosize(){ input.style.height='auto'; input.style.height = Math.min(input.scrollHeight, 160)+'px'; }
input.addEventListener('input', autosize);
input.addEventListener('keydown', e => {
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

    def do_DELETE(self):
        if self.path.startswith("/api/sessions/"):
            ok = history.delete(self.path.rsplit("/", 1)[1])
            self._json({"ok": ok})
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
    print(f"🌐 Rnai UI เปิดที่ {url}  (กด Ctrl+C เพื่อหยุด)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nปิด UI แล้วครับ")
