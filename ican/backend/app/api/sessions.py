"""会话管理接口：按当前用户（或游客）隔离。"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_optional
from app.services import session_service

router = APIRouter(tags=["sessions"])


def _uid(user: dict | None) -> str | None:
    return user["id"] if user else None


def _check_owner(session_id: str, uid: str | None) -> None:
    """归属校验：不存在或不属于当前用户（含游客）→ 404 防枚举。"""
    row = session_service.get_session_row(session_id)
    if row is None or (row["user_id"] or None) != uid:
        raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/sessions")
async def list_sessions(user: dict | None = Depends(get_current_user_optional)) -> list[dict]:
    return session_service.list_sessions(user_id=_uid(user))


@router.post("/sessions")
async def create_session(user: dict | None = Depends(get_current_user_optional)) -> dict:
    sid = session_service.create_session(user_id=_uid(user))
    return {"id": sid, "title": "新对话"}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str, user: dict | None = Depends(get_current_user_optional)
) -> dict:
    _check_owner(session_id, _uid(user))
    sessions = [
        s for s in session_service.list_sessions(user_id=_uid(user)) if s["id"] == session_id
    ]
    if not sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {**sessions[0], "messages": session_service.get_messages(session_id)}


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str, body: dict, user: dict | None = Depends(get_current_user_optional)
) -> dict:
    _check_owner(session_id, _uid(user))
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    session_service.rename_session(session_id, title)
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, user: dict | None = Depends(get_current_user_optional)
) -> dict:
    _check_owner(session_id, _uid(user))
    session_service.delete_session(session_id)
    return {"ok": True}
