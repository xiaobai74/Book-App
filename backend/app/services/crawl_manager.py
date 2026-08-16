"""
抓取任务管理器 v4

后台抓取流水线：连接预检 → 规则匹配 → 获取章节 → 并发抓取 → 写入 DB → 生成 EPUB。
v4: 适配规则驱动的 CrawlerService，支持源站规则覆盖并发/间隔配置。
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import delete, select

from app.database import async_session
from app.models.book import Book
from app.models.chapter import Chapter
from app.services.crawler_service import crawler
from app.services.epub_service import epub_service
from app.services.txt_service import txt_service

logger = logging.getLogger(__name__)

# 抓取进度: {book_id: {"current": int, "total": int, "status": str, "error": str|None}}
_crawl_progress: dict[str, dict] = {}

# 全局任务引用: {book_id: asyncio.Task}
_running_tasks: dict[str, asyncio.Task] = {}

# EPUB 在线程池中生成
_thread_pool = ThreadPoolExecutor(max_workers=2)

_DEFAULT_MAX_CHAPTERS = 5000


def get_crawl_progress(book_id: str) -> dict | None:
    return _crawl_progress.get(book_id)


def _cleanup_task(book_id: str, task: asyncio.Task) -> None:
    """任务结束（成功/失败/取消）后清理内存状态，防止进度条目无限增长。"""
    if book_id in _running_tasks:
        del _running_tasks[book_id]
    if task.cancelled():
        logger.warning(f"抓取任务被取消: book_id={book_id}")
    elif task.exception() is not None:
        logger.error(f"抓取任务异常结束: book_id={book_id} — {task.exception()}")
    _crawl_progress.pop(book_id, None)


async def start_crawl(book_id: str, max_chapters: int = _DEFAULT_MAX_CHAPTERS) -> None:
    """启动后台抓取任务。"""
    # 清理已完成的旧任务
    if book_id in _running_tasks and _running_tasks[book_id].done():
        del _running_tasks[book_id]

    if book_id in _running_tasks:
        logger.warning(f"书籍 {book_id} 已有抓取任务在运行")
        return

    loop = asyncio.get_running_loop()
    task = loop.create_task(_crawl_pipeline(book_id, max_chapters))
    task.add_done_callback(lambda t: _cleanup_task(book_id, t))
    _running_tasks[book_id] = task
    logger.info(f"后台抓取任务已创建: book_id={book_id}")


async def _crawl_pipeline(book_id: str, max_chapters: int) -> None:
    """完整的异步抓取流水线。"""
    _crawl_progress[book_id] = {
        "current": 0, "total": 0, "status": "crawling", "error": None,
    }

    # ══ 1. 从 DB 读取书籍信息（排除已软删除的书籍） ══
    async with async_session() as db:
        result = await db.execute(
            select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
        )
        book = result.scalar_one_or_none()

        if not book:
            _crawl_progress[book_id] = {
                "current": 0, "total": 0, "status": "failed",
                "error": "书籍不存在或已被删除",
            }
            logger.error(f"书籍 {book_id} 不存在或已被删除")
            return

        if not book.source_url:
            _crawl_progress[book_id] = {
                "current": 0, "total": 0, "status": "failed",
                "error": "缺少 source_url，无法抓取",
            }
            book.status = "failed"
            await db.commit()
            return

        source_url = book.source_url
        await db.commit()

    # 读取一次书籍标题/作者用于日志与文件生成（session 关闭后 ORM 对象过期，
    # 不能再访问 book.title，否则抛 DetachedInstanceError）
    book_title = book.title
    book_author = book.author

    # ── 进度回调辅助 ──────────────────────────────
    def update_progress(current: int, total: int):
        _crawl_progress[book_id] = {
            "current": current, "total": total, "status": "crawling", "error": None,
        }

    # ══ 2. 爬取所有章节 ══
    logger.info(f"开始抓取《{book_title}》: {source_url}")
    try:
        chapters = await crawler.crawl_book(
            source_url=source_url,
            progress_callback=update_progress,
            max_chapters=max_chapters,
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"抓取失败: {error_msg}")
        _crawl_progress[book_id] = {
            "current": 0, "total": 0, "status": "failed", "error": error_msg,
        }
        async with async_session() as db:
            result = await db.execute(
                select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
            )
            book = result.scalar_one_or_none()
            if book:
                book.status = "failed"
                await db.commit()
        return

    if not chapters:
        _crawl_progress[book_id] = {
            "current": 0, "total": 0, "status": "failed",
            "error": "未获取到任何章节内容",
        }
        async with async_session() as db:
            result = await db.execute(
                select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
            )
            book = result.scalar_one_or_none()
            if book:
                book.status = "failed"
                await db.commit()
        return

    # ══ 3. 写入章节到 DB（新 session） ══
    logger.info(f"写入 {len(chapters)} 章到数据库…")
    book_title = ""
    book_author = ""
    async with async_session() as db:
        # 排除已软删除的书籍：避免删除后章节仍被写回、状态被覆盖为 done
        result = await db.execute(
            select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
        )
        book = result.scalar_one_or_none()
        if not book:
            logger.warning(f"书籍 {book_id} 已被删除，跳过章节写入与文件生成")
            return

        book_title = book.title
        book_author = book.author

        # 清除旧章节（在这里删除 — 确保新内容已抓取成功）
        await db.execute(delete(Chapter).where(Chapter.book_id == book_id))

        for i, ch in enumerate(chapters):
            db.add(Chapter(
                book_id=book_id,
                index=ch.index,
                title=ch.title,
                content=ch.content,
                word_count=len(ch.content),
            ))
            if (i + 1) % 50 == 0:
                await db.flush()

        book.chapter_count = len(chapters)
        book.status = "done"
        await db.commit()

    # 注意：此时仍标记为 done，因为章节内容已成功获取
    # EPUB/TXT 生成失败不影响 done 状态，仅在 progress 中记录错误
    _crawl_progress[book_id] = {
        "current": len(chapters),
        "total": len(chapters),
        "status": "done",
        "error": None,
    }
    logger.info(f"《{book_title}》章节写入完成: {len(chapters)} 章，开始生成电子书文件…")

    # ══ 4. 生成 EPUB 和 TXT ══
    epub_path = None
    txt_path = None

    # 生成 EPUB
    try:
        epub_path = await asyncio.get_running_loop().run_in_executor(
            _thread_pool,
            lambda: epub_service.generate(
                book_id=book_id,
                title=book_title,
                author=book_author,
                chapters=[{"title": c.title, "content": c.content} for c in chapters],
            ),
        )
        logger.info(f"EPUB 已生成: {epub_path}")
    except Exception as e:
        logger.error(f"EPUB 生成失败: {e}")
        _crawl_progress[book_id]["error"] = f"章节抓取成功，但 EPUB 生成失败: {e}"

    # 生成 TXT
    try:
        txt_path = await asyncio.get_running_loop().run_in_executor(
            _thread_pool,
            lambda: txt_service.generate(
                book_id=book_id,
                title=book_title,
                author=book_author,
                chapters=[{"title": c.title, "content": c.content} for c in chapters],
            ),
        )
        logger.info(f"TXT 已生成: {txt_path}")
    except Exception as e:
        logger.error(f"TXT 生成失败: {e}")
        current_error = _crawl_progress[book_id].get("error") or ""
        if current_error:
            current_error += "; "
        _crawl_progress[book_id]["error"] = f"{current_error}TXT 生成失败: {e}"

    # 统一更新文件路径 — 使用单个 DB Session（排除已删除的书籍）
    if epub_path or txt_path:
        async with async_session() as db:
            result = await db.execute(
                select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
            )
            book = result.scalar_one_or_none()
            if book:
                if epub_path:
                    book.epub_path = epub_path
                if txt_path:
                    book.txt_path = txt_path
                await db.commit()
            else:
                logger.warning(f"书籍 {book_id} 已被删除，文件路径未写入数据库")

    # 清理内存状态由 _cleanup_task 的 done callback 统一处理
