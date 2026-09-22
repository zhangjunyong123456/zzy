"""SSE 事件流契约测试：事件序列与 agent 归属字段。"""
import json

import pytest

from app.schemas import RouteDecision


def parse_sse(text: str):
    """把 SSE 文本解析为 [(event, data_dict)]。"""
    events = []
    for frame in text.split("\n\n"):
        ev, data = None, None
        for line in frame.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if ev and data:
            events.append((ev, json.loads(data)))
        elif data and not ev:
            # 无 event 名的 data 帧（如初始 session 通知）按 'message' 分发
            events.append(("message", json.loads(data)))
    return events


@pytest.mark.anyio
async def test_sse_event_sequence(client, fake_llm):
    """完整事件流：message(session) → route_plan → agent_start → token* → agent_end → done。"""
    resp = await client.post(
        "/api/chat/stream", json={"session_id": None, "message": "你好"}
    )
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    names = [e for e, _ in events]

    assert names[0] == "message"  # session 通知帧
    assert "route_plan" in names
    assert "agent_start" in names
    assert names.count("token") >= 1
    assert "agent_end" in names
    assert names[-1] == "done"

    # token 事件的 agent 字段必须合法
    for ev, data in events:
        if ev == "token":
            assert data["agent"] in {
                "study", "research", "competition", "career", "campus", "main"
            }
            assert isinstance(data["content"], str)
    # done 事件携带 session_id
    assert events[-1][1]["session_id"]


@pytest.mark.anyio
async def test_sse_single_route_skips_summary(client, fake_llm):
    """single 路由不出现 summary_* 事件。"""
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    events = parse_sse(resp.text)
    names = [e for e, _ in events]
    assert not any(n.startswith("summary") for n in names)


@pytest.mark.anyio
async def test_no_api_key_enters_demo_mode(client, monkeypatch):
    """未配置 Key 不再 503：进入演示模式，返回规则回复 + notice 引导接入。"""
    from app.config import settings

    for name in ("deepseek_api_key", "siliconflow_api_key", "zhipu_api_key"):
        monkeypatch.setattr(settings, name, "")
    resp = await client.post("/api/chat/stream", json={"message": "你好"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    names = [e for e, _ in events]
    assert "notice" in names
    assert names[-1] == "done"


@pytest.mark.anyio
async def test_multi_route_has_summary(client, fake_llm):
    """multi 路由：token 后出现 summary_*，且持久化 summary 消息。"""

    class FakeStructured:
        async def ainvoke(self, messages):
            return RouteDecision(
                agents=["competition", "campus"],
                complexity="multi",
                sub_queries={"competition": "q1", "campus": "q2"},
                plan_summary="两路并行",
            )

    fake_llm.with_structured_output = lambda schema, **kwargs: FakeStructured()

    resp = await client.post("/api/chat/stream", json={"message": "我要参赛还要查图书馆"})
    events = parse_sse(resp.text)
    names = [e for e, _ in events]
    route = next((d for e, d in events if e == "route_plan"), None)
    assert route is not None and [a["name"] for a in route["agents"]] == [
        "competition", "campus"
    ], f"route_plan={route}, events={names}"
    assert "summary_start" in names and "summary_end" in names
    sid = events[-1][1]["session_id"]

    hist = await client.get(f"/api/sessions/{sid}")
    roles = {m["role"] for m in hist.json()["messages"]}
    assert "summary" in roles and "agent" in roles and "user" in roles
