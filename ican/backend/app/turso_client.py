"""Turso 云数据库适配器：通过 HTTP（Hrana v2 /v2/pipeline）模拟项目用到的 sqlite3 接口面。

libsql-experimental 官方包无 Windows wheel（本地无法安装/测试），故自研纯 Python 适配。
仅实现 app 各服务实际用到的能力：
    conn.execute(sql, params) -> 游标（fetchone / fetchall，行支持 row["列名"]、dict(row)）
    conn.executescript(sql)   -> 建表/幂等迁移用（仅限无内嵌分号的 SQLite DDL）
    with get_conn() as conn:  -> 上下文管理器（HTTP 模式单语句即独立事务，无需 commit）
SQL 仍为 SQLite 方言，Turso(libSQL) 服务端完全兼容。
协议参考：https://docs.turso.tech/sdk/http/reference
"""
import base64
import os
import sqlite3
import threading

import httpx


class TursoRow:
    """模拟 sqlite3.Row：支持 row["col"]、row[i]、dict(row)、len(row)。"""

    def __init__(self, keys: list[str], values: list):
        self._keys = list(keys)
        self._values = list(values)

    def keys(self):
        return list(self._keys)

    def __len__(self):
        return len(self._values)

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._values[key]
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise IndexError(f"no such column: {key}") from None

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return f"TursoRow({dict(zip(self._keys, self._values))!r})"


class TursoCursor:
    def __init__(self, cols: list[str], rows: list[list]):
        self._cols = cols
        self._rows = rows
        self._idx = 0

    def fetchone(self) -> TursoRow | None:
        if self._idx >= len(self._rows):
            return None
        row = TursoRow(self._cols, self._rows[self._idx])
        self._idx += 1
        return row

    def fetchall(self) -> list[TursoRow]:
        out = [TursoRow(self._cols, r) for r in self._rows[self._idx:]]
        self._idx = len(self._rows)
        return out


def _encode_arg(v) -> dict:
    """Python 值 -> Hrana 参数编码。integer/float 的 value 按协议要求传字符串。"""
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": repr(v)}
    if isinstance(v, bytes):
        return {"type": "blob", "value": base64.b64encode(v).decode()}
    return {"type": "text", "value": str(v)}


def _decode_cell(cell: dict):
    t = cell.get("type")
    if t == "null" or t is None:
        return None
    v = cell.get("value")
    if t == "integer":
        return v if isinstance(v, int) else int(v)
    if t == "float":
        return v if isinstance(v, (int, float)) else float(v)
    if t == "blob":
        return base64.b64decode(v)
    return v  # text


def _map_error(msg: str) -> Exception:
    """把 Turso 错误映射为 sqlite3 异常族，保留既有 except / 字符串匹配语义。"""
    low = msg.lower()
    if any(k in low for k in ("unique", "foreign key", "not null", "check constraint")):
        return sqlite3.IntegrityError(msg)
    return sqlite3.OperationalError(msg)


def _is_only_comments(stmt: str) -> bool:
    lines = [ln.strip() for ln in stmt.splitlines()]
    return all((not ln) or ln.startswith("--") for ln in lines)


class TursoConnection:
    """无状态连接：每次 execute 一个 HTTP 请求（execute + close），可多线程共享。"""

    def __init__(self, url: str, token: str, client: httpx.Client | None = None):
        self._url = url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=30.0)

    def _pipeline(self, stmts: list[tuple[str, tuple]]) -> list[dict]:
        body = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": [_encode_arg(v) for v in p]}}
                for sql, p in stmts
            ]
            + [{"type": "close"}]
        }
        resp = self._client.post(
            f"{self._url}/v2/pipeline",
            json=body,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code != 200:
            raise sqlite3.OperationalError(
                f"Turso HTTP {resp.status_code}: {resp.text[:300]}"
            )
        results = resp.json().get("results", [])
        exec_results = []
        for r in results:
            if r.get("type") == "error":
                raise _map_error(r.get("error", {}).get("message", "unknown Turso error"))
            if r.get("type") == "ok" and r.get("response", {}).get("type") == "execute":
                exec_results.append(r["response"]["result"])
        return exec_results

    def execute(self, sql: str, params=()) -> TursoCursor:
        res = self._pipeline([(sql, tuple(params))])[0]
        cols = [c["name"] for c in res.get("cols", [])]
        rows = [[_decode_cell(c) for c in row] for row in res.get("rows", [])]
        return TursoCursor(cols, rows)

    def execute_many(self, stmts: list[tuple[str, tuple]]) -> list[dict]:
        """单次 HTTP 请求批量执行多条语句（数据迁移等写入密集场景）。"""
        return self._pipeline([(s, tuple(p)) for s, p in stmts])

    def executescript(self, script: str) -> None:
        stmts = [
            (s, ()) for s in (x.strip() for x in script.split(";"))
            if s and not _is_only_comments(s)
        ]
        if stmts:
            self._pipeline(stmts)

    # sqlite3 连接上下文语义：异常向上抛、成功即完成。
    # 与本地 SQLite 的差异：同一 with 块内多条语句各自独立提交，中途失败不回滚前面的语句。
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self) -> None:  # 兼容 sqlite3 接口面；共享连接实际不关闭
        pass


def connect(database_url: str, auth_token: str, client: httpx.Client | None = None) -> TursoConnection:
    """libsql:// / turso:// 协议头统一转为 https://。"""
    url = database_url.strip()
    for prefix in ("libsql://", "turso://"):
        if url.startswith(prefix):
            url = "https://" + url[len(prefix):]
            break
    if not url.startswith("https://"):
        raise ValueError("TURSO_DATABASE_URL 需为 libsql:// 或 https:// 开头")
    if client is None:
        client = httpx.Client(timeout=30.0, proxy=_detect_system_proxy())
    return TursoConnection(url, auth_token, client=client)


def _detect_system_proxy() -> str | None:
    """读取 Windows 系统代理（Clash 等工具开启时自动走代理，解决本地直连 turso.io 被墙）。
    优先级低于 HTTPS_PROXY 环境变量；非 Windows / 未开启代理 / PAC 配置返回 None（直连，
    Render 等 Linux 服务器即走此路径）。"""
    if os.name != "nt":
        return None
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        try:
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
        finally:
            winreg.CloseKey(key)
        if not enable or not server or ".pac" in server:
            return None
        if "=" in server:  # 形如 http=127.0.0.1:7890;https=127.0.0.1:7890
            parts = dict(p.split("=", 1) for p in server.split(";") if "=" in p)
            server = parts.get("https") or parts.get("http") or ""
        if not server:
            return None
        if not server.startswith("http"):
            server = "http://" + server
        return server
    except OSError:
        return None
