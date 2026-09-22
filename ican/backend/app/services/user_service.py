"""用户持久化服务：注册 / 登录 / 画像更新。"""
import re
import uuid
from datetime import datetime, timezone

from app.core.security import hash_password, verify_password
from app.database import get_conn

PROFILE_FIELDS = ("nickname", "major", "grade", "interests", "experience", "goal")

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5]{3,32}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_public(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    return d


def create_user(username: str, password: str, nickname: str = "") -> dict:
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise ValueError("用户名需为 3-32 位字母/数字/下划线/中文")
    if not (6 <= len(password) <= 64):
        raise ValueError("密码长度需为 6-64 位")
    uid = uuid.uuid4().hex
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, nickname, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (uid, username, hash_password(password), nickname.strip(), _now()),
            )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise ValueError("用户名已存在")
        raise
    return get_user_by_id(uid)


def _fetch(where: str, arg: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(f"SELECT * FROM users WHERE {where} = ?", (arg,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(uid: str) -> dict | None:
    user = _fetch("id", uid)
    return to_public(user) if user else None


def get_user_with_hash_by_username(username: str) -> dict | None:
    return _fetch("username", username)


def verify_login(username: str, password: str) -> dict | None:
    user = get_user_with_hash_by_username(username.strip())
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return to_public(user)


def update_profile(uid: str, fields: dict) -> dict | None:
    patch = {k: str(fields[k]).strip() for k in PROFILE_FIELDS if k in fields}
    if patch:
        sets = ", ".join(f"{k} = ?" for k in patch)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE users SET {sets} WHERE id = ?", (*patch.values(), uid)
            )
    return get_user_by_id(uid)
