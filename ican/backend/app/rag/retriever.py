"""检索：向量召回 top_k，按页拼接为带来源标注的上下文。"""
from app.rag.embeddings import embed_query
from app.rag.vectorstore import get_collection


def retrieve(
    query: str,
    doc_ids: list[str] | None = None,
    scene: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    col = get_collection()
    if col.count() == 0:
        return []
    where = None
    if doc_ids:
        where = {"doc_id": {"$in": doc_ids}}
    elif scene:
        where = {"scene": scene}
    res = col.query(
        query_embeddings=[embed_query(query)],
        n_results=min(top_k, col.count()),
        where=where,
    )
    hits: list[dict] = []
    ids = res["ids"][0]
    for i in range(len(ids)):
        meta = res["metadatas"][0][i]
        hits.append(
            {
                "text": res["documents"][0][i],
                "doc_id": meta.get("doc_id", ""),
                "page": meta.get("page", 0),
                "distance": res["distances"][0][i],
            }
        )
    return hits


def format_context(hits: list[dict]) -> str:
    if not hits:
        return ""
    blocks = [f"[来源：第{h['page']}页]\n{h['text']}" for h in hits]
    return "\n\n---\n\n".join(blocks)
