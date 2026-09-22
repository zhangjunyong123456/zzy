"""多供应商 LLM 工厂（OpenAI 兼容接口）：DeepSeek / 硅基流动 / 智谱。"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings

PROVIDERS = ("deepseek", "siliconflow", "zhipu")


def active_provider() -> str:
    """当前生效供应商：优先 settings.llm_provider；其 Key 未配置时回退到任一已配置的。"""
    p = settings.llm_provider if settings.llm_provider in PROVIDERS else "deepseek"
    if not getattr(settings, f"{p}_api_key").strip():
        for name in PROVIDERS:
            if getattr(settings, f"{name}_api_key").strip():
                return name
    return p


@lru_cache
def get_llm(temperature: float | None = None, streaming: bool = True) -> ChatOpenAI:
    p = active_provider()
    return ChatOpenAI(
        api_key=getattr(settings, f"{p}_api_key"),
        base_url=getattr(settings, f"{p}_base_url"),
        model=getattr(settings, f"{p}_model"),
        temperature=settings.deepseek_temperature if temperature is None else temperature,
        streaming=streaming,
    )


@lru_cache
def get_vision_llm() -> ChatOpenAI:
    """视觉模型（图片内容提取）：固定走智谱 glm-4v-flash 系。

    注意：热更智谱 Key/模型后必须 get_vision_llm.cache_clear()（同 get_llm 教训）。
    """
    return ChatOpenAI(
        api_key=settings.zhipu_api_key,
        base_url=settings.zhipu_base_url,
        model=settings.zhipu_vision_model,
        temperature=0.2,
        streaming=False,
    )
