"""SQLite 持久化：会话 / 消息 / 文档元数据。WAL 模式，每调用开独立连接。"""
import sqlite3
from pathlib import Path

from app.config import settings

# Turso 共享连接（无状态、线程安全，进程内只建一次）
_turso_conn = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,             -- user / agent / summary
    agent TEXT,                     -- study/research/competition/career/campus/main
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    scene TEXT NOT NULL,            -- study / research / campus
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / ready / failed
    pages INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    builtin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL DEFAULT '',
    major TEXT NOT NULL DEFAULT '',
    grade TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT '',
    experience TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    user_id TEXT,                   -- 鉴权主体（NULL=游客）
    session_id TEXT,                -- 发送消息时绑定；上传时可为 NULL（暂存）
    message_id TEXT,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    kind TEXT NOT NULL,             -- image / file
    path TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    extracted_text TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attachments_session ON attachments(session_id);
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT,                   -- NULL=游客记忆，与 sessions 同模式
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_session_id TEXT,
    source_message_ids TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL             -- 简单 KV：目前存 secret_key（云库模式下密钥跨重启持久）
);
CREATE TABLE IF NOT EXISTS usage_daily (
    quota_key TEXT NOT NULL,        -- 'u:<uid>' 登录用户独立额度；'guest' 游客共享池
    day TEXT NOT NULL,              -- 归零日期 YYYY-MM-DD（按 quota_utc_offset）
    used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (quota_key, day)
);
"""


def get_conn():
    """配置了 TURSO_DATABASE_URL 时返回云库连接（共享无状态实例，线程安全）；
    否则返回本地 SQLite 文件连接（WAL 模式，每调用开独立连接）。"""
    if settings.turso_database_url:
        global _turso_conn
        if _turso_conn is None:
            from app.turso_client import connect

            _turso_conn = connect(
                settings.turso_database_url, settings.turso_auth_token
            )
        return _turso_conn
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
        # 幂等迁移：老库的 sessions 表补 user_id 列（NULL=游客会话）
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        # 幂等迁移：老库的 messages 表补 attachments 列（JSON 数组字符串，NULL=无附件）
        mcols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "attachments" not in mcols:
            conn.execute("ALTER TABLE messages ADD COLUMN attachments TEXT")
        # 幂等迁移：老库的 sessions 表补 category 列（NULL=综合，前端场景方向写入）
        if "category" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN category TEXT")
