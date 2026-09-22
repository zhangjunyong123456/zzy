"""文档服务：上传 → 解析 → 分块 → 向量化 → 登记。同步处理（20MB 内秒级）。"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.database import get_conn
from app.rag import parser
from app.rag.chunker import chunk_pages
from app.rag.embeddings import embed_documents
from app.rag.vectorstore import get_collection

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _insert_row(doc_id: str, filename: str, scene: str, builtin: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, scene, status, builtin, created_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (doc_id, filename, scene, int(builtin), _now()),
        )


def _finish_row(doc_id: str, status: str, pages: int, chunk_count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = ?, pages = ?, chunk_count = ? WHERE id = ?",
            (status, pages, chunk_count, doc_id),
        )


def _add_chunks_to_chroma(doc_id: str, scene: str, chunks: list[dict]) -> None:
    col = get_collection()
    batch = 64
    for start in range(0, len(chunks), batch):
        part = chunks[start : start + batch]
        col.add(
            ids=[f"{doc_id}_{c['seq']}" for c in part],
            documents=[c["text"] for c in part],
            metadatas=[
                {"doc_id": doc_id, "scene": scene, "page": c["page"], "seq": c["seq"]}
                for c in part
            ],
        )


def ingest_text(
    filename: str,
    text: str,
    scene: str = "campus",
    builtin: bool = True,
    doc_id: str | None = None,
) -> dict:
    """纯文本文档入库（校园知识库 seed 用）。"""
    doc_id = doc_id or uuid.uuid4().hex[:16]
    _insert_row(doc_id, filename, scene, builtin)
    try:
        chunks = chunk_pages([(1, text)])
        _add_chunks_to_chroma(doc_id, scene, chunks)
        _finish_row(doc_id, "ready", 1, len(chunks))
    except Exception as e:
        _finish_row(doc_id, "failed", 0, 0)
        logger.exception("ingest_text failed: %s", e)
        raise
    return {"id": doc_id, "filename": filename, "scene": scene, "status": "ready",
            "pages": 1, "chunk_count": len(chunks), "created_at": _now()}


def ingest_pdf(filename: str, data: bytes, scene: str = "study") -> dict:
    """PDF 上传入库：校验 → 保存 → 解析 → 分块 → 向量化。"""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValueError(f"文件超过 {settings.max_upload_mb}MB 限制")
    doc_id = uuid.uuid4().hex[:16]
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{doc_id}.pdf"
    pdf_path.write_bytes(data)

    _insert_row(doc_id, filename, scene, builtin=False)
    try:
        pages = parser.parse_pdf(data)
        if not pages:
            raise ValueError("未能从 PDF 中解析出文本（可能是扫描件，需 OCR 支持）")
        if len(pages) > settings.max_pdf_pages:
            raise ValueError(f"PDF 页数超过 {settings.max_pdf_pages} 页限制")
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("文档分块结果为空")
        _add_chunks_to_chroma(doc_id, scene, chunks)
        _finish_row(doc_id, "ready", len(pages), len(chunks))
    except Exception:
        _finish_row(doc_id, "failed", 0, 0)
        raise
    return {"id": doc_id, "filename": filename, "scene": scene, "status": "ready",
            "pages": len(pages), "chunk_count": len(chunks), "created_at": _now()}


def list_documents(include_builtin: bool = False) -> list[dict]:
    sql = "SELECT id, filename, scene, status, pages, chunk_count, builtin, created_at " \
          "FROM documents"
    if not include_builtin:
        sql += " WHERE builtin = 0"
    sql += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT id, builtin FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    get_collection().delete(where={"doc_id": doc_id})
    pdf_path = Path(settings.upload_dir) / f"{doc_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    return True
