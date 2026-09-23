"""LangGraph supervisor：router → 并行 fan-out → aggregator。

token 流式采用应用层 asyncio.Queue 上报（worker 内直推），
SSE 协议见 app/sse.py；graph 只负责编排与状态汇聚。
"""
import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.base import SpecialistAgent, is_transient_error
from app.agents.campus_agent import CampusAgent
from app.agents.career_agent import CareerAgent
from app.agents.competition_agent import CompetitionAgent
from app.agents.main_agent import MainAgent
from app.agents.meta import AGENT_META
from app.agents.research_agent import ResearchAgent
from app.agents.router import make_route_decision
from app.agents.state import AgentOutput, UniGrowState
from app.agents.study_agent import StudyAgent
from app.schemas import RouteDecision
from app.services import session_service
from app.sse import sse_event

logger = logging.getLogger(__name__)

SPECIALISTS: dict[str, SpecialistAgent] = {
    "study": StudyAgent(),
    "research": ResearchAgent(),
    "competition": CompetitionAgent(),
    "career": CareerAgent(),
    "campus": CampusAgent(),
    "main": MainAgent(),
}


def _queue(config: RunnableConfig) -> asyncio.Queue:
    return config["configurable"]["queue"]


def _sink(config: RunnableConfig) -> dict:
    """中断时落库部分内容用的共享收集器（即 stream_chat 里的 collected）。"""
    return config["configurable"].get("sink") or {}


# ---------- 图节点 ----------

async def router_node(state: UniGrowState, config: RunnableConfig):
    decision: RouteDecision = await make_route_decision(
        state["user_query"], state.get("history", [])
    )
    q = _queue(config)
    await q.put(
        sse_event(
            "route_plan",
            {
                "complexity": decision.complexity,
                "plan_summary": decision.plan_summary,
                "agents": [
                    {"name": a, **AGENT_META[a]} for a in decision.agents
                ],
            },
        )
    )
    for a in decision.agents:  # 先建卡片骨架，随后并行打字
        await q.put(sse_event("agent_start", {"agent": a, **AGENT_META[a]}))
    return {"route": decision.model_dump()}


def _make_worker(agent_name: str):
    agent = SPECIALISTS[agent_name]

    async def worker(state: UniGrowState, config: RunnableConfig):
        q = _queue(config)
        route = state.get("route") or {}
        sub_query = (route.get("sub_queries") or {}).get(agent_name) or state["user_query"]
        _sk = _sink(config).setdefault("partials", {})
        try:
            content = await agent.stream_to(
                sub_query,
                state.get("history", []),
                state.get("doc_ids", []),
                q,
                user_profile=state.get("user_profile", ""),
                attachments_text=state.get("attachments_text", ""),
                memory_text=state.get("memory_text", ""),
                sink=_sk,
            )
            return {"agent_outputs": [AgentOutput(agent=agent_name, content=content)]}
        except Exception as e:
            logger.exception("worker %s failed", agent_name)
            await q.put(
                sse_event(
                    "error",
                    {"agent": agent_name, "message": _err_msg(e), "recoverable": True},
                )
            )
            await q.put(sse_event("agent_end", {"agent": agent_name}))
            return {"agent_outputs": [AgentOutput(agent=agent_name, content="")]}

    return worker


def _dispatch(state: UniGrowState) -> list[str]:
    route = state.get("route") or {}
    agents = [a for a in route.get("agents", []) if a in SPECIALISTS]
    if not agents:
        agents = ["main"]
    return [f"{a}_worker" for a in agents]


def _after_worker(state: UniGrowState) -> str:
    route = state.get("route") or {}
    return "aggregator" if route.get("complexity") == "multi" else END


async def aggregator_node(state: UniGrowState, config: RunnableConfig):
    q = _queue(config)
    outputs = [o for o in state.get("agent_outputs", []) if o.content]
    if len(outputs) <= 1:
        return {"final_answer": outputs[0].content if outputs else ""}
    await q.put(sse_event("summary_start", {"agent": "main", **AGENT_META["main"]}))
    sections = "\n\n".join(
        f"## {AGENT_META.get(o.agent, {}).get('label', o.agent)} 的结论\n{o.content}"
        for o in outputs
    )
    messages = [
        SystemMessage(
            "你是 UniGrow 的主Agent汇总器。\n"
            + _AGG_PROMPT
            + (f"\n\n{state['user_profile']}" if state.get("user_profile") else "")
        ),
        HumanMessage(content=f"用户问题：{state['user_query']}\n\n各Agent输出：\n{sections}"),
    ]
    parts: list[str] = []
    final_sink: list[str] = _sink(config).setdefault("final_parts", [])
    from app.agents.llm import get_llm

    attempt = 0
    while True:
        try:
            async for chunk in get_llm(temperature=0.5).astream(messages):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if not text:
                    continue
                parts.append(text)
                final_sink.append(text)
                await q.put(
                    sse_event("summary_token", {"agent": "main", "content": text})
                )
            break
        except Exception as e:
            # 瞬时网络抖动：尚未产出任何内容时重试一次
            if not parts and attempt < 1 and is_transient_error(e):
                attempt += 1
                logger.warning("aggregator transient error, retrying once")
                await asyncio.sleep(0.8)
                continue
            logger.exception("aggregator failed")
            await q.put(
                sse_event("error", {"agent": "main", "message": _err_msg(e), "recoverable": True})
            )
            break
    await q.put(sse_event("summary_end", {"agent": "main"}))
    return {"final_answer": "".join(parts)}


