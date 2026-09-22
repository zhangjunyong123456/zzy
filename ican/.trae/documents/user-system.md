# UniGrow Agent 用户系统实施计划

## Context

用户要求为 UniGrow Agent 添加用户系统：注册/登录，用户可填写个人画像（专业、年级、兴趣爱好、经历/背景、发展目标，外加昵称），AI 回答时自动结合画像个性化。

已确认的策略：
- **游客可用**：未登录仍可正常使用（现状行为不变）；登录后更智能
- **登录后会话隔离**：会话与用户绑定，互不可见
- **零新增 pip 依赖**：PBKDF2 密码哈希 + HMAC-SHA256 签名 Token（Bearer 头）

## 阶段 1：后端安全基础

### 1.1 修改 `backend/app/config.py`
新增字段：`secret_key: str = ""`、`secret_file: str = "./data/secret.key"`、`token_expire_days: int = 7`

### 1.2 新建 `backend/app/core/security.py`（+ `backend/app/core/__init__.py`）
- `hash_password(password)`：`secrets.token_hex(16)` 作盐，`hashlib.pbkdf2_hmac("sha256", pwd, salt, 120_000)`，存 `pbkdf2$<salt>$<hash>`
- `verify_password(password, stored)`：重算后 `hmac.compare_digest` 比对
- `_load_secret()`：`settings.secret_key` 非空则用之；否则读 `data/secret.key`，不存在则 `secrets.token_hex(32)` 生成写入
- `create_token(uid)`：payload `{uid, exp}` → base64url JSON → HMAC-SHA256 签名 → `body.sig`
- `decode_token(token)`：验签+验 exp，任何异常返回 None（绝不抛出）

### 1.3 修改 `backend/app/database.py`
- `_SCHEMA` 追加 `users` 表：
```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL DEFAULT '',
    major TEXT NOT NULL DEFAULT '',
    grade TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT '',
    experience TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
```
- `init_db()` 在 executescript 后做幂等迁移：
```python
cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
if "user_id" not in cols:
    conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
```

## 阶段 2：用户服务与认证接口

### 2.1 新建 `backend/app/services/user_service.py`
- `to_public(row)`：剔除 password_hash
- `create_user(username, password, nickname="")`：username 3-32、密码 6-64；UNIQUE 冲突抛 ValueError（API 层映射 400）；id=uuid4().hex
- `get_user_by_id(uid)` / `get_user_with_hash_by_username(username)` / `verify_login(username, password)`
- `update_profile(uid, fields)`：白名单 `{nickname, major, grade, interests, experience, goal}` 动态 SET

### 2.2 新建 `backend/app/api/deps.py`
- `get_current_user_optional(authorization: Header)`：非 Bearer 或 decode 失败 → None；否则查库返回 user
- `require_user(user=Depends(...))`：None 时 `HTTPException(401, {"code":"unauthorized","message":"请先登录"})`

### 2.3 新建 `backend/app/api/auth.py`
| 方法 | 路径 | 依赖 | 请求体 | 成功 | 失败 |
|---|---|---|---|---|---|
| POST | `/auth/register` | 无 | `{username, password, nickname?}` | `{token, user}`（注册即登录） | 400 已存在/格式错 |
| POST | `/auth/login` | 无 | `{username, password}` | `{token, user}` | 401 |
| GET | `/auth/me` | require_user | — | user | 401 |
| PATCH | `/auth/profile` | require_user | 五字段+昵称可选 | user | 401 |

### 2.4 修改 `backend/app/main.py`
注册 `auth.router`。

## 阶段 3：会话隔离与画像个性化

### 3.1 修改 `backend/app/services/session_service.py`
- `create_session(title, user_id=None)` — INSERT 增加该列
- `list_sessions(user_id=None)`：user_id=None → `WHERE s.user_id IS NULL`（游客）；否则 `WHERE s.user_id = ?`
- 新增 `get_session_row(session_id)`：`SELECT id, user_id FROM sessions WHERE id = ?`（归属校验用）

### 3.2 修改 `backend/app/api/sessions.py`
每个端点加 `Depends(get_current_user_optional)`，`uid = user["id"] if user else None`：
- GET/POST /sessions 按.uid 过滤/写入
- GET/PATCH/DELETE /sessions/{id} 先校验归属：`row is None or (row["user_id"] or None) != uid` → 404（防枚举）。游客 uid=None 与 NULL 相等 → 现状行为完全保留

### 3.3 修改 `backend/app/api/chat.py`
- 签名加 optional user；`req.session_id` 存在时先做归属校验（404）
- `session_id = req.session_id or session_service.create_session(user_id=uid)`
- `profile_text = build_profile_text(user) if user else ""` → `stream_chat(..., user_profile=profile_text)`

### 3.4 新建 `backend/app/agents/profile.py`
```python
def build_profile_text(user: dict | None) -> str:
    """游客返回 ""；登录用户返回画像块，空字段跳过。"""
```
格式：
```
【用户画像】请结合以下用户信息个性化你的回答（自然融入即可，不要复述或逐条解释）：
- 昵称：... / 专业：... / 年级：... / 兴趣爱好：... / 经历/背景：... / 发展目标：...
```

