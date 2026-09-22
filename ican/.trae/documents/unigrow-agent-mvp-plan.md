# UniGrow Agent（智学成长Agent）MVP 实现计划

## Context

新建 iCAN 竞赛参赛项目：面向大学生的多智能体成长平台。用户通过一个聊天窗口获得学习/科研/竞赛/求职/校园五大场景的智能服务。项目目录 `c:\YY\ai\trea\ican` 当前为空，从零搭建。

**已确认决策**：
- 范围：全骨架 MVP —— 主Agent + 5 个专业Agent 全部接入，每个 Agent 实现 1-2 个核心功能，架构可扩展
- 大模型：DeepSeek（OpenAI 兼容接口），API Key 由用户配置
- 用途：竞赛演示，UI 精美、交互流畅、有演示亮点（多Agent并行打字 + 调度链路可视化）

**环境实测事实**（已验证）：
- 本机 `python` 为 Store 占位 stub、`py` launcher 指向失效路径 → **P0 必须先装 Python 3.12**（winget），全程用 `.venv\Scripts\python.exe` 或 `python -m`，不依赖 `py`
- Node v24.14.1 ✓、git 2.54 ✓、uv 未安装
- DeepSeek 模型名近期有变更（deepseek-chat → 新模型名），**模型名必须走 .env 配置，代码零硬编码**；.env.example 注明"若报模型不存在则改为官方当前模型名"

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue3 + Vite 7 + Element Plus + Pinia + markdown-it + highlight.js |
| 后端 | FastAPI + uvicorn，SQLite（标准库 sqlite3, WAL） |
| 编排 | LangGraph 1.x 手工 StateGraph supervisor（不用 langgraph-supervisor 包） |
| LLM | langchain-openai ChatOpenAI → DeepSeek（base_url=https://api.deepseek.com） |
| 向量库 | Chroma PersistentClient（本地持久化 backend/data/chroma） |
| Embedding | fastembed + BAAI/bge-small-zh-v1.5（ONNX 无 torch 依赖，中文效果好） |
| PDF 解析 | PyMuPDF（要求 Python ≥3.10 → 定 3.12） |
| 流式 | SSE（FastAPI StreamingResponse；前端 fetch + ReadableStream 手动解析） |

## 核心架构设计

### LangGraph 多Agent编排
- **router 节点**：`with_structured_output(RouteDecision)` 一次调用返回 `{agents: [...], complexity: single|multi, sub_queries: {agent: 改写子问题}, plan_summary}`；解析失败 fallback 到 main 兜底
- **并行 fan-out**：multi 时条件边同一 super-step 派发多个 worker 节点并行执行
- **State**：`agent_outputs: Annotated[list, operator.or_]`（并行写必须带 reducer，否则 InvalidUpdateError）
- **aggregator 节点**：multi 路径末尾一次 LLM 调用生成综合成长建议（金色汇总卡）；single 路径跳过
- **流式归属**：`graph.astream(stream_mode=["messages","updates"])`，AIMessageChunk metadata 的 `langgraph_node` → 映射为 SSE token 事件的 `agent` 字段；**P3 首日实测该字段，若缺失则切 asyncio.Queue 应用层上报 fallback（协议不变）**

### SSE 事件协议（前后端契约）
`event: <type>\ndata: <json>\n\n`，事件类型：
`route_plan`（调度计划）→ `agent_start`（agent名/图标/颜色）→ `token {agent, content}`（并行打字）→ `agent_end` → `summary_start/summary_token/summary_end`（汇总卡）→ `done`；`error {agent?, message, recoverable}`（429等映射为可恢复错误）

### RAG 管线
上传(≤20MB/300页) → PyMuPDF 按页提取 → RecursiveCharacterTextSplitter(500/50) → fastembed bge-small-zh → Chroma(collection=ican_docs, metadata: doc_id/scene/page/seq)；检索 top_k=5，回答附"[来源: 第N页]"。校园Agent用 seed 脚本预灌虚构"示例大学"知识库。

### 后端 API
- `POST /api/chat/stream`（SSE 主通道）
- `GET/POST /api/sessions`、`GET/DELETE /api/sessions/{id}`
- `POST /api/documents/upload`、`GET /api/documents`、`DELETE /api/documents/{id}`（同步解析，不做任务队列）
- `GET /api/health`、`GET /api/config/status`（API Key 未配置时前端引导页）

### 五个专业Agent功能
| Agent | 功能1 | 功能2 |
|---|---|---|
| 学习 | PDF RAG问答 | AI笔记（重点/难点/考点） |
| 科研 | 文献结构化分析 | 200/500字摘要 |
| 竞赛 | 赛题分析 | 项目周计划+团队分工 |
| 求职 | 简历优化建议 | 面试模拟（prompt多轮） |
| 校园 | 校园知识库RAG问答 | 活动推荐 |
| 主 | 意图路由+汇总 | 兜底通用回答 |

