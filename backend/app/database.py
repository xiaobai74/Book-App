"""
数据库连接管理

创建 SQLAlchemy 异步引擎和会话工厂，提供 get_db 依赖注入。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 异步引擎（MySQL 用连接池参数；桌面版 SQLite 用独立连接参数）
if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=False,          # 生产环境关闭 SQL 日志
        pool_size=10,        # 连接池大小
        max_overflow=20,     # 溢出连接数
        pool_pre_ping=True,  # 连接前检查可用性，防止使用断开的连接
    )

# 异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit 后不过期对象，方便序列化
)


class Base(DeclarativeBase):
    """ORM 模型基类"""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入：每次请求创建一个新的数据库会话，请求结束后自动关闭。

    用法:
        @app.get("/books")
        async def list_books(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