_AGG_PROMPT = """多个专业Agent并行完成了各自的分析，请整合它们的输出，为用户生成一份统一的「综合成长行动建议」。
要求：
- 使用 Markdown，结构清晰，控制在 300 字以内。
- 不要罗列原话，要提炼跨Agent的关键结论并指出衔接关系。
- 最后给出「下一步行动」清单（3-5 条，按优先级排序）。
- 语气积极、面向大学生。"""


def _err_msg(e: Exception) -> str:
    text = str(e)
    if "429" in text or "rate" in text.lower():
        return "模型服务限流（429），请稍后重试"
    if "401" in text or "api key" in text.lower():
        return "API Key 无效或未配置：请到 个人中心 → 模型服务 检查你自己的 Key"
    return text[:200] or "服务内部错误"


def _persist_partial(session_id: str, collected: dict) -> None:
    """客户端停止生成/断连等中断场景：把已生成的部分内容落库，避免回复「凭空消失」。"""
    try:
        contents = {o.agent: o.content for o in collected["outputs"] if o.content}
        # 未跑完的 worker：完整内容缺失时用流式增量兜底
        for agent, text in (collected.get("partials") or {}).items():
            if agent not in contents and text.strip():
                contents[agent] = text
        for agent, content in contents.items():
            session_service.add_message(session_id, "agent", agent, content)
        final = collected["final"] or "".join(collected.get("final_parts") or [])
        if collected.get("complexity") == "multi" and final.strip():
            session_service.add_message(session_id, "summary", "main", final)
    except Exception:
        logger.exception("persist partial content failed")


def build_graph():
    g = StateGraph(UniGrowState)
    g.add_node("router", router_node)
    for name in SPECIALISTS:
        g.add_node(f"{name}_worker", _make_worker(name))
    g.add_node("aggregator", aggregator_node)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", _dispatch)
    for name in SPECIALISTS:
        g.add_conditional_edges(f"{name}_worker", _after_worker)
    g.add_edge("aggregator", END)
    return g.compile()


graph = build_graph()


# ---------- 流式入口 ----------

async def stream_chat(
    session_id: str,
    user_query: str,
    doc_ids: list[str],
    history: list[dict],
    user_profile: str = "",
    attachments_text: str = "",
    memory_text: str = "",
):
    """产出 SSE 事件字符串；结束后持久化消息并产出 done 事件。

    客户端中断（停止生成/断连）时在 finally 中落库已生成的部分内容。
    """
    queue: asyncio.Queue = asyncio.Queue()
    collected: dict = {
        "outputs": [], "final": "", "complexity": "single",
        "partials": {}, "final_parts": [],
    }
    config: RunnableConfig = {"configurable": {"queue": queue, "sink": collected}}
    inputs = {
        "session_id": session_id,
        "user_query": user_query,
        "history": history,
        "doc_ids": doc_ids,
        "user_profile": user_profile,
        "attachments_text": attachments_text,
        "memory_text": memory_text,
    }

    async def produce():
        try:
            async for updates in graph.astream(inputs, config, stream_mode="updates"):
                for node, update in updates.items():
                    if node == "router" and update.get("route"):
                        collected["complexity"] = update["route"].get("complexity", "single")
                    for out in update.get("agent_outputs", []) or []:
                        collected["outputs"].append(out)
                    if node == "aggregator" and update.get("final_answer"):
                        collected["final"] = update["final_answer"]
        except Exception as e:
            logger.exception("graph execution failed")
            await queue.put(
                sse_event("error", {"agent": None, "message": _err_msg(e), "recoverable": False})
            )
        finally:
            await queue.put(None)

    task = asyncio.create_task(produce())
    persisted = False
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            if item is None:
                break
            yield item
        await task

        # 正常结束：完整内容落库
        for out in collected["outputs"]:
            if out.content:
                session_service.add_message(session_id, "agent", out.agent, out.content)
        if collected["complexity"] == "multi" and collected["final"]:
            session_service.add_message(session_id, "summary", "main", collected["final"])
        persisted = True
        yield sse_event("done", {"session_id": session_id})
    finally:
        if not persisted:
            # 客户端停止生成/断连/执行崩溃：落库已生成的部分内容
            task.cancel()
            _persist_partial(session_id, collected)
