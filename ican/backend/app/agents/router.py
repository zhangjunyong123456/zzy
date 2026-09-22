"""意图识别：一次结构化输出得到目标 agent 集合，失败时 fallback 到 main。"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_llm
from app.agents.prompts import ROUTER_PROMPT
from app.agents.state import AgentOutput  # noqa: F401  (re-export convenience)
from app.schemas import RouteDecision

logger = logging.getLogger(__name__)

_VALID_AGENTS = {"study", "research", "competition", "career", "campus", "main"}


def _fallback(query: str) -> RouteDecision:
    return RouteDecision(
        agents=["main"],
        complexity="single",
        sub_queries={"main": query},
        plan_summary="由主Agent直接回答",
    )


async def make_route_decision(user_query: str, history: list[dict]) -> RouteDecision:
    llm = get_llm(temperature=0.1, streaming=False)
    try:
        # json_schema/函数强制调用在思考型模型（如 deepseek-flash）上均不可用，
        # 因此统一走 json_object 模式，由提示词约束 JSON 格式。
        llm_structured = llm.with_structured_output(RouteDecision, method="json_mode")
        result = await llm_structured.ainvoke(
            [SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=user_query)]
        )
        # 校验与清洗
        agents = [a for a in result.agents if a in _VALID_AGENTS]
        if not agents:
            return _fallback(user_query)
        result.agents = agents
        result.sub_queries = {
            a: q for a, q in result.sub_queries.items() if a in agents and q.strip()
        }
        for a in agents:
            result.sub_queries.setdefault(a, user_query)
        result.plan_summary = result.plan_summary or "、".join(
            a for a in agents if a != "main"
        ) + " 协同处理"
        return result
    except Exception as e:  # 结构化解析失败 / 网络 / 限流 → 兜底，保证永不中断
        logger.warning("router fallback: %s", e)
        return _fallback(user_query)
