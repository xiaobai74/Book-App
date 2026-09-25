"""
书架 & 搜索业务逻辑

处理书籍 CRUD、搜索、抓取触发与进度查询等操作。
v1.2 扩展：标记置顶、章节获取、阅读进度。
"""

import logging
import os
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.reading_progress import ReadingProgress
from app.models.user import User
from app.schemas.book import (
    BookCreateRequest,
    BookResponse,
    ChapterDetailResponse,
    ChapterResponse,
    CrawlStatusResponse,
    ReadingProgressResponse,
)
from rules.rule_engine import get_rule_engine

logger = logging.getLogger(__name__)


def _resolve_source_name(source_url: str | None) -> str | None:
    """将 source_url 映射为可读的源站名。

    优先级：内置规则匹配 → 域名（去 www. 前缀）→ None。
    当前仅涵盖内置 main.json 规则；用户自定义源站的书籍自然回退到域名。
    """
    if not source_url:
        return None
    try:
        engine = get_rule_engine()
        rule = engine.match_rule(source_url)
        if rule and rule.get("name"):
            return str(rule["name"])
    except Exception:  # noqa: BLE001 规则引擎异常不影响主流程
        logger.debug("source_name 规则匹配失败，回退到域名: %s", source_url)
    try:
        netloc = urlparse(source_url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or None
    except Exception:  # noqa: BLE001
        return None


class BookService:
    """书籍服务"""

    @staticmethod
    async def get_books(
        db: AsyncSession,
        user: User,
        page: int = 1,
        page_size: int = 20,
        filter_marked: bool | None = None,
    ) -> tuple[list[Book], int]:
        """
        获取当前用户书架列表。

        v1.2 排序规则：已标记书籍置顶（按 marked_at 倒序），
        未标记书籍按 added_at 倒序。
        支持 filter_marked 参数筛选已标记书籍。

        返回: (书籍列表, 总数)
        """
        conditions = [Book.user_id == user.id, Book.deleted_at.is_(None)]
        if filter_marked is True:
            conditions.append(Book.is_marked == True)

        # 查询总数
        count_query = (
            select(func.count())
            .select_from(Book)
            .where(*conditions)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询 — MySQL 不支持 NULLS FIRST/LAST，使用 CASE 表达式替代
        offset = (page - 1) * page_size
        query = (
            select(Book)
            .where(*conditions)
            .order_by(
                Book.is_marked.desc(),   # 已标记的在前
                func.coalesce(Book.marked_at, datetime(1970, 1, 1)).desc(),  # 标记时间倒序（NULL 视为最远日期）
                Book.added_at.desc(),    # 未标记的按添加时间倒序
            )
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
    async def enrich_metadata(db: AsyncSession, book: Book) -> None:
        """从源站详情页抓取封面/简介等元数据并写回 book（不提交，由调用方 commit）。

        仅在 book.source_url 存在时执行；任何失败静默降级，不影响添加流程。
        不覆盖用户已填写的书名；作者为「未知」时用源站值补全。
        封面下载到本地 cover_output_dir/{book_id}.jpg，规避防盗链、支持离线。
        """
        if not book.source_url:
            return
        from app.config import settings
        from app.services.crawler_service import crawler

        try:
            meta = await crawler.fetch_book_metadata(book.source_url)
        except Exception as e:  # noqa: BLE001 元数据非关键路径
            logger.warning(f"元数据抓取失败: book_id={book.id} — {e}")
            return

        # 文本元数据（不覆盖用户填写的书名；作者仅在为空/未知时补全）
        if meta.description:
            book.description = meta.description
        if meta.category:
            book.category = meta.category[:255]
        if meta.latest_chapter:
            book.latest_chapter = meta.latest_chapter[:500]
        if meta.last_update_time:
            book.last_update_time = meta.last_update_time[:100]
        if meta.author and (not book.author or book.author == "未知"):
            book.author = meta.author[:255]

        # 封面：下载到本地
        if meta.cover_url:
            book.cover_url = meta.cover_url[:2048]
            dest = os.path.join(settings.cover_output_dir, f"{book.id}.jpg")
            ok = await crawler.download_cover(meta.cover_url, dest, referer=book.source_url)
            if ok:
                book.cover_path = dest

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
        软删除书籍，同时清理本地 .epub/.txt 文件（v1.2 增强）。

        先查询书籍获取文件路径，执行软删除，再删除本地文件。
        文件删除失败不影响数据库操作。
        """
        book = await BookService.get_book_detail(db, user, book_id)
        epub_path = book.epub_path
        txt_path = book.txt_path
        cover_path = book.cover_path

        book.deleted_at = datetime.now(UTC)
        await db.flush()

        # 清理章节与阅读进度记录，避免软删除后留下孤儿数据（章节正文最占空间）
        await db.execute(delete(Chapter).where(Chapter.book_id == book_id))
        await db.execute(delete(ReadingProgress).where(ReadingProgress.book_id == book_id))
        await db.flush()

        # 清理本地文件
        for path in (epub_path, txt_path, cover_path):
            if not path:
                continue
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info("已删除本地文件: %s", path)
                else:
                    logger.debug("文件不存在，跳过: %s", path)
            except PermissionError:
                logger.warning("权限不足，无法删除文件: %s", path)
            except OSError as exc:
                logger.error("删除文件失败: %s — %s", path, exc)

    @staticmethod
    async def search_books(
        db: AsyncSession,
        user: User,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Book], int]:
        """
        在已有书架中按书名或作者模糊搜索（SHELF-004, P2）。

        v1.2 增强：支持同时搜索书名和作者字段，匹配任一字段即返回。
        """
        keyword = keyword.strip()
        if not keyword:
            return [], 0

        offset = (page - 1) * page_size
        # 转义 LIKE 通配符（% _ \），避免用户输入被当作通配符导致语义错误
        escaped = (
            keyword.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        like_pattern = f"%{escaped}%"

        conditions = [
            Book.user_id == user.id,
            Book.deleted_at.is_(None),
            or_(
                Book.title.like(like_pattern, escape="\\"),
                Book.author.like(like_pattern, escape="\\"),
            ),
        ]

        # 总数
        count_query = select(func.count()).select_from(Book).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = (
            select(Book)
            .where(*conditions)
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
        旧章节的清除在抓取流水线内执行（新内容成功获取后才替换）。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        if not book.source_url:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=400, detail="缺少 source_url，无法抓取")

        # 原子状态守卫：并发触发时仅第一个请求成功置为 crawling，其余返回 409
        result = await db.execute(
            update(Book)
            .where(
                Book.id == book_id,
                Book.user_id == user.id,
                Book.status != "crawling",
            )
            .values(status="crawling")
        )
        if result.rowcount == 0:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=409, detail="该书籍正在抓取中，请勿重复操作")

        # 注意：不在此处清除 chapter_count / epub_path / txt_path
        # 旧数据保留到新内容抓取成功后，由 crawl_manager 更新覆盖
        # 这样即使抓取失败，用户仍可阅读旧章节、下载之前生成的文件
        # 先提交状态变更，避免后台任务与请求会话的提交顺序竞态
        await db.commit()

        # 启动后台抓取
        from app.services.crawl_manager import start_crawl
        import asyncio as _asyncio
        loop = _asyncio.get_running_loop()
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

    # ── v1.2 新增：标记与置顶 ────────────────────────────

    @staticmethod
    async def toggle_mark(db: AsyncSession, user: User, book_id: str) -> Book:
        """
        切换书籍的标记状态。

        标记 → 取消标记：is_marked 取反，marked_at 更新或清空。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        if book.is_marked:
            book.is_marked = False
            book.marked_at = None
        else:
            book.is_marked = True
            book.marked_at = datetime.now(UTC)

        await db.flush()
        return book

    # ── v1.2 新增：章节获取 ──────────────────────────────

    @staticmethod
    async def get_chapters(
        db: AsyncSession, user: User, book_id: str
    ) -> list[Chapter]:
        """
        获取书籍的完整章节列表（仅摘要，不含正文）。

        按 chapter.index 升序排列。
        """
        # 先验证书籍存在且属于当前用户
        await BookService.get_book_detail(db, user, book_id)

        result = await db.execute(
            select(Chapter)
            .where(Chapter.book_id == book_id)
            .order_by(Chapter.index.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_book_cache_meta(
        db: AsyncSession, user: User, book_id: str
    ) -> tuple[datetime | None, int]:
        """轻量获取书籍缓存元数据 (updated_at, chapter_count) 并校验归属。

        使用列查询而非加载 Book 实体，避免触发 chapters 关系的 selectin 加载
        （否则会连带把整本书的 MEDIUMTEXT 正文读入内存），专用于目录 API 的 ETag 计算。
        书籍不存在或非本人时抛 404，语义与 get_book_detail 一致。
        """
        row = (
            await db.execute(
                select(Book.updated_at, Book.chapter_count).where(
                    Book.id == book_id,
                    Book.user_id == user.id,
                    Book.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if row is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=404, detail="书籍不存在或已被删除")
        return row.updated_at, row.chapter_count

    @staticmethod
    async def get_chapters_list(
        db: AsyncSession, book_id: str
    ) -> list[Chapter]:
        """获取书籍目录元数据（不加载正文 content 字段），专用于目录 API。

        使用 load_only 仅拉取 id/book_id/index/title/word_count/created_at 列，
        将 MEDIUMTEXT 正文延迟加载（defer），避免整本目录的正文被读入内存。
        返回的仍是 Chapter ORM 实体，chapter_to_response() 可直接使用
        （规避了 select(Chapter.index, ...) 返回 Row 时 .index 与序列方法名冲突的问题）。

        注意：本方法不再校验书籍归属，调用方须先通过 get_book_cache_meta /
        get_book_detail 完成校验，避免重复查询。按 chapter.index 升序排列。
        """
        result = await db.execute(
            select(Chapter)
            .options(
                load_only(
                    Chapter.id,
                    Chapter.book_id,
                    Chapter.index,
                    Chapter.title,
                    Chapter.word_count,
                    Chapter.created_at,
                )
            )
            .where(Chapter.book_id == book_id)
            .order_by(Chapter.index.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_chapter_content(
        db: AsyncSession, user: User, book_id: str, chapter_index: int
    ) -> Chapter:
        """
        获取单章正文内容。

        校验章节存在性，不存在时抛出 404。
        """
        await BookService.get_book_detail(db, user, book_id)

        result = await db.execute(
            select(Chapter).where(
                Chapter.book_id == book_id,
                Chapter.index == chapter_index,
            )
        )
        chapter = result.scalar_one_or_none()
        if chapter is None:
            from app.middleware.error_handler import AppException
            raise AppException(
                status_code=404,
                detail=f"第 {chapter_index} 章不存在",
            )
        return chapter

    # ── v1.2 新增：阅读进度 ──────────────────────────────

    @staticmethod
    async def get_reading_progress(
        db: AsyncSession, user: User, book_id: str
    ) -> ReadingProgressResponse:
        """
        获取用户在某本书的阅读进度。

        若无记录则返回默认值（第 1 章）。
        """
        # 校验书籍存在且属于当前用户（与 update_reading_progress 行为一致）
        await BookService.get_book_detail(db, user, book_id)

        result = await db.execute(
            select(ReadingProgress).where(
                ReadingProgress.book_id == book_id,
                ReadingProgress.user_id == user.id,
            )
        )
        progress = result.scalar_one_or_none()

        if progress is None:
            return ReadingProgressResponse(
                book_id=book_id,
                last_chapter_index=1,
                updated_at=None,
            )

        return ReadingProgressResponse(
            book_id=progress.book_id,
            last_chapter_index=progress.last_chapter_index,
            updated_at=progress.updated_at,
        )

    @staticmethod
    async def update_reading_progress(
        db: AsyncSession, user: User, book_id: str, chapter_index: int
    ) -> ReadingProgressResponse:
        """
        更新用户在某本书的阅读进度（upsert）。

        验证书籍存在且 chapter_index 在有效范围内。
        """
        book = await BookService.get_book_detail(db, user, book_id)

        if chapter_index < 1 or chapter_index > max(book.chapter_count, 1):
            from app.middleware.error_handler import AppException
            raise AppException(
                status_code=400,
                detail=f"章节序号必须在 1 到 {max(book.chapter_count, 1)} 之间",
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE 实现原子 upsert，
        # 避免并发两次请求都 SELECT 到 None 后双 INSERT 触发唯一键冲突
        stmt = mysql_insert(ReadingProgress).values(
            book_id=book_id,
            user_id=user.id,
            last_chapter_index=chapter_index,
            updated_at=now,
        )
        stmt = stmt.on_duplicate_key_update(
            last_chapter_index=stmt.inserted.last_chapter_index,
            updated_at=now,
        )
        await db.execute(stmt)
        await db.flush()

        return ReadingProgressResponse(
            book_id=book_id,
            last_chapter_index=chapter_index,
            updated_at=now,
        )


def book_to_response(book: Book) -> BookResponse:
    """将 ORM 模型转换为 Pydantic 响应"""
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        source_url=book.source_url,
        source_name=_resolve_source_name(book.source_url),
        status=book.status,
        chapter_count=book.chapter_count,
        has_epub=book.epub_path is not None and book.epub_path != "",
        has_txt=book.txt_path is not None and book.txt_path != "",
        has_cover=book.cover_path is not None and book.cover_path != "",
        description=book.description,
        category=book.category,
        latest_chapter=book.latest_chapter,
        last_update_time=book.last_update_time,
        is_marked=book.is_marked,
        marked_at=book.marked_at,
        ai_summary=book.ai_summary,
        ai_summary_at=book.ai_summary_at,
        added_at=book.added_at,
    )


def chapter_to_response(chapter: Chapter) -> ChapterResponse:
    """将章节 ORM 模型转换为摘要响应"""
    return ChapterResponse(
        index=chapter.index,
        title=chapter.title,
        word_count=chapter.word_count,
    )


def chapter_to_detail_response(chapter: Chapter) -> ChapterDetailResponse:
    """将章节 ORM 模型转换为详情响应（含正文）"""
    return ChapterDetailResponse(
        index=chapter.index,
        title=chapter.title,
        content=chapter.content,
        word_count=chapter.word_count,
    )
