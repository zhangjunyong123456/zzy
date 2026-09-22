"""对话注入测试：附件与记忆进入 prompt，越权 id 被忽略。"""
import pytest
from langchain_core.messages import SystemMessage

from app.services import session_service


pytestmark = pytest.mark.anyio


def _msg_text(messages, cls):
    return "\n".join(m.content for m in messages if isinstance(m, cls))


async def test_memory_and_attachment_injected(client, fake_llm):
    # 准备历史会话与消息 → 存为记忆
    sid = session_service.create_session()
    m1 = session_service.add_message(sid, "user", None, "我在准备秋招")
    m2 = session_service.add_message(sid, "agent", "career", "把项目描述按 STAR 重写")
    mem = (
        await client.post(
            "/api/memories",
            json={"title": "秋招背景", "source_session_id": sid, "message_ids": [m1, m2]},
        )
    ).json()

    # 上传附件
    up = await client.post(
        "/api/chat/upload",
        files={"file": ("提纲.txt", "简历提纲第一版".encode("utf-8"), "text/plain")},
    )
    att = up.json()

    # 发消息：同时带记忆与附件
    resp = await client.post(
        "/api/chat/stream",
        json={
            "message": "帮我继续改简历",
            "memory_ids": [mem["id"]],
            "attachment_ids": [att["id"]],
        },
    )
    assert resp.status_code == 200

    captured = fake_llm.captured[-1]
    system_text = _msg_text(captured, SystemMessage)
    assert "【历史记忆】" in system_text
    assert "秋招背景" in system_text
    assert "把项目描述按 STAR 重写" in system_text

    human_texts = [m.content for m in captured if type(m).__name__ == "HumanMessage"]
    assert any("【附件内容】" in t and "简历提纲第一版" in t for t in human_texts)


async def test_cross_user_ids_ignored(client, fake_llm):
    # 用注册用户存一条记忆 + 上传一个附件
    import uuid

    uname = f"user_{uuid.uuid4().hex[:10]}"
    reg = await client.post(
        "/api/auth/register", json={"username": uname, "password": "pass123456"}
    )
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    sid = session_service.create_session(user_id=reg.json()["user"]["id"])
    mid = session_service.add_message(sid, "user", None, "他人内容")
    mem = (
        await client.post(
            "/api/memories",
            headers=headers,
            json={"source_session_id": sid, "message_ids": [mid]},
        )
    ).json()
    up = await client.post(
        "/api/chat/upload",
        headers=headers,
        files={"file": ("他人.txt", "他人附件".encode("utf-8"), "text/plain")},
    )
    att = up.json()

    # 游客携带越权 id 发消息 → 均被忽略
    resp = await client.post(
        "/api/chat/stream",
        json={"message": "hi", "memory_ids": [mem["id"]], "attachment_ids": [att["id"]]},
    )
    assert resp.status_code == 200
    captured = fake_llm.captured[-1]
    system_text = _msg_text(captured, SystemMessage)
    assert "【历史记忆】" not in system_text
    human_texts = [m.content for m in captured if type(m).__name__ == "HumanMessage"]
    assert not any("【附件内容】" in t for t in human_texts)


async def test_no_ids_no_injection(client, fake_llm):
    resp = await client.post("/api/chat/stream", json={"message": "hi"})
    assert resp.status_code == 200
    captured = fake_llm.captured[-1]
    assert "【历史记忆】" not in _msg_text(captured, SystemMessage)
