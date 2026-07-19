# -*- coding: utf-8 -*-
"""Rnai-CLI — คุย/เทียบ/สั่งงาน agent กับโมเดล rnai-llm และโมเดลฟรีอื่นๆ

ติดตั้ง:  pip install -e .
ใช้งาน:   rnai chat "สวัสดี"  |  rnai status  |  rnai compare "โจทย์"  |  rnai agent "งาน"
"""
from __future__ import annotations
import json as jsonlib
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from . import config as cfg_store
from .providers import get_provider, rnai_messages

app = typer.Typer(help="Rnai-CLI — AI agent สำหรับระบบ Rnai.io", no_args_is_help=True)
config_app = typer.Typer(help="จัดการ config (~/.rnai/config.json)")
app.add_typer(config_app, name="config")
console = Console()


# ── chat ────────────────────────────────────────────────────────────────────
@app.command()
def chat(
    prompt: str = typer.Argument(..., help="ข้อความที่จะถาม"),
    model: str = typer.Option("rnai", "--model", "-m", help="rnai | gemini | groq | groq/<model-id>"),
    think: bool = typer.Option(False, "--think", help="แสดง reasoning ของโมเดล"),
    raw: bool = typer.Option(False, "--raw", help="แสดง JSON ดิบ"),
    max_tokens: int = typer.Option(1024, "--max-tokens"),
):
    """คุยกับโมเดล (default: rnai-llm พร้อม system prompt ที่ถูกต้องเสมอ)"""
    p = get_provider(model)
    messages = rnai_messages(prompt) if p.name == "rnai" else [{"role": "user", "content": prompt}]
    with console.status(f"[cyan]{p.name}/{p.model} กำลังคิด... (ถ้าโมเดลหลับ รอ ~2 นาที)[/cyan]"):
        resp = p.chat(messages, max_tokens=max_tokens)
    if raw:
        console.print_json(jsonlib.dumps(resp["raw_message"], ensure_ascii=False))
        return
    if think and resp["reasoning"]:
        console.print(Panel(resp["reasoning"], title="🧠 reasoning", border_style="dim"))
    console.print(Markdown(resp["content"] or "(ไม่มีคำตอบ)"))
    u = resp["usage"]
    console.print(f"[dim]⏱ {resp['elapsed']:.1f}s | tokens {u.get('total_tokens', '?')} | {resp['finish_reason']}[/dim]")
    # บันทึกลงประวัติ (~/.rnai/history) ให้ Web UI เห็นด้วย
    from . import history as hist
    sid = hist.new_session(prompt, p.name)
    hist.append(sid, "user", prompt)
    hist.append(sid, "assistant", resp["content"], model=f"{p.name}/{p.model}")


# ── status ──────────────────────────────────────────────────────────────────
@app.command()
def status():
    """เช็คสถานะระบบ: Modal (adapter version), Vercel, keys ที่ตั้งไว้"""
    import httpx
    cfg = cfg_store.load()
    table = Table(title="Rnai System Status")
    table.add_column("ระบบ", style="cyan")
    table.add_column("สถานะ")
    table.add_column("รายละเอียด", overflow="fold")

    # Modal
    try:
        with console.status("[cyan]เช็ค Modal (ถ้าหลับอยู่จะปลุก รอได้ถึง ~3 นาที)...[/cyan]"):
            models = get_provider("rnai").list_models()
        lora = next((m for m in models if m["id"] == "rnai-llm"), None)
        detail = f"adapter: {lora.get('root', '?')}" if lora else "ไม่พบ rnai-llm!"
        table.add_row("Modal (rnai-llm)", "🟢 online", detail)
    except Exception as e:
        table.add_row("Modal (rnai-llm)", "🔴 offline", str(e)[:80])

    # Vercel
    try:
        r = httpx.get(cfg["RNAI_IO_BASE"], timeout=15, follow_redirects=True)
        table.add_row("Vercel (rnai.io)", "🟢 online" if r.status_code < 500 else f"🔴 {r.status_code}", cfg["RNAI_IO_BASE"])
    except Exception as e:
        table.add_row("Vercel (rnai.io)", "🔴 offline", str(e)[:80])

    # Keys
    for key, label in [("GEMINI_API_KEY", "Gemini"), ("GROQ_API_KEY", "Groq"),
                       ("OPENROUTER_API_KEY", "OpenRouter"), ("CEREBRAS_API_KEY", "Cerebras"),
                       ("MISTRAL_API_KEY", "Mistral"), ("GITHUB_API_KEY", "GitHub Models"),
                       ("TAVILY_API_KEY", "Tavily search"), ("RNAI_IO_API_KEY", "Rnai.io skills")]:
        table.add_row(label, "🟢 set" if cfg.get(key) else "⚪ not set",
                      "" if cfg.get(key) else f"rnai config set {key} <key>")
    console.print(table)


# ── wake ────────────────────────────────────────────────────────────────────
@app.command()
def wake():
    """ปลุกโมเดลบน Modal ให้ตื่นรอ (เช่น ก่อนเดโม่)"""
    with console.status("[cyan]กำลังปลุกโมเดล (cold start ~2 นาที)...[/cyan]"):
        models = get_provider("rnai").list_models()
    lora = next((m for m in models if m["id"] == "rnai-llm"), {})
    console.print(f"[green]✓ โมเดลตื่นแล้ว[/green] adapter: {lora.get('root', '?')}")


