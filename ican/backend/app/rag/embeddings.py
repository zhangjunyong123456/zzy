"""Embedding：fastembed + BAAI/bge-small-zh-v1.5（ONNX，无 torch 依赖）。"""
from functools import lru_cache

from app.config import settings


@lru_cache
def get_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return [e.tolist() for e in get_model().embed(texts)]


def embed_query(text: str) -> list[float]:
    try:
        vec = list(get_model().query_embed([text]))[0]
    except Exception:
        # bge 中文检索指令前缀（query_embed 不可用时手动加）
        vec = list(get_model().embed(["为这个句子生成表示，用于检索相关文章：" + text]))[0]
    return vec.tolist()
