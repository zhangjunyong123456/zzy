"""Pydantic 请求/响应模型。"""
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["study", "research", "competition", "career", "campus", "main"]


# ---------- Chat ----------

class RouteDecision(BaseModel):
    """router 结构化输出：目标agent集合 + 每个agent的改写子问题。"""

    agents: list[AgentName] = Field(description="需要参与回答的agent列表")
    complexity: Literal["single", "multi"] = Field(
        description="single=只需一个agent；multi=需要多个agent并行协同"
    )
    sub_queries: dict[str, str] = Field(
        default_factory=dict,
        description="每个目标agent对应的改写后子问题",
    )
    plan_summary: str = Field(description="一句话调度计划，展示给用户")


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    doc_ids: list[str] = Field(default_factory=list)
    attachment_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    category: str | None = None  # 场景方向（study/research/…），首次写入会话分类


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageAttachment(BaseModel):
    id: str
    filename: str
    kind: str  # image / file
    mime: str


class MessageOut(BaseModel):
    id: str
    role: str
    agent: str | None
    content: str
    created_at: str
    attachments: list[MessageAttachment] = Field(default_factory=list)


# ---------- Memories ----------

class MemoryCreate(BaseModel):
    title: str | None = Field(default=None, max_length=60)
    source_session_id: str
    message_ids: list[str] = Field(min_length=1)


class MemoryRename(BaseModel):
    title: str = Field(min_length=1, max_length=60)


class MemoryOut(BaseModel):
    id: str
    title: str
    content: str
    source_session_id: str | None
    created_at: str


# ---------- Documents ----------

class DocumentOut(BaseModel):
    id: str
    filename: str
    scene: str
    status: str
    pages: int
    chunk_count: int
    builtin: bool
    created_at: str
