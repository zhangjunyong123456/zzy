"""用户认证接口测试：注册 / 登录 / me / 画像更新。"""
import uuid

import pytest

from app.core.security import create_token


pytestmark = pytest.mark.anyio


async def _register(client, username=None, password="pass123456", nickname="小明"):
    username = username or f"user_{uuid.uuid4().hex[:10]}"
    resp = await client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "nickname": nickname},
    )
    return resp, username


async def test_register_success(client):
    resp, username = await _register(client)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["user"]["username"] == username
    assert data["user"]["nickname"] == "小明"
    assert "password_hash" not in data["user"]


async def test_register_duplicate_username(client):
    resp, username = await _register(client, nickname="另一个人")
    dup, _ = await _register(client, username=username)
    assert dup.status_code == 400


async def test_register_invalid_username(client):
    resp, _ = await _register(client, username="ab")
    assert resp.status_code == 400


async def test_login_success_and_wrong_password(client):
    _, username = await _register(client)
    ok = await client.post(
        "/api/auth/login", json={"username": username, "password": "pass123456"}
    )
    assert ok.status_code == 200
    assert ok.json()["token"]

    bad = await client.post(
        "/api/auth/login", json={"username": username, "password": "wrong-password"}
    )
    assert bad.status_code == 401


async def test_me_requires_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_with_token(client):
    reg, _ = await _register(client)
    token = reg.json()["token"]
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "小明"


async def test_me_with_tampered_token(client):
    token = create_token("someone")
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}x"}
    )
    assert resp.status_code == 401


async def test_update_profile(client):
    reg, _ = await _register(client)
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/auth/profile",
        headers=headers,
        json={
            "major": "计算机科学与技术",
            "grade": "大二",
            "interests": "篮球、摄影",
            "experience": "参加过挑战杯",
            "goal": "考研上岸",
        },
    )
    assert resp.status_code == 200
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["major"] == "计算机科学与技术"
    assert me.json()["goal"] == "考研上岸"