## 目录结构

```
ican\
├── README.md  .gitignore
├── scripts\warmup_models.py（预下载bge模型）  seed_demo.py（灌校园知识库）
├── backend\
│   ├── .env.example  requirements.txt  run.py（设PYTHONUTF8=1）
│   └── app\
│       ├── main.py  config.py(pydantic-settings)  database.py  schemas.py  sse.py
│       ├── api\ chat.py  sessions.py  documents.py  system.py
│       ├── agents\ state.py  llm.py  prompts.py  router.py  supervisor.py  base.py
│       │           study_agent.py  research_agent.py  competition_agent.py
│       │           career_agent.py  campus_agent.py
│       ├── rag\ parser.py  chunker.py  embeddings.py  vectorstore.py  retriever.py
│       ├── services\ session_service.py  doc_service.py
│       └── tests\ test_router.py  test_sse_contract.py  test_rag_pipeline.py
└── frontend\
    ├── vite.config.js（proxy /api → 127.0.0.1:8000）
    └── src\
        ├── views\ ChatView.vue（三栏）  DocsView.vue
        ├── stores\ chat.js（SSE事件归并）  docs.js
        ├── api\ client.js  sse.js（SSE解析核心）  chat.js  documents.js
        ├── components\chat\ ChatWindow  AgentMessage(主题色卡片+打字机)  SummaryCard
        │                  RouteTimeline(★调度链路可视化)  MarkdownRenderer  InputBar(示例chip)
        ├── components\docs\ DocManager  UploadPanel
        ├── components\layout\ Sidebar  HeaderBar(Agent呼吸灯)
        └── styles\main.scss（每Agent一色：学习蓝/科研紫/竞赛橙/求职绿/校园青/主金）
```

## 实现步骤

| Phase | 内容 | 验收 |
|---|---|---|
| P0 环境 | winget 装 Python 3.12 + venv；写 .gitignore/.env.example/requirements.txt | python 3.12 可用、依赖装完 |
| P1 后端骨架 | FastAPI+CORS+config+database 建表+/api/health | uvicorn 起服务，health 通 |
| P2 LLM直通+SSE | llm.py、sse.py、/api/chat/stream 单模型直通、sessions 持久化 | curl 看到 token 流，重启历史在 |
| P3 supervisor单路由 | state/router/图(single路径)/5 agent骨架；**实测 langgraph_node 归属** | 单 agent 问题正确路由，SSE 带 agent 字段 |
| P4 并行+汇总 | 条件边 fan-out、reducer、aggregator | "参加iCAN"触发 3 agent 并行+汇总卡 |
| P5 RAG管线（可与P3/P4并行） | rag/全套、doc_service、documents API、warmup | 上传PDF→ready→检索命中 |
| P6 学习/科研完善 | RAG问答、AI笔记、文献分析、摘要 | 输出符合结构约定 |
| P7 竞赛/求职/校园 | 各功能 + seed_demo 灌校园库 | 五场景示例问题达标 |
| P8 前端骨架 | Vite+EP+Pinia、SSE解析器、聊天窗、会话列表 | 对话+单agent流式渲染 |
| P9 前端完整化 | RouteTimeline、并行多卡、汇总卡、DocsView、示例chip、引导/错误页 | 全功能可演示 |
| P10 测试打磨 | pytest 三件套、smoke脚本、README、主题美化 | E2E 清单全绿 |

关键路径：P0→P1→P2→P3→P4→P8→P9；P5 独立可并行。

## 验证方式

- 自动化：pytest（路由决策断言 mock LLM、SSE 事件序列契约、RAG fixture PDF 检索命中）
- 手动冒烟：五场景示例问题逐一验证路由；"我要参加iCAN比赛"验证并行+汇总；上传课件→笔记生成→追问引用页码；面试模拟多轮记忆；输错Key→error 事件优雅呈现
- 前端：`npm run build` 零报错 + dev 全流程手测
- 注意 Windows 下用 `curl.exe`（非 PowerShell 别名）

## 风险与对策

1. **LangGraph 1.x API 与旧教程不一致** → 锁 1.2.x，以官方文档为准，P3 实测流式归属，备 asyncio.Queue fallback
2. **DeepSeek 模型名漂移** → 全走 .env，代码零硬编码
3. **429 限流**（并行耗3-4倍token）→ 可恢复 error 事件+重试按钮+1次指数退避
4. **fastembed 首次下载慢** → warmup 脚本 + HF_ENDPOINT=hf-mirror.com 注释
5. **Windows 编码** → PYTHONUTF8=1，文件 I/O 显式 utf-8
6. **SSE 被缓冲** → no-cache 头 + 逐事件 flush + 15s 心跳，演示时关系统代理
