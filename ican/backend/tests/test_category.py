"""会话场景分类测试：首次发消息写入方向分类，非法值与后续消息不覆盖。"""
import pytest

from tests.test_sse_contract import parse_sse


pytestmark = pytest.mark.anyio


async def _latest_session(client):
    return (await client.get("/api/sessions")).json()[0]


async def _chat(client, **payload):
    resp = await client.post("/api/chat/stream", json={"message": "hi", **payload})
    assert resp.status_code == 200
    return parse_sse(resp.text)[0][1]["session_id"]


async def test_category_written_on_first_send(client, fake_llm):
    sid = await _chat(client, message="帮我制定复习计划", category="study")
    rows = {s["id"]: s for s in (await client.get("/api/sessions")).json()}
    assert rows[sid]["category"] == "study"


async def test_category_not_overwritten(client, fake_llm):
    sid = await _chat(client, message="q1", category="career")
    await _chat(client, message="q2", category="study", session_id=sid)
    rows = {s["id"]: s for s in (await client.get("/api/sessions")).json()}
    assert rows[sid]["category"] == "career"


async def test_invalid_category_ignored(client, fake_llm):
    sid = await _chat(client, message="q", category="hack")
    rows = {s["id"]: s for s in (await client.get("/api/sessions")).json()}
    assert rows[sid]["category"] == "general"
