"""多供应商 LLM 工厂（OpenAI 兼容接口）：DeepSeek / 硅基流动 / 智谱。

BYOK 模式：用户 Key 由请求头 X-LLM-* 带入，set_user_llm() 绑定到 ContextVar；
get_llm/get_vision_llm 优先用用户 Key，未绑定时回退到 .env 全局 Key。
"""
from contextvars import ContextVar
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings

PROVIDERS = ("deepseek", "siliconflow", "zhipu")

# 当前请求的用户 LLM 配置（None = 走全局 .env 配置）
_user_llm: ContextVar[dict | None] = ContextVar("user_llm", default=None)


def active_provider() -> str:
    """当前生效供应商：优先 settings.llm_provider；其 Key 未配置时回退到任一已配置的。"""
    p = settings.llm_provider if settings.llm_provider in PROVIDERS else "deepseek"
    if not getattr(settings, f"{p}_api_key").strip():
        for name in PROVIDERS:
            if getattr(settings, f"{name}_api_key").strip():
                return name
    return p


def set_user_llm(cfg: dict | None) -> None:
    """绑定当前请求的用户 LLM 配置。

    cfg: {"provider": "deepseek|siliconflow|zhipu", "api_key": "sk-...",
          "model": "...", "base_url": "..."}
    """
    _user_llm.set(cfg)


def get_user_llm_cfg() -> dict | None:
    """读取当前请求的用户 LLM 配置（未绑定时 None）。"""
    return _user_llm.get()


def _user_cfg() -> dict | None:
    return _user_llm.get()


def _make_llm(api_key: str, base_url: str, model: str, temperature: float, streaming: bool) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        streaming=streaming,
    )


def get_llm(temperature: float | None = None, streaming: bool = True) -> ChatOpenAI:
    # 用户自带 Key 优先
    uc = _user_cfg()
    if uc and uc.get("api_key"):
        return _make_llm(
            api_key=uc["api_key"],
            base_url=uc.get("base_url") or getattr(settings, f"{uc['provider']}_base_url"),
            model=uc.get("model") or getattr(settings, f"{uc['provider']}_model"),
            temperature=settings.deepseek_temperature if temperature is None else temperature,
            streaming=streaming,
        )
    # 回退全局
    p = active_provider()
    return _make_llm(
        api_key=getattr(settings, f"{p}_api_key"),
        base_url=getattr(settings, f"{p}_base_url"),
        model=getattr(settings, f"{p}_model"),
        temperature=settings.deepseek_temperature if temperature is None else temperature,
        streaming=streaming,
    )


def get_vision_llm() -> ChatOpenAI:
    """视觉模型（图片内容提取）：用户 Key 优先（仅智谱），无则走全局配置。"""
    uc = _user_cfg()
    if uc and uc.get("api_key") and uc.get("provider") == "zhipu":
        return _make_llm(
            api_key=uc["api_key"],
            base_url=uc.get("base_url") or settings.zhipu_base_url,
            model=settings.zhipu_vision_model,
            temperature=0.2,
            streaming=False,
        )
    if not settings.byok_only and settings.zhipu_api_key.strip():
        # 仅非独占模式（本地开发）回退全局智谱 Key；BYOK 独占模式不消耗服务端 Key
        return _make_llm(
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            model=settings.zhipu_vision_model,
            temperature=0.2,
            streaming=False,
        )
    # 用户没配智谱 Key 且独占模式 → 返回 None（调用方需判空并跳过识图）
    return None
