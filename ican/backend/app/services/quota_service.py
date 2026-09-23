"""每日免费额度：未自带 Key 的用户使用服务器 Key 的真 AI 次数限制。

- 登录用户：每账号独立额度（quota_key = 'u:<uid>'）
- 游客：所有未登录请求共享一个池（quota_key = 'guest'），防匿名滥用
- 日期按 settings.quota_utc_offset（默认 UTC+8）每日归零
- 消费用 UPSERT 原子累加，本地 SQLite 与 Turso 云库均支持
"""
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import get_conn


def _day() -> str:
    tz = timezone(timedelta(hours=settings.quota_utc_offset))
    return datetime.now(tz).strftime("%Y-%m-%d")


def quota_key(uid: str | None) -> str:
    return f"u:{uid}" if uid else "guest"


def get_used(uid: str | None) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT used FROM usage_daily WHERE quota_key = ? AND day = ?",
            (quota_key(uid), _day()),
        ).fetchone()
        return int(row["used"]) if row else 0


def consume(uid: str | None, n: int = 1) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO usage_daily (quota_key, day, used) VALUES (?, ?, ?)
            ON CONFLICT(quota_key, day) DO UPDATE SET used = used + ?
            """,
            (quota_key(uid), _day(), n, n),
        )


def remaining(uid: str | None) -> int | None:
    """剩余次数；额度关闭（<=0）返回 None 表示不限。"""
    limit = settings.daily_free_quota
    if limit <= 0:
        return None
    return max(0, limit - get_used(uid))
