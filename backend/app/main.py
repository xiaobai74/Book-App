"""
小说管理App — FastAPI 应用入口

启动方式:
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API 文档:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc:      http://localhost:8000/redoc
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# 确保所有 ORM 模型在应用启动前被导入
from app.models import User, Book, RefreshToken, Chapter, CrawlSource, ReadingProgress  # noqa: F401

logger = logging.getLogger(__name__)

# 应用版本（与 PRD v1.3 功能对齐）
APP_VERSION = "1.3.0"

from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.api.v1.books import crawl_source_router
from app.api.v1.ai import router as ai_router
from app.config import settings
from app.database import Base, engine
from app.middleware.error_handler import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 桌面版（SQLite）：首次启动自动建表，无需手动迁移
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    # 安全提示：默认密钥仅用于本地开发，生产部署必须在 .env 中配置
    if settings.jwt_secret == "dev-secret-key-change-in-production-please":
        logger.warning(
            "检测到 JWT_SECRET 仍为默认值（开发密钥），生产部署请务必在 .env 中配置自定义密钥，"
            "否则任何人都能签发有效的登录 Token"
        )
    yield
    # 关闭时释放数据库连接池
    await engine.dispose()


app = FastAPI(
    title="小说管理App API",
    version=APP_VERSION,
    description="日常小说管理工具 — 搜索、抓取、生成 .epub 并集中管理个人书架",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器（注册顺序：具体 → 通用）
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册 API 路由
app.include_router(auth_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")
app.include_router(crawl_source_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")


@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """返回服务运行状态"""
    return {"status": "ok", "version": APP_VERSION}
