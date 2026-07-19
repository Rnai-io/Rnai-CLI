# -*- coding: utf-8 -*-
"""บันทึกประวัติสนทนาเป็นไฟล์ JSON ที่ ~/.rnai/history/ (ใช้ร่วมกันทั้ง CLI และ UI)"""
from __future__ import annotations
import json
import time
import uuid
from pathlib import Path

HIST_DIR = Path.home() / ".rnai" / "history"


def _path(session_id: str) -> Path:
    return HIST_DIR / f"{session_id}.json"


def new_session(title: str, model: str = "rnai") -> str:
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    sid = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    data = {
        "id": sid,
        "title": (title or "สนทนาใหม่").strip()[:60],
        "model": model,
        "created": time.time(),
        "updated": time.time(),
        "messages": [],
    }
    _path(sid).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return sid


def load(session_id: str) -> dict | None:
    p = _path(session_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def append(session_id: str, role: str, content: str, model: str = "") -> None:
    data = load(session_id)
    if not data:
        return
    data["messages"].append({"role": role, "content": content,
                             "model": model, "ts": time.time()})
    data["updated"] = time.time()
    _path(session_id).write_text(json.dumps(data, ensure_ascii=False, indent=1))


def list_sessions(limit: int = 50) -> list[dict]:
    if not HIST_DIR.exists():
        return []
    items = []
    for p in HIST_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text())
            items.append({"id": d["id"], "title": d["title"], "model": d.get("model", ""),
                          "updated": d.get("updated", 0), "count": len(d.get("messages", []))})
        except Exception:
            continue
    items.sort(key=lambda x: x["updated"], reverse=True)
    return items[:limit]


def delete(session_id: str) -> bool:
    p = _path(session_id)
    if p.exists():
        p.unlink()
        return True
    return False