# ── compare ─────────────────────────────────────────────────────────────────
@app.command()
def compare(
    prompt: str = typer.Argument(..., help="โจทย์ที่จะยิงทุกโมเดล"),
    models: str = typer.Option("rnai,gemini,groq", "--models", help="คั่นด้วย comma"),
    max_tokens: int = typer.Option(700, "--max-tokens"),
):
    """ยิงโจทย์เดียวกันใส่หลายโมเดล เทียบคำตอบ + ความเร็ว"""
    names = [m.strip() for m in models.split(",") if m.strip()]
    results = []
    for name in names:
        try:
            p = get_provider(name)
            messages = rnai_messages(prompt) if p.name == "rnai" else [{"role": "user", "content": prompt}]
            with console.status(f"[cyan]{name} กำลังตอบ...[/cyan]"):
                resp = p.chat(messages, max_tokens=max_tokens)
            results.append((name, p.model, resp))
        except Exception as e:
            results.append((name, "-", {"content": f"ERROR: {e}", "elapsed": 0, "usage": {}}))

    for name, model_id, resp in results:
        console.print(Panel(Markdown(resp["content"][:2500] or "(ว่าง)"),
                            title=f"🤖 {name} ({model_id}) — {resp['elapsed']:.1f}s",
                            border_style="cyan"))
    table = Table(title="สรุป")
    table.add_column("โมเดล", style="cyan")
    table.add_column("เวลา (s)", justify="right")
    table.add_column("tokens", justify="right")
    table.add_column("ความยาวคำตอบ", justify="right")
    for name, _, resp in results:
        table.add_row(name, f"{resp['elapsed']:.1f}",
                      str(resp["usage"].get("total_tokens", "-")),
                      str(len(resp["content"])))
    console.print(table)


# ── agent ───────────────────────────────────────────────────────────────────
@app.command()
def agent(
    task: str = typer.Argument(..., help="งานที่ให้ agent ทำ"),
    planner: Optional[str] = typer.Option(None, "--planner", help="groq | gemini (default ตาม config)"),
    voice: Optional[str] = typer.Option(None, "--voice", help="rnai | none"),
    steps: Optional[int] = typer.Option(None, "--steps", help="จำนวน step สูงสุด"),
):
    """สั่งงาน agent — ค้นเว็บ อ่าน/เขียนไฟล์ รันคำสั่ง (ถามก่อนเสมอ) เรียก Rnai.io skills"""
    from .agent import run_agent
    answer = run_agent(task, planner_name=planner, voice=voice, max_steps=steps)
    console.print()
    console.print(Panel(Markdown(answer or "(ไม่มีคำตอบ)"), title="✅ ผลลัพธ์", border_style="green"))


# ── ui / history ────────────────────────────────────────────────────────────
@app.command()
def ui(
    port: int = typer.Option(8765, "--port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="ไม่เปิดเบราว์เซอร์อัตโนมัติ"),
):
    """เปิด Web UI บนเครื่อง — Recents + แชทต่อเนื่อง (Cowork หน้าแรก)"""
    from .ui import serve
    serve(port=port, open_browser=not no_browser)


@app.command("history")
def show_history(limit: int = typer.Option(20, "--limit", "-n")):
    """ดูรายการสนทนาล่าสุด"""
    from . import history as hist
    sessions = hist.list_sessions(limit)
    if not sessions:
        console.print("[dim]ยังไม่มีประวัติสนทนา — เริ่มด้วย rnai chat หรือ rnai ui[/dim]")
        return
    import datetime
    table = Table(title=f"Recents ({len(sessions)})")
    table.add_column("เมื่อ", style="dim")
    table.add_column("หัวข้อ", style="cyan", overflow="fold")
    table.add_column("โมเดล")
    table.add_column("ข้อความ", justify="right")
    for s in sessions:
        when = datetime.datetime.fromtimestamp(s["updated"]).strftime("%d/%m %H:%M")
        table.add_row(when, s["title"], s["model"], str(s["count"]))
    console.print(table)
    console.print("[dim]เปิดดูเต็มๆ ใน Web UI: rnai ui[/dim]")


# ── config ──────────────────────────────────────────────────────────────────
@config_app.command("set")
def config_set(key: str, value: str):
    """ตั้งค่า เช่น rnai config set GROQ_API_KEY gsk_xxx"""
    cfg_store.set_value(key.upper(), value)
    console.print(f"[green]✓ ตั้ง {key.upper()} แล้ว[/green]")


@config_app.command("list")
def config_list():
    """แสดง config ปัจจุบัน (ซ่อนค่า key)"""
    table = Table(title=f"config — {cfg_store.CONFIG_PATH}")
    table.add_column("key", style="cyan")
    table.add_column("value", overflow="fold")
    for k, v in cfg_store.load().items():
        if "KEY" in k and v:
            v = v[:6] + "…" + v[-4:] if len(v) > 12 else "***"
        table.add_row(k, str(v))
    console.print(table)


if __name__ == "__main__":
    app()
