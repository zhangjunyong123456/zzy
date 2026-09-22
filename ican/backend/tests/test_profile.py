"""用户画像注入测试：build_profile_text 单元 + chat 流集成。"""
import json

import pytest

from app.agents.profile import build_profile_text


pytestmark = pytest.mark.anyio


def test_build_profile_text_guest():
    assert build_profile_text(None) == ""


def test_build_profile_text_full():
    user = {
        "nickname": "小明",
        "major": "计算机",
        "grade": "大二",
        "interests": "篮球",
        "experience": "打过挑战杯",
        "goal": "考研",
    }
    text = build_profile_text(user)
    assert text.startswith("【用户画像】")
    for kw in ["小明", "计算机", "大二", "篮球", "挑战杯", "考研"]:
        assert kw in text


def test_build_profile_text_skips_empty_fields():
    user = {"nickname": "", "major": "计算机", "grade": "", "interests": "", "experience": "", "goal": ""}
    text = build_profile_text(user)
    assert "专业" in text
    assert "昵称" not in text and "年级" not in text


def test_build_profile_text_all_empty():
    user = {"nickname": "", "major": "", "grade": "", "interests": "", "experience": "", "goal": ""}
    assert build_profile_text(user) == ""


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


async def _capture_llm(fake_llm, monkeypatch):
    """给 FakeLLM 换上可捕获 messages 的 astream。"""
    from tests.conftest import FakeChunk

    captured = []

    async def capturing_astream(messages):
        captured.append(messages)
        for piece in ["你好，", "我是UniGrow主Agent。"]:
            yield FakeChunk(piece)

    monkeypatch.setattr(fake_llm, "astream", capturing_astream)
    return captured


async def test_chat_with_profile_injects_system_message(client, fake_llm, monkeypatch):
    captured = await _capture_llm(fake_llm, monkeypatch)

    reg = await client.post(
        "/api/auth/register",
        json={"username": "profiled", "password": "pass123456", "nickname": "小明"},
    )
    token = reg.json()["token"]
    await client.patch(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"major": "计算机", "grade": "大二", "goal": "考研"},
    )

    resp = await client.post(
        "/api/chat/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "帮我规划这学期"},
    )
    assert resp.status_code == 200
    assert captured, "worker 应调用过 LLM"
    system_contents = [str(m.content) for m in captured[0] if m.type == "system"]
    assert any("【用户画像】" in c and "计算机" in c and "考研" in c for c in system_contents)


async def test_chat_without_profile_has_no_profile_block(client, fake_llm, monkeypatch):
    captured = await _capture_llm(fake_llm, monkeypatch)

    resp = await client.post("/api/chat/stream", json={"message": "帮我规划这学期"})
    assert resp.status_code == 200
    assert captured
    system_contents = [str(m.content) for m in captured[0] if m.type == "system"]
    assert all("【用户画像】" not in c for c in system_contents)
