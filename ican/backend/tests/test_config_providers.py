"""多供应商配置接口：切换供应商 / 修改模型名。"""
import pytest

from app.config import settings


@pytest.mark.anyio
async def test_switch_provider_without_key_rejected(client, monkeypatch):
    """未配置 Key 的供应商不允许切换为当前。"""
    monkeypatch.setattr(settings, "zhipu_api_key", "")
    resp = await client.post("/api/config/provider", json={"provider": "zhipu"})
    assert resp.status_code == 400
    assert "Key" in resp.json()["detail"]


@pytest.mark.anyio
async def test_switch_provider_with_key_ok(client, monkeypatch):
    """已配置 Key 的供应商可切换，且热更新 settings.llm_provider。"""
    monkeypatch.setattr(settings, "siliconflow_api_key", "sk-test")
    monkeypatch.setattr(settings, "siliconflow_model", "deepseek-ai/DeepSeek-V4-Flash")
    resp = await client.post("/api/config/provider", json={"provider": "siliconflow"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True and data["provider"] == "siliconflow"
    assert settings.llm_provider == "siliconflow"
    # 还原，避免影响其他用例
    monkeypatch.setattr(settings, "llm_provider", "deepseek")


@pytest.mark.anyio
async def test_set_model_updates_settings(client, monkeypatch):
    """修改模型名：返回 ok，settings 与响应一致（env 写入被 mock 掉）。"""
    import app.api.system as system_mod

    monkeypatch.setattr(system_mod, "_upsert_env", lambda name, value: None)
    monkeypatch.setattr(settings, "zhipu_model", "glm-4.5-flash")
    resp = await client.post("/api/config/model", json={"provider": "zhipu", "model": "glm-5.3"})
    assert resp.status_code == 200
    assert resp.json()["model"] == "glm-5.3"
    assert settings.zhipu_model == "glm-5.3"


@pytest.mark.anyio
async def test_status_includes_provider_matrix(client):
    """/config/status 返回三家配置矩阵（含 model/base_url）。"""
    resp = await client.get("/api/config/status")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["providers"].keys()) == {"deepseek", "siliconflow", "zhipu"}
    for info in data["providers"].values():
        assert "configured" in info and "active" in info
        assert "model" in info and "base_url" in info
