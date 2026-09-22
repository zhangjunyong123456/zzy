"""LangGraph 状态定义。

并行 worker 共写 agent_outputs，必须带 reducer（operator.add），
否则会抛 InvalidUpdateError。
"""
import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel


class AgentOutput(BaseModel):
    agent: str
    content: str


class UniGrowState(TypedDict, total=False):
    session_id: str
    user_query: str
    history: list[dict]          # [{"role": "user"|"assistant", "content": str}]
    doc_ids: list[str]
    user_profile: str            # 用户画像提示词块（游客为空串）
    attachments_text: str        # 本轮附件提取文本（拼进最后一条 HumanMessage）
    memory_text: str             # 启用记忆内容（拼进 SystemMessage）
    route: dict                  # RouteDecision.model_dump()
    agent_outputs: Annotated[list[AgentOutput], operator.add]
    final_answer: str
