"""
小说管理App — FastAPI 应用入口

启动方式:
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API 文档:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc:      http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.config import settings
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
    yield


app = FastAPI(
    title="小说管理App API",
    version="1.0.0",
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


@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """返回服务运行状态"""
    return {"status": "ok", "version": "1.0.0"}
