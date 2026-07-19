# -*- coding: utf-8 -*-
"""Tools ของ agent — ทุกตัวที่แก้ไขระบบต้อง confirm ก่อนเสมอ"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

from . import config

console = Console()

# ── OpenAI tools schema (ให้โมเดลวางแผนเรียก) ──────────────────────────────
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web for current information. Use for anything time-sensitive, factual lookups, prices, news, or things you are not sure about.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query"},
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file from the user's machine. Returns up to ~15000 chars.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Absolute or ~ path"},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write/overwrite a text file. The user will be asked to confirm before writing.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Run a shell command on the user's machine. The user will be asked to confirm first. Use for git, npm, file listing, etc. Never use for destructive operations unless the user explicitly asked.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "reason": {"type": "string", "description": "Why this command is needed (shown to user)"},
        }, "required": ["command", "reason"]},
    }},
    {"type": "function", "function": {
        "name": "rnai_skill",
        "description": "Call an Rnai.io skill API. Available skills: text-sum (summarize), text-trans (translate), text-rewrite, text-grammar, text-hashtag, text-extract (text -> JSON), text-gen. Input is text, returns the processed result.",
        "parameters": {"type": "object", "properties": {
            "skill": {"type": "string", "description": "Skill id, e.g. text-sum"},
            "text": {"type": "string", "description": "Input text for the skill"},
        }, "required": ["skill", "text"]},
    }},
]

SKILL_PATHS = {
    "text-sum": "/api/v1/text/summarize",
    "text-trans": "/api/v1/text/translate",
    "text-rewrite": "/api/v1/text/rewrite",
    "text-gen": "/api/v1/text/generate",
    "text-grammar": "/api/v1/text/generate",
    "text-hashtag": "/api/v1/text/generate",
    "text-extract": "/api/v1/text/extract",
}


# ── Implementations ─────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    key = config.get("TAVILY_API_KEY")
    if not key:
        return "ERROR: TAVILY_API_KEY not set. Tell the user to run: rnai config set TAVILY_API_KEY <key> (free at tavily.com)"
    try:
        r = httpx.post("https://api.tavily.com/search",
                       json={"query": query, "max_results": 5,
                             "include_answer": True},
                       headers={"Authorization": f"Bearer {key}",
                                "Content-Type": "application/json"},
                       timeout=30)
        r.raise_for_status()
        data = r.json()
        parts = []
        if data.get("answer"):
            parts.append(f"Summary: {data['answer']}")
        for res in data.get("results", [])[:5]:
            parts.append(f"- {res.get('title')}: {res.get('content', '')[:300]} ({res.get('url')})")
        return "\n".join(parts) or "No results."
    except Exception as e:
        return f"ERROR: search failed — {e}"


def read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: file not found: {p}"
    try:
        text = p.read_text(errors="replace")
    except Exception as e:
        return f"ERROR: {e}"
    if len(text) > 15000:
        return text[:15000] + f"\n...[truncated, total {len(text)} chars]"
    return text


def write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    console.print(Panel(content[:1500] + ("\n..." if len(content) > 1500 else ""),
                        title=f"✏️ agent ขอเขียนไฟล์: {p}", border_style="yellow"))
    if not typer.confirm("อนุญาตให้เขียนไฟล์นี้?", default=False):
        return "DENIED: user rejected the write."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"OK: wrote {len(content)} chars to {p}"


def run_command(command: str, reason: str = "") -> str:
    console.print(Panel(f"[bold]{command}[/bold]\n\nเหตุผล: {reason or '-'}",
                        title="⚡ agent ขอรันคำสั่ง", border_style="red"))
    if not typer.confirm("อนุญาตให้รันคำสั่งนี้?", default=False):
        return "DENIED: user rejected the command."
    try:
        res = subprocess.run(command, shell=True, capture_output=True,
                             text=True, timeout=120)
        out = (res.stdout or "") + (res.stderr or "")
        if len(out) > 8000:
            out = out[:8000] + "\n...[truncated]"
        return f"exit={res.returncode}\n{out.strip()}"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out (120s)"
    except Exception as e:
        return f"ERROR: {e}"


def rnai_skill(skill: str, text: str) -> str:
    path = SKILL_PATHS.get(skill)
    if not path:
        return f"ERROR: unknown skill '{skill}'. Available: {', '.join(SKILL_PATHS)}"
    key = config.get("RNAI_IO_API_KEY")
    if not key:
        return "ERROR: RNAI_IO_API_KEY not set. Tell the user to run: rnai config set RNAI_IO_API_KEY <key> (create one in Rnai.io profile)"
    prompt_map = {
        "text-grammar": f"Correct ALL grammar and spelling. Return ONLY the corrected text:\n\n{text}",
        "text-hashtag": f"Generate 20 trending hashtags for this content, one line, space-separated, each starting with #:\n\n{text}",
    }
    body = ({"text": text} if skill in ("text-sum", "text-extract")
            else {"prompt": prompt_map.get(skill, text)})
    try:
        r = httpx.post(config.get("RNAI_IO_BASE") + path, json=body,
                       headers={"Authorization": f"Bearer {key}",
                                "Content-Type": "application/json"},
                       timeout=60)
        r.raise_for_status()
        data = r.json()
        return json.dumps(data, ensure_ascii=False)[:6000]
    except Exception as e:
        return f"ERROR: skill call failed — {e}"


IMPLEMENTATIONS = {
    "web_search": web_search,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
    "rnai_skill": rnai_skill,
}


def execute(name: str, args: dict) -> str:
    fn = IMPLEMENTATIONS.get(name)
    if not fn:
        return f"ERROR: unknown tool '{name}'"
    try:
        return fn(**args)
    except TypeError as e:
        return f"ERROR: bad arguments for {name} — {e}"
