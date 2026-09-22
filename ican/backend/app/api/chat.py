"""聊天主通道：POST /api/chat/stream（SSE）。"""
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.demo import stream_demo
from app.agents.profile import build_profile_text
from app.agents.supervisor import stream_chat
from app.api.deps import get_current_user_optional
from app.config import settings
from app.schemas import ChatRequest
from app.services import attachment_service, memory_service, session_service
from app.sse import SSE_HEADERS

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, user: dict | None = Depends(get_current_user_optional)
):
    uid = user["id"] if user else None
    if req.session_id:
        # 归属校验：不存在或不属于当前用户（含游客）→ 404 防枚举
        row = session_service.get_session_row(req.session_id)
        if row is None or (row["user_id"] or None) != uid:
            return JSONResponse(status_code=404, content={"detail": "会话不存在"})

    session_id = req.session_id or session_service.create_session(user_id=uid)

    # 场景方向分类：首次发消息时写入，已有分类不覆盖（非法值忽略）
    if req.category in {"study", "research", "competition", "career", "campus"}:
        session_service.set_category_if_unset(session_id, req.category)

    # 演示模式：未配置 Key 也提供基础对话（规则回复）并提示接入
    if not settings.has_api_key:
        demo_mid = session_service.add_message(session_id, "user", None, req.message)
        session_service.set_title_if_default(session_id, req.message)
        attachment_service.bind_attachments(demo_mid, session_id, req.attachment_ids, uid)

        async def demo_gen():
            yield f"data: {__import__('json').dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
            async for event in stream_demo(session_id, req.message):
                yield event

        return StreamingResponse(demo_gen(), media_type="text/event-stream", headers=SSE_HEADERS)

    history = [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in session_service.get_messages(session_id, limit=12)
    ]
    user_mid = session_service.add_message(session_id, "user", None, req.message)
    session_service.set_title_if_default(session_id, req.message)
    bound = attachment_service.bind_attachments(user_mid, session_id, req.attachment_ids, uid)
    attachments_text = attachment_service.build_attachments_text(bound)
    profile_text = build_profile_text(user) if user else ""
    memory_text = memory_service.build_memory_text(req.memory_ids, uid)

    async def gen():
        yield f"data: {__import__('json').dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
        try:
            async for event in stream_chat(
                session_id, req.message, req.doc_ids, history, user_profile=profile_text,
                attachments_text=attachments_text, memory_text=memory_text,
            ):
                yield event
        except Exception:
            logger.exception("chat stream crashed")
            import json as _json

            yield f"event: error\ndata: {_json.dumps({'agent': None, 'message': '服务内部错误', 'recoverable': False}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
