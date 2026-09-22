"""专业 Agent 基类：流式生成 + RAG 上下文注入 + 事件推送。"""
import asyncio
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.prompts import AGENT_PROMPTS
from app.sse import sse_event

logger = logging.getLogger(__name__)

# 瞬时网络错误的异常类名（沿异常链匹配，兼容 openai/httpx/httpcore/langchain 各层包装）
_TRANSIENT_NAMES = {
    "APIConnectionError", "OpenAIConnectionError", "APITimeoutError",
    "ReadError", "WriteError", "ConnectError", "RemoteProtocolError",
    "BrokenResourceError", "ConnectionResetError", "IncompleteRead",
}


def is_transient_error(e: BaseException) -> bool:
    """判断是否为可重试的瞬时网络错误（连接被重置、读中断等）。"""
    seen: set[int] = set()
    cur: BaseException | None = e
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if type(cur).__name__ in _TRANSIENT_NAMES:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


class SpecialistAgent:
    name: str = ""
    use_rag: bool = False

    @property
    def system_prompt(self) -> str:
        return AGENT_PROMPTS[self.name]

    async def build_context(self, sub_query: str, doc_ids: list[str]) -> str:
        if not self.use_rag:
            return ""
        from app.rag.retriever import format_context, retrieve

        try:
            docs = retrieve(sub_query, doc_ids=doc_ids or None, scene=self.name)
            return format_context(docs)
        except Exception as e:
            logger.warning("RAG retrieve failed for %s: %s", self.name, e)
            return ""

    def compose_user_message(self, sub_query: str, context: str, attachments_text: str = "") -> str:
        parts = [sub_query]
        if attachments_text:
            parts.append(f"【附件内容】\n{attachments_text}")
        if context:
            parts.append(f"【参考资料】\n{context}")
        return "\n\n".join(parts)

    def _history_messages(self, history: list[dict]) -> list:
        msgs = []
        for h in history[-12:]:
            if h.get("role") == "user":
                msgs.append(HumanMessage(content=h["content"]))
            elif h.get("content"):
                msgs.append(AIMessage(content=h["content"]))
        return msgs

    async def stream_to(
        self,
        sub_query: str,
        history: list[dict],
        doc_ids: list[str],
        queue: asyncio.Queue,
        user_profile: str = "",
        attachments_text: str = "",
        memory_text: str = "",
        sink: dict | None = None,
    ) -> str:
        """流式生成回答：token 事件实时推入队列，返回完整文本。

        sink 提供时，增量内容同步写入 sink[self.name]，
        供客户端中断（停止生成/断连）时落库部分回复。
        """
        from app.agents.llm import get_llm

        context = await self.build_context(sub_query, doc_ids)
        sys_content = self.system_prompt + (f"\n\n{user_profile}" if user_profile else "")
        if memory_text:
            sys_content += f"\n\n【历史记忆】\n{memory_text}"
        messages = [
            SystemMessage(content=sys_content),
            *self._history_messages(history),
            HumanMessage(content=self.compose_user_message(sub_query, context, attachments_text)),
        ]
        parts: list[str] = []
        attempt = 0
        while True:
            try:
                async for chunk in get_llm().astream(messages):
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if not text:
                        continue
                    parts.append(text)
                    if sink is not None:
                        sink[self.name] = sink.get(self.name, "") + text
                    await queue.put(sse_event("token", {"agent": self.name, "content": text}))
                break
            except Exception as e:
                # 瞬时网络抖动：尚未产出任何 token 时整体重试一次（不会重复输出）
                if not parts and attempt < 1 and is_transient_error(e):
                    attempt += 1
                    logger.warning("stream_to transient error for %s, retrying once", self.name)
                    await asyncio.sleep(0.8)
                    continue
                raise
        content = "".join(parts)
        await queue.put(sse_event("agent_end", {"agent": self.name}))
        return content
