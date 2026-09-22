"""用户认证接口：注册 / 登录 / 当前用户 / 画像更新。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import require_user
from app.core.security import create_token
from app.services import stats_service, user_service

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)
    nickname: str = Field(default="", max_length=32)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


class ProfileRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=32)
    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=50)
    interests: str | None = Field(default=None, max_length=2000)
    experience: str | None = Field(default=None, max_length=2000)
    goal: str | None = Field(default=None, max_length=2000)


@router.post("/auth/register")
async def register(req: RegisterRequest):
    try:
        user = user_service.create_user(req.username, req.password, req.nickname)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    return {"token": create_token(user["id"]), "user": user}


@router.post("/auth/login")
async def login(req: LoginRequest):
    user = user_service.verify_login(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"code": "bad_credentials", "message": "用户名或密码错误"},
        )
    return {"token": create_token(user["id"]), "user": user}


@router.get("/auth/me")
async def me(user: dict = Depends(require_user)):
    return user


@router.patch("/auth/profile")
async def update_profile(req: ProfileRequest, user: dict = Depends(require_user)):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    return user_service.update_profile(user["id"], fields)


@router.get("/auth/me/stats")
async def my_stats(user: dict = Depends(require_user)):
    return stats_service.get_user_stats(user)
