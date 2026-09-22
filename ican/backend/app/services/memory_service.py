"""记忆持久化服务：从历史会话勾选消息保存为可复用的「记忆」。"""
import json
import uuid
from datetime import datetime, timezone

from app.database import get_conn

MAX_CONTENT = 8000   # 单条记忆内容上限
MAX_INJECT = 4000    # 注入 prompt 的记忆总长上限


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _owned(row, uid: str | None) -> bool:
    """归属判定：游客(uid=None)只能看 user_id IS NULL 的记忆，登录用户只看本人。"""
    return (row["user_id"] or None) == (uid or None)


def create_memory(
    user_id: str | None, title: str, source_session_id: str, message_ids: list[str]
) -> dict | None:
    """按消息 id 取内容渲染成对话文本；会话归属由调用方校验。"""
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in message_ids)
        rows = conn.execute(
            f"SELECT role, content FROM messages "
            f"WHERE session_id = ? AND id IN ({placeholders}) ORDER BY created_at, rowid",
            (source_session_id, *message_ids),
        ).fetchall()
    if not rows:
        return None
    lines = [
        f"用户：{r['content']}" if r["role"] == "user" else f"助手：{r['content']}"
        for r in rows
    ]
    content = "\n".join(lines)
    if len(content) > MAX_CONTENT:
        content = content[:MAX_CONTENT] + "\n（已截断）"
    mid = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO memories (id, user_id, title, content, source_session_id, "
            "source_message_ids, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                mid, user_id, title, content, source_session_id,
                json.dumps(message_ids, ensure_ascii=False), _now(),
            ),
        )
    return get_memory(mid)


def get_memory(memory_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return dict(row) if row else None


def list_memories(user_id: str | None) -> list[dict]:
    where, args = ("user_id IS NULL", ()) if user_id is None else ("user_id = ?", (user_id,))
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT id, title, content, source_session_id, created_at "
            f"FROM memories WHERE {where} ORDER BY created_at DESC",
            args,
        ).fetchall()
    return [dict(r) for r in rows]


def rename_memory(memory_id: str, uid: str | None, title: str) -> dict | None:
    mem = get_memory(memory_id)
    if not mem or not _owned(mem, uid):
        return None
    with get_conn() as conn:
        conn.execute("UPDATE memories SET title = ? WHERE id = ?", (title, memory_id))
    return get_memory(memory_id)


def delete_memory(memory_id: str, uid: str | None) -> bool:
    mem = get_memory(memory_id)
    if not mem or not _owned(mem, uid):
        return False
    with get_conn() as conn:
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    return True


def build_memory_text(memory_ids: list[str], uid: str | None) -> str:
    """把已启用且归属合法的记忆拼成注入文本；越权/不存在的 id 静默忽略。"""
    blocks: list[str] = []
    total = 0
    for mid in memory_ids:
        mem = get_memory(mid)
        if not mem or not _owned(mem, uid):
            continue
        block = f"「{mem['title']}」\n{mem['content']}"
        if total + len(block) > MAX_INJECT:
            remain = MAX_INJECT - total
            if remain > 50:
                blocks.append(block[:remain] + "（已截断）")
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)
