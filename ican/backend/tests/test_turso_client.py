"""Turso 适配器单元测试：httpx.MockTransport 模拟 HTTP 响应，无需真实云库。"""
import sqlite3

import httpx
import pytest

from app.turso_client import TursoConnection, connect, _encode_arg


def _make_conn(handler):
    return TursoConnection(
        "https://db-org.turso.io", "tok",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_select_rows_and_access_patterns():
    """SELECT 结果解码 + row['col'] / dict(row) / fetchone / fetchall 语义。"""
    payload = {
        "results": [
            {
                "type": "ok",
                "response": {
                    "type": "execute",
                    "result": {
                        "cols": [{"name": "id"}, {"name": "score"}, {"name": "note"}],
                        "rows": [
                            [{"type": "text", "value": "a1"}, {"type": "integer", "value": "42"}, {"type": "null"}],
                            [{"type": "text", "value": "a2"}, {"type": "float", "value": "3.5"}, {"type": "text", "value": "x"}],
                        ],
                        "affected_row_count": 0,
                    },
                },
            },
            {"type": "ok", "response": {"type": "close"}},
        ]
    }
    conn = _make_conn(lambda req: httpx.Response(200, json=payload))

    with conn as c:
        cur = c.execute("SELECT id, score, note FROM t WHERE k = ?", ("v",))
        first = cur.fetchone()
        assert first["id"] == "a1"
        assert first["score"] == 42
        assert first["note"] is None
        assert dict(first) == {"id": "a1", "score": 42, "note": None}
        rest = cur.fetchall()
        assert rest[0]["id"] == "a2"
        assert rest[0]["score"] == 3.5
        assert cur.fetchone() is None  # 耗尽后返回 None


def test_insert_param_encoding():
    """各类型参数按 Hrana 协议编码，SQL 原样透传。"""
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = req.read()
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={
            "results": [
                {"type": "ok", "response": {"type": "execute", "result": {
                    "cols": [], "rows": [], "affected_row_count": 1}}},
                {"type": "ok", "response": {"type": "close"}},
            ]
        })

    conn = _make_conn(handler)
    conn.execute("INSERT INTO t VALUES (?, ?, ?, ?, ?)", (1, 2.5, None, "txt", True))

    import json
    body = json.loads(seen["body"])
    assert seen["auth"] == "Bearer tok"
    reqs = body["requests"]
    assert reqs[-1] == {"type": "close"}
    stmt = reqs[0]["stmt"]
    assert stmt["sql"].startswith("INSERT INTO t")
    assert stmt["args"] == [
        {"type": "integer", "value": "1"},
        {"type": "float", "value": "2.5"},
        {"type": "null"},
        {"type": "text", "value": "txt"},
        {"type": "integer", "value": "1"},
    ]


def test_unique_error_maps_to_integrity_error():
    """UNIQUE 冲突映射为 sqlite3.IntegrityError（user_service 靠 str(e) 含 UNIQUE 判重）。"""
    def handler(req):
        return httpx.Response(200, json={
            "results": [
                {"type": "error", "error": {"message": "UNIQUE constraint failed: users.username"}}
            ]
        })

    conn = _make_conn(handler)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute("INSERT INTO users (username) VALUES (?)", ("dup",))


def test_http_error_maps_to_operational_error():
    def handler(req):
        return httpx.Response(401, text='{"error":"unauthorized"}')

    conn = _make_conn(handler)
    with pytest.raises(sqlite3.OperationalError, match="401"):
        conn.execute("SELECT 1")


def test_executescript_splits_statements():
    """DDL 按 ; 拆分批量执行；纯注释块被跳过。"""
    seen = []

    def handler(req):
        import json
        body = json.loads(req.read())
        execs = [r for r in body["requests"] if r["type"] == "execute"]
        seen.extend(r["stmt"]["sql"] for r in execs)
        return httpx.Response(200, json={
            "results": [
                {"type": "ok", "response": {"type": "execute", "result": {
                    "cols": [], "rows": [], "affected_row_count": 0}}}
                for _ in execs
            ] + [{"type": "ok", "response": {"type": "close"}}]
        })

    conn = _make_conn(handler)
    conn.executescript(
        "-- 建表\nCREATE TABLE a (id TEXT);;\n"
        "-- 仅注释应被跳过\n;\n"
        "CREATE TABLE b (id TEXT);"
    )
    assert seen == ["-- 建表\nCREATE TABLE a (id TEXT)", "CREATE TABLE b (id TEXT)"]


def test_connect_url_normalization():
    c1 = connect("libsql://db-org.turso.io", "t")
    assert c1._url == "https://db-org.turso.io"
    c2 = connect("https://db-org.turso.io/", "t")
    assert c2._url == "https://db-org.turso.io"
    with pytest.raises(ValueError):
        connect("http://db-org.turso.io", "t")


def test_encode_arg_bytes():
    import base64
    assert _encode_arg(b"\x00\xff") == {"type": "blob", "value": base64.b64encode(b"\x00\xff").decode()}
