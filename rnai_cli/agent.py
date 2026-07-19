# -*- coding: utf-8 -*-
"""Agent loop แบบ hybrid:
- Planner (Groq/Gemini): คิดและเรียก tools ผ่าน native tool-calling
- Voice (rnai-llm): เรียบเรียงคำตอบสุดท้ายเป็นภาษาไทยบุคลิก Rnai (ปิดได้)
"""
from __future__ import annotations
import json

from rich.console import Console

from . import config, tools
from .providers import get_provider, rnai_messages

console = Console()

PLANNER_SYSTEM = """You are the planning brain of "Rnai", a Thai AI assistant with tools.
Work step by step: decide if you need tools, call them, read results, and continue until the task is done.
Rules:
- Use web_search for anything current or factual you are not sure about.
- Ask for destructive actions only if the user explicitly requested them.
- When you have everything needed, give the FINAL answer in the same language the user used (Thai for Thai).
- Be concise and concrete. If a tool returns ERROR or DENIED, adapt or explain."""


def run_agent(task: str, planner_name: str | None = None,
              voice: str | None = None, max_steps: int | None = None) -> str:
    cfg = config.load()
    planner = get_provider(planner_name or cfg["AGENT_PLANNER"])
    voice = voice if voice is not None else cfg["AGENT_VOICE"]
    max_steps = max_steps or int(cfg["AGENT_MAX_STEPS"])

    console.print(f"[dim]🧠 planner: {planner.name}/{planner.model} | 🗣 voice: {voice} | max {max_steps} steps[/dim]")

    messages: list = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": task},
    ]

    final_answer = ""
    for step in range(1, max_steps + 1):
        resp = planner.chat(messages, tools=tools.TOOL_SCHEMAS, max_tokens=2048)

        if resp["tool_calls"]:
            # เก็บ assistant message (พร้อม tool_calls) เข้า history
            messages.append(resp["raw_message"])
            for tc in resp["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                arg_preview = json.dumps(args, ensure_ascii=False)
                if len(arg_preview) > 120:
                    arg_preview = arg_preview[:120] + "…"
                console.print(f"[cyan]step {step}[/cyan] 🔧 {name}({arg_preview})")
                result = tools.execute(name, args)
                preview = result[:200].replace("\n", " ")
                console.print(f"[dim]   ↳ {preview}{'…' if len(result) > 200 else ''}[/dim]")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": result,
                })
            continue

        # ไม่มี tool call = คำตอบสุดท้าย
        final_answer = resp["content"]
        break
    else:
        final_answer = "ครบจำนวน step สูงสุดแล้วยังไม่จบงาน — สรุปเท่าที่ได้:\n" + (final_answer or "(ไม่มีผลลัพธ์)")

    # ── Voice: ให้ rnai-llm เรียบเรียงเป็นเสียง Rnai ────────────────────────
    if voice == "rnai" and final_answer:
        try:
            rnai = get_provider("rnai")
            polished = rnai.chat(rnai_messages(
                "ช่วยเรียบเรียงคำตอบต่อไปนี้ให้เป็นธรรมชาติแบบคุณ Rnai กระชับ ตรงประเด็น "
                "คงข้อเท็จจริง ตัวเลข และลิงก์ไว้ครบถ้วน ห้ามเพิ่มข้อมูลใหม่:\n\n" + final_answer
            ), max_tokens=1024, timeout=200)
            if polished["content"]:
                return polished["content"]
        except Exception as e:
            console.print(f"[dim]⚠️ voice rnai ใช้ไม่ได้ ({e}) — ส่งคำตอบจาก planner ตรงๆ[/dim]")
    return final_answer
