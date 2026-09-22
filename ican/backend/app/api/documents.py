"""文档管理接口：上传 / 列表 / 删除。"""
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import DocumentOut
from app.services import doc_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])

_ALLOWED_SCENES = {"study", "research", "career", "campus"}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    scene: str = Form("study"),
) -> DocumentOut:
    if scene not in _ALLOWED_SCENES:
        raise HTTPException(status_code=400, detail=f"scene 仅支持 {sorted(_ALLOWED_SCENES)}")
    filename = file.filename or "未命名.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前仅支持 PDF 文件")
    data = await file.read()
    try:
        result = doc_service.ingest_pdf(filename, data, scene=scene)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("文档解析失败: %s", filename)
        raise HTTPException(status_code=500, detail="文档解析失败，请重试")
    return DocumentOut(builtin=False, **result)


@router.get("/documents")
async def list_documents() -> list[DocumentOut]:
    return [
        DocumentOut(**{**d, "builtin": bool(d["builtin"])})
        for d in doc_service.list_documents()
    ]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    ok = doc_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}
