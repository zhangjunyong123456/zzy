"""BYOK 测试：用户自带 Key 请求头绑定、BYOK_ONLY 模式、非法供应商拒绝。"""
import json

import pytest

from app.agents import llm as llm_mod

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


@pytest.fixture
def llm_spy(monkeypatch):
    """捕获 _make_llm 入参，验证用户 Key / 全局 Key 的选择逻辑。"""
    real = llm_mod._make_llm
    captured = {}

    def spy(**kwargs):
        captured.update(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(llm_mod, "_make_llm", spy)
    return captured


async def test_user_key_overrides_global(client, llm_spy):
    """绑定用户 Key 后 get_llm 使用用户的供应商/Key；空模型名回落供应商默认。"""
    llm_mod.set_user_llm({"provider": "zhipu", "api_key": "1.a", "model": "", "base_url": ""})
    try:
        llm_mod.get_llm()
        assert llm_spy["api_key"] == "1.a"
        assert llm_spy["base_url"] == "https://open.bigmodel.cn/api/paas/v4"
        assert llm_spy["model"] == "glm-4.5-flash"  # 默认模型
    finally:
        llm_mod.set_user_llm(None)

    # 未绑定 → 回落全局（client 夹具注入的 deepseek test-key）
    llm_mod.get_llm()
    assert llm_spy["api_key"] == "test-key"


async def test_user_model_override(llm_spy):
    """用户显式指定模型名时优先于供应商默认。"""
    llm_mod.set_user_llm(
        {"provider": "deepseek", "api_key": "sk-u", "model": "glm-5.3", "base_url": ""}
    )
    try:
        llm_mod.get_llm()
        assert llm_spy["model"] == "glm-5.3"
    finally:
        llm_mod.set_user_llm(None)


async def test_byok_only_demo_without_header(client, monkeypatch):
    """BYOK 独占模式：服务端有 Key 但请求未带用户 Key → 演示模式。"""
    from app.config import settings

    monkeypatch.setattr(settings, "byok_only", True)
    resp = await client.post("/api/chat/stream", json={"message": "帮我复习高数"})
    assert resp.status_code == 200
    names = [e for e, _ in _sse_events(resp.text)]
    assert "notice" in names  # 演示模式提示
    assert names[-1] == "done"


async def test_byok_only_real_with_user_header(client, fake_llm, monkeypatch):
    """BYOK 独占模式：带用户 Key 请求头 → 走正式流，不出现演示提示。"""
    from app.config import settings

    monkeypatch.setattr(settings, "byok_only", True)
    resp = await client.post(
        "/api/chat/stream",
        json={"message": "你好"},
        headers={"X-LLM-Provider": "deepseek", "X-LLM-Key": "sk-user-key"},
    )
    assert resp.status_code == 200
    names = [e for e, _ in _sse_events(resp.text)]
    assert "notice" not in names
    assert names[-1] == "done"
    assert "agent_start" in names


async def test_user_header_works_without_byok_flag(client, fake_llm):
    """非独占模式：带用户 Key 也走正式流（本地开发兼容）。"""
    resp = await client.post(
        "/api/chat/stream",
        json={"message": "你好"},
        headers={"X-LLM-Provider": "zhipu", "X-LLM-Key": "1.a"},
    )
    assert resp.status_code == 200
    names = [e for e, _ in _sse_events(resp.text)]
    assert "notice" not in names
    assert names[-1] == "done"


async def test_bad_provider_header_rejected(client):
    """带了 Key 但供应商缺失/非法 → 400，提示去模型服务配置。"""
    resp = await client.post(
        "/api/chat/stream", json={"message": "hi"}, headers={"X-LLM-Key": "sk-x"}
    )
    assert resp.status_code == 400
    assert "模型服务" in resp.json()["detail"]["message"]


async def test_verify_key_ok(client, monkeypatch):
    """/config/verify-key：Key 可用返回 ok（LLM 调用被 mock）。"""
    from langchain_core.messages import AIMessage

    import app.api.system as system_mod

    class FakeOK:
        async def ainvoke(self, messages):
            return AIMessage(content="pong")

    monkeypatch.setattr(system_mod, "ChatOpenAI", lambda **kwargs: FakeOK())
    resp = await client.post(
        "/api/config/verify-key", json={"provider": "zhipu", "api_key": "1234567890.abcdef"}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_verify_key_invalid(client, monkeypatch):
    """/config/verify-key：Key 无效返回 400 与可读原因。"""
    import app.api.system as system_mod

    class FakeBad:
        async def ainvoke(self, messages):
            raise RuntimeError("Error code: 401 - invalid api key")

    monkeypatch.setattr(system_mod, "ChatOpenAI", lambda **kwargs: FakeBad())
    resp = await client.post(
        "/api/config/verify-key", json={"provider": "deepseek", "api_key": "sk-bad"}
    )
    assert resp.status_code == 400
    assert "无效" in resp.json()["detail"]
