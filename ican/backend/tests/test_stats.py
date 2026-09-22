"""个人中心统计接口测试：空数据 / 聊天计入 / 游客隔离 / 鉴权。"""
from datetime import date

import pytest

from app.services import session_service

pytestmark = pytest.mark.anyio


async def test_stats_requires_auth(client):
    resp = await client.get("/api/auth/me/stats")
    assert resp.status_code == 401


async def test_stats_new_user_empty(client):
    reg = await client.post(
        "/api/auth/register", json={"username": "statnew", "password": "pass123456"}
    )
    token = reg.json()["token"]
    resp = await client.get("/api/auth/me/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["totals"]["session_count"] == 0
    assert data["totals"]["question_count"] == 0
    assert data["totals"]["reply_count"] == 0
    assert data["totals"]["active_days"] == 0
    # UTC/本地日期最多差 1 天
    assert data["totals"]["days_since_register"] in (1, 2)

    assert len(data["agent_usage"]) == 6
    assert all(item["count"] == 0 for item in data["agent_usage"])
    assert {item["agent"] for item in data["agent_usage"]} == {
        "study", "research", "competition", "career", "campus", "main",
    }

    assert len(data["daily"]) == 14
    assert all(item["count"] == 0 for item in data["daily"])

    assert data["recent_sessions"] == []
    assert data["member_since"] == reg.json()["user"]["created_at"]


async def test_stats_counts_chat_messages(client, fake_llm):
    reg = await client.post(
        "/api/auth/register", json={"username": "statchat", "password": "pass123456"}
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/chat/stream", headers=headers, json={"message": "帮我规划这学期"}
    )
    assert resp.status_code == 200

    data = (await client.get("/api/auth/me/stats", headers=headers)).json()
    assert data["totals"]["session_count"] == 1
    assert data["totals"]["question_count"] == 1
    assert data["totals"]["reply_count"] == 1  # single 复杂度无 summary 消息
    assert data["totals"]["active_days"] == 1

    usage = {item["agent"]: item["count"] for item in data["agent_usage"]}
    assert usage["main"] == 1
    assert sum(usage.values()) == 1

    today = date.today().isoformat()
    today_item = next(item for item in data["daily"] if item["date"] == today)
    assert today_item["count"] == 2

    assert len(data["recent_sessions"]) == 1
    assert data["recent_sessions"][0]["message_count"] == 2
    assert data["recent_sessions"][0]["title"].startswith("帮我规划")


async def test_stats_excludes_guest_data(client, fake_llm):
    reg = await client.post(
        "/api/auth/register", json={"username": "statiso", "password": "pass123456"}
    )
    token = reg.json()["token"]

    # 游客会话 + 消息（user_id=NULL），不应计入任何用户统计
    sid = session_service.create_session(user_id=None)
    session_service.add_message(sid, "user", None, "游客提问")
    session_service.add_message(sid, "agent", "study", "游客回答")

    data = (
        await client.get(
            "/api/auth/me/stats", headers={"Authorization": f"Bearer {token}"}
        )
    ).json()
    assert data["totals"]["session_count"] == 0
    assert data["totals"]["question_count"] == 0
    assert data["totals"]["reply_count"] == 0
