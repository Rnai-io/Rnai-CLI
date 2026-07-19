# -*- coding: utf-8 -*-
"""Rnai Web UI — เซิร์ฟเวอร์ localhost (stdlib ล้วน ไม่ต้องลง dependency เพิ่ม)
เปิดด้วย: rnai ui  →  http://localhost:8765
ดีไซน์: minimal สไตล์ ollama.com — พื้นขาว เส้นบาง เนื้อหากลางจอ
"""
from __future__ import annotations
import json
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, history
from . import templates as tpl
from . import worker as wk
from .providers import get_provider

PORT = 8765

HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>Rnai</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Crect width='512' height='512' rx='116' fill='%230B3945'/%3E%3Cpath d='M196 196v160' stroke='%23fff' stroke-width='62' stroke-linecap='round'/%3E%3Cpath d='M196 300q0-104 110-104' stroke='%23fff' stroke-width='62' stroke-linecap='round' fill='none'/%3E%3Ccircle cx='382' cy='196' r='34' fill='%23D77757'/%3E%3C/svg%3E">
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
.projlabel { display:flex; align-items:center; justify-content:space-between; padding-right:12px; }
#newProj { border:0; background:transparent; color:var(--faint); font-size:16px; line-height:1;
           width:22px; height:22px; border-radius:6px; cursor:pointer; }
