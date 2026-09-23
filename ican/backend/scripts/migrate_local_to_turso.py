"""一次性迁移：本地 SQLite (data/ican.db) → Turso 云库。

幂等：全部用 INSERT OR IGNORE（按主键去重），可安全重复执行。
用法：cd backend 后  python scripts/migrate_local_to_turso.py
（本地直连 turso.io 被墙时需先设 HTTPS_PROXY=http://127.0.0.1:7897）
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.database import get_conn  # noqa: E402

LOCAL_DB = Path(settings.sqlite_path)
BATCH = 25
# 外键依赖顺序
TABLES = ["users", "sessions", "messages", "documents", "attachments", "memories"]


def main() -> None:
    assert settings.turso_database_url, "TURSO_DATABASE_URL 未配置"

    local = sqlite3.connect(str(LOCAL_DB))
    local.row_factory = sqlite3.Row

    cloud = get_conn()
    init_sql = "SELECT 1"
    cloud.execute(init_sql).fetchone()  # 连通性检查
    print(f"源库: {LOCAL_DB}  →  目标: {settings.turso_database_url}\n")

    for table in TABLES:
        cols = [r["name"] for r in local.execute(f"PRAGMA table_info({table})")]
        if not cols:
            print(f"{table:12} 本地无此表，跳过")
            continue
        rows = local.execute(
            f"SELECT {', '.join(cols)} FROM {table} ORDER BY rowid"
        ).fetchall()
        if not rows:
            print(f"{table:12} 0 行")
            continue

        sql = (
            f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})"
        )
        inserted = 0
        t0 = time.time()
        for i in range(0, len(rows), BATCH):
            stmts = [(sql, tuple(r)) for r in rows[i : i + BATCH]]
            cloud.execute_many(stmts)
            inserted += len(stmts)
        print(f"{table:12} {inserted:4} 行已写入 ({time.time() - t0:.1f}s)")

    print("\n=== 云库核对 ===")
    ok = True
    for table in TABLES:
        local_n = local.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cloud_n = cloud.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        mark = "OK " if cloud_n >= local_n else "!!! "
        if cloud_n < local_n:
            ok = False
        print(f"{mark}{table:10} 本地 {local_n:4}  云库 {cloud_n:4}")
    print("\n迁移完成 ✔" if ok else "\n有表数量不符，请检查！")
    local.close()


if __name__ == "__main__":
    if not os.environ.get("HTTPS_PROXY"):
        print("(提示：本地直连 turso.io 可能被墙，必要时先设 HTTPS_PROXY)")
    main()
