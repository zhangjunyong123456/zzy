# 对话附件 + 记忆系统 实施计划

## Context

用户需要两个功能：
1. **对话附件**：聊天时上传「图片 / PDF / Word / TXT」，AI 解析提取信息辅助回答。图片由视觉模型（智谱 glm-4v-flash，用户已确认）提取内容文本；主对话模型不支持图片，不改多模态消息格式。
2. **记忆系统**：用户从历史会话中勾选部分消息保存为可命名的「记忆」；聊天时手动勾选启用若干记忆注入当前对话上下文，解决对话过长上下文丢失问题。记忆按用户隔离（游客 user_id=NULL，与 sessions 表同模式）。

现有可复用范式：数据库幂等迁移（database.py PRAGMA table_info + ALTER TABLE）、prompt 注入（base.py RAG「【参考资料】」段、supervisor.py user_profile 段）、归属校验（chat.py session user_id 比对）、PDF 解析（rag/parser.py pymupdf）、lru_cache 热更教训（get_llm.cache_clear）。

## 关键设计决策

| # | 决策 | 理由 |
|---|------|------|
| A1 | `POST /api/chat/upload`，session_id 可选；未选会话时附件暂存（session_id=NULL），发消息时绑定 | 首条消息发送前会话尚不存在 |
| A2 | 图片存 `{upload_dir}/attachments/`（uuid 文件名），经 `GET /api/attachments/{id}/raw` 归属校验返回；**不用 StaticFiles** | StaticFiles 无法鉴权 |
| A3 | 前端图片预览走 axios blob → objectURL（带 Bearer 头） | `<img src>` 带不了 Authorization |
| A4 | 附件文本注入最后一条 HumanMessage「【附件内容】」段（改 base.py 一处覆盖 6 个 agent）；记忆注入 SystemMessage「【历史记忆】」段（与 user_profile 同范式） | 附件≈本次资料（同 RAG）；记忆≈长期画像（同 profile） |
| A5 | 多 agent 并行均注入 + 硬上限（附件 8000 字、记忆 4000 字，截断加「（已截断）」） | worker 的 sub_query 独立改写，缺上下文会答偏；截断控成本 |
| B1 | 入口组合：Sidebar 会话项「保存记忆」弹窗勾选消息 + InputBar 🧠 按钮 Popover 管理启用，启用的记忆以 chips 显示在输入栏上方 | 创建需会话级消息清单；启用是输入时决策 |
| B2 | 启用状态仅存前端（`activeMemoryIds`），随 ChatRequest.memory_ids 每条消息发送 | 零库表改动 |

## 一、后端改动

### 新增文件
- `backend/app/api/attachments.py`：POST /chat/upload（multipart）+ GET /attachments/{id}/raw（归属校验 FileResponse）
- `backend/app/services/attachment_service.py`：落盘、按类型提取（图片→视觉模型 / PDF→parse_pdf / docx→python-docx / txt、md→utf-8 失败退 gbk，asyncio.to_thread 包裹）、建行/查询/绑定、拼接截断
- `backend/app/api/memories.py`：POST/GET/PUT/DELETE /memories
- `backend/app/services/memory_service.py`：CRUD、按消息 ids 渲染「用户：…／助手：…」、8000 字截断

### 修改文件
- `app/database.py`：_SCHEMA 增 attachments/memories 两表；messages 幂等补 `attachments` 列（照抄 user_id 范式）
- `app/config.py`：增 `zhipu_vision_model: str = "glm-4v-flash"`
- `app/agents/llm.py`：增 `@lru_cache get_vision_llm()`（zhipu 配置，streaming=False）
- `app/main.py`：include memories、attachments router
- `app/schemas.py`：ChatRequest 增 `attachment_ids`/`memory_ids`；MessageOut 增 `attachments`；新增 AttachmentOut/MemoryOut
- `app/api/chat.py`：校验/绑定附件与记忆归属（越权 id 静默忽略）→ 构造两段文本 → 传 stream_chat；demo 模式同绑定不注入
- `app/agents/supervisor.py`：stream_chat 增 `attachments_text`/`memory_text` 参数入 inputs，worker 透传
- `app/agents/state.py`：UniGrowState 增两字段（total=False）
- `app/agents/base.py`：stream_to 增两参数：memory_text 拼 SystemMessage；attachments_text 传入 compose_user_message（顺序：附件段在前、参考资料段在后）
- `app/services/session_service.py`：增 `bind_attachments(message_id, session_id, att_ids)`；get_messages SELECT 增 attachments 列
- `app/api/system.py`：Key/模型热更处增 `get_vision_llm.cache_clear()`
- `requirements.txt`：增 `python-docx`

### 数据库迁移（init_db 内，幂等）

```sql
ALTER TABLE messages ADD COLUMN attachments TEXT;  -- JSON: [{"id","filename","kind","mime"}]
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT, message_id TEXT,
  filename TEXT NOT NULL, mime TEXT NOT NULL, kind TEXT NOT NULL,  -- image|file
  path TEXT NOT NULL, size INTEGER DEFAULT 0,
  extracted_text TEXT DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY, user_id TEXT, title TEXT NOT NULL, content TEXT NOT NULL,
  source_session_id TEXT, source_message_ids TEXT DEFAULT '[]', created_at TEXT NOT NULL
);
```

