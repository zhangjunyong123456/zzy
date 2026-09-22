# 个人中心（资料 + 使用统计 + 数据分析）实现计划

## Context
现有 /profile 仅是画像表单。用户希望升级为完整"个人中心"：填写资料之外，还能看到自己的使用情况与数据分析（多Agent使用分布、活跃趋势、最近会话等）。已确认：图表用 ECharts、升级现有 /profile 路由、统计维度全选（总览数字卡 / Agent 使用分布 / 近14天活跃趋势 / 最近会话列表）。

数据基础：`messages` 表已记录 role（user/agent/summary）、agent 归属、created_at（UTC ISO）；`sessions` 有 user_id；统计可全部由 SQL 聚合推导，**无需改表结构**。documents 表全局共享（无 user_id），不纳入个人统计。

## 后端（FastAPI + SQLite）

### 1. 新建 `backend/app/services/stats_service.py`
`get_user_stats(user) -> dict`，纯 SQL 聚合（消息无 user_id，须 `messages JOIN sessions ON s.id=m.session_id WHERE s.user_id=?`）：

- **totals**（单条 SQL 用 SUM(CASE)）：question_count（role='user'）、reply_count（role='agent'，summary 不计）、active_days（COUNT(DISTINCT date(created_at,'localtime'))，仅 role='user'）；session_count 单独 COUNT sessions WHERE user_id=?。空表 SUM 返回 None → 兜底 0
- **agent_usage**：GROUP BY agent（role='agent' AND agent IS NOT NULL），Python 端补齐 6 个 agent 的 0 值（AGENTS=("study","research","competition","career","campus","main")）
- **daily（近14天）**：`WHERE m.created_at >= date('now','localtime','-13 days')`，按 `date(m.created_at,'localtime')` 分组；Python 端生成 14 个本地日期键零填充
- **days_since_register**：本地今天 − date(user.created_at[:10]) + 1，min 为 1
- **recent_sessions**：复用 `session_service.list_sessions(user_id)[:5]`
- **member_since**：直接用 user["created_at"]

响应契约：
```json
{"member_since": "...", "totals": {"session_count","question_count","reply_count","active_days","days_since_register"},
 "agent_usage": [{"agent","count"}x6], "daily": [{"date","count"}x14], "recent_sessions": [{"id","title","message_count","updated_at"}]}
```

### 2. `backend/app/api/auth.py` 末尾追加路由
```python
@router.get("/auth/me/stats")
async def my_stats(user: dict = Depends(require_user)):
    return stats_service.get_user_stats(user)
```
（main.py 已挂 /api 前缀，无需改动；游客调不到，require_user 401）

## 前端（Vue3 + Element Plus）

### 3. ECharts 按需引入
- `frontend/` 下 `npm install echarts`
- 新建 `frontend/src/utils/echarts.js`：`echarts/core` + BarChart/LineChart + Grid/Tooltip/Legend + CanvasRenderer，`echarts.use([...])` 后导出

### 4. `frontend/src/api/auth.js` 加 `myStats()`

### 5. 新建 `frontend/src/components/profile/` 组件
| 组件 | 要点 |
|---|---|
| ProfileBanner.vue | 顶部横幅：大头像（首字母，--accent 底）、昵称 + @username、「注册于 YYYY-MM-DD」 |
| StatsOverview.vue | 5 张数字卡 grid（会话/提问/AI回复/活跃天/注册天），<720px 两列 |
| AgentUsageChart.vue | **横向柱状图**（能显式显示 0 值，优于饼图）；6 agent 用主题色 study #E8896B / research #93AB84 / competition #DFA453 / career #86AD72 / campus #7FB39C / main #D9694A；label 显示数值 |
| ActivityTrendChart.vue | 近14天折线 + 珊瑚色渐变 areaStyle，smooth，x 轴 MM-DD |
| RecentSessions.vue | 最近5会话：标题省略、消息数、时间；整行可点 → `router.push({name:'chat', query:{session:id}})` |
| StatsPanel.vue | 编排：onMounted 调 myStats() + v-loading；空态（无会话且无提问）→ 数字卡显示 0、图表区替换为「还没有使用记录」+ 开始对话按钮，不初始化 ECharts；有数据 → Overview → 两列(两个图表) → RecentSessions |

图表组件统一模式：`echarts.init(el)` + setOption，onMounted 加 resize 监听，onBeforeUnmount dispose + 移除监听。

### 6. 改造 `frontend/src/views/ProfileView.vue`
- 保留现有渐变背景与卡片样式，max-width ~880px
- 结构：ProfileBanner → profile-card 内 `el-tabs`（「我的资料」= 现有表单整块迁移不动逻辑；「数据统计」= StatsPanel）
- **两个 pane 内容用 v-if**（Tab 默认 display:none 会导致 ECharts 初始化得 0 尺寸 canvas）
- 删除原 head 小头像区（Banner 承担），保留「返回」按钮

### 7. `frontend/src/components/layout/HeaderBar.vue:38`
文案 `👤 个人资料` → `🏠 个人中心`（command 逻辑不变）

### 8. 深链接：`frontend/src/views/ChatView.vue`
```js
const route = useRoute()
onMounted(async () => {
  const sid = route.query.session
  if (sid) { try { await store.selectSession(String(sid)) } catch { /* 404 静默降级 */ } }
})
```
后端 GET /sessions/{id} 已有归属校验，越权/不存在时降级为空会话。

## 测试
新建 `backend/tests/test_stats.py`（沿用 conftest 的 client/fake_llm、`pytestmark = pytest.mark.anyio`）：
1. 未登录 → 401
2. 新用户 → totals 全 0、days_since_register==1、agent_usage 6 项全 0、daily 14 项全 0、recent_sessions==[]
3. 注册→chat/stream（fake_llm）→ session_count==1、question_count==1、reply_count==1、main==1、今天 daily==2、recent_sessions[0].message_count==2
4. 游客会话/消息（service 直造 user_id=NULL）不进用户统计（验证 JOIN 隔离）

## 实施顺序与验证
1. stats_service + auth 路由 → `pytest backend/tests/test_stats.py -q` 通过
2. pytest 全量回归（原 9 + 新 4）
3. npm install echarts + utils/echarts.js + myStats → `npm run build` 零错误
4. 6 个 profile 组件 + ProfileView 改造 → 手动验证（backend `python run.py` :8000、frontend `npm run dev` :5173）：登录 /profile，Tab 切换图表正常、窗口 resize 自适应
5. HeaderBar 文案 + ChatView 深链接 → 个人中心点最近会话跳 /chat 正确载入且侧栏高亮
6. 空态验收：新注册账号看统计 Tab
7. 最终 `npm run build` + `pytest` 双零错误

## 风险备注
- SQLite `'localtime'` 取后端进程所在机器时区；本项目前后端同机本地部署，语义正确（UTC+8）
- created_at 恒为同格式 ISO 字符串（写入端 session_service._now 保证），字符串比较边界可靠
