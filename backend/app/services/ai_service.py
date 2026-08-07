"""
AI 服务 — Dify 工作流调用封装

提供: 自然语言书架搜索、智能阅读摘要生成。
后台任务使用 asyncio.create_task() 模式（与 crawl_manager.py 一致）。

v1.4 优化:
- 语义搜索增加阅读进度 + 标记状态等丰富上下文传给 Dify
- 增加本地关键词回退搜索（Dify 不可用时自动降级）
- 优化 Dify Workflow 响应解析路径
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import or_, select

from app.config import settings
from app.database import async_session
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.reading_progress import ReadingProgress
from app.models.user import User

logger = logging.getLogger(__name__)

# 摘要生成进度: {book_id: {"status": str, "error": str|None}}
_summary_progress: dict[str, dict] = {}

# 后台任务引用
_running_summary_tasks: dict[str, asyncio.Task] = {}

# Dify 请求超时
_DIFY_TIMEOUT = httpx.Timeout(120.0, connect=15.0)


def _strip_markdown_fence(text: str) -> str:
    """去除 LLM 返回结果外层可能包裹的 markdown 代码块标记（```json ... ```）。"""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        # 去掉首行 ``` 或 ```json
        lines = lines[1:]
        # 去掉尾行 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return t


def _safe_parse_json_array(raw: str, fallback: list | None = None) -> list:
    """安全解析 JSON 数组，解析失败时返回 fallback（默认空列表）。"""
    fallback = fallback if fallback is not None else []
    if not raw or not raw.strip():
        return fallback
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else fallback
    except json.JSONDecodeError:
        logger.warning("JSON 数组解析失败，原始文本前 200 字符: %s", raw[:200])
        return fallback


class AiService:
    """AI 服务 — Dify 工作流调用封装"""

    # ═══════════════════════════════════════════════════════
    # 自然语言书架搜索
    # ═══════════════════════════════════════════════════════

    @staticmethod
    async def semantic_search(user: User, query: str) -> list[dict]:
        """自然语言搜索书架中的书籍。

        工作流:
        1. 从 DB 获取当前用户的全部书籍 + 阅读进度
        2. 将书籍列表 JSON + 用户 query 发给 Dify Chatflow
        3. Dify 返回语义匹配的 Top 5 结果
        4. Dify 不可用时自动回退为本地关键词搜索

        Returns:
            [{"book_id": str, "title": str, "author": str, "match_reason": str, "score": int}, ...]
        """
        # 1. 获取用户全部书籍 + 阅读进度
        async with async_session() as db:
            book_result = await db.execute(
                select(Book).where(
                    Book.user_id == user.id,
                    Book.deleted_at.is_(None),
                ).order_by(Book.added_at.desc())
            )
            books = list(book_result.scalars().all())

            # 获取所有书籍的阅读进度（用于 Dify 匹配排序）
            progress_result = await db.execute(
                select(ReadingProgress).where(
                    ReadingProgress.user_id == user.id,
                    ReadingProgress.book_id.in_([b.id for b in books]),
                )
            )
            progress_map: dict[str, int] = {}
            for p in progress_result.scalars().all():
                progress_map[p.book_id] = p.last_chapter_index

        if not books:
            return []

        # 2. 构造丰富的书籍上下文数据
        books_data = [
            {
                "book_id": b.id,
                "title": b.title,
                "author": b.author,
                "status": b.status,
                "chapter_count": b.chapter_count,
                "is_marked": b.is_marked,
                "marked_at": b.marked_at.isoformat() if b.marked_at else None,
                "reading_progress": {
                    "last_chapter": progress_map.get(b.id, 0),
                    "is_reading": progress_map.get(b.id, 0) > 0,
                },
                "has_epub": b.epub_path is not None and b.epub_path != "",
                "added_at": b.added_at.isoformat() if b.added_at else None,
            }
            for b in books
        ]

        total_count = len(books)

        # 3. 调用 Dify Chatflow（如果不可用则回退为本地搜索）
        if not settings.dify_api_url or not settings.dify_api_key:
            logger.warning("Dify 未配置，使用本地关键词搜索回退")
            return AiService._local_fallback_search(books, query, top_k=5)

        try:
            async with httpx.AsyncClient(timeout=_DIFY_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.dify_api_url}/chat-messages",
                    headers={
                        "Authorization": f"Bearer {settings.dify_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "user": user.id,
                        "response_mode": "blocking",
                        "inputs": {
                            "query": query,
                            "total_book_count": total_count,
                            "books_json": json.dumps(books_data, ensure_ascii=False),
                        },
                    },
                )
                resp.raise_for_status()
                body = resp.json()

            # 4. 解析 Dify 返回的 answer（应为 JSON 数组）
            answer = body.get("answer", "[]")
            answer = _strip_markdown_fence(answer)
            results = _safe_parse_json_array(answer, fallback=[])
            return results[:5]

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("Dify 搜索请求网络错误: %s，回退为本地搜索", e)
            return AiService._local_fallback_search(books, query, top_k=5)
        except Exception as e:
            logger.exception("Dify 搜索请求异常: %s，回退为本地搜索", e)
            return AiService._local_fallback_search(books, query, top_k=5)

    @staticmethod
    def _local_fallback_search(
        books: list[Book], query: str, top_k: int = 5
    ) -> list[dict]:
        """本地关键词回退搜索（当 Dify 不可用时）。

        在书名和作者字段中做不区分大小写的子串匹配，
        按以下权重排序:
        - 书名精确匹配 > 书名包含 > 作者包含
        - 已标记的书籍加分
        - 有阅读进度的书籍加分
        """
        q = query.strip().lower()
        scored: list[tuple[Book, int]] = []

        for b in books:
            score = 0
            title_l = b.title.lower()
            author_l = b.author.lower()

            # 精确匹配加分
            if q == title_l:
                score += 100
            elif q in title_l:
                score += 60
            elif any(word in title_l for word in q.split()):
                score += 40
            elif q in author_l:
                score += 30

            # 标记加分
            if b.is_marked:
                score += 15

            # 有内容加分（越丰富分越高）
            if b.chapter_count > 0:
                score += min(b.chapter_count // 10, 10)

            # 有已生成文件加分
            if b.epub_path:
                score += 5

            if score > 0:
                scored.append((b, score))

        # 按分数降序排列
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for b, score in scored[:top_k]:
            results.append({
                "book_id": str(b.id),
                "title": b.title,
                "author": b.author,
                "match_reason": _generate_match_reason(b, query),
                "score": min(score, 100),
            })

        return results

    # ═══════════════════════════════════════════════════════
    # 智能阅读摘要生成
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _cleanup_task_state(book_id: str) -> None:
        """同步清理已完成/异常任务的内存状态（_summary_progress + _running_summary_tasks）。"""
        if book_id in _running_summary_tasks:
            task = _running_summary_tasks[book_id]
            if task.done():
                del _running_summary_tasks[book_id]
                # done 的进度已在 _run_summary_pipeline 中最后设置；
                # 若 pipeline 中途崩溃导致状态仍为 queued/generating，标记为 unknown
                prog = _summary_progress.get(book_id, {})
                if prog.get("status") in ("queued", "generating", None):
                    _summary_progress[book_id] = {
                        "status": "failed",
                        "error": "后台任务异常终止，请重试",
                    }
                return
            # 任务仍存活：保留下 _running_summary_tasks 引用
        else:
            # _running_summary_tasks 中无记录但 _summary_progress 中有残留 queued/generating
            prog = _summary_progress.get(book_id, {})
            if prog.get("status") in ("queued", "generating"):
                _summary_progress[book_id] = {
                    "status": "failed",
                    "error": "后台任务异常终止（可能服务重启），请重试",
                }

    @staticmethod
    def get_summary_status(book_id: str) -> dict | None:
        """获取摘要生成进度。若内存中有异常残留状态，自动修正。"""
        AiService._cleanup_task_state(book_id)
        return _summary_progress.get(book_id)

    @staticmethod
    async def start_summary_generation(book_id: str) -> dict:
        """启动摘要生成后台任务。

        Returns:
            {"status": "queued"|"running"|"failed"}
        """
        # 清理已完成的任务（同时清理 _summary_progress 中残留的 queued/generating 状态）
        AiService._cleanup_task_state(book_id)

        if book_id in _running_summary_tasks:
            return {"status": "running"}

        if not settings.dify_api_url or not settings.dify_summary_api_key:
            return {"status": "failed", "error": "Dify 未配置"}

        _summary_progress[book_id] = {"status": "queued", "error": None}
        loop = asyncio.get_running_loop()
        task = loop.create_task(AiService._run_summary_pipeline(book_id))
        _running_summary_tasks[book_id] = task
        logger.info("AI 摘要生成任务已创建: book_id=%s", book_id)
        return {"status": "queued"}

    @staticmethod
    async def _run_summary_pipeline(book_id: str) -> None:
        """后台摘要生成流水线：获取样本 → 调用 Dify → 存储结果。"""
        _summary_progress[book_id] = {"status": "generating", "error": None}

        book_title = ""
        book_author = ""
        chapter_samples = ""

        # 1. 获取书籍信息和章节样本
        async with async_session() as db:
            book_result = await db.execute(select(Book).where(Book.id == book_id))
            book = book_result.scalar_one_or_none()

            if not book:
                _summary_progress[book_id] = {"status": "failed", "error": "书籍不存在"}
                return

            book_title = book.title
            book_author = book.author

            # 获取章节列表（按序号排序）
            ch_result = await db.execute(
                select(Chapter)
                .where(Chapter.book_id == book_id)
                .order_by(Chapter.index.asc())
            )
            chapters = list(ch_result.scalars().all())

            if not chapters:
                _summary_progress[book_id] = {"status": "failed", "error": "无章节数据，请先抓取"}
                return

            # 选取样本：前 3 章 + 后 2 章（去重，总共最多 5 章）
            sample_indices: set[int] = set()
            for i in range(min(3, len(chapters))):
                sample_indices.add(i)
            for i in range(max(0, len(chapters) - 2), len(chapters)):
                sample_indices.add(i)

            samples = []
            for i in sorted(sample_indices):
                ch = chapters[i]
                # 正文截取前 800 字符（避免超出 Dify token 限制）
                content_preview = ch.content[:800] if ch.content else "（无内容）"
                samples.append(
                    f"第{ch.index}章 {ch.title}\n{content_preview}"
                )
            chapter_samples = "\n\n---\n\n".join(samples)

        # 2. 调用 Dify Workflow
        try:
            async with httpx.AsyncClient(timeout=_DIFY_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.dify_api_url}/workflows/run",
                    headers={
                        "Authorization": f"Bearer {settings.dify_summary_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "inputs": {
                            "book_title": book_title,
                            "book_author": book_author,
                            "chapter_samples": chapter_samples,
                        },
                        "response_mode": "blocking",
                        "user": book.user_id,
                    },
                )
                resp.raise_for_status()
                body = resp.json()

            # 3. 提取摘要文本 — 适配多种 Dify API 响应格式
            # Dify v1.x 格式: {"data": {"outputs": {"summary_text": "..."}}}
            # Dify 自托管/云版可能: {"data": {"outputs": {"text": "..."}}}
            # Dify Chatflow: {"answer": "..."}
            summary_text = ""
            data_section = body.get("data", {})
            if isinstance(data_section, dict):
                outputs = data_section.get("outputs", {}) or {}
                summary_text = outputs.get("summary_text") or outputs.get("text") or ""
            if not summary_text:
                # 尝试 Chatflow 格式
                summary_text = body.get("answer", "")
            if not summary_text:
                _summary_progress[book_id] = {
                    "status": "failed",
                    "error": "Dify 工作流未返回摘要内容，请检查工作流配置",
                }
                logger.error("Dify 摘要响应格式不符预期: %s", json.dumps(body, ensure_ascii=False)[:500])
                return

            # 4. 存储摘要到数据库
            async with async_session() as db:
                book_result = await db.execute(select(Book).where(Book.id == book_id))
                book = book_result.scalar_one_or_none()
                if book:
                    book.ai_summary = summary_text.strip()
                    book.ai_summary_at = datetime.now(UTC).replace(tzinfo=None)
                    await db.commit()
                    logger.info("AI 摘要已生成并存储: book_id=%s", book_id)

            _summary_progress[book_id] = {"status": "done", "error": None}

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            error_msg = f"Dify 网络错误: {e}"
            _summary_progress[book_id] = {"status": "failed", "error": error_msg}
            logger.error("摘要生成失败 [%s]: %s", book_id, error_msg)
        except Exception as e:
            error_msg = str(e)
            _summary_progress[book_id] = {"status": "failed", "error": error_msg}
            logger.exception("摘要生成异常 [%s]: %s", book_id, error_msg)

    @staticmethod
    async def get_summary_from_db(book_id: str, user_id: str | None = None) -> dict | None:
        """从数据库获取已生成的摘要（用于 GET 端点）。

        若提供 user_id，则校验书籍所有权，防止跨用户数据泄露。
        同时过滤已软删除的记录。
        """
        async with async_session() as db:
            conditions = [
                Book.id == book_id,
                Book.deleted_at.is_(None),
            ]
            if user_id:
                conditions.append(Book.user_id == user_id)
            result = await db.execute(select(Book).where(*conditions))
            book = result.scalar_one_or_none()
            if not book:
                return None
            return {
                "ai_summary": book.ai_summary,
                "ai_summary_at": book.ai_summary_at.isoformat() if book.ai_summary_at else None,
                "status": "done" if book.ai_summary else (
                    _summary_progress.get(book_id, {}).get("status", "none")
                ),
            }


def _generate_match_reason(book: Book, query: str) -> str:
    """为本地回退搜索生成匹配原因说明（中文）。"""
    title_l = book.title.lower()
    author_l = book.author.lower()
    q = query.strip().lower()

    parts = []
    if q in title_l:
        parts.append(f"书名包含「{query}」")
    elif any(word in title_l for word in q.split()):
        parts.append(f"书名关键词匹配「{query}」")
    if q in author_l:
        parts.append(f"作者为「{book.author}」")
    if book.is_marked:
        parts.append("已标记")
    if book.chapter_count > 0:
        parts.append(f"已有{book.chapter_count}章内容")
    if not parts:
        parts.append("综合匹配")

    return "，".join(parts)


# 全局单例
ai_service = AiService()
