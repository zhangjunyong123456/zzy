"""预下载 embedding 模型（演示前运行一次）。

用法：.venv\\Scripts\\python.exe scripts\\warmup_models.py
国内网络慢可在 .env 设置 HF_ENDPOINT=https://hf-mirror.com
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 国内镜像
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # 镜像不支持 Xet

from app.rag.embeddings import embed_documents, embed_query  # noqa: E402

if __name__ == "__main__":
    print("正在加载/下载 embedding 模型（首次约 100MB）...")
    v = embed_query("测试查询")
    print("query embedding 维度:", len(v))
    print("documents embedding:", len(embed_documents(["你好，世界"])[0]), "维")
    print("模型就绪 ✔")
