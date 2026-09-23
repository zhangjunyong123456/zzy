"""Turso 真实云库冒烟测试：建表/密钥/token/用户/会话/消息 全链路。跑完自动清理数据。"""
import app.core.security as sec
from app.config import settings

assert settings.turso_database_url, "TURSO_DATABASE_URL 未配置"
print("URL:", settings.turso_database_url)

from app.database import get_conn, init_db

init_db()
print("[1] init_db OK —— 表已在云库建好")

# 密钥持久化（app_meta）
sec._secret_cache = None
s1 = sec._load_secret()
sec._secret_cache = None
s2 = sec._load_secret()
assert s1 == s2, "两次加载密钥不一致"
print("[2] secret_key 已写入 app_meta 并可复读:", s1[:8].hex(), "...")

# token 签发/验签
tok = sec.create_token("smoke-user")
assert sec.decode_token(tok)["uid"] == "smoke-user"
print("[3] token 签发/验签 OK")

# 用户注册 + UNIQUE 语义
from app.services import session_service, user_service

u = user_service.create_user("smoketest001", "pass123456", "冒烟")
print("[4] 注册用户 OK:", u["username"])
try:
    user_service.create_user("smoketest001", "pass123456")
    raise SystemExit("ERROR: 重复注册未触发 UNIQUE")
except ValueError as e:
    print("[5] UNIQUE 冲突正确映射:", e)

# 会话 + 消息
sid = session_service.create_session("冒烟会话", user_id=u["id"])
session_service.add_message(sid, "user", None, "你好，云库")
msgs = session_service.get_messages(sid)
assert len(msgs) == 1 and msgs[0]["content"] == "你好，云库"
print("[6] 会话/消息 写读 OK:", len(msgs), "条")

# 列表查询（含子查询聚合）
sess = session_service.list_sessions(u["id"])
assert any(x["id"] == sid for x in sess)
print("[7] list_sessions OK:", len(sess), "个会话")

# 清理冒烟数据（保留 app_meta 的密钥，它本来就该持久）
with get_conn() as c:
    c.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
    c.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    c.execute("DELETE FROM users WHERE id = ?", (u["id"],))
print("[8] 冒烟数据已清理；全链路通过 ✔")
