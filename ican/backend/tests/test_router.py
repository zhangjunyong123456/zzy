"""路由决策测试：mock LLM 结构化输出。"""
import asyncio

import pytest

from app.agents.router import make_route_decision
from app.schemas import RouteDecision


def test_router_multi_route(fake_llm):
    """mock 返回合法多agent决策 → 原样通过。"""

    class FakeStructured:
        async def ainvoke(self, messages):
            return RouteDecision(
                agents=["competition", "research", "study"],
                complexity="multi",
                sub_queries={
                    "competition": "iCAN赛题分析",
                    "research": "创新点调研",
                    "study": "学习计划",
                },
                plan_summary="竞赛+科研+学习并行",
            )

    fake_llm.with_structured_output = lambda schema, **kwargs: FakeStructured()

    async def run():
        return await make_route_decision("我要参加iCAN比赛", [])

    d = asyncio.run(run())
    assert d.complexity == "multi"
    assert set(d.agents) == {"competition", "research", "study"}


def test_router_fallback_on_error(monkeypatch):
    """结构化输出抛异常 → fallback 到 main，永不中断。"""
    import app.agents.router as router_mod

    class Boom:
        def with_structured_output(self, schema, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(router_mod, "get_llm", lambda *a, **k: Boom())

    async def run():
        return await make_route_decision("随便聊聊", [])

    d = asyncio.run(run())
    assert d.agents == ["main"]
    assert d.complexity == "single"


def test_router_filters_invalid_agents(fake_llm):
    """非法 agent 名被清洗，空列表 → fallback。"""

    class FakeStructured:
        async def ainvoke(self, messages):
            return RouteDecision(
                agents=["unknown_agent"], complexity="single",
                sub_queries={}, plan_summary="x",
            )

    fake_llm.with_structured_output = lambda schema, **kwargs: FakeStructured()

    async def run():
        return await make_route_decision("test", [])

    d = asyncio.run(run())
    assert d.agents == ["main"]
