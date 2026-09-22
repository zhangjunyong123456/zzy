"""认证依赖：从 Authorization: Bearer 头解析当前用户（可选/必须）。"""
from fastapi import Depends, Header, HTTPException

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
