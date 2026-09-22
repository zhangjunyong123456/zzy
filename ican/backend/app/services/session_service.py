"""会话/消息持久化服务。"""
import json
import uuid
from datetime import datetime, timezone

from app.database import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_session(title: str = "新对话", user_id: str | None = None) -> str:
    sid = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at, user_id) VALUES (?, ?, ?, ?, ?)",
            (sid, title, _now(), _now(), user_id),
        )
    return sid


def list_sessions(user_id: str | None = None) -> list[dict]:
    """user_id=None → 游客：只看 user_id IS NULL 的会话；否则只看本人会话。"""
    where, args = ("s.user_id IS NULL", ()) if user_id is None else ("s.user_id = ?", (user_id,))
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT s.id, s.title, s.user_id, s.category, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
            FROM sessions s WHERE {where} ORDER BY s.updated_at DESC
            """,
            args,
        ).fetchall()
    return [{**dict(r), "category": r["category"] or "general"} for r in rows]


def set_category_if_unset(session_id: str, category: str) -> None:
    """首次进入场景方向时写入分类；已有分类不覆盖。"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET category = ? WHERE id = ? AND category IS NULL",
            (category, session_id),
        )


def get_session_row(session_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, user_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None


def rename_session(session_id: str, title: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), session_id),
        )


def delete_session(session_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def touch_session(session_id: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))


def set_title_if_default(session_id: str, first_message: str) -> None:
    title = first_message.strip().replace("\n", " ")[:30] or "新对话"
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ? AND title = '新对话'",
            (title, session_id),
        )


def add_message(session_id: str, role: str, agent: str | None, content: str) -> str:
    mid = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, agent, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mid, session_id, role, agent, content, _now()),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))
    return mid


def get_messages(session_id: str, limit: int | None = None) -> list[dict]:
    sql = (
        "SELECT id, role, agent, content, attachments, created_at "
        "FROM messages WHERE session_id = ? ORDER BY created_at, rowid"
    )
    with get_conn() as conn:
        rows = conn.execute(sql, (session_id,)).fetchall()
    msgs = [dict(r) for r in rows]
    if limit is not None:
        msgs = msgs[-limit:]
    for m in msgs:
        raw = m.pop("attachments", None)
        try:
            m["attachments"] = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            m["attachments"] = []
    return msgs
