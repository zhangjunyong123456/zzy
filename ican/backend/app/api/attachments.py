"""对话附件接口：上传（含内容提取）+ 原文件下载（归属校验）。"""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_current_user_optional, get_user_llm
from app.agents.llm import set_user_llm
from app.config import settings
from app.services import attachment_service, session_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["attachments"])


@router.post("/chat/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    user: dict | None = Depends(get_current_user_optional),
    user_llm: dict | None = Depends(get_user_llm),
) -> dict:
    uid = user["id"] if user else None
    set_user_llm(user_llm)  # BYOK：视觉模型优先用用户的智谱 Key
    if session_id:
        row = session_service.get_session_row(session_id)
        if row is None or (row["user_id"] or None) != uid:
            raise HTTPException(status_code=404, detail="会话不存在")

    filename = file.filename or "未命名文件"
    resolved = attachment_service.resolve_type(filename)
    if resolved is None:
        raise HTTPException(
            status_code=400,
            detail="仅支持 png / jpg / webp / pdf / docx / pptx / txt / md 文件（.doc/.ppt 请先转存为 .docx/.pptx）",
        )
    mime, kind = resolved

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件不能超过 {settings.max_upload_mb}MB")

    # 落盘：uuid 文件名杜绝路径穿越与重名
    ext = "." + filename.lower().rsplit(".", 1)[-1]
    disk_name = uuid.uuid4().hex + ext
    path = attachment_service.att_dir() / disk_name
    path.write_bytes(data)

    extracted = await attachment_service.extract_text(path, ext, mime, kind)
    warning = None
    if kind == "image" and not extracted:
        user_zhipu = bool(user_llm and user_llm.get("api_key") and user_llm.get("provider") == "zhipu")
        if settings.byok_only:
            warning = "图片识图需配置你自己的智谱 API Key（个人中心 → 模型服务），已保存图片但暂不参与回答"
        elif not user_zhipu and not settings.zhipu_api_key.strip():
            warning = "图片解析需配置智谱 API Key（个人中心 → 模型服务），已保存图片但暂不参与回答"
        else:
            warning = "图片内容解析失败，本次回答暂不使用图片内容"

    att = attachment_service.create_attachment(
        uid, session_id, filename, mime, kind, str(path), len(data), extracted
    )
    return {
        "id": att["id"],
        "filename": att["filename"],
        "mime": att["mime"],
        "kind": att["kind"],
        "size": att["size"],
        "extracted_text": att["extracted_text"],
        "warning": warning,
        "url": f"/api/attachments/{att['id']}/raw",
    }


@router.get("/attachments/{att_id}/raw")
async def attachment_raw(
    att_id: str, user: dict | None = Depends(get_current_user_optional)
) -> FileResponse:
    uid = user["id"] if user else None
    att = attachment_service.get_attachment(att_id)
    if not att or not attachment_service._owned(att, uid):
        raise HTTPException(status_code=404, detail="附件不存在")
    path = Path(att["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="附件文件已丢失")
    return FileResponse(path, media_type=att["mime"], filename=att["filename"])
