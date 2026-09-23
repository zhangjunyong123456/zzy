"""聊天主通道：POST /api/chat/stream（SSE）。"""
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.demo import stream_demo
from app.agents.llm import set_user_llm
from app.agents.profile import build_profile_text
from app.agents.supervisor import stream_chat
from app.api.deps import get_current_user_optional, get_user_llm
from app.config import settings
from app.schemas import ChatRequest
from app.services import attachment_service, memory_service, quota_service, session_service
from app.sse import SSE_HEADERS

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.get("/chat/quota")
async def chat_quota(
    user: dict | None = Depends(get_current_user_optional),
    user_llm: dict | None = Depends(get_user_llm),
):
    """当日免费额度状态（登录用户独立 / 游客共享池）。
    limit 为 null 表示不展示额度（自带 Key / 额度功能关闭 / 独占模式）。"""
    if (user_llm and user_llm.get("api_key")) or settings.daily_free_quota <= 0 or settings.byok_only:
        return {"limit": None, "used": 0, "remaining": None}
    uid = user["id"] if user else None
    used = quota_service.get_used(uid)
    return {
        "limit": settings.daily_free_quota,
        "used": used,
        "remaining": max(0, settings.daily_free_quota - used),
    }


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    user: dict | None = Depends(get_current_user_optional),
    user_llm: dict | None = Depends(get_user_llm),
):
    uid = user["id"] if user else None
    # BYOK：绑定到当前请求上下文（worker / aggregator / 附件视觉均可见）
    set_user_llm(user_llm)

    # 有效 Key 判定：用户 Key 优先；无用户 Key 时走服务器 Key，受每日免费额度约束
    user_has_key = bool(user_llm and user_llm.get("api_key"))
    quota_exhausted = False
    if settings.byok_only:
        # 独占模式：未带用户 Key 一律演示模式，服务器 Key 不参与
        has_key = user_has_key
    elif user_has_key or settings.daily_free_quota <= 0:
        # 自带 Key 不限；额度功能关闭（=0）时保持旧行为（服务器 Key 不限次）
        has_key = user_has_key or settings.has_api_key
    else:
        # 无自带 Key + 额度开启：查询/占用当日额度（游客共享 'guest' 池）
        has_key = settings.has_api_key
        if has_key and quota_service.get_used(uid) >= settings.daily_free_quota:
            has_key = False
            quota_exhausted = True
        elif has_key:
            quota_service.consume(uid)

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
    if not has_key:
        demo_mid = session_service.add_message(session_id, "user", None, req.message)
        session_service.set_title_if_default(session_id, req.message)
        attachment_service.bind_attachments(demo_mid, session_id, req.attachment_ids, uid)

        exhausted_notice = (
            f"今日免费额度已用完（每天 {settings.daily_free_quota} 次），"
            "已切换为演示模式（规则回复）。明天自动恢复，或在「个人中心 → 模型服务」"
            "配置你自己的 Key 即可不限次使用。"
        ) if quota_exhausted else ""

        async def demo_gen():
            yield f"data: {__import__('json').dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
            async for event in stream_demo(session_id, req.message, notice=exhausted_notice):
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
        set_user_llm(user_llm)  # 流式阶段重新绑定（响应体在请求后段消费，确保上下文可见）
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