### API 契约

```
POST /api/chat/upload   FormData: file, session_id?
→ {"id","filename","mime","kind","size","extracted_text","warning","url":"/api/attachments/{id}/raw"}
  图片无智谱 Key → extracted_text="" + warning 引导去 /profile?tab=models；400 类型白名单(png/jpg/jpeg/webp/pdf/docx/txt/md)/超限(max_upload_mb)

POST /api/memories  {"title?","source_session_id","message_ids":[]}
→ MemoryOut（content="用户：…\n助手：…"，8000 字截断；404 会话归属校验）
GET  /api/memories → [MemoryOut]（游客只看 user_id IS NULL）
PUT  /api/memories/{id} {"title"} / DELETE → {"ok":true}

ChatRequest: {"session_id","message","doc_ids":[],"attachment_ids":[],"memory_ids":[]}
```

### 视觉模型调用（attachment_service.extract_image）

无智谱 Key 直接返回空；否则读文件 base64，构造 HumanMessage content 数组：
`[{"type":"text","text":"请完整描述图片中的文字与内容…"},{"type":"image_url","image_url":{"url":"data:{mime};base64,{b64}"}}]`
→ `get_vision_llm().ainvoke`，结果截 8000 字，异常仅 warning 不阻塞上传。

### Prompt 注入格式

```
SystemMessage: {agent 系统提示}\n\n{用户画像}\n\n【历史记忆】\n「秋招复盘」\n用户：…\n助手：…
HumanMessage:  {sub_query}\n\n【附件内容】\n[附件：简历.docx]\n…\n\n【参考资料】\n[来源：第3页]\n…
```

## 二、前端改动

### 新增
- `src/api/attachment.js`（upload / raw blob）、`src/api/memory.js`
- `src/components/chat/PendingAttachments.vue`（待发送附件条：图片本地 blob 缩略图、文件名+大小、× 删除）
- `src/components/chat/MemoryPanel.vue`（🧠 Popover：启用 checkbox / 重命名 / 删除 / 空态引导）
- `src/components/chat/MemorySaveDialog.vue`（会话消息 el-checkbox 勾选 + 命名，默认名取首条消息前 20 字）

### 修改
- `InputBar.vue`：📎 按钮 + 隐藏 input[type=file]（accept 白名单，multiple，流式中禁用）；🧠 按钮；输入栏上方启用记忆 chips（可 × 取消）；doSend 传附件与记忆
- `UserMessage.vue`：渲染附件卡——el-image 缩略图预览大图、文件名点击下载 raw blob
- `Sidebar.vue`：会话项加「保存记忆」入口
- `stores/chat.js`：pendingAttachments / memories / activeMemoryIds / objectURL 缓存 Map；send 扩展参数；selectSession 映射 m.attachments
- `src/api/chat.js`：body 增 `attachment_ids` / `memory_ids`

## 三、测试（现 41 例全过为底线）

- 新增 `test_memories.py`：CRUD、游客/登录隔离、渲染格式、8000 截断、归属 404
- 新增 `test_attachments.py`：白名单/超限 400；txt/pdf/docx 提取；图片 monkeypatch 假视觉模型；无 Key warning；raw 403/404；暂存→发送绑定
- 新增 `test_chat_injection.py`：fake LLM 捕获 messages，断言「【附件内容】」「【历史记忆】」注入；越权 id 忽略
- 新增 `test_migrations.py`：老库构造 → init_db() → 迁移成功旧数据可查
- conftest.py fake LLM 增消息捕获；现有 chat/sse 测试因新字段带默认值预计不改

## 四、实施顺序

| 里程碑 | 内容 | 验证 |
|---|---|---|
| M1 | 记忆后端（表+service+API+注入链路+测试） | pytest 全过 + curl |
| M2 | 附件后端（表+上传/提取/raw+绑定+视觉模型+测试） | pytest + curl 各类型文件 |
| M3 | 前端附件（上传/预览/历史回显） | npm run build + 页面手测游客/登录两态 |
| M4 | 前端记忆（保存/启用/删除 + 回答体现记忆） | build + 手测 |
| M5 | 回归：现网 ican.db 备份后启动验证迁移；全量 pytest + build | 全过 |

## 五、风险与边界

1. 图片鉴权用 blob 方案，勿用 StaticFiles
2. 视觉模型不可用：附件照存 + warning，不阻塞发送
3. token 控制：附件提取/注入 8000、记忆注入 4000 上限，截断加「（已截断）」
4. python-docx 仅支持 .docx，.doc 直接 400 提示转存
5. 向后兼容：老消息 attachments 为 NULL → 默认 `[]`；迁移幂等
6. get_vision_llm 热更必须 cache_clear（复用 get_llm 教训）
7. demo 模式附件可传可回显但不参与回答，notice 说明
8. 落盘文件名 uuid，杜绝路径穿越；pytest 不读 .env（视觉模型 mock）
