"""会话按用户隔离测试：游客看游客会话，用户只看本人会话，跨用户 404。"""
import uuid

import pytest


pytestmark = pytest.mark.anyio


def _uname():
    return f"user_{uuid.uuid4().hex[:10]}"


async def _register(client, username):
    resp = await client.post(
        "/api/auth/register", json={"username": username, "password": "pass123456"}
    )
    assert resp.status_code == 200
    return resp.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_guest_and_user_sessions_isolated(client):
    guest_sid = (await client.post("/api/sessions")).json()["id"]
    u = await _register(client, _uname())
    user_sid = (await client.post("/api/sessions", headers=_auth(u["token"]))).json()["id"]

    guest_list = [s["id"] for s in (await client.get("/api/sessions")).json()]
    assert guest_sid in guest_list and user_sid not in guest_list

    user_list = [s["id"] for s in (await client.get("/api/sessions", headers=_auth(u["token"]))).json()]
    assert user_sid in user_list and guest_sid not in user_list


async def test_cross_user_session_access_denied(client):
    owner = await _register(client, _uname())
    other = await _register(client, _uname())
    sid = (await client.post("/api/sessions", headers=_auth(owner["token"]))).json()["id"]

    assert (await client.get(f"/api/sessions/{sid}", headers=_auth(other["token"]))).status_code == 404
    assert (
        await client.patch(
            f"/api/sessions/{sid}", headers=_auth(other["token"]), json={"title": "hack"}
        )
    ).status_code == 404
    assert (await client.delete(f"/api/sessions/{sid}", headers=_auth(other["token"]))).status_code == 404

    # 归属者可正常访问
    assert (await client.get(f"/api/sessions/{sid}", headers=_auth(owner["token"]))).status_code == 200


async def test_cross_user_chat_stream_denied(client):
    owner = await _register(client, _uname())
    other = await _register(client, _uname())
    sid = (await client.post("/api/sessions", headers=_auth(owner["token"]))).json()["id"]

    resp = await client.post(
        "/api/chat/stream", headers=_auth(other["token"]), json={"session_id": sid, "message": "hi"}
    )
    assert resp.status_code == 404


async def test_guest_can_still_chat(client, fake_llm):
    """游客对话回归：不带头也能走通。"""
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    assert resp.status_code == 200
    assert "session_id" in resp.text