### 3.5 修改 `backend/app/agents/state.py`
`UniGrowState` 增加 `user_profile: str`

### 3.6 修改 `backend/app/agents/supervisor.py`
- `stream_chat(..., user_profile: str = "")` → inputs 增加 user_profile
- `_make_worker`：`agent.stream_to(sub_query, history, doc_ids, q, user_profile=state.get("user_profile", ""))`
- `aggregator_node`：user_profile 非空时追加到 SystemMessage

### 3.7 修改 `backend/app/agents/base.py`
`stream_to(..., user_profile: str = "")`：SystemMessage 内容 = `self.system_prompt + (f"\n\n{user_profile}" if user_profile else "")`

### 3.8 不改动
`pet.py`、`documents.py`（文档全局共享，本期不隔离）、`router.py`、`requirements.txt`

## 阶段 4：后端测试

- 修改 `backend/tests/conftest.py`：app import 之前加 `os.environ.setdefault("SECRET_KEY", "test-secret")`
- 新建 `tests/test_auth.py`：注册成功/重名400/登录/错密码401/无token访问me 401/PATCH profile 生效/篡改token 401
- 新建 `tests/test_sessions_scoping.py`：游客只见游客会话；用户A会话对用户B 404；跨用户 chat/stream 404（用 fake_llm）
- 新建 `tests/test_profile.py`：单元测 `build_profile_text`（None→""、空字段跳过）；集成测 FakeLLM 捕获 messages，带头时 SystemMessage 含画像文本、不带头不含

## 阶段 5：前端 API 层与状态

### 5.1 新建 `frontend/src/api/auth.js`
`register / login / me / updateProfile` 四个函数，复用现有 `api` 实例

### 5.2 修改 `frontend/src/api/client.js`
- 请求拦截器：localStorage 有 `ug_token` → `Authorization: Bearer <token>`
- 响应拦截器：401 且非 /auth/login|register → 清 token/user，`dispatchEvent('ug:unauthorized')`

### 5.3 新建 `frontend/src/stores/user.js`
- state：token、user（localStorage 持久化 `ug_token`/`ug_user`）
- getter：isLoggedIn
- actions：login/register（持久化）、logout（清空）、updateProfile、init（监听 ug:unauthorized → 提示"登录已过期"降级游客）

### 5.4 修改 `frontend/src/api/sse.js` + `chat.js`
`streamSSE` 增加 token 参数 → fetch headers 加 Authorization；`sendMessage` 内部读 localStorage 传入

## 阶段 6：前端路由与页面

### 6.1 修改 `frontend/src/router/index.js`
- 新路由 `/login`（LoginView）、`/profile`（ProfileView，`meta:{requiresAuth:true}`）
- 守卫只拦 `/profile`（游客其余全放行）：无 token → 重定向 `/login?redirect=...`

### 6.2 新建 `frontend/src/views/LoginView.vue`
el-tabs「登录/注册」，白底珊瑚色风格（复用 --accent 等设计变量）；成功后 loadSessions + 跳转 redirect || /chat；提供"游客模式先逛逛"链接

### 6.3 新建 `frontend/src/views/ProfileView.vue`
el-form 六字段：昵称、专业、年级、兴趣爱好、经历/背景（textarea）、发展目标（textarea）；用户名只读；保存调 updateProfile

### 6.4 修改 `frontend/src/components/layout/HeaderBar.vue`
右侧新增（API Key tag 之后）：
- 游客：「登录 / 注册」按钮 → /login
- 已登录：el-avatar（昵称首字，珊瑚色）+ el-dropdown（个人资料 → /profile、退出登录 → logout + newSession + loadSessions）

### 6.5 修改 `frontend/src/App.vue`
`onMounted` 调 `useUserStore().init()`

## 边界场景

1. **SSE 流中途 token 过期**：入口校验一次，已建立流不中断；下次请求 401 → 全局降级游客态
2. **游客历史会话登录后**：登录后列表只显示本人会话；孤儿游客会话留在库中，退出登录后仍可见（不做迁移）
3. **跨用户访问**：统一 404 防枚举
4. **secret.key 丢失**：全部 token 失效需重新登录，可接受
5. **迁移幂等**：PRAGMA table_info 守护 ALTER TABLE，重复启动不报错

## 验证

1. `cd backend && python -m pytest tests/ -x -q` 全绿（新 3 个测试文件 + 既有 3 个）
2. 用现有 `data/ican.db` 启动后端，确认启动无错、sessions 表新增 user_id 列、老数据为 NULL
3. 浏览器 E2E（`npm run dev`）：
   - 游客态回归：/chat 对话、会话列表正常
   - 注册 → 自动登录 → 头像显示；新建会话后退出 → 列表空 → 再登录 → 会话回来
   - 双浏览器上下文注册 A/B，互不可见对方会话
   - 填画像（如"计算机/大二/考研"）提问"帮我规划这学期"，对比游客回答体现个性化
   - localStorage 改乱 token → 刷新 → 401 → 降级游客并提示
   - 未登录访问 /profile → 重定向 /login
