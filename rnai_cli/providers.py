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
        if r.status_code >= 400:
            raise SystemExit(
                f"[{self.name}] HTTP {r.status_code} จาก {self.base_url}\n"
                f"รายละเอียด: {r.text[:600]}"
            )
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


# provider name -> (ต้องมี key ไหม, ที่สมัคร key)
# หมายเหตุ "rnai": get_provider("rnai") ยังสร้าง Provider นี้ได้ปกติ (ไม่ต้องใส่ key
# ที่นี่) แต่จุดใช้งานจริงทั้งหมด (chat/agent voice/templates/Cowork UI) ไม่เรียก
# .chat() ของมันตรงๆ อีกต่อไป — ใช้ auth.platform_chat() ซึ่งต้อง `rnai login` ก่อน
# (คุยผ่าน Rnai.io ใช้เครดิต/quota ของบัญชี, endpoint Modal ตรงถูกล็อกด้วย --api-key แล้ว)
PROVIDER_INFO = {
    "rnai":       (False, ""),
    "ollama":     (False, "ติดตั้ง ollama.com แล้วรัน: ollama create rnai -f Modelfile"),
    "gemini":     (True, "aistudio.google.com"),
    "groq":       (True, "console.groq.com"),
    "openrouter": (True, "openrouter.ai/keys"),
    "cerebras":   (True, "cloud.cerebras.ai"),
    "mistral":    (True, "console.mistral.ai"),
    "github":     (True, "github.com/settings/tokens (PAT ธรรมดาก็ใช้ได้)"),
}


def get_provider(name: str) -> Provider:
    """สร้าง provider จาก config เช่น 'groq' หรือ 'openrouter/qwen/qwen3-32b:free'"""
    cfg = config.load()
    model_override = None
    if "/" in name:
        name, model_override = name.split("/", 1)
    name = name.lower()
    if name not in PROVIDER_INFO:
        raise SystemExit(f"ไม่รู้จัก provider '{name}' (ใช้ได้: {', '.join(PROVIDER_INFO)})")
    needs_key, where = PROVIDER_INFO[name]
    up = name.upper()
    key = cfg.get(f"{up}_API_KEY", "")
    if needs_key and not key:
        raise SystemExit(f"ยังไม่ได้ตั้ง {up}_API_KEY — รัน: rnai config set {up}_API_KEY <key> (สมัครฟรีที่ {where})")
    p = Provider(name, cfg[f"{up}_BASE_URL"], key, cfg[f"{up}_MODEL"])
    if model_override:
        p.model = model_override
    return p


def rnai_messages(user_text: str) -> list:
    """สร้าง messages พร้อม system prompt ที่ตรงกับตอนเทรนเสมอ"""
    return [
        {"role": "system", "content": config.get("RNAI_SYSTEM_PROMPT")},
        {"role": "user", "content": user_text},
    ]
