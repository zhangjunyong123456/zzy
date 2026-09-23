"""每日免费额度测试：无 Key 用户限量用服务器 Key，游客共享池，用尽降级演示。"""
import json

import pytest

from app.config import settings
from app.services import quota_service

pytestmark = pytest.mark.anyio


def _sse_events(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.split("\n\n"):
        event, data_lines = "message", []
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            try:
                events.append((event, json.loads("\n".join(data_lines))))
            except Exception:
                pass
    return events


@pytest.fixture(autouse=True)
def clean_quota(monkeypatch):
    """每个用例独立额度环境：清表 + 固定限额，避免共享 tmp 库串数据。"""
    monkeypatch.setattr(settings, "daily_free_quota", 2)
    from app.database import get_conn, init_db

    init_db()  # 幂等：夹具可能先于 client 夹具执行，确保表已建
    with get_conn() as conn:
        conn.execute("DELETE FROM usage_daily")
    yield


async def test_no_key_user_under_quota_gets_real_reply(client, fake_llm):
    """服务端有 Key + 用户无 Key + 额度未超 → 真 AI 流，额度 +1。"""
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    assert resp.status_code == 200
    names = [e for e, _ in _sse_events(resp.text)]
    assert "route_plan" in names  # 走了正式流（fake_llm 路由）
    assert "notice" not in names
    assert quota_service.get_used(None) == 1  # 游客池


async def test_quota_exhausted_falls_back_to_demo(client, fake_llm):
    """额度用尽 → 后续请求降级演示模式，notice 提示额度与恢复方式。"""
    for _ in range(2):  # limit=2，前两条走真流
        resp = await client.post("/api/chat/stream", json={"message": "你好"})
        assert "route_plan" in [e for e, _ in _sse_events(resp.text)]

    resp = await client.post("/api/chat/stream", json={"message": "再来一条"})
    events = _sse_events(resp.text)
    names = [e for e, _ in events]
    assert "route_plan" not in names  # 已降级演示
    notice = next(d for e, d in events if e == "notice")
    assert "免费额度已用完" in notice["message"]
    assert "演示模式" in notice["message"]
    assert quota_service.get_used(None) == 2  # 演示回复不再扣额度


async def test_user_key_bypasses_quota(client, fake_llm, monkeypatch):
    """自带 Key 的用户不占免费额度（服务端 Key 零消耗）。"""
    for _ in range(3):  # 超过 limit=2 也不限
        resp = await client.post(
            "/api/chat/stream",
            json={"message": "你好"},
            headers={"X-LLM-Provider": "deepseek", "X-LLM-Key": "sk-user"},
        )
        assert "route_plan" in [e for e, _ in _sse_events(resp.text)]
    assert quota_service.get_used(None) == 0
    assert quota_service.get_used("some-uid") == 0


async def test_guests_share_one_pool(client, fake_llm):
    """游客（未登录）所有请求共享 'guest' 池，不按 IP/会话拆分。"""
    for _ in range(2):
        await client.post("/api/chat/stream", json={"message": "你好"})
    assert quota_service.get_used(None) == 2
    resp = await client.post("/api/chat/stream", json={"message": "再来"})
    assert "route_plan" not in [e for e, _ in _sse_events(resp.text)]  # 池空 → 演示


async def test_logged_user_quota_isolated(client, fake_llm):
    """登录用户独立额度，与游客池互不影响。"""
    reg = await client.post(
        "/api/auth/register",
        json={"username": "quotauser1", "password": "pass123456", "nickname": "额户"},
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/chat/quota", headers=headers)).json()["remaining"] == 2
    await client.post("/api/chat/stream", json={"message": "你好"}, headers=headers)
    data = (await client.get("/api/chat/quota", headers=headers)).json()
    assert data == {"limit": 2, "used": 1, "remaining": 1}
    # 游客池未被登录用户的消耗波及
    assert quota_service.get_used(None) == 0


async def test_quota_endpoint_hidden_when_user_key(client, fake_llm):
    """自带 Key 访问额度接口 → limit=null（前端不展示角标）。"""
    resp = await client.get(
        "/api/chat/quota",
        headers={"X-LLM-Provider": "deepseek", "X-LLM-Key": "sk-user"},
    )
    assert resp.json() == {"limit": None, "used": 0, "remaining": None}


async def test_quota_disabled_keeps_legacy_behavior(client, fake_llm, monkeypatch):
    """daily_free_quota=0（关闭）→ 无 Key 用户也不限次（旧行为）。"""
    monkeypatch.setattr(settings, "daily_free_quota", 0)
    for _ in range(3):
        resp = await client.post("/api/chat/stream", json={"message": "你好"})
        assert "route_plan" in [e for e, _ in _sse_events(resp.text)]


async def test_byok_only_still_blocks_server_key(client, monkeypatch):
    """独占模式优先于额度：无用户 Key 一律演示模式，不消耗服务器 Key 也不扣额度。"""
    monkeypatch.setattr(settings, "byok_only", True)
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    names = [e for e, _ in _sse_events(resp.text)]
    assert "notice" in names and "route_plan" not in names
    assert quota_service.get_used(None) == 0
