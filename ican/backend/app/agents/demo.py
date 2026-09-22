"""演示模式：未配置 DeepSeek API Key 时，按关键词规则生成基础回复，保证对话闭环。

流程与正式流一致（agent_start → token* → agent_end → done），额外先发 notice 事件
提示前端展示「接入 API」引导；回复照常持久化（agent='规则命中的方向'），统计不受影响。
"""
import asyncio

from app.services import session_service
from app.sse import sse_event

# (关键词组, 命中后归属的 agent, 演示回复)
_RULES = [
    (
        ("复习", "考试", "课件", "高数", "课程", "学习", "绩点"),
        "study",
        "📚 **学习方向（演示回复）**\n- 把目标拆到周：每周固定 2 个复习时段，优先补最弱的一章\n- 用「费曼法」检验：合上书能讲出 80% 才算过\n- 错题按「概念不清 / 计算失误 / 审题偏差」归类，只重做前两类\n",
    ),
    (
        ("论文", "科研", "开题", "文献", "导师", "课题"),
        "research",
        "🔬 **科研方向（演示回复）**\n- 先做 20 篇文献的精读笔记，按「问题-方法-结论」三列表格整理\n- 从综述的 future work 里找切口，比凭空选题成功率高\n- 开题报告框架：背景 → 现状不足 → 你的问题 → 方法 → 预期贡献\n",
    ),
    (
        ("竞赛", "比赛", "ican", "大创", "挑战杯", "路演"),
        "competition",
        "🏆 **竞赛方向（演示回复）**\n- 组队先定分工：技术 / 方案书 / 路演，三者都要有主责人\n- 立项书围绕「真实痛点 + 可验证指标」写，避免堆功能\n- 倒排时间线：报名 → 校赛 → 省赛，每段留 2 周缓冲\n",
    ),
    (
        ("简历", "面试", "求职", "实习", "秋招", "春招", "offer"),
        "career",
        "💼 **求职方向（演示回复）**\n- 简历每条经历用「动词 + 做了什么 + 量化结果」重写\n- 面试用 STAR 结构准备 3 个核心故事，覆盖协作 / 攻坚 / 复盘\n- 时间线：现在起每周投 10 份 + 复盘 1 次，别等「准备好了」\n",
    ),
    (
        ("图书馆", "食堂", "校园", "社团", "自习", "宿舍", "选修"),
        "campus",
        "🏫 **校园方向（演示回复）**\n- 自习位：工作日早上开馆时最充裕，期末周建议预约制图书馆\n- 社团贵精不贵多：留 1 个兴趣 + 1 个与目标相关的\n- 选修课优先看考核方式（论文 / 考试 / 出勤）再选\n",
    ),
]

_NOTICE = (
    "当前为演示模式（未配置 DeepSeek API Key），回复由内置规则生成。"
    "点击右上角「⚙ 未配置 API Key」即可配置，接入后获得真实 AI 回答。"
)


def _build_reply(message: str) -> tuple[str, str]:
    """返回 (agent, 回复文本)；按关键词命中方向，否则走主 Agent。"""
    lowered = message.lower()
    for keywords, agent, reply in _RULES:
        if any(k in lowered for k in keywords):
            return agent, reply
    main_reply = (
        "🧭 **主 Agent（演示回复）**\n"
        f"- 已收到你的问题：「{message[:40]}」\n"
        "- 我可以先帮你把问题拆解成「目标 / 现状 / 下一步」三段\n"
        "- 接入 DeepSeek API 后，这个问题会路由到对应的专业 Agent 并生成真实深度回答\n"
    )
    return "main", main_reply


async def stream_demo(session_id: str, message: str):
    """演示流：notice → agent_start → token* → agent_end → done，与正式流事件协议一致。"""
    agent, content = _build_reply(message)

    yield sse_event("notice", {"message": _NOTICE})
    yield sse_event("agent_start", {"agent": agent})

    # 切成小块模拟流式输出
    size = 6
    for i in range(0, len(content), size):
        yield sse_event("token", {"agent": agent, "content": content[i : i + size]})
        await asyncio.sleep(0.02)

    yield sse_event("agent_end", {"agent": agent})

    # 与正式流一致：持久化 agent 回复（计入使用统计）
    session_service.add_message(session_id, "agent", agent, content)
    yield sse_event("done", {"session_id": session_id})
