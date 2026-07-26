"""
书架 & 搜索业务逻辑

处理书籍 CRUD、搜索、抓取触发与进度查询等操作。
"""

from datetime import UTC, datetime
from math import ceil

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.user import User
from app.schemas.book import BookCreateRequest, BookResponse, CrawlStatusResponse


class BookService:
    """书籍服务"""

    @staticmethod
    async def get_books(
        db: AsyncSession,
        user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Book], int]:
        """
        获取当前用户书架列表。

        按 added_at 倒序排列，支持分页。
        自动排除已软删除的书籍。

        返回: (书籍列表, 总数)
        """
        # 查询总数
        count_query = select(func.count()).select_from(Book).where(
            Book.user_id == user.id,
            Book.deleted_at.is_(None),
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
        offset = (page - 1) * page_size
        query = (
            select(Book)
            .where(Book.user_id == user.id, Book.deleted_at.is_(None))
            .order_by(Book.added_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        books = list(result.scalars().all())

        return books, total

    @staticmethod
    async def create_book(db: AsyncSession, user: User, data: BookCreateRequest) -> Book:
        """
        手动添加一本书到书架。

        v1.0: 仅手动输入书名和作者。
        后续版本从搜索结果页添加时会包含 source_url。
        """
        book = Book(
            user_id=user.id,
            title=data.title,
            author=data.author,
            source_url=data.source_url,
        )
        db.add(book)
        await db.flush()
        return book

    @staticmethod
    async def get_book_detail(db: AsyncSession, user: User, book_id: str) -> Book:
        """
        获取单本小说详情。

        校验: 该书属于当前用户且未被软删除。
        不存在时抛出 404。
        """
        result = await db.execute(
            select(Book).where(
                Book.id == book_id,
                Book.user_id == user.id,
                Book.deleted_at.is_(None),
            )
        )
        book = result.scalar_one_or_none()
        if book is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=404, detail="书籍不存在或已被删除")
        return book

    @staticmethod
    async def delete_book(db: AsyncSession, user: User, book_id: str) -> None:
        """
        软删除书籍。

        设置 deleted_at = 当前时间，不物理删除数据。
        校验: 该书属于当前用户且未被软删除。
        """
        book = await BookService.get_book_detail(db, user, book_id)
        book.deleted_at = datetime.now(UTC)
        await db.flush()

    @staticmethod
    async def search_books(
        db: AsyncSession,
        user: User,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Book], int]:
        """
        在已有书架中按书名模糊搜索（SHELF-004, P2）。

        后续 v2.0 将接入外部搜索引擎实现在线搜索（SEARCH-001）。
        """
        offset = (page - 1) * page_size
        like_pattern = f"%{keyword}%"

        # 总数
        count_query = select(func.count()).select_from(Book).where(
            Book.user_id == user.id,
            Book.deleted_at.is_(None),
            Book.title.like(like_pattern),
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = (
            select(Book)
            .where(
                Book.user_id == user.id,
                Book.deleted_at.is_(None),
                Book.title.like(like_pattern),
            )
            .order_by(Book.added_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        books = list(result.scalars().all())

        return books, total

    @staticmethod
    async def trigger_crawl(db: AsyncSession, user: User, book_id: str) -> Book:
        """
        触发内容抓取。

        状态流转: idle / failed / done → crawling
        若已是 crawling 状态则拒绝重复触发。

        启动后台 asyncio 任务执行实际抓取。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        if book.status == "crawling":
            from app.middleware.error_handler import AppException
            raise AppException(status_code=409, detail="该书籍正在抓取中，请勿重复操作")

        if not book.source_url:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=400, detail="缺少 source_url，无法抓取")

        # 清除旧章节（重新抓取场景）
        from sqlalchemy import delete
        from app.models.chapter import Chapter
        await db.execute(delete(Chapter).where(Chapter.book_id == book_id))

        book.status = "crawling"
        book.chapter_count = 0
        book.epub_path = None
        await db.flush()

        # 启动后台抓取
        from app.services.crawl_manager import start_crawl
        import asyncio as _asyncio
        try:
            loop = _asyncio.get_running_loop()
        except RuntimeError:
            loop = _asyncio.get_event_loop()
        loop.create_task(start_crawl(book_id))

        return book

    @staticmethod
    async def get_crawl_status(db: AsyncSession, user: User, book_id: str) -> CrawlStatusResponse:
        """
        查询抓取进度。

        优先从内存中的实时进度获取，否则从 DB 读取。
        """
        from app.services.crawl_manager import get_crawl_progress
        book = await BookService.get_book_detail(db, user, book_id)

        # 优先读取内存中的实时进度
        progress = get_crawl_progress(book_id)
        if progress:
            pct = 0.0
            if progress["total"] > 0:
                pct = round(progress["current"] / progress["total"] * 100, 1)
            return CrawlStatusResponse(
                status=progress["status"],
                chapter_count=progress["current"],
                total_chapters=progress["total"],
                percentage=pct,
                error=progress.get("error"),
            )

        # 无实时进度则从 DB 读取
        return CrawlStatusResponse(
            status=book.status,
            chapter_count=book.chapter_count,
            total_chapters=book.chapter_count if book.status == "done" else None,
            percentage=100.0 if book.status == "done" else 0.0,
        )


def book_to_response(book: Book) -> BookResponse:
    """将 ORM 模型转换为 Pydantic 响应"""
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        source_url=book.source_url,
        status=book.status,
        chapter_count=book.chapter_count,
        has_epub=book.epub_path is not None and book.epub_path != "",
        has_txt=book.txt_path is not None and book.txt_path != "",
        added_at=book.added_at,
    )
