# -*- coding: utf-8 -*-
"""เชื่อมต่อบัญชี Rnai.io จาก CLI (Phase 3b)

`rnai login` = ล็อกอินด้วย email/password ตรงจาก Terminal แทนที่จะต้อง
เปิดเว็บไปหน้า Profile แล้วกดสร้าง API key เอง:
  1. ยิง email/password เข้า Firebase (signInWithPassword) ได้ idToken ชั่วคราว
  2. เอา idToken ไปขอ API key ถาวร (rnai_sk_...) จาก POST /api/keys ของ Rnai.io
  3. เก็บ key นั้นลง config เป็น RNAI_IO_API_KEY — ใช้ได้ทั้งเรียก skills (agent tools)
     และเช็คเครดิตคงเหลือ (credits() ด้านล่าง) โดยไม่ต้องแตะ idToken อีกเลย
"""
from __future__ import annotations
import socket
from typing import Optional

import httpx

from . import config

FIREBASE_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"

_ERROR_MESSAGES = {
    "EMAIL_NOT_FOUND": "ไม่พบอีเมลนี้ในระบบ Rnai.io",
    "INVALID_PASSWORD": "รหัสผ่านไม่ถูกต้อง",
    "INVALID_LOGIN_CREDENTIALS": "อีเมลหรือรหัสผ่านไม่ถูกต้อง",
    "USER_DISABLED": "บัญชีนี้ถูกระงับการใช้งาน",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "ลองผิดหลายครั้งเกินไป โปรดลองใหม่ภายหลัง",
}


class AuthError(Exception):
    """ล็อกอิน/เช็คเครดิตไม่สำเร็จ — message เป็นภาษาไทยพร้อมแสดงผู้ใช้ได้เลย"""


def _firebase_sign_in(email: str, password: str) -> str:
    key = config.get("FIREBASE_WEB_API_KEY")
    try:
        r = httpx.post(
            FIREBASE_SIGNIN_URL,
            params={"key": key},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=20,
        )
    except httpx.HTTPError as e:
        raise AuthError(f"ต่ออินเทอร์เน็ตไม่ได้: {e}") from e

    if r.status_code >= 400:
        try:
            code = r.json().get("error", {}).get("message", "LOGIN_FAILED")
        except Exception:
            code = "LOGIN_FAILED"
        raise AuthError(_ERROR_MESSAGES.get(code, code))
    return r.json()["idToken"]


def _mint_api_key(id_token: str) -> str:
    base = config.get("RNAI_IO_BASE")
    name = f"Rnai-CLI ({socket.gethostname()})"
    try:
        r = httpx.post(
            f"{base}/api/keys",
            headers={"Authorization": f"Bearer {id_token}"},
            json={"name": name},
            timeout=20,
        )
    except httpx.HTTPError as e:
        raise AuthError(f"ต่อ Rnai.io ไม่ได้: {e}") from e
    if r.status_code >= 400:
        raise AuthError(f"ขอ API key ไม่สำเร็จ (HTTP {r.status_code}): {r.text[:200]}")
    return r.json()["key"]


def login(email: str, password: str) -> str:
    """login เต็มขั้นตอน — คืน email เมื่อสำเร็จ, raise AuthError เมื่อไม่สำเร็จ"""
    id_token = _firebase_sign_in(email, password)
    api_key = _mint_api_key(id_token)
    config.set_value("RNAI_IO_API_KEY", api_key)
    config.set_value("RNAI_IO_EMAIL", email)
    return email


def logout() -> None:
    config.set_value("RNAI_IO_API_KEY", "")
    config.set_value("RNAI_IO_EMAIL", "")


def is_logged_in() -> bool:
    return bool(config.get("RNAI_IO_API_KEY"))


def credits() -> Optional[dict]:
    """เช็คเครดิตคงเหลือ — คืน None ถ้ายังไม่ login หรือเรียก Rnai.io ไม่สำเร็จ"""
    key = config.get("RNAI_IO_API_KEY")
    if not key:
        return None
    base = config.get("RNAI_IO_BASE")
    try:
        r = httpx.get(
            f"{base}/api/billing/me",
            headers={"Authorization": f"Bearer {key}"},
            timeout=15,
        )
        if r.status_code >= 400:
            return None
        data = r.json()
        data["total"] = data.get("freeCreditsRemaining", 0) + data.get("paidCreditsBalance", 0)
        return data
    except httpx.HTTPError:
        return None
