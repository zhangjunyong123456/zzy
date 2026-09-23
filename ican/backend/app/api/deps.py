"""认证依赖：从 Authorization: Bearer 头解析当前用户（可选/必须）；BYOK 头解析。"""
from fastapi import Depends, Header, HTTPException

from app.agents.llm import PROVIDERS
from app.core.security import decode_token
from app.services import user_service


def get_current_user_optional(
    authorization: str | None = Header(default=None),
) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(authorization[7:].strip())
    if not payload:
        return None
    return user_service.get_user_by_id(payload.get("uid", ""))


def require_user(user: dict | None = Depends(get_current_user_optional)) -> dict:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "请先登录"},
        )
    return user


def get_user_llm(
    x_llm_provider: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
) -> dict | None:
    """解析 BYOK 请求头为用户 LLM 配置；未带 Key 返回 None（走全局/演示模式）。"""
    key = (x_llm_key or "").strip()
    if not key:
        return None
    provider = (x_llm_provider or "").strip()
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_provider", "message": "未知的模型供应商，请到「模型服务」重新选择"},
        )
    return {
        "provider": provider,
        "api_key": key,
        "model": (x_llm_model or "").strip(),
        "base_url": "",
    }
