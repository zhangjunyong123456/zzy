"""系统接口：健康检查 + 配置状态 + 多供应商 API Key 在线配置。"""
import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agents.llm import PROVIDERS, active_provider, get_llm, get_vision_llm
from app.config import settings

router = APIRouter(tags=["system"])

ENV_PATH = Path(settings.model_config.get("env_file", ".env"))

PROVIDER_LABEL = {
    "deepseek": "DeepSeek",
    "siliconflow": "硅基流动",
    "zhipu": "智谱",
}


class ApiKeyRequest(BaseModel):
    provider: str = "deepseek"
    api_key: str = Field(min_length=6, max_length=160)


class ProviderRequest(BaseModel):
    provider: str


class ModelRequest(BaseModel):
    provider: str
    model: str = Field(min_length=1, max_length=80)


def _upsert_env(name: str, value: str) -> None:
    """在 backend/.env 中更新或追加一个变量（保留其余内容）。"""
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    line = f"{name}={value}"
    pattern = re.compile(rf"^{name}=.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(line, text, count=1)
    else:
        text = (text.rstrip("\n") + "\n" if text.strip() else "") + line + "\n"
    ENV_PATH.write_text(text, encoding="utf-8")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": "UniGrow Agent"}


@router.get("/config/status")
async def config_status() -> dict:
    provider = active_provider()
    return {
        "api_key_configured": settings.has_api_key,
        "provider": provider,
        "model": getattr(settings, f"{provider}_model"),
        "base_url": getattr(settings, f"{provider}_base_url"),
        "providers": {
            name: {
                "configured": bool(getattr(settings, f"{name}_api_key").strip()),
                "active": name == provider,
                "model": getattr(settings, f"{name}_model"),
                "base_url": getattr(settings, f"{name}_base_url"),
            }
            for name in PROVIDERS
        },
    }


@router.post("/config/provider")
async def set_provider(req: ProviderRequest) -> dict:
    """切换当前生效的供应商（须已配置该家 Key），热生效。"""
    provider = req.provider if req.provider in PROVIDERS else ""
    if not provider:
        return JSONResponse(status_code=400, content={"detail": "未知的模型供应商"})
    if not getattr(settings, f"{provider}_api_key").strip():
        return JSONResponse(
            status_code=400,
            content={"detail": f"请先保存 {PROVIDER_LABEL[provider]} 的 API Key，再切换过去"},
        )
    _upsert_env("LLM_PROVIDER", provider)
    settings.llm_provider = provider
    get_llm.cache_clear()
    get_vision_llm.cache_clear()
    return {"ok": True, "provider": provider, "model": getattr(settings, f"{provider}_model")}


@router.post("/config/model")
async def set_model(req: ModelRequest) -> dict:
    """修改某供应商的默认模型名（如 deepseek-flash / glm-5.3），热生效。"""
    provider = req.provider if req.provider in PROVIDERS else ""
    model = req.model.strip()
    if not provider:
        return JSONResponse(status_code=400, content={"detail": "未知的模型供应商"})
    if not model:
        return JSONResponse(status_code=400, content={"detail": "模型名不能为空"})
    _upsert_env(f"{provider.upper()}_MODEL", model)
    setattr(settings, f"{provider}_model", model)
    get_llm.cache_clear()
    get_vision_llm.cache_clear()
    return {"ok": True, "provider": provider, "model": model}


@router.post("/config/api-key")
async def set_api_key(req: ApiKeyRequest) -> dict:
    provider = req.provider if req.provider in PROVIDERS else "deepseek"
    key = req.api_key.strip()

    # 各平台 Key 形态校验（宽松）：DeepSeek/硅基流动 sk- 开头；智谱 id.secret 含点
    if provider in ("deepseek", "siliconflow") and not key.startswith("sk-"):
        return JSONResponse(
            status_code=400,
            content={"detail": f"{PROVIDER_LABEL[provider]} 的 Key 一般以 sk- 开头，请检查是否复制完整"},
        )
    if provider == "zhipu" and "." not in key:
        return JSONResponse(
            status_code=400,
            content={"detail": "智谱 Key 形如 id.secret（中间有个点），请检查是否复制完整"},
        )

    _upsert_env(f"{provider.upper()}_API_KEY", key)
    _upsert_env("LLM_PROVIDER", provider)
    # 热更新运行时单例 + 清空 LLM 缓存，立即生效无需重启
    setattr(settings, f"{provider}_api_key", key)
    settings.llm_provider = provider
    get_llm.cache_clear()
    get_vision_llm.cache_clear()
    return {"ok": True, "api_key_configured": True, "provider": provider}
