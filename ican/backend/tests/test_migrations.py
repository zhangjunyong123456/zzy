"""老库幂等迁移测试：无新列/新表的老库经 init_db 后补齐且旧数据可查。"""
import sqlite3

import pytest

from app.config import settings
from app.database import get_conn, init_db


_OLD_SCHEMA = """
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    agent TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE TABLE documents (id TEXT PRIMARY KEY);
CREATE TABLE users (id TEXT PRIMARY KEY);
"""


@pytest.mark.anyio
async def test_old_db_migrates_idempotently(monkeypatch, tmp_path):
    old_db = tmp_path / "old.db"
    monkeypatch.setattr(settings, "sqlite_path", str(old_db))

    with sqlite3.connect(str(old_db)) as conn:
        conn.executescript(_OLD_SCHEMA)
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES ('s1', '旧会话', 't', 't')"
        )
        conn.execute(
            "INSERT INTO messages (id, session_id, role, agent, content, created_at) "
            "VALUES ('m1', 's1', 'user', NULL, '旧消息', 't')"
        )

    init_db()  # 第一次迁移
    init_db()  # 幂等：重复执行不报错

    with get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
        assert "attachments" in cols
        scols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        assert "user_id" in scols
        tables = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert {"attachments", "memories"} <= tables
        row = conn.execute("SELECT content FROM messages WHERE id='m1'").fetchone()
        assert row["content"] == "旧消息"
