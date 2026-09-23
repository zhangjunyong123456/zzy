"""secret_key 云端持久化测试：MockTransport 模拟 app_meta 表，验证重启后 token 仍有效。"""
import json as _json

import httpx

from app.core import security
from app.core.security import create_token, decode_token
from app.turso_client import TursoConnection


def _ok_rows(cols, rows, affected=0):
    return {
        "type": "ok",
        "response": {
            "type": "execute",
            "result": {
                "cols": [{"name": c} for c in cols],
                "rows": [[{"type": "text", "value": v} for v in row] for row in rows],
                "affected_row_count": affected,
            },
        },
    }


def _fake_meta_conn(state: dict) -> TursoConnection:
    """用闭包字典模拟 app_meta 表，只支持 _db_secret 用到的两条 SQL。"""

    def handler(req: httpx.Request) -> httpx.Response:
        body = _json.loads(req.read())
        results = []
        for r in body["requests"]:
            if r["type"] != "execute":
                continue
            sql = r["stmt"]["sql"]
            args = r["stmt"].get("args", [])
            if sql.startswith("SELECT value FROM app_meta"):
                results.append(
                    _ok_rows(["value"], [[state["secret"]]]) if "secret" in state
                    else _ok_rows(["value"], [])
                )
            elif sql.startswith("INSERT OR IGNORE INTO app_meta"):
                state.setdefault("secret", args[0]["value"])
                results.append(_ok_rows([], [], affected=1))
            else:
                results.append({"type": "error", "error": {"message": f"fake db 不支持的 SQL: {sql}"}})
        return httpx.Response(
            200,
            json={"results": results + [{"type": "ok", "response": {"type": "close"}}]},
        )

    return TursoConnection(
        "https://fake.turso.io", "t",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_secret_persists_across_restart(monkeypatch):
    from app.config import settings
    import app.database as db_mod

    state = {}  # 同一个 dict 模拟同一块云存储
    monkeypatch.setattr(settings, "turso_database_url", "libsql://fake.turso.io")
    monkeypatch.setattr(settings, "turso_auth_token", "t")
    monkeypatch.setattr(settings, "secret_key", "")
    monkeypatch.setattr(db_mod, "_turso_conn", _fake_meta_conn(state))
    monkeypatch.setattr(security, "_secret_cache", None)

    token = create_token("u1")  # 首次启动：生成密钥并写入云库
    assert "secret" in state

    # 模拟重启：清密钥缓存 + 新建连接（进程换了，云库数据还在）
    monkeypatch.setattr(security, "_secret_cache", None)
    monkeypatch.setattr(db_mod, "_turso_conn", _fake_meta_conn(state))
    payload = decode_token(token)
    assert payload and payload["uid"] == "u1"


def test_local_file_mode_unchanged(monkeypatch, tmp_path):
    """未配 Turso 时走本地文件逻辑，行为与旧版一致。"""
    from app.config import settings

    f = tmp_path / "s.key"
    monkeypatch.setattr(settings, "turso_database_url", "")
    monkeypatch.setattr(settings, "secret_key", "")
    monkeypatch.setattr(settings, "secret_file", str(f))
    monkeypatch.setattr(security, "_secret_cache", None)
    s1 = security._load_secret()
    s2 = security._load_secret()
    assert s1 == s2 and f.exists()
