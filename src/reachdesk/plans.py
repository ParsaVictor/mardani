"""Commercial tiers and owner-signed license keys.

Keys are Ed25519-signed, so the app verifies them with a public key while only the
owner can issue them. The implementation follows the RFC 8032 reference and is pure
Python to keep the zero-dependency promise.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import date
from functools import lru_cache

PLANS = {
    "free": {"label": "Free", "campaigns": 1, "items": 200, "daily_cap": 10, "auto_email": False, "job_sources": False, "export": False},
    "pro": {"label": "Pro", "campaigns": 5, "items": 5000, "daily_cap": 50, "auto_email": True, "job_sources": True, "export": True},
    "agency": {"label": "Agency", "campaigns": 50, "items": 100000, "daily_cap": 100, "auto_email": True, "job_sources": True, "export": True},
    "owner": {"label": "Owner", "campaigns": 100000, "items": 10000000, "daily_cap": 200, "auto_email": True, "job_sources": True, "export": True},
}
# Public half of the owner's signing key; set REACHDESK_LICENSE_PUBKEY to override.
OWNER_PUBLIC_KEY = "12b88d5e5950c16f68afd989c7d5b4d64837f40c00d831602ae10f4bbe66f65e"

# ------------------------------------------------------------------- Ed25519
_p = 2**255 - 19
_q = 2**252 + 27742317777372353535851937790883648493
_d = -121665 * pow(121666, _p - 2, _p) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p) % _p
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p:
        x = x * _I % _p
    return _p - x if x % 2 else x


_By = 4 * pow(5, _p - 2, _p) % _p
_B = (_xrecover(_By), _By, 1, _xrecover(_By) * _By % _p)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(P, e: int):
    Q = (0, 1, 1, 0)
    while e:
        if e & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        e >>= 1
    return Q


def _encode(P) -> bytes:
    zi = pow(P[2], _p - 2, _p)
    x, y = P[0] * zi % _p, P[1] * zi % _p
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decode(s: bytes):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _p:
        raise ValueError("bad point")
    x = _xrecover(y)
    if x & 1 != sign:
        x = _p - x
    if (-x * x + y * y - 1 - _d * x * x * y * y) % _p:
        raise ValueError("not on curve")
    return (x, y, 1, x * y % _p)


def _expand(secret: bytes) -> tuple[int, bytes]:
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    return _encode(_mul(_B, _expand(secret)[0]))


def sign(secret: bytes, message: bytes) -> bytes:
    a, prefix = _expand(secret)
    A = _encode(_mul(_B, a))
    r = int.from_bytes(_sha512(prefix + message), "little") % _q
    R = _encode(_mul(_B, r))
    k = int.from_bytes(_sha512(R + A + message), "little") % _q
    return R + ((r + k * a) % _q).to_bytes(32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    try:
        if len(signature) != 64 or len(public) != 32:
            return False
        s = int.from_bytes(signature[32:], "little")
        if s >= _q:
            return False
        A = _decode(public)
        R = _decode(signature[:32])
    except ValueError:
        return False
    k = int.from_bytes(_sha512(signature[:32] + public + message), "little") % _q
    return _encode(_mul(_B, s)) == _encode(_add(R, _mul(A, k)))


# ------------------------------------------------------------------ licenses
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_license(secret: bytes, plan: str, customer: str, expires: str = "") -> str:
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan}")
    payload = json.dumps({"plan": plan, "customer": customer, "expires": expires}, sort_keys=True).encode()
    return f"RD1.{_b64(payload)}.{_b64(sign(secret, payload))}"


@lru_cache(maxsize=32)
def _verified_payload(token: str, public_hex: str) -> str | None:
    """Pure-Python signature checks are slow, and the plan is read on most operations."""
    try:
        tag, body, sig = token.strip().split(".")
        if tag != "RD1" or not public_hex:
            return None
        payload = _unb64(body)
        return payload.decode() if verify(bytes.fromhex(public_hex), payload, _unb64(sig)) else None
    except (ValueError, TypeError):
        return None


def read_license(token: str, public_hex: str | None = None, today: date | None = None) -> dict | None:
    """Return the payload of a valid, unexpired key, else None."""
    public_hex = public_hex or os.environ.get("REACHDESK_LICENSE_PUBKEY") or OWNER_PUBLIC_KEY
    payload = _verified_payload(token or "", public_hex)
    if payload is None:
        return None
    try:
        data = json.loads(payload)
        if data.get("plan") not in PLANS:
            return None
        if data.get("expires") and date.fromisoformat(data["expires"]) < (today or date.today()):
            return None
        return data
    except (ValueError, TypeError):
        return None


def current_plan(token: str | None) -> dict:
    data = read_license(token) if token else None
    name = data["plan"] if data else "free"
    return {"name": name, "customer": (data or {}).get("customer", ""), "expires": (data or {}).get("expires", ""), **PLANS[name]}
