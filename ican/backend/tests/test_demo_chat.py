"""演示模式测试：无 API Key 时返回规则回复 + 接入提示，且正常持久化。"""
import json

import pytest

from app.services import session_service

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


def _strip_keys(monkeypatch, settings) -> None:
    """模拟无 Key 环境：has_api_key 检查任一供应商，须全部清空。"""
    for name in ("deepseek_api_key", "siliconflow_api_key", "zhipu_api_key"):
        monkeypatch.setattr(settings, name, "")


async def test_demo_mode_basic_chat(client, monkeypatch):
    from app.config import settings

    _strip_keys(monkeypatch, settings)

    resp = await client.post("/api/chat/stream", json={"message": "帮我复习高数"})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    names = [e for e, _ in events]

    # 事件协议完整：notice 提示 + agent 流 + done 收尾
    assert "notice" in names
    assert "agent_start" in names and "agent_end" in names
    assert names[-1] == "done"

    # 关键词命中学习方向，token 拼出完整回复
    start = next(d for e, d in events if e == "agent_start")
    assert start["agent"] == "study"
    tokens = "".join(d["content"] for e, d in events if e == "token" and d["agent"] == "study")
    assert "学习方向" in tokens

    # notice 携带接入提示
    notice = next(d for e, d in events if e == "notice")
    assert "演示模式" in notice["message"] and "API" in notice["message"]

    # 用户与 agent 消息均持久化（计入统计）
    sid = next(d["session_id"] for e, d in events if e == "message" and d.get("session_id"))
    msgs = session_service.get_messages(sid)
    assert [(m["role"], m["agent"]) for m in msgs] == [("user", None), ("agent", "study")]


async def test_demo_mode_default_main_agent(client, monkeypatch):
    from app.config import settings

    _strip_keys(monkeypatch, settings)

    resp = await client.post("/api/chat/stream", json={"message": "今天天气不错"})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    start = next(d for e, d in events if e == "agent_start")
    assert start["agent"] == "main"
    tokens = "".join(d["content"] for e, d in events if e == "token")
    assert "今天天气不错" in tokens[:120]  # 引用原问题


async def test_real_mode_unchanged_when_key_present(client, fake_llm):
    """配置了 Key 时仍走正式流（fake_llm），不产生 notice。"""
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    assert resp.status_code == 200
    names = [e for e, _ in _sse_events(resp.text)]
    assert "notice" not in names
    assert names[-1] == "done"
