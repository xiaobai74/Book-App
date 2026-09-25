"""
小说管理App — FastAPI 应用入口

启动方式:
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API 文档:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc:      http://localhost:8000/redoc
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, update
from starlette.middleware.gzip import GZipMiddleware

# 确保所有 ORM 模型在应用启动前被导入
from app.models import User, Book, RefreshToken, Chapter, CrawlSource, ReadingProgress, RankingCache  # noqa: F401

logger = logging.getLogger(__name__)

# 应用版本（与 PRD v1.3 功能对齐）
APP_VERSION = "1.3.0"

from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.api.v1.books import crawl_source_router
from app.api.v1.ai import router as ai_router
from app.api.v1.ranking import router as ranking_router
from app.config import settings
from app.database import Base, async_session, engine
from app.middleware.error_handler import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


def _migrate_sqlite_missing_columns(sync_conn) -> None:
    """
    SQLite 桌面版轻量列迁移。

    create_all 只创建缺失的表，不会给已存在的旧表补新列（如 books.cover_path 等 v1.7 列），
    导致旧库升级后查询报 "no such column" → 登录 500。
    这里逐表对比模型与实际结构，缺失的可空列用 ALTER TABLE ADD COLUMN 补齐。
    """
    from sqlalchemy import inspect

    dialect = sync_conn.dialect
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # 表不存在时 create_all 已负责整表创建
        actual = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in actual:
                continue
            if not column.nullable and column.server_default is None:
                logger.warning(
                    "跳过补列 %s.%s：NOT NULL 且无默认值，需人工迁移",
                    table.name, column.name,
                )
                continue
            col_type = column.type.compile(dialect)
            sync_conn.execute(
                text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
            )
            logger.info("SQLite 列迁移：%s.%s (%s)", table.name, column.name, col_type)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 桌面版（SQLite）：首次启动自动建表；旧库自动补齐新增列（列级轻量迁移）
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_migrate_sqlite_missing_columns)
    # 启动复位：进程刚启动时不可能有真实抓取任务在运行，
    # 上次因崩溃/重启而中断、遗留为 crawling 的书籍会永久卡在“抓取中”，
    # 统一复位为 failed（语义准确，且前端提供“重新抓取”入口）。
    try:
        async with async_session() as db:
            result = await db.execute(
                update(Book).where(Book.status == "crawling").values(status="failed")
            )
            await db.commit()
            if result.rowcount:
                logger.warning(
                    "启动复位：将 %d 本遗留「抓取中」的书籍状态重置为 failed",
                    result.rowcount,
                )
    except Exception as e:  # noqa: BLE001 复位失败不应阻断应用启动
        logger.error("启动复位遗留 crawling 状态失败: %s", e)
    # 安全提示：默认密钥仅用于本地开发，生产部署必须在 .env 中配置
    if settings.jwt_secret == "dev-secret-key-change-in-production-please":
        logger.warning(
            "检测到 JWT_SECRET 仍为默认值（开发密钥），生产部署请务必在 .env 中配置自定义密钥，"
            "否则任何人都能签发有效的登录 Token"
        )

    async def _startup_warmup():
        """后台预热（不阻塞启动握手）：消化重启后首请求的连接/缓存冷开销。"""
        try:
            await asyncio.sleep(1.0)  # 让 uvicorn 先就绪，避免与启动抢占
            from app.services.ranking_service import ranking_service as _rs
            async with async_session() as db:
                await db.execute(text("SELECT 1"))  # 预热连接池首条连接
                await _rs.prewarm(db)               # DB 榜单缓存 → 内存层
        except Exception as e:  # noqa: BLE001 预热失败不影响服务
            logger.warning("启动预热失败（不影响使用）: %s", e)

    warmup_task = asyncio.create_task(_startup_warmup())
    yield
    warmup_task.cancel()
    # 关闭时释放共享 HTTP 客户端的连接池（爬虫服务）
    # 避免进程退出时 httpx 连接未优雅关闭产生告警/句柄泄漏
    try:
        from app.services.crawler_service import crawler as _crawler_singleton
        await _crawler_singleton.close()
    except Exception as e:  # noqa: BLE001 关闭失败不应影响进程退出
        logger.warning("关闭爬虫共享 HTTP 客户端失败: %s", e)
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

# GZip 压缩中间件（响应体 ≥500 字节时压缩）。
# 章节正文 / 书架列表 / 搜索结果等 JSON 体积较大，压缩后显著降低传输开销。
# 中间件执行顺序：后添加的先执行（更靠外），故 GZip 在 CORS 之外，
# 可对最终响应体（含 CORS 处理后的结果）统一压缩。
app.add_middleware(GZipMiddleware, minimum_size=500)

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
app.include_router(ranking_router, prefix="/api/v1")


@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """返回服务运行状态"""
    return {"status": "ok", "version": APP_VERSION}
