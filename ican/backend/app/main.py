"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import attachments, auth, chat, documents, memories, sessions, system
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="UniGrow Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # MVP：放开来源，便于本地调试
    allow_credentials=False,    # 未使用 cookie 认证，关闭以兼容通配来源
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(memories.router, prefix="/api")
app.include_router(attachments.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
