"""pytest 公共夹具：隔离的数据目录 + FakeLLM。"""
import os
import sys
import tempfile
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("PYTHONUTF8", "1")
# huggingface_hub 只读 os.environ：与 run.py 保持一致，国内走镜像（模型未缓存时 RAG 测试需联网下载）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_tmp = tempfile.mkdtemp(prefix="unigrow_test_")
os.environ["SQLITE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["CHROMA_PERSIST_DIR"] = os.path.join(_tmp, "chroma")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
# 强制本地 SQLite：防止 .env 里配置的 TURSO_DATABASE_URL 让测试误连云库
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""
# 测试固定非独占模式：防止 .env 里 BYOK_ONLY=1 把所有不带用户 Key 的测试打进演示模式
# （BYOK 独占行为由 test_byok.py 的用例自行 monkeypatch 验证）
os.environ["BYOK_ONLY"] = "0"
os.environ.setdefault("SECRET_KEY", "test-secret")  # 在 import app 之前，避免测试写真实 secret.key

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import RouteDecision  # noqa: E402


class FakeChunk:
    def __init__(self, content):
        self.content = content


class FakeStructured:
    def __init__(self, decision=None):
        self._decision = decision or RouteDecision(
            agents=["main"], complexity="single",
            sub_queries={"main": "hi"}, plan_summary="主Agent直接回答",
        )

    async def ainvoke(self, messages):
        return self._decision


class FakeLLM:
    """无网络 Fake：结构化输出返回固定路由，astream 返回固定 token 并捕获入参。"""

    def __init__(self, *args, **kwargs):
        self.captured = []  # 每次 astream 的 messages 列表，供注入断言用

    def with_structured_output(self, schema, **kwargs):
        return FakeStructured(getattr(FakeLLM, "_next_decision", None))

    async def astream(self, messages):
        self.captured.append(list(messages))
        for piece in ["你好，", "我是UniGrow主Agent。"]:
            yield FakeChunk(piece)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_llm(monkeypatch):
    import app.agents.llm as llm_mod
    import app.agents.router as router_mod

    inst = FakeLLM()
    monkeypatch.setattr(llm_mod, "get_llm", lambda *a, **k: inst)
    monkeypatch.setattr(router_mod, "get_llm", lambda *a, **k: inst)
    return inst


@pytest.fixture
async def client(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
