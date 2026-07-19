# -*- coding: utf-8 -*-
"""OpenAI-compatible client เดียว ใช้ได้ทุก provider (rnai/gemini/groq)"""
from __future__ import annotations
import time
from typing import Optional

import httpx

from . import config


class Provider:
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list, tools: Optional[list] = None,
             max_tokens: int = 1024, temperature: float = 0.6,
             timeout: float = 180.0) -> dict:
        """เรียก /chat/completions คืน dict: {content, reasoning, tool_calls, elapsed, usage}"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        t0 = time.time()
        r = httpx.post(f"{self.base_url}/chat/completions",
                       json=payload, headers=headers, timeout=timeout,
                       follow_redirects=True)
        r.raise_for_status()
        data = r.json()
        msg = data["choices"][0]["message"]
        return {
            "content": (msg.get("content") or "").strip(),
            "reasoning": (msg.get("reasoning") or msg.get("reasoning_content") or "").strip(),
            "tool_calls": msg.get("tool_calls") or [],
            "raw_message": msg,
            "finish_reason": data["choices"][0].get("finish_reason"),
            "elapsed": time.time() - t0,
            "usage": data.get("usage") or {},
        }

    def list_models(self, timeout: float = 300.0) -> list:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        r = httpx.get(f"{self.base_url}/models", headers=headers, timeout=timeout,
                      follow_redirects=True)
        r.raise_for_status()
        return r.json().get("data", [])


def get_provider(name: str) -> Provider:
    """สร้าง provider จาก config: rnai | gemini | groq หรือ 'groq/model-id'"""
    cfg = config.load()
    model_override = None
    if "/" in name:
        name, model_override = name.split("/", 1)
    name = name.lower()
    if name == "rnai":
        p = Provider("rnai", cfg["RNAI_BASE_URL"], "", cfg["RNAI_MODEL"])
    elif name == "gemini":
        if not cfg["GEMINI_API_KEY"]:
            raise SystemExit("ยังไม่ได้ตั้ง GEMINI_API_KEY — รัน: rnai config set GEMINI_API_KEY <key>")
        p = Provider("gemini", cfg["GEMINI_BASE_URL"], cfg["GEMINI_API_KEY"], cfg["GEMINI_MODEL"])
    elif name == "groq":
        if not cfg["GROQ_API_KEY"]:
            raise SystemExit("ยังไม่ได้ตั้ง GROQ_API_KEY — รัน: rnai config set GROQ_API_KEY <key> (ฟรีที่ console.groq.com)")
        p = Provider("groq", cfg["GROQ_BASE_URL"], cfg["GROQ_API_KEY"], cfg["GROQ_MODEL"])
    else:
        raise SystemExit(f"ไม่รู้จัก provider '{name}' (ใช้ได้: rnai, gemini, groq)")
    if model_override:
        p.model = model_override
    return p


def rnai_messages(user_text: str) -> list:
    """สร้าง messages พร้อม system prompt ที่ตรงกับตอนเทรนเสมอ"""
    return [
        {"role": "system", "content": config.get("RNAI_SYSTEM_PROMPT")},
        {"role": "user", "content": user_text},
    ]
