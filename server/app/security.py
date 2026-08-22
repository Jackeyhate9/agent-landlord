import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Header, HTTPException, status

from .config import get_settings


def sign_token(subject: str, kind: str, ttl_seconds: int = 86_400) -> str:
    payload = {"sub": subject, "kind": kind, "exp": int(time.time()) + ttl_seconds}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(get_settings().session_secret.encode(), body, hashlib.sha256).digest()
    return f"{body.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def verify_token(token: str, expected_kind: str) -> dict[str, Any]:
    try:
        body_text, signature_text = token.split(".", 1)
        body = body_text.encode()
        padded = signature_text + "=" * (-len(signature_text) % 4)
        actual = base64.urlsafe_b64decode(padded)
        expected = hmac.new(get_settings().session_secret.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(actual, expected):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
        if payload.get("kind") != expected_kind or payload.get("exp", 0) < time.time():
            raise ValueError("expired or wrong kind")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session token") from exc


def bearer(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization[7:]


def require_agent(token: str = Header(alias="Authorization", default="")) -> str:
    raw = token[7:] if token.startswith("Bearer ") else ""
    return str(verify_token(raw, "agent")["sub"])


def require_admin(token: str = Header(alias="Authorization", default="")) -> str:
    raw = token[7:] if token.startswith("Bearer ") else ""
    return str(verify_token(raw, "admin")["sub"])


def opaque_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12)}"

