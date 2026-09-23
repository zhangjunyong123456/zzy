"""个人中心统计服务：纯 SQL 聚合。消息无 user_id，一律 JOIN sessions 做归属过滤。"""
from datetime import date, datetime, timedelta

from app.database import get_conn
from app.services import session_service

AGENTS = ("study", "research", "competition", "career", "campus", "main")


def get_user_stats(user: dict) -> dict:
    uid = user["id"]
    with get_conn() as conn:
        totals_row = conn.execute(
            """
            SELECT
              SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) AS question_count,
              SUM(CASE WHEN m.role = 'agent' THEN 1 ELSE 0 END) AS reply_count,
              COUNT(DISTINCT CASE WHEN m.role = 'user'
                    AND date(m.created_at, 'localtime') >= date(?)
                    THEN date(m.created_at, 'localtime') END) AS active_days
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = ?
            """,
            (user["created_at"], uid),
        ).fetchone()
        session_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ?", (uid,)
        ).fetchone()["c"]
        agent_rows = conn.execute(
            """
            SELECT m.agent AS agent, COUNT(*) AS count
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = ? AND m.role = 'agent' AND m.agent IS NOT NULL
            GROUP BY m.agent
            """,
            (uid,),
        ).fetchall()
        # 边界放宽到 -14 天：UTC 深夜消息的本地日期可能 +1 天，多出的行由下方字典按本地日期过滤
        daily_rows = conn.execute(
            """
            SELECT date(m.created_at, 'localtime') AS date, COUNT(*) AS count
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE s.user_id = ?
              AND m.created_at >= date('now', 'localtime', '-14 days')
              AND m.created_at >= ?
            GROUP BY date
            """,
            (uid, user["created_at"]),
        ).fetchall()

    by_agent = {r["agent"]: r["count"] for r in agent_rows}
    agent_usage = [{"agent": a, "count": by_agent.get(a, 0)} for a in AGENTS]

    today = datetime.now().astimezone().date()
    by_date = {r["date"]: r["count"] for r in daily_rows}
    daily = [
        {
            "date": (today - timedelta(days=13 - i)).isoformat(),
            "count": by_date.get((today - timedelta(days=13 - i)).isoformat(), 0),
        }
        for i in range(14)
    ]

    reg_date = date.fromisoformat(user["created_at"][:10])
    days_since = max(1, (today - reg_date).days + 1)

    return {
        "member_since": user["created_at"],
        "totals": {
            "session_count": session_count,
            "question_count": totals_row["question_count"] or 0,
            "reply_count": totals_row["reply_count"] or 0,
            "active_days": min(totals_row["active_days"] or 0, days_since),
            "days_since_register": days_since,
        },
        "agent_usage": agent_usage,
        "daily": daily,
        "recent_sessions": session_service.list_sessions(user_id=uid)[:5],
    }
