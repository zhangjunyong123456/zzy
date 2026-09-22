"""PDF 解析：PyMuPDF 按页提取文本。"""
import re

import pymupdf


def _clean(text: str) -> str:
    text = text.replace("\u00ad-\n", "").replace("-\n", "")  # 连字符断行
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf(data: bytes) -> list[tuple[int, str]]:
    """返回 [(页码, 文本)]，跳过空页。"""
    docs: list[tuple[int, str]] = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for i, page in enumerate(pdf, start=1):
            text = _clean(page.get_text("text"))
            if text:
                docs.append((i, text))
    return docs
