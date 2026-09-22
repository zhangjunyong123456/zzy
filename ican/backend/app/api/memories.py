"""记忆接口：从历史会话保存 / 列表 / 重命名 / 删除。"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_optional
from app.schemas import MemoryCreate, MemoryOut, MemoryRename
from app.services import memory_service, session_service

router = APIRouter(tags=["memories"])


@router.post("/memories")
async def create_memory(
    req: MemoryCreate, user: dict | None = Depends(get_current_user_optional)
) -> MemoryOut:
    uid = user["id"] if user else None
    row = session_service.get_session_row(req.source_session_id)
    if row is None or (row["user_id"] or None) != uid:
        raise HTTPException(status_code=404, detail="会话不存在")
    mem = memory_service.create_memory(
        uid, (req.title or "").strip(), req.source_session_id, req.message_ids
    )
    if mem is None:
        raise HTTPException(status_code=400, detail="所选消息不存在或不属于该会话")
    return MemoryOut(**mem)


@router.get("/memories")
async def list_memories(
    user: dict | None = Depends(get_current_user_optional)
) -> list[MemoryOut]:
    uid = user["id"] if user else None
    return [MemoryOut(**m) for m in memory_service.list_memories(uid)]


@router.put("/memories/{memory_id}")
async def rename_memory(
    memory_id: str, req: MemoryRename, user: dict | None = Depends(get_current_user_optional)
) -> MemoryOut:
    uid = user["id"] if user else None
    mem = memory_service.rename_memory(memory_id, uid, req.title.strip())
    if mem is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return MemoryOut(**mem)


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str, user: dict | None = Depends(get_current_user_optional)
) -> dict:
    uid = user["id"] if user else None
    if not memory_service.delete_memory(memory_id, uid):
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"ok": True}
