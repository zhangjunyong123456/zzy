"""RAG 管线测试：PDF 解析 → 分块 → 向量入库 → 检索命中（需已预热 embedding 模型）。"""
import io

import pymupdf
import pytest

from app.rag import parser
from app.rag.chunker import chunk_pages
from app.rag.retriever import retrieve
from app.services import doc_service


def make_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "UniGrow RAG Fixture Page 1", fontsize=14)
    page.insert_text((72, 110), "Chroma is a vector database for AI applications." * 5, fontsize=11)
    page2 = doc.new_page()
    page2.insert_text((72, 72), "LangGraph orchestrates multi-agent workflows.", fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_and_chunk():
    pages = parser.parse_pdf(make_pdf_bytes())
    assert len(pages) == 2
    assert pages[0][0] == 1
    chunks = chunk_pages(pages)
    assert len(chunks) > 0
    assert all(c["page"] in (1, 2) for c in chunks)


@pytest.mark.anyio
async def test_ingest_and_retrieve():
    from app.database import init_db

    init_db()
    data = make_pdf_bytes()
    result = doc_service.ingest_pdf("fixture.pdf", data, scene="study")
    assert result["status"] == "ready"
    assert result["chunk_count"] > 0

    hits = retrieve("What is Chroma vector database?", scene="study", top_k=3)
    assert len(hits) > 0
    joined = " ".join(h["text"] for h in hits)
    assert "Chroma" in joined or "vector" in joined

    assert doc_service.delete_document(result["id"])
