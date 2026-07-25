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

        当前为占位实现，后续将接入 Celery/ARQ 异步任务队列。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        if book.status == "crawling":
            from app.middleware.error_handler import AppException
            raise AppException(status_code=409, detail="该书籍正在抓取中，请勿重复操作")

        book.status = "crawling"
        await db.flush()
        return book

    @staticmethod
    async def get_crawl_status(db: AsyncSession, user: User, book_id: str) -> CrawlStatusResponse:
        """
        查询抓取进度。

        返回 status、已抓取章节数、进度百分比等。

        后续爬虫实现后，total_chapters 将从源站获取。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        # 计算进度百分比（当有 total_chapters 时）
        percentage = 0.0
        total_chapters = None

        return CrawlStatusResponse(
            status=book.status,
            chapter_count=book.chapter_count,
            total_chapters=total_chapters,
            percentage=percentage,
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
        added_at=book.added_at,
    )
