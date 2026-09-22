"""记忆系统测试：CRUD、用户隔离、内容渲染与截断。"""
import uuid

import pytest

from app.services import memory_service, session_service


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


def _seed_session(msgs, user_id=None):
    """直接建会话并写入消息，返回 (session_id, message_ids)。"""
    sid = session_service.create_session(user_id=user_id)
    ids = [session_service.add_message(sid, role, None, content) for role, content in msgs]
    return sid, ids


async def test_memory_crud_and_render(client):
    sid, ids = _seed_session(
        [("user", "投了 20 家只进 3 家面试"), ("agent", "建议把项目描述按 STAR 重写")]
    )
    resp = await client.post(
        "/api/memories",
        json={"title": "秋招复盘", "source_session_id": sid, "message_ids": ids},
    )
    assert resp.status_code == 200
    mem = resp.json()
    assert mem["title"] == "秋招复盘"
    assert "用户：投了 20 家只进 3 家面试" in mem["content"]
    assert "助手：建议把项目描述按 STAR 重写" in mem["content"]

    listed = (await client.get("/api/memories")).json()
    assert mem["id"] in [m["id"] for m in listed]

    renamed = await client.put(f"/api/memories/{mem['id']}", json={"title": "春招复盘"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "春招复盘"

    deleted = await client.delete(f"/api/memories/{mem['id']}")
    assert deleted.status_code == 200
    assert mem["id"] not in [m["id"] for m in (await client.get("/api/memories")).json()]


async def test_memory_session_owner_check(client):
    owner = await _register(client, _uname())
    other = await _register(client, _uname())
    sid, ids = _seed_session([("user", "hi")], user_id=owner["user"]["id"])

    # 非归属者保存该会话记忆 → 404
    resp = await client.post(
        "/api/memories",
        headers=_auth(other["token"]),
        json={"source_session_id": sid, "message_ids": ids},
    )
    assert resp.status_code == 404

    # 归属者可保存
    resp = await client.post(
        "/api/memories",
        headers=_auth(owner["token"]),
        json={"source_session_id": sid, "message_ids": ids},
    )
    assert resp.status_code == 200


async def test_memory_cross_user_isolated(client):
    owner = await _register(client, _uname())
    other = await _register(client, _uname())
    sid, ids = _seed_session([("user", "秘密内容")], user_id=owner["user"]["id"])
    mem = (
        await client.post(
            "/api/memories",
            headers=_auth(owner["token"]),
            json={"source_session_id": sid, "message_ids": ids},
        )
    ).json()

    # 他人列表看不到 / 改名删除 404
    assert (await client.get("/api/memories", headers=_auth(other["token"]))).json() == []
    assert (
        await client.put(f"/api/memories/{mem['id']}", headers=_auth(other["token"]),
                         json={"title": "hack"})
    ).status_code == 404
    assert (
        await client.delete(f"/api/memories/{mem['id']}", headers=_auth(other["token"]))
    ).status_code == 404
    # 归属者正常删除
    assert (
        await client.delete(f"/api/memories/{mem['id']}", headers=_auth(owner["token"]))
    ).status_code == 200


async def test_memory_truncated_and_bad_ids(client):
    long_text = "长" * 9000
    sid, ids = _seed_session([("user", long_text)])
    resp = await client.post(
        "/api/memories",
        json={"source_session_id": sid, "message_ids": ids},
    )
    assert resp.status_code == 200
    assert resp.json()["content"].endswith("（已截断）")

    # 不存在的消息 id → 400；默认标题兜底
    resp2 = await client.post(
        "/api/memories",
        json={"source_session_id": sid, "message_ids": ["nonexistent"]},
    )
    assert resp2.status_code == 400

    # 会话不存在 → 404
    resp3 = await client.post(
        "/api/memories",
        json={"source_session_id": "nope", "message_ids": ["x"]},
    )
    assert resp3.status_code == 404


async def test_build_memory_text_ownership():
    sid, ids = _seed_session([("user", "游客内容")])
    mem = memory_service.create_memory(None, "游客记忆", sid, ids)
    assert "「游客记忆」" in memory_service.build_memory_text([mem["id"]], None)
    # 登录用户拿不到游客记忆
    assert memory_service.build_memory_text([mem["id"]], "someone") == ""
