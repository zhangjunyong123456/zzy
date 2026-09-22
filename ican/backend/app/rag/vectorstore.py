"""Chroma 向量库：嵌入式 PersistentClient + fastembed 封装。"""
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import settings

_COLLECTION = "ican_docs"
_client: chromadb.api.ClientAPI | None = None


class FastEmbedFunction(EmbeddingFunction[Documents]):
    def __init__(self, model_name: str):
        self._model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        from app.rag.embeddings import embed_documents

        return embed_documents(list(input))


def get_client() -> chromadb.api.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=_COLLECTION,
        embedding_function=FastEmbedFunction(settings.embedding_model),
        metadata={"hnsw:space": "cosine"},
    )
