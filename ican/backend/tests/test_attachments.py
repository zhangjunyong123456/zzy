"""附件系统测试：类型白名单、各类解析、图片视觉模型、归属校验、raw 下载。"""
import uuid

import pymupdf
import pytest

from app.services import attachment_service, session_service


pytestmark = pytest.mark.anyio


def _uname():
    return f"user_{uuid.uuid4().hex[:10]}"


async def _register(client, username):
    resp = await client.post(
        "/api/auth/register", json={"username": username, "password": "pass123456"}
    )
    assert resp.status_code == 200
    return resp.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    return doc.tobytes()


def _fake_vision(monkeypatch, text="图片里有简历标题"):
    """替换视觉模型：ainvoke 返回固定文本。"""
    import app.agents.llm as llm_mod

    class FakeVision:
        async def ainvoke(self, messages):
            class R:
                content = text

            return R()

    monkeypatch.setattr(llm_mod, "get_vision_llm", lambda: FakeVision())


async def test_upload_txt_and_pdf(client):
    # txt
    resp = await client.post(
        "/api/chat/upload",
        files={"file": ("笔记.txt", "第一行内容\n第二行内容".encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 200
    att = resp.json()
    assert att["kind"] == "file" and "第一行内容" in att["extracted_text"]
    assert att["url"] == f"/api/attachments/{att['id']}/raw"

    # pdf
    resp2 = await client.post(
        "/api/chat/upload",
        files={"file": ("doc.pdf", _pdf_bytes("PDF CONTENT 123"), "application/pdf")},
    )
    assert resp2.status_code == 200
    assert "PDF CONTENT 123" in resp2.json()["extracted_text"]


async def test_upload_docx(client):
    from docx import Document
    from io import BytesIO

    buf = BytesIO()
    doc = Document()
    doc.add_paragraph("简历项目描述段落")
    doc.save(buf)
    resp = await client.post(
        "/api/chat/upload",
        files={"file": ("简历.docx", buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200
    assert "简历项目描述段落" in resp.json()["extracted_text"]


async def test_upload_pptx(client):
    from io import BytesIO

    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "课题研究背景"
    slide.placeholders[1].text = "第一页要点内容"
    slide2 = prs.slides.add_slide(prs.slide_layouts[5])
    slide2.shapes.title.text = "第二页标题"
    buf = BytesIO()
    prs.save(buf)
    resp = await client.post(
        "/api/chat/upload",
        files={"file": ("汇报.pptx", buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert resp.status_code == 200
    text = resp.json()["extracted_text"]
    assert "[第1页]" in text and "课题研究背景" in text and "第一页要点内容" in text
    assert "[第2页]" in text and "第二页标题" in text


async def test_upload_rejects_bad_type_and_oversize(client, monkeypatch):
    from app.config import settings

    resp = await client.post(
        "/api/chat/upload", files={"file": ("virus.exe", b"MZ", "application/octet-stream")}
    )
    assert resp.status_code == 400

    monkeypatch.setattr(settings, "max_upload_mb", 0)  # 0MB → 任何内容都超限
    resp2 = await client.post(
        "/api/chat/upload", files={"file": ("a.txt", b"hello", "text/plain")}
    )
    assert resp2.status_code == 400


async def test_image_without_zhipu_key(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "zhipu_api_key", "")
    png = b"\x89PNG\r\n\x1a\nfake"
    resp = await client.post(
        "/api/chat/upload", files={"file": ("shot.png", png, "image/png")}
    )
    assert resp.status_code == 200
    att = resp.json()
    assert att["kind"] == "image" and att["extracted_text"] == ""
    assert "智谱" in att["warning"]


async def test_image_with_vision_model(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "zhipu_api_key", "test-key")
    _fake_vision(monkeypatch, "图中是一张课程表")
    resp = await client.post(
        "/api/chat/upload", files={"file": ("shot.png", b"\x89PNGfake", "image/png")}
    )
    att = resp.json()
    assert att["warning"] is None
    assert "课程表" in att["extracted_text"]


async def test_raw_download_ownership(client):
    owner = await _register(client, _uname())
    resp = await client.post(
        "/api/chat/upload",
        headers=_auth(owner["token"]),
        files={"file": ("a.txt", "秘密".encode("utf-8"), "text/plain")},
    )
    att = resp.json()

    # 游客拿不到他人附件
    assert (await client.get(att["url"])).status_code == 404
    # 归属者可下载
    raw = await client.get(att["url"], headers=_auth(owner["token"]))
    assert raw.status_code == 200
    assert raw.content == "秘密".encode("utf-8")


async def test_upload_session_check_and_bind(client, fake_llm):
    """带 session_id 上传 → 发送消息 → 附件绑定到消息并注入回答上下文。"""
    sid = (await client.post("/api/sessions")).json()["id"]

    # 会话归属校验：登录用户指向游客会话 → 404
    other = await _register(client, _uname())
    resp404 = await client.post(
        "/api/chat/upload",
        headers=_auth(other["token"]),
        files={"file": ("a.txt", b"x", "text/plain")},
        data={"session_id": sid},
    )
    assert resp404.status_code == 404

    up = await client.post(
        "/api/chat/upload",
        files={"file": ("提纲.txt", "项目提纲内容".encode("utf-8"), "text/plain")},
        data={"session_id": sid},
    )
    att = up.json()

    resp = await client.post(
        "/api/chat/stream",
        json={"session_id": sid, "message": "帮我看看这份提纲", "attachment_ids": [att["id"]]},
    )
    assert resp.status_code == 200

    # 附件已绑定到用户消息
    hist = (await client.get(f"/api/sessions/{sid}")).json()
    user_msgs = [m for m in hist["messages"] if m["role"] == "user"]
    assert user_msgs[-1]["attachments"] == [
        {"id": att["id"], "filename": "提纲.txt", "kind": "file", "mime": "text/plain"}
    ]

    # 重复绑定幂等：同一附件再次绑定不产生重复（session_id 已占）
    up2 = await client.post(
        "/api/chat/upload",
        files={"file": ("other.txt", "y".encode("utf-8"), "text/plain")},
    )
    _ = up2.json()


async def test_build_attachments_text_truncation():
    sid = session_service.create_session()
    path = attachment_service.att_dir() / "t.txt"
    path.write_text("x" * 50)
    atts = [
        attachment_service.create_attachment(
            None, sid, f"f{i}.txt", "text/plain", "file", str(path), 50, "内容" * 2000
        )
        for i in range(3)
    ]
    bound = [{"id": a["id"], "filename": a["filename"], "kind": a["kind"], "mime": a["mime"]}
             for a in atts]
    text = attachment_service.build_attachments_text(bound)
    assert len(text) <= attachment_service.MAX_TEXT + 10
    assert text.endswith("（已截断）")
