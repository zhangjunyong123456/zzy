"""安全基础：PBKDF2 密码哈希 + HMAC 签名 Token（零第三方依赖）。"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from app.config import settings

_PBKDF2_ITER = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), _PBKDF2_ITER)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), _PBKDF2_ITER)
    return hmac.compare_digest(dk.hex(), expected)


def _load_secret() -> bytes:
    if settings.secret_key.strip():
        return settings.secret_key.strip().encode()
    path = Path(settings.secret_file)
    if path.exists():
        return path.read_bytes().strip() or _generate_secret(path)
    return _generate_secret(path)


def _generate_secret(path: Path) -> bytes:
    secret = secrets.token_hex(32).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret)
    return secret


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _from_b64url(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_token(uid: str) -> str:
    payload = {"uid": uid, "exp": int(time.time()) + settings.token_expire_days * 86400}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_load_secret(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def decode_token(token: str) -> dict | None:
    """验签+验过期；任何异常返回 None，绝不抛出。"""
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(_load_secret(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _from_b64url(sig)):
            return None
        payload = json.loads(_from_b64url(body))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except Exception:
        return None
