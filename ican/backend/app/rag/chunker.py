"""文本分块：按段落边界递归切分，保留页码元数据。"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
)


def chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    """输入 [(页码, 文本)]，输出 [{"text", "page", "seq"}]。"""
    chunks: list[dict] = []
    for page_no, text in pages:
        for piece in _SPLITTER.split_text(text):
            piece = piece.strip()
            if piece:
                chunks.append({"text": piece, "page": page_no, "seq": len(chunks)})
    return chunks
