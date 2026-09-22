# UniGrow Agent（智学成长Agent）

面向大学生全生命周期的多智能体成长平台。一个聊天入口，覆盖 **学习 · 科研 · 竞赛 · 求职 · 校园** 五大场景。

```text
                    主Agent（意图路由 → 并行调度 → 汇总）
                        │
 ┌──────────┬──────────┬──────────┬──────────┬──────────┐
 学习Agent  科研Agent  竞赛Agent  求职Agent  校园Agent
 PDF问答    文献分析    赛题分析    简历优化    校园问答
 AI笔记     论文摘要    项目规划    面试模拟    活动推荐
     │          │          │          │          │
     └──── Chroma 向量知识库（课程资料 / 论文 / 简历 / 校园信息）────┘
```

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue3 + Vite + Element Plus + Pinia |
| 后端 | FastAPI + SQLite（WAL） |
| 多Agent编排 | LangGraph（supervisor：结构化输出路由 → 并行 fan-out → 汇总） |
| 大模型 | DeepSeek（OpenAI 兼容接口，模型名可配置） |
| 向量库 | Chroma（嵌入式持久化） |
| Embedding | fastembed + BAAI/bge-small-zh-v1.5（本地 ONNX，无 torch） |
| 文档解析 | PyMuPDF |
| 流式输出 | SSE（带 agent 归属字段，前端多卡片并行打字） |

## 快速开始

### 1. 配置 API Key

在 [platform.deepseek.com](https://platform.deepseek.com) 申请 Key，编辑 `backend/.env`：

```ini
DEEPSEEK_API_KEY=sk-xxxx
# 若提示"模型不存在"，请改为 DeepSeek 官方文档当前的模型名
DEEPSEEK_MODEL=deepseek-chat
```

### 2. 启动后端（首次先预热 embedding 模型 + 灌入校园知识库）

```powershell
# 项目根目录执行（Windows，Python 3.12 venv 已就绪）
.\.venv\Scripts\python.exe scripts\warmup_models.py   # 首次下载 ~100MB 模型
.\.venv\Scripts\python.exe scripts\seed_demo.py       # 预置校园知识库

cd backend
..\ .venv\Scripts\python.exe run.py                   # 服务运行于 127.0.0.1:8000
```

### 3. 启动前端

```powershell
cd frontend
npm install     # 首次
npm run dev     # 运行于 http://localhost:5173
```

浏览器打开 http://localhost:5173 即可使用。

## 演示要点（iCAN）

1. **多Agent并行协同**：输入"我要参加 iCAN 比赛，帮我全面规划"→ 主Agent 调度竞赛+科研+学习三个 Agent 并行作答（右侧链路图 + 三张彩色卡片同时打字），最后生成金色汇总卡"综合成长行动建议"。
2. **PDF 即传即问**：知识库页上传课件 → 回对话问"总结这份课件的考点"，回答带"（来源: 第N页）"页码标注。
3. **一键示例问题**：输入框上方五个场景示例，零打字演示。
4. **面试模拟**：对求职Agent说"模拟一场前端工程师的技术面试"，支持多轮问答与点评。

## 后端 API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/chat/stream | SSE 聊天主通道（route_plan / agent_start / token / summary_* / done 事件） |
| GET/POST | /api/sessions | 会话列表 / 新建；GET·DELETE /api/sessions/{id} 历史·删除 |
| POST | /api/documents/upload | 上传 PDF（multipart：file + scene） |
| GET/DELETE | /api/documents | 文档列表 / 删除（含向量数据） |
| GET | /api/health · /api/config/status | 健康检查 / API Key 配置状态 |

## 测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests -q    # 路由 / SSE契约 / RAG管线
```

## 目录结构

```
backend/app
├── agents/    # supervisor 编排 + router + 6个Agent（study/research/competition/career/campus/main）
├── rag/       # parser → chunker → embeddings → vectorstore → retriever
├── api/       # chat(SSE) / sessions / documents / system
├── services/  # session / doc 持久化
└── sse.py schemas.py config.py database.py
frontend/src
├── components/chat/  # 聊天窗 / Agent彩色卡片 / 调度链路图 / 汇总卡
├── components/docs/  # 上传面板 / 知识库管理
└── stores/ api/      # Pinia 状态与 SSE 解析
```

## 常见问题

- **提示"未配置 API Key"**：编辑 `backend/.env` 填入 `DEEPSEEK_API_KEY` 后重启后端。
- **首次上传文档很慢**：在下载 embedding 模型，先运行 `scripts\warmup_models.py`。
- **模型不存在报错**：DeepSeek 模型名有变更，改 `.env` 中 `DEEPSEEK_MODEL`。
- **429 限流**：并行调度一次消耗 3-4 倍 token，可在前端重试。