#newProj:hover { background:var(--soft); color:var(--ink); }
#projects { padding:0 8px 6px; }
.proj { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:8px; cursor:pointer;
        font-size:13px; color:#404040; }
.proj:hover { background:var(--soft); }
.proj.active { background:var(--soft); color:var(--ink); font-weight:600; }
.proj .ic { font-size:14px; }
.proj .nm { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.proj .x { display:none; border:0; background:transparent; color:var(--faint); font-size:12px;
           padding:2px 5px; border-radius:5px; }
.proj:hover .x { display:block; }
.proj .x:hover { color:#dc2626; background:#fee; }
.proj.active .dot2 { width:6px; height:6px; border-radius:50%; background:#22c55e; }
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
/* mode bar (Chat / Cowork) */
#modebar { display:flex; align-items:center; gap:14px; padding:12px 24px;
           border-bottom:1px solid var(--line); flex-shrink:0; }
#modeswitch { display:flex; background:var(--soft); border-radius:99px; padding:3px; gap:2px; }
.modebtn { border:0; background:transparent; border-radius:99px; padding:6px 18px; font-size:13.5px;
           font-weight:600; color:var(--sub); display:flex; align-items:center; gap:6px; cursor:pointer; transition:.15s; }
.modebtn.on { background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.09); }
.modebtn.chat.on { color:var(--ink); }
.modebtn.cowork.on { color:#0B3945; }
#modedesc { font-size:12.5px; color:var(--faint); }
#main.cowork #modebar { background:linear-gradient(90deg,#FBF4F0,transparent 60%); }
/* workspace folder chip */
#folderbar { display:none; align-items:center; gap:8px; margin-left:auto; }
#main.cowork #folderbar { display:flex; }
#folderchip { display:flex; align-items:center; gap:7px; border:1px solid var(--line); background:#fff;
              border-radius:8px; padding:6px 12px; font-size:12.5px; color:#404040; cursor:pointer; max-width:340px; }
#folderchip:hover { border-color:#c9c9c9; background:var(--hover); }
#folderchip .fp { white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                  font-family:ui-monospace,monospace; direction:rtl; text-align:left; }
/* folder dialog */
#folderdlg { position:fixed; inset:0; background:rgba(0,0,0,.28); display:none; align-items:center;
             justify-content:center; z-index:50; }
#folderdlg.show { display:flex; }
.fdcard { background:#fff; border-radius:16px; width:460px; max-width:92vw; padding:24px;
          box-shadow:0 20px 60px rgba(0,0,0,.25); }
.fdcard h3 { font-size:17px; font-weight:700; margin-bottom:6px; }
.fdcard p { font-size:13px; color:var(--sub); margin-bottom:16px; }
.fdcard input { width:100%; border:1px solid var(--line); border-radius:9px; padding:10px 12px;
                font:13px ui-monospace,monospace; }
.fdcard .row { display:flex; align-items:center; gap:8px; margin-top:12px; font-size:13px; color:#404040; }
.fdcard .files { margin-top:14px; max-height:180px; overflow-y:auto; border:1px solid var(--line);
                 border-radius:9px; padding:8px; font-size:12.5px; color:#555; }
.fdcard .files .it { padding:3px 6px; }
.fdcard .actions { display:flex; justify-content:flex-end; gap:10px; margin-top:18px; }
.fdcard .actions button { border:0; border-radius:9px; padding:9px 18px; font-size:13.5px; font-weight:600; cursor:pointer; }
.fd-save { background:var(--ink); color:#fff; }
.fd-cancel { background:transparent; color:var(--sub); }
#fdmsg { font-size:12.5px; margin-top:10px; }
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
#attach { width:34px; height:34px; border:0; border-radius:99px; background:transparent; color:var(--sub);
          display:none; align-items:center; justify-content:center; flex-shrink:0; }
#main.cowork #attach { display:flex; }
#attach:hover { background:var(--soft); color:var(--ink); }
#composer { position:relative; }
#attachpop { display:none; position:absolute; left:24px; bottom:78px; width:340px; max-height:300px;
             overflow-y:auto; background:#fff; border:1px solid var(--line); border-radius:12px;
             box-shadow:0 8px 30px rgba(0,0,0,.14); padding:8px; z-index:20; }
#attachpop.show { display:block; }
#attachpop .aphead { font-size:11.5px; color:var(--faint); padding:6px 8px 8px; }
#attachpop .aphead span { font-family:ui-monospace,monospace; }
.apitem { display:flex; align-items:center; gap:9px; padding:8px 10px; border-radius:8px;
          font-size:13px; cursor:pointer; }
.apitem:hover { background:var(--soft); }
.apitem .nm { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.apitem .go { color:var(--faint); font-size:11px; }
.apempty { padding:14px 10px; color:var(--faint); font-size:12.5px; text-align:center; }
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

/* ── Settings ── */
#settings { display:none; flex:1; overflow-y:auto; }
#settings.show { display:block; }
#setwrap { max-width:640px; margin:0 auto; padding:40px 24px 80px; }
#setwrap h2 { font-size:22px; font-weight:700; letter-spacing:-.02em; margin-bottom:4px; }
#setwrap .sub { color:var(--sub); font-size:14px; margin-bottom:28px; }
.sethead { font-size:12px; font-weight:600; color:var(--faint); text-transform:uppercase;
           letter-spacing:.06em; margin:28px 0 10px; }
.setrow { border:1px solid var(--line); border-radius:var(--r); padding:14px 16px; margin-bottom:10px;
          display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.setrow .info { flex:1; min-width:200px; }
.setrow .name { font-size:14px; font-weight:600; display:flex; align-items:center; gap:8px; }
.setrow .desc { font-size:12.5px; color:var(--sub); }
.setrow .desc a { color:var(--accent); text-decoration:none; }
.setrow input, .setrow select.val { border:1px solid var(--line); border-radius:8px; padding:8px 12px;
             font-size:13px; width:230px; font-family:ui-monospace,monospace; }
.setrow input:focus { outline:0; border-color:#c9c9c9; }
.setrow .save { border:0; background:var(--ink); color:#fff; border-radius:8px;
                padding:8px 16px; font-size:13px; font-weight:500; }
.setrow .save:hover { background:#000; }
.st { width:8px; height:8px; border-radius:50%; background:#d4d4d4; }
.st.on { background:#22c55e; }
.saved { color:#22c55e; font-size:12.5px; }

/* ── Agent steps + approval ── */
.steps { font-size:12.5px; color:var(--sub); border-left:2px solid var(--line);
         padding:4px 14px; margin:6px 0 14px; line-height:1.9; }
.steps .tl { color:#0B3945; }
.steps .rs { color:var(--faint); }
.approvebox { border:1px solid #f3c9b8; background:#FDF3EE; border-radius:12px;
              padding:14px 16px; margin:10px 0; font-size:13.5px; }
.approvebox .ttl { font-weight:600; margin-bottom:6px; }
.approvebox pre { background:#fff; border:1px solid var(--line); border-radius:8px; padding:10px;
                  font:12px ui-monospace,monospace; white-space:pre-wrap; max-height:180px;
                  overflow-y:auto; margin:8px 0; }
.approvebox button { border:0; border-radius:8px; padding:7px 16px; font-size:13px; font-weight:600; margin-right:8px; cursor:pointer; }
.ap-ok { background:#0B3945; color:#fff; }
.ap-no { background:#eee; color:#444; }

/* ── Workspace (Templates + Tasks รวมหน้าเดียว) ── */
#ws { display:none; flex:1; overflow-y:auto; }
#ws.show { display:block; }
#wswrap { max-width:860px; margin:0 auto; padding:40px 24px 80px; }
.wshead h2 { font-size:24px; font-weight:700; letter-spacing:-.02em; }
.wshead p { color:var(--sub); font-size:14px; margin:4px 0 8px; }
.wssection { margin-top:34px; }
.wstitle { display:flex; align-items:center; gap:10px; font-size:16px; font-weight:700;
           color:var(--ink); padding-bottom:12px; margin-bottom:16px; border-bottom:1px solid var(--line); }
.wscount { font-size:12px; font-weight:600; color:var(--faint); background:var(--soft);
           border-radius:99px; padding:2px 10px; }
.wsnote { font-size:12.5px; color:var(--faint); margin:-4px 0 16px; }
.wsnote code { background:var(--soft); padding:2px 7px; border-radius:6px; font:12px ui-monospace,monospace; color:#404040; }
/* task rows */
.taskrow { border:1px solid var(--line); border-radius:var(--r); padding:14px 16px; margin-bottom:10px;
           display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.taskrow .info { flex:1; min-width:220px; }
.taskrow .tp { font-size:14px; font-weight:500; }
.taskrow .tm { font-size:12px; color:var(--sub); margin-top:3px; }
.taskrow button { border:1px solid var(--line); background:#fff; border-radius:8px;
                  padding:6px 12px; font-size:12.5px; color:#404040; cursor:pointer; }
.taskrow button:hover { border-color:#c9c9c9; background:var(--hover); }
.taskrow .danger:hover { color:#dc2626; border-color:#f3c1c1; background:#fff5f5; }
/* template cards */
.tplcat { font-size:12px; font-weight:600; color:var(--faint); text-transform:uppercase;
          letter-spacing:.06em; margin:20px 0 10px; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:10px; }
.card { border:1px solid var(--line); border-radius:var(--r); padding:14px 16px; cursor:pointer;
        transition:.15s; background:#fff; }
.card:hover { border-color:#c9c9c9; box-shadow:0 2px 8px rgba(0,0,0,.05); }
.card .t { font-size:14.5px; font-weight:600; display:flex; gap:8px; align-items:center; }
.card .p { font-size:12.5px; color:var(--sub); margin-top:4px; display:-webkit-box;
           -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card .badge { font-size:11px; color:var(--faint); margin-top:8px; }
/* ฟอร์มใช้ template */
#tplform { border:1px solid var(--line); border-radius:14px; padding:20px; margin-bottom:24px;
           background:var(--hover); display:none; }
#tplform.show { display:block; }
#tplform h3 { font-size:16px; margin-bottom:4px; }
#tplform .fp { font-size:12.5px; color:var(--sub); margin-bottom:14px; white-space:pre-wrap; }
.frow { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.frow label { font-size:13px; width:180px; color:#404040; }
.frow input { flex:1; border:1px solid var(--line); border-radius:8px; padding:8px 12px; font:13.5px inherit; }
#tplform .actions { display:flex; gap:10px; margin-top:14px; align-items:center; }
#tplform .go { border:0; background:var(--ink); color:#fff; border-radius:8px; padding:9px 20px;
               font-size:13.5px; font-weight:600; }
#tplform .cancel { border:0; background:transparent; color:var(--sub); font-size:13px; }
#tplmsg { font-size:13px; }

/* ── Download ── */
#download { display:none; flex:1; overflow-y:auto; }
#download.show { display:block; }
#dlwrap { max-width:560px; margin:0 auto; padding:56px 24px 80px; text-align:center; }
#dlwrap h2 { font-size:26px; font-weight:700; letter-spacing:-.02em; margin:18px 0 26px; }
.ostabs { display:flex; gap:6px; justify-content:center; margin-bottom:28px; }
.ostab { border:0; background:transparent; border-radius:99px; padding:8px 20px;
         font-size:14px; color:var(--sub); transition:.15s; }
.ostab.on { background:var(--soft); color:var(--ink); font-weight:600; }
.ostab:hover { color:var(--ink); }
.codebox { position:relative; text-align:left; background:var(--soft); border:1px solid var(--line);
           border-radius:12px; padding:18px 52px 18px 20px;
           font:13.5px/1.6 ui-monospace,'SF Mono',Menlo,monospace; word-break:break-all; }
.copybtn { position:absolute; right:10px; top:12px; border:1px solid var(--line); background:#fff;
           border-radius:8px; padding:5px 10px; font-size:12px; color:var(--sub); }
.copybtn:hover { color:var(--ink); border-color:#d4d4d4; }
.dlcaption { color:var(--faint); font-size:13px; margin:12px 0 26px; }
.dlor { color:var(--faint); font-size:13px; margin:2px 0 14px; }
.dlbtn { display:inline-block; background:var(--ink); color:#fff; text-decoration:none;
         border-radius:99px; padding:12px 28px; font-size:14.5px; font-weight:600; transition:.15s; }
.dlbtn:hover { background:#000; }
.dlnote { margin-top:34px; font-size:12.5px; color:var(--faint); line-height:1.8; }
.dlnote code { background:var(--soft); padding:2px 7px; border-radius:6px;
               font:12px ui-monospace,monospace; color:#404040; }
@media (max-width:760px){ #side{display:none} }
</style>
</head>
<body>
<nav>
  <div class="brand">
    <svg width="26" height="26" viewBox="0 0 512 512"><rect width="512" height="512" rx="116" fill="#0B3945"/><path d="M196 196v160" stroke="#fff" stroke-width="62" stroke-linecap="round"/><path d="M196 300q0-104 110-104" stroke="#fff" stroke-width="62" stroke-linecap="round" fill="none"/><circle cx="382" cy="196" r="34" fill="#D77757"/></svg>
    Rnai
  </div>
  <a href="#" onclick="showChat();return false">Chat</a>
  <a href="#" onclick="showWorkspace();return false">Workspace</a>
  <a href="#" onclick="showSettings();return false">Settings</a>
  <a href="#" onclick="showDownload();return false">Download</a>
  <a href="https://rnai-io.vercel.app" target="_blank">Rnai.io</a>
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
    <div class="label projlabel">โปรเจกต์
      <button id="newProj" onclick="openNewProject()" title="เพิ่มโปรเจกต์ใหม่">＋</button>
    </div>
    <div id="projects"></div>
    <div class="label">Recents</div>
    <div id="recents"></div>
  </div>
  <div id="main">
    <div id="modebar">
      <div id="modeswitch">
        <button class="modebtn chat on" id="mode-chat" onclick="setMode('chat')">💬 Chat</button>
        <button class="modebtn cowork" id="mode-cowork" onclick="setMode('cowork')">🛠 Cowork</button>
      </div>
      <span id="modedesc">คุยกับโมเดลอย่างเดียว — ตอบเร็ว ไม่ใช้เครื่องมือ</span>
      <div id="folderbar">
        <div id="folderchip" onclick="openFolder()" title="โฟลเดอร์ทำงานของ agent">
          📁 <span class="fp" id="folderPath">~/RnaiWorkspace</span>
        </div>
      </div>
    </div>
    <div id="chat"><div id="thread">
      <div id="empty">
        <svg width="56" height="56" viewBox="0 0 512 512" style="margin-bottom:16px"><rect width="512" height="512" rx="116" fill="#0B3945"/><path d="M196 196v160" stroke="#fff" stroke-width="62" stroke-linecap="round"/><path d="M196 300q0-104 110-104" stroke="#fff" stroke-width="62" stroke-linecap="round" fill="none"/><circle cx="382" cy="196" r="34" fill="#D77757"/></svg>
        <h2 id="emptyTitle">คุยกับ Rnai ได้เลย</h2>
        <p id="emptyDesc">โมเดลของคุณเอง รันบนเครื่อง ประวัติเก็บในเครื่อง</p>
        <div class="chips" id="emptyChips"></div>
      </div>
    </div></div>
    <div id="composer">
      <div id="box">
        <button id="attach" onclick="toggleAttach(event)" title="แนบไฟล์/โฟลเดอร์จาก workspace">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M21 12.5l-8 8a5 5 0 01-7-7l8-8a3.5 3.5 0 015 5l-8 8a2 2 0 01-3-3l7.5-7.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <textarea id="input" rows="1" placeholder="พิมพ์ข้อความถึง Rnai..."></textarea>
        <button id="send" onclick="send()" title="ส่ง">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
      <div id="attachpop">
        <div class="aphead">แนบจากโฟลเดอร์ทำงาน <span id="apdir"></span></div>
        <div id="aplist"></div>
      </div>
      <div id="hint">Enter ส่ง · Shift+Enter ขึ้นบรรทัดใหม่ · ประวัติอยู่ที่ ~/.rnai/history</div>
    </div>
  </div>
  <div id="settings"><div id="setwrap">
    <h2>Settings</h2>
    <div class="sub">API keys และการตั้งค่า — บันทึกที่ ~/.rnai/config.json บนเครื่องคุณเท่านั้น</div>
    <div id="setlist"></div>
  </div></div>
  <div id="ws"><div id="wswrap">
    <div class="wshead">
      <h2>Workspace</h2>
      <p>เลือกงานสำเร็จรูปจากคลัง แล้วสั่งทำทันทีหรือตั้งเวลาให้ Worker รันอัตโนมัติ</p>
    </div>

    <div class="wssection">
      <div class="wstitle"><span>📋 คลัง Templates</span>
        <span class="wscount" id="tplCount"></span></div>
      <div id="tplform"></div>
      <div id="tpllist"></div>
    </div>

    <div class="wssection">
      <div class="wstitle"><span>⏰ งานในคิว Worker</span>
        <span class="wscount" id="taskCount"></span></div>
      <div class="wsnote">Worker ต้องทำงานอยู่จึงจะรันตามเวลา — ติดตั้งครั้งเดียว: <code>rnai worker --install</code></div>
      <div id="tasklist"></div>
    </div>
  </div></div>
  <div id="download"><div id="dlwrap">
    <svg width="64" height="64" viewBox="0 0 512 512"><rect width="512" height="512" rx="116" fill="#0B3945"/><path d="M196 196v160" stroke="#fff" stroke-width="62" stroke-linecap="round"/><path d="M196 300q0-104 110-104" stroke="#fff" stroke-width="62" stroke-linecap="round" fill="none"/><circle cx="382" cy="196" r="34" fill="#D77757"/></svg>
    <h2>Download Rnai-CLI</h2>
    <div class="ostabs">
      <button class="ostab on" id="os-mac" onclick="setOS('mac')">macOS</button>
      <button class="ostab" id="os-linux" onclick="setOS('linux')">Linux</button>
      <button class="ostab" id="os-win" onclick="setOS('win')">Windows</button>
    </div>
    <div class="codebox"><span id="dlcmd">curl -fsSL https://raw.githubusercontent.com/Rnai-io/Rnai-CLI/main/install.sh | sh</span>
      <button class="copybtn" onclick="copyCmd(this)">Copy</button>
    </div>
    <div class="dlcaption" id="dlcap">วางคำสั่งนี้ใน Terminal</div>
    <div class="dlor">หรือ</div>
    <a class="dlbtn" href="https://github.com/Rnai-io/Rnai-CLI/archive/refs/heads/main.zip">Download Source (.zip)</a>
    <div class="dlnote">
      ต้องมี Python 3.9+ ในเครื่อง · ติดตั้งแล้วเริ่มที่ <code>rnai --help</code><br>
      เปิดหน้าจอนี้ได้ทุกเมื่อด้วย <code>rnai ui</code> · ตั้งค่า API keys ที่แท็บ Settings
    </div>
  </div></div>
</div>
<div id="folderdlg">
  <div class="fdcard">
    <h3>📁 โฟลเดอร์ทำงาน</h3>
    <p>Cowork จะอ่าน/เขียนไฟล์อ้างอิงจากโฟลเดอร์นี้ (เหมือนเปิดโปรเจกต์ใน IDE)</p>
    <input id="fdInput" placeholder="~/RnaiWorkspace หรือ /Users/you/projects/myapp">
    <label class="row"><input type="checkbox" id="fdCreate"> สร้างโฟลเดอร์นี้ถ้ายังไม่มี</label>
    <div class="files" id="fdFiles"></div>
    <div id="fdmsg"></div>
    <div class="actions">
      <button class="fd-cancel" onclick="$('folderdlg').classList.remove('show')">ยกเลิก</button>
      <button class="fd-save" onclick="saveFolder()">ใช้โฟลเดอร์นี้</button>
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
/* ── Mode: chat / cowork ── */
let agentMode = false;
const CHIPS = {
  chat: [
    ["💰 วางแผนเก็บเงิน", "วางแผนเก็บเงินเดือนละ 5,000 ให้หน่อย"],
    ["✉️ ร่างอีเมล", "ช่วยร่างอีเมลขอเลื่อนนัดประชุม"],
    ["📊 ถามความรู้", "สรุปหลัก 50/30/20 สั้นๆ"],
  ],
  cowork: [
    ["🔎 ค้นข่าววันนี้", "ค้นข่าว AI ที่น่าสนใจวันนี้ สรุปเป็นภาษาไทย 3 ข้อ บันทึกเป็นไฟล์ ainews.md"],
    ["📄 สรุปไฟล์", "อ่านไฟล์ ~/Downloads/เอกสาร.txt แล้วสรุปประเด็นสำคัญเป็นภาษาไทย"],
    ["💹 เทียบราคา", "ค้นราคาทองคำกับ USD/THB วันนี้ ทำตารางเทียบ บันทึกเป็นไฟล์ market.md"],
  ],
};
function renderChips(){
  const mode = agentMode ? 'cowork' : 'chat';
  $('emptyChips').innerHTML = CHIPS[mode].map(c =>
    `<button class="chip" onclick="fill(${JSON.stringify(c[1]).replace(/"/g,'&quot;')})">${c[0]}</button>`).join('');
}
function setMode(mode){
  agentMode = (mode === 'cowork');
  $('mode-chat').classList.toggle('on', !agentMode);
  $('mode-cowork').classList.toggle('on', agentMode);
  $('main').classList.toggle('cowork', agentMode);
  $('modedesc').textContent = agentMode
    ? 'ค้นเว็บ · จัดการไฟล์ · เรียก skills — agent ทำงานหลายขั้นและขออนุมัติก่อนแก้ไข'
    : 'คุยกับโมเดลอย่างเดียว — ตอบเร็ว ไม่ใช้เครื่องมือ';
  $('input').placeholder = agentMode
    ? '🛠 สั่งงาน Cowork — เช่น "ค้นข่าววันนี้ สรุปเป็นไฟล์"...'
    : 'พิมพ์ข้อความถึง Rnai...';
  $('emptyTitle').textContent = agentMode ? 'Cowork — ผู้ช่วยลงมือทำ' : 'คุยกับ Rnai ได้เลย';
  $('emptyDesc').textContent = agentMode
    ? 'สั่งงานที่ต้องค้นข้อมูล จัดการไฟล์ หรือทำหลายขั้นตอน แล้วดู agent ทำให้ทีละสเต็ป'
    : 'โมเดลของคุณเอง รันบนเครื่อง ประวัติเก็บในเครื่อง';
  renderChips();
  if (agentMode) loadFolder();
}

async function sendAgent(text) {
  addMsg('user', text);
  const stepsDiv = document.createElement('div'); stepsDiv.className = 'steps';
  stepsDiv.innerHTML = '<span class="tl">🛠 agent เริ่มทำงาน...</span>';
  $('thread').appendChild(stepsDiv); scrollBottom();
  const r = await fetch('/api/agent', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ session_id: sid, message: text }) });
  const d = await r.json();
  if (d.error) { stepsDiv.remove(); const b = addMsg('bot', d.error); b.classList.add('err');
    $('send').disabled = false; return; }
  sid = d.session_id;
  let apDiv = null, shown = 0;
  const poll = setInterval(async () => {
    const s = await (await fetch('/api/agent/status?id=' + d.job_id)).json();
    while (shown < s.steps.length) {
      const st = s.steps[shown++];
      const line = document.createElement('div');
      line.className = st.kind === 'tool' ? 'tl' : 'rs';
      line.textContent = (st.kind === 'tool' ? '🔧 ' : '   ↳ ') + st.text;
      stepsDiv.appendChild(line); scrollBottom();
    }
    if (s.pending && !apDiv) {
      apDiv = document.createElement('div'); apDiv.className = 'approvebox';
      apDiv.innerHTML = `<div class="ttl">⚠️ agent ขออนุญาต: ${esc(s.pending.title)}</div>
        <pre>${esc(s.pending.preview||'')}</pre>
        <button class="ap-ok" onclick="approve('${d.job_id}',true,this)">อนุญาต</button>
        <button class="ap-no" onclick="approve('${d.job_id}',false,this)">ปฏิเสธ</button>`;
      $('thread').appendChild(apDiv); scrollBottom();
    }
    if (!s.pending && apDiv) { apDiv.remove(); apDiv = null; }
    if (s.status !== 'running') {
      clearInterval(poll); if (apDiv) apDiv.remove();
      addMsg('bot', s.answer, 'agent'); $('send').disabled = false;
      loadRecents(); scrollBottom();
    }
  }, 1000);
}
/* ── Projects ── */
async function loadProjects(){
  const d = await (await fetch('/api/projects')).json();
  $('projects').innerHTML = d.projects.map(p => `
    <div class="proj ${p.active?'active':''}" onclick="switchProject('${esc(p.path)}')" title="${esc(p.path)}">
      <span class="ic">${p.active?'📂':'📁'}</span>
      <span class="nm">${esc(p.name||'workspace')}</span>
      ${p.active?'<span class="dot2"></span>':''}
      <button class="x" title="เอาออกจากรายการ" onclick="removeProject(event,'${esc(p.path)}')">✕</button>
    </div>`).join('');
}
async function switchProject(path){
  await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ path }) });
  loadProjects();
  if (agentMode) loadFolder();
  toast('เปิดโปรเจกต์: ' + path.split('/').pop());
}
function openNewProject(){
  const name = prompt('ชื่อโปรเจกต์ใหม่ (จะสร้างโฟลเดอร์ใน ~/RnaiProjects/)\\nหรือใส่ path เต็มก็ได้:');
  if (!name) return;
  const path = name.includes('/') ? name : '~/RnaiProjects/' + name;
  fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ path, create: true }) })
    .then(r=>r.json()).then(d=>{
      if (d.ok) { loadProjects(); if (agentMode) loadFolder();
        if (!agentMode) setMode('cowork'); toast('สร้างโปรเจกต์แล้ว: ' + path.split('/').pop()); }
      else alert(d.error || 'สร้างไม่สำเร็จ');
    });
}
async function removeProject(ev, path){
  ev.stopPropagation();
  await fetch('/api/projects/remove', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ path }) });
  loadProjects();
}
function toast(msg){
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id='toast'; document.body.appendChild(t);
    t.style.cssText='position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#171717;color:#fff;padding:9px 18px;border-radius:99px;font-size:13px;z-index:100;opacity:0;transition:.2s'; }
  t.textContent = msg; t.style.opacity='1';
  clearTimeout(t._h); t._h = setTimeout(()=>t.style.opacity='0', 1800);
}

/* ── Attach file/folder from workspace ── */
let apSub = '';  // subfolder ที่กำลังเปิดในป็อปอัป
async function toggleAttach(ev){
  ev.stopPropagation();
  const pop = $('attachpop');
  if (pop.classList.contains('show')) { pop.classList.remove('show'); return; }
  apSub = ''; await renderAttach(); pop.classList.add('show');
}
async function renderAttach(){
  const url = '/api/workspace' + (apSub ? '?sub=' + encodeURIComponent(apSub) : '');
  const d = await (await fetch(url)).json();
  $('apdir').textContent = homeShort(d.dir) + (apSub ? '/' + apSub : '');
  let html = '';
  if (apSub) html += `<div class="apitem" onclick="apUp()"><span>↩︎</span><span class="nm">.. ย้อนกลับ</span></div>`;
  if (!d.entries.length && !apSub) html += '<div class="apempty">โฟลเดอร์ว่าง — สร้างไฟล์แล้วค่อยแนบได้</div>';
  html += d.entries.map(e => e.dir
    ? `<div class="apitem" onclick="apOpen('${esc(e.name)}')"><span>📁</span><span class="nm">${esc(e.name)}</span><span class="go">เปิด ›</span></div>`
    : `<div class="apitem" onclick="apPick('${esc(e.name)}')"><span>📄</span><span class="nm">${esc(e.name)}</span><span class="go">แนบ</span></div>`
  ).join('');
  html += `<div class="apitem" onclick="apPickFolder()" style="border-top:1px solid var(--line);margin-top:6px;color:#0B3945">
             <span>📎</span><span class="nm">แนบทั้งโฟลเดอร์นี้</span></div>`;
  $('aplist').innerHTML = html;
}
function apOpen(name){ apSub = apSub ? apSub + '/' + name : name; renderAttach(); }
function apUp(){ apSub = apSub.includes('/') ? apSub.slice(0, apSub.lastIndexOf('/')) : ''; renderAttach(); }
function apInsert(ref){
  const cur = $('input').value;
  $('input').value = (cur ? cur.replace(/\\s*$/, '') + ' ' : '') + ref + ' ';
  $('input').focus(); autosize();
  $('attachpop').classList.remove('show');
}
function apPick(name){ apInsert('`' + (apSub ? apSub + '/' : '') + name + '`'); }
function apPickFolder(){ apInsert('`' + (apSub || '.') + '/`'); }
document.addEventListener('click', e => {
  const pop = $('attachpop');
  if (pop && pop.classList.contains('show') && !pop.contains(e.target) && e.target.id !== 'attach')
    pop.classList.remove('show');
});

/* ── Workspace folder ── */
function homeShort(p){ return p.replace(/^\\/Users\\/[^/]+/, '~').replace(/^\\/home\\/[^/]+/, '~'); }
async function loadFolder(){
  const d = await (await fetch('/api/workspace')).json();
  $('folderPath').textContent = homeShort(d.dir);
  return d;
}
async function openFolder(){
  const d = await loadFolder();
  $('fdInput').value = d.dir;
  $('fdFiles').innerHTML = d.entries.length
    ? d.entries.map(e => `<div class="it">${e.dir?'📁':'📄'} ${esc(e.name)}${e.dir?'/':''}</div>`).join('')
    : '<div class="it" style="color:#aaa">(โฟลเดอร์ว่าง)</div>';
  $('fdmsg').textContent = '';
  $('folderdlg').classList.add('show');
}
async function saveFolder(){
  const dir = $('fdInput').value.trim();
  const r = await fetch('/api/workspace', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ dir, create: $('fdCreate').checked }) });
  const d = await r.json();
  if (d.ok) { $('folderPath').textContent = homeShort(d.dir); $('folderdlg').classList.remove('show'); }
  else { $('fdmsg').innerHTML = '<span class="err">'+esc(d.error)+'</span>'; }
}

async function approve(jobId, ok, btn){
  btn.parentElement.querySelectorAll('button').forEach(b=>b.disabled=true);
  await fetch('/api/agent/approve', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ id: jobId, approve: ok }) });
}

/* ── Tasks view ── */
async function loadTaskList(){
  const tasks = await (await fetch('/api/tasks')).json();
  const tc = $('taskCount'); if (tc) tc.textContent = tasks.length + ' งาน';
  const icon = { ok:'🟢', error:'🔴', running:'🟡' };
  $('tasklist').innerHTML = tasks.length ? tasks.map(t => `
    <div class="taskrow">
      <div class="info">
        <div class="tp">${esc(t.prompt)}</div>
        <div class="tm">${esc(schedTxt(t.schedule))} · รันแล้ว ${t.runs||0} ครั้ง · ${icon[t.last_status]||'⚪'} ${t.last_status||'รอ'}</div>
      </div>
      ${t.last_session ? `<button onclick="openTaskResult('${t.last_session}')">ดูผลล่าสุด</button>` : ''}
      <button onclick="runTaskNow('${t.id}',this)">▶ รันเลย</button>
      <button class="danger" onclick="delTask('${t.id}')">ลบ</button>
    </div>`).join('')
    : '<div style="color:var(--faint);font-size:14px">ยังไม่มีงานในคิว — ไปเลือกจากแท็บ Templates ได้เลยครับ</div>';
}
function schedTxt(s){ if (s.type==='daily') return 'ทุกวัน '+s.time;
  if (s.type==='every') return 'ทุก '+s.minutes+' นาที';
  if (s.type==='once') return 'ครั้งเดียวตามเวลา'; return 'รันครั้งเดียว'; }
function openTaskResult(sessionId){ showChat(); openSession(sessionId); }
async function runTaskNow(id, btn){ btn.textContent = 'กำลังรัน...'; btn.disabled = true;
  await fetch('/api/tasks/run', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ id }) });
  setTimeout(()=>{ btn.textContent='▶ รันเลย'; btn.disabled=false; loadTaskList(); }, 4000); }
async function delTask(id){ await fetch('/api/tasks/'+id, { method:'DELETE' }); loadTaskList(); }

async function send() {
  const text = $('input').value.trim(); if (!text) return;
  $('input').value = ''; autosize(); $('send').disabled = true;
  if (agentMode) { sendAgent(text); return; }
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
renderChips();
loadProjects();

/* ── Views: chat / templates / settings / download ── */
function hideAll(){ $('main').style.display='none'; $('side').style.display='none';
  $('settings').classList.remove('show'); $('download').classList.remove('show');
  $('ws').classList.remove('show'); }
function showWorkspace(){ hideAll(); $('ws').classList.add('show'); loadTemplates(); loadTaskList(); }
function showSettings(){ hideAll(); $('settings').classList.add('show'); loadConfig(); }
function showDownload(){ hideAll(); $('download').classList.add('show'); }
function showChat(){ hideAll(); $('main').style.display='flex'; $('side').style.display='flex'; }

/* ── Templates ── */
const TYPE_ICON = { task:'⏰', chat:'💬', agent:'🤖' };
let TPLS = [];
async function loadTemplates(){
  const r = await fetch('/api/templates'); TPLS = await r.json();
  const tc = $('tplCount'); if (tc) tc.textContent = TPLS.length + ' รายการ';
  const cats = [...new Set(TPLS.map(t=>t.cat))];
  $('tpllist').innerHTML = cats.map(c =>
    `<div class="tplcat">${c}</div><div class="cards">` +
    TPLS.filter(t=>t.cat===c).map(t =>
      `<div class="card" onclick="pickTpl('${t.id}')">
         <div class="t">${TYPE_ICON[t.type]} ${esc(t.title)}</div>
         <div class="p">${esc(t.prompt)}</div>
         <div class="badge">${t.sched_txt||''}</div>
       </div>`).join('') + '</div>').join('');
}
function tplVars(prompt){ return [...prompt.matchAll(/\\{([^}]+)\\}/g)].map(m=>m[1]); }
function pickTpl(id){
  const t = TPLS.find(x=>x.id===id); if (!t) return;
  const vars = tplVars(t.prompt);
  let rows = vars.map((v,i) =>
    `<div class="frow"><label>${esc(v)}</label><input id="tv-${i}" placeholder="กรอก${esc(v)}"></div>`).join('');
  if (t.type==='task' && t.schedule && t.schedule.daily !== undefined)
    rows += `<div class="frow"><label>รันทุกวันเวลา (HH:MM)</label><input id="tv-sched" value="${t.schedule.daily}"></div>`;
  if (t.type==='task' && t.schedule && t.schedule.every !== undefined)
    rows += `<div class="frow"><label>รันทุกกี่นาที</label><input id="tv-sched" value="${t.schedule.every}"></div>`;
  if (t.type==='task' && t.schedule && t.schedule.at !== undefined)
    rows += `<div class="frow"><label>รันเมื่อ (YYYY-MM-DD HH:MM)</label><input id="tv-sched" placeholder="2026-07-21 09:30"></div>`;
  const f = $('tplform');
  f.innerHTML = `<h3>${TYPE_ICON[t.type]} ${esc(t.title)}</h3><div class="fp">${esc(t.prompt)}</div>${rows}
    <div class="actions">
      <button class="go" onclick="useTpl('${t.id}')">${t.type==='task'?'เพิ่มเข้าคิว Worker':t.type==='chat'?'ไปคุยต่อในแชท':'คัดลอกคำสั่ง Terminal'}</button>
      <button class="cancel" onclick="$('tplform').classList.remove('show')">ยกเลิก</button>
      <span id="tplmsg"></span>
    </div>`;
  f.classList.add('show'); f.scrollIntoView({behavior:'smooth'});
}
async function useTpl(id){
  const t = TPLS.find(x=>x.id===id);
  let prompt = t.prompt;
  tplVars(t.prompt).forEach((v,i) => { prompt = prompt.split('{'+v+'}').join($('tv-'+i).value.trim() || v); });
  if (t.type === 'chat') { showChat(); newChatSoft(); $('input').value = prompt; $('input').focus(); autosize(); return; }
  if (t.type === 'agent') {
    navigator.clipboard.writeText('rnai agent "' + prompt.replace(/"/g,'\\\\"') + '"');
    $('tplmsg').innerHTML = '<span class="saved">✓ คัดลอกแล้ว — วางใน Terminal ได้เลย</span>'; return;
  }
  const body = { prompt };
  const sv = $('tv-sched') ? $('tv-sched').value.trim() : '';
  if (t.schedule.daily !== undefined) body.daily = sv;
  else if (t.schedule.every !== undefined) body.every = parseInt(sv);
  else body.at = sv;
  const r = await fetch('/api/task', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body) });
  const d = await r.json();
  $('tplmsg').innerHTML = d.ok
    ? `<span class="saved">✓ เพิ่มงาน ${d.id} แล้ว (${d.sched}) — Worker จะรันตามเวลา</span>`
    : `<span class="err">${d.error||'ผิดพลาด'}</span>`;
}
function newChatSoft(){ sid = null; $('title') && ($('title').textContent='สนทนาใหม่');
  $('thread').innerHTML=''; loadRecents(); }

const DL = {
  mac:   { cmd:'curl -fsSL https://raw.githubusercontent.com/Rnai-io/Rnai-CLI/main/install.sh | sh', cap:'วางคำสั่งนี้ใน Terminal' },
  linux: { cmd:'curl -fsSL https://raw.githubusercontent.com/Rnai-io/Rnai-CLI/main/install.sh | sh', cap:'วางคำสั่งนี้ใน Terminal' },
  win:   { cmd:'pip install git+https://github.com/Rnai-io/Rnai-CLI.git', cap:'วางคำสั่งนี้ใน PowerShell (ต้องมี Python + Git)' },
};
function setOS(os){
  for (const k of ['mac','linux','win']) $('os-'+k).classList.toggle('on', k===os);
  $('dlcmd').textContent = DL[os].cmd; $('dlcap').textContent = DL[os].cap;
}
function copyCmd(btn){
  navigator.clipboard.writeText($('dlcmd').textContent).then(()=>{
    btn.textContent='Copied ✓'; setTimeout(()=>btn.textContent='Copy', 1500); });
}
async function loadConfig(){
  const r = await fetch('/api/config'); const d = await r.json();
  let html = '';
  for (const sec of d.sections) {
    html += `<div class="sethead">${sec.title}</div>`;
    for (const it of sec.items) {
      const secret = it.secret;
      html += `<div class="setrow">
        <div class="info">
          <div class="name"><span class="st ${it.set?'on':''}"></span>${it.label}</div>
          <div class="desc">${it.desc}</div>
        </div>
        <input id="in-${it.key}" type="${secret?'password':'text'}"
               placeholder="${it.set ? (secret ? it.masked : it.value) : (it.placeholder||'ยังไม่ได้ตั้งค่า')}">
        <button class="save" onclick="saveKey('${it.key}')">บันทึก</button>
        <span id="ok-${it.key}"></span>
      </div>`;
    }
  }
  $('setlist').innerHTML = html;
}
async function saveKey(key){
  const v = $('in-'+key).value.trim();
  if (!v) return;
  const r = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ key, value: v }) });
  const d = await r.json();
  if (d.ok) { $('ok-'+key).className='saved'; $('ok-'+key).textContent='✓ บันทึกแล้ว';
    setTimeout(loadConfig, 900); }
  else { $('ok-'+key).className='err'; $('ok-'+key).textContent=d.error||'ผิดพลาด'; }
}
loadRecents();
</script>
</body>
</html>"""


# ── Agent jobs (รันเบื้องหลัง + อนุมัติผ่านเว็บ) ─────────────────────────────
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def start_agent_job(session_id: str | None, message: str) -> dict:
    from . import tools
    from .agent import run_agent

    with JOBS_LOCK:
        if any(j["status"] == "running" for j in JOBS.values()):
            return {"error": "มี agent กำลังทำงานอยู่ รอให้เสร็จก่อนครับ"}
        sid = session_id or history.new_session("🤖 " + message[:50], "agent")
        job_id = "j-" + uuid.uuid4().hex[:8]
        job = {"id": job_id, "session_id": sid, "status": "running", "steps": [],
               "pending": None, "approved": None, "answer": "", "event": threading.Event()}
        JOBS[job_id] = job

    history.append(sid, "user", message)

    def approval_handler(detail: dict) -> bool:
        job["pending"] = detail
        job["event"].clear()
        job["event"].wait(timeout=300)  # รอการตัดสินใจจากหน้าเว็บสูงสุด 5 นาที
        job["pending"] = None
        return bool(job.get("approved"))

    def on_event(kind: str, text: str):
        job["steps"].append({"kind": kind, "text": text, "ts": time.time()})

    def runner():
        tools.WEB_APPROVAL = approval_handler
        try:
            answer = run_agent(message, on_event=on_event)
            job["answer"] = answer or "(ไม่มีผลลัพธ์)"
            history.append(sid, "assistant", job["answer"], model="agent")
            job["status"] = "done"
        except BaseException as e:  # รวม SystemExit จาก provider error
            job["answer"] = f"⚠️ {e}"
            history.append(sid, "assistant", job["answer"], model="agent")
            job["status"] = "error"
        finally:
            tools.WEB_APPROVAL = None

    threading.Thread(target=runner, daemon=True).start()
    return {"job_id": job_id, "session_id": sid}


# ── โครงหน้า Settings: หมวด → รายการ (key, ป้าย, คำอธิบาย, ลับไหม) ──────────
CONFIG_SECTIONS = [
    ("API Keys", [
        ("GROQ_API_KEY", "Groq", 'ฟรีที่ <a href="https://console.groq.com" target="_blank">console.groq.com</a> — โมเดลเร็ว + ตัวเลือก planner', True, "gsk_..."),
        ("GEMINI_API_KEY", "Gemini", 'ฟรีที่ <a href="https://aistudio.google.com" target="_blank">aistudio.google.com</a> — planner หลักของ agent', True, "AIza..."),
        ("OPENROUTER_API_KEY", "OpenRouter", 'ฟรีที่ <a href="https://openrouter.ai/keys" target="_blank">openrouter.ai/keys</a> — โมเดลฟรีหลายสิบตัว', True, "sk-or-..."),
        ("CEREBRAS_API_KEY", "Cerebras", 'ที่ <a href="https://cloud.cerebras.ai" target="_blank">cloud.cerebras.ai</a>', True, "csk-..."),
        ("MISTRAL_API_KEY", "Mistral", 'ที่ <a href="https://console.mistral.ai" target="_blank">console.mistral.ai</a>', True, ""),
        ("GITHUB_API_KEY", "GitHub Models", 'ใช้ GitHub PAT จาก <a href="https://github.com/settings/tokens" target="_blank">settings/tokens</a>', True, "ghp_..."),
        ("TAVILY_API_KEY", "Tavily (Web Search)", 'ฟรี 1,000 ครั้ง/เดือนที่ <a href="https://tavily.com" target="_blank">tavily.com</a> — ให้ agent ค้นเว็บ', True, "tvly-..."),
        ("RNAI_IO_API_KEY", "Rnai.io Skills", 'สร้างจากหน้าโปรไฟล์ <a href="https://rnai-io.vercel.app" target="_blank">Rnai.io</a> — ให้ agent เรียก skills', True, "rnai_sk_..."),
    ]),
    ("Agent", [
        ("AGENT_PLANNER", "Planner (สมองวางแผน)", "gemini | groq — ตัวที่คิดและเรียก tools", False, "gemini"),
        ("AGENT_VOICE", "Voice (เสียงตอบ)", "rnai = เรียบเรียงคำตอบด้วย rnai-llm | none = ปิด", False, "rnai"),
        ("AGENT_MAX_STEPS", "Max steps", "จำนวนขั้นสูงสุดต่อการสั่งงานหนึ่งครั้ง", False, "10"),
    ]),
    ("Models", [
        ("GEMINI_MODEL", "Gemini model", "", False, "gemini-2.5-flash"),
        ("GROQ_MODEL", "Groq model", "", False, "llama-3.3-70b-versatile"),
        ("OPENROUTER_MODEL", "OpenRouter model", "openrouter/free = เลือกโมเดลฟรีอัตโนมัติ", False, "openrouter/free"),
        ("CEREBRAS_MODEL", "Cerebras model", "", False, "gpt-oss-120b"),
    ]),
]
ALLOWED_KEYS = {k for _, items in CONFIG_SECTIONS for k, *_ in items}


def _mask(v: str) -> str:
    return (v[:5] + "…" + v[-4:]) if len(v) > 12 else "•••"


def config_payload() -> dict:
    cfg = config.load()
    sections = []
    for title, items in CONFIG_SECTIONS:
        rows = []
        for key, label, desc, secret, placeholder in items:
            val = cfg.get(key, "")
            rows.append({
                "key": key, "label": label, "desc": desc, "secret": secret,
                "set": bool(val), "placeholder": placeholder,
                "masked": _mask(val) if (secret and val) else "",
                "value": "" if secret else val,
            })
        sections.append({"title": title, "items": rows})
    return {"sections": sections}


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
        elif self.path == "/api/config":
            self._json(config_payload())
        elif self.path == "/api/templates":
            out = []
            for t in tpl.TEMPLATES:
                s = t.get("schedule", {})
                sched_txt = (f"ทุกวัน {s['daily']}" if "daily" in s
                             else f"ทุก {s['every']} นาที" if "every" in s
                             else "ตั้งเวลาเอง" if "at" in s else "")
                out.append({**t, "sched_txt": sched_txt, "schedule": s})
            self._json(out)
        elif self.path.startswith("/api/agent/status"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            job = JOBS.get((q.get("id") or [""])[0])
            if not job:
                return self._json({"error": "job not found"}, 404)
            self._json({"status": job["status"], "steps": job["steps"],
                        "pending": job["pending"], "answer": job["answer"],
                        "session_id": job["session_id"]})
        elif self.path == "/api/projects":
            cfg = config.load()
            active = cfg.get("WORKSPACE_DIR")
            projs = []
            for p in cfg.get("PROJECTS", []):
                from pathlib import Path as _P
                projs.append({"path": p, "name": _P(p).name, "active": p == active,
                              "exists": _P(p).expanduser().exists()})
            self._json({"projects": projs, "active": active})
        elif self.path.startswith("/api/workspace"):
            from urllib.parse import parse_qs, urlparse
            from . import tools
            wd = tools.workspace_dir()
            sub = (parse_qs(urlparse(self.path).query).get("sub") or [""])[0]
            target = (wd / sub) if sub else wd
            entries = []
            try:
                # กันหลุดออกนอก workspace
                target = target.resolve()
                if wd.resolve() in target.parents or target == wd.resolve():
                    for e in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:200]:
                        entries.append({"name": e.name, "dir": e.is_dir()})
            except Exception:
                pass
            self._json({"dir": str(wd), "entries": entries})
        elif self.path == "/api/tasks":
            self._json(wk.load_tasks())
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
        elif self.path.startswith("/api/tasks/"):
            ok = wk.remove_task(self.path.rsplit("/", 1)[1])
            self._json({"ok": ok})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/projects":
            try:
                from pathlib import Path as _P
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                raw = (req.get("path") or "").strip()
                if not raw:
                    return self._json({"ok": False, "error": "path ว่าง"})
                p = _P(raw).expanduser()
                if req.get("create"):
                    p.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    return self._json({"ok": False, "error": f"ไม่พบโฟลเดอร์: {p}"})
                cfg = config.load()
                projs = cfg.get("PROJECTS", [])
                if str(p) not in projs:
                    projs.insert(0, str(p))
                cfg["PROJECTS"] = projs
                cfg["WORKSPACE_DIR"] = str(p)
                config.save(cfg)
                return self._json({"ok": True, "path": str(p)})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/projects/remove":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                cfg = config.load()
                cfg["PROJECTS"] = [p for p in cfg.get("PROJECTS", []) if p != req.get("path")]
                config.save(cfg)
                return self._json({"ok": True})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/workspace":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                raw = (req.get("dir") or "").strip()
                if not raw:
                    return self._json({"ok": False, "error": "path ว่าง"})
                from pathlib import Path as _P
                p = _P(raw).expanduser()
                if req.get("create"):
                    p.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    return self._json({"ok": False, "error": f"ไม่พบโฟลเดอร์: {p} (ติ๊ก 'สร้างใหม่' เพื่อสร้าง)"})
                config.set_value("WORKSPACE_DIR", str(p))
                return self._json({"ok": True, "dir": str(p)})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/agent":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                out = start_agent_job(req.get("session_id"), (req.get("message") or "").strip())
                return self._json(out)
            except Exception as e:
                return self._json({"error": str(e)})
        if self.path == "/api/agent/approve":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                job = JOBS.get(req.get("id", ""))
                if not job:
                    return self._json({"ok": False, "error": "job not found"})
                job["approved"] = bool(req.get("approve"))
                job["event"].set()
                return self._json({"ok": True})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/tasks/run":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                task = next((t for t in wk.load_tasks() if t["id"] == req.get("id")), None)
                if not task:
                    return self._json({"ok": False, "error": "ไม่พบงาน"})
                threading.Thread(target=wk.run_task, args=(task,), daemon=True).start()
                return self._json({"ok": True})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/task":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                prompt = (req.get("prompt") or "").strip()
                if not prompt:
                    return self._json({"ok": False, "error": "prompt ว่าง"})
                task = wk.add_task(prompt, daily=req.get("daily"),
                                   every=req.get("every"), at=req.get("at"))
                return self._json({"ok": True, "id": task["id"],
                                   "sched": wk.describe_schedule(task["schedule"])})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/api/config":
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                key, value = req.get("key", ""), (req.get("value") or "").strip()
                if key not in ALLOWED_KEYS:
                    return self._json({"ok": False, "error": "key ไม่ถูกต้อง"})
                config.set_value(key, value)
                return self._json({"ok": True})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
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
