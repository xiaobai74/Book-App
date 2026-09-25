"""
书架 & 搜索 & 抓取路由

GET    /api/v1/books                → 书架列表
POST   /api/v1/books                → 添加书籍
POST   /api/v1/books/import         → 导入本地小说文件（.txt/.epub/.pdf/.docx）
DELETE /api/v1/books/{book_id}      → 删除书籍（v1.2 清理本地文件）
GET    /api/v1/books/{book_id}      → 书籍详情

GET    /api/v1/search?q=&page=1    → 在线搜索（书架内 + 外部源站）
GET    /api/v1/sources              → 获取可用源站列表

POST   /api/v1/books/{book_id}/crawl        → 触发抓取
GET    /api/v1/books/{book_id}/crawl-status → 查询抓取进度
GET    /api/v1/books/{book_id}/crawl-stream → 抓取进度实时推送（SSE，边爬边看 v1.4）
GET    /api/v1/books/{book_id}/download     → 下载 .epub/.txt
POST   /api/v1/crawl/check-url              → 检查 URL 连通性

v1.2 新增：
PUT    /api/v1/books/{book_id}/mark                 → 标记/取消标记
GET    /api/v1/books/{book_id}/chapters             → 章节列表
GET    /api/v1/books/{book_id}/chapters/{index}     → 章节内容
GET    /api/v1/books/{book_id}/progress             → 阅读进度
PUT    /api/v1/books/{book_id}/progress             → 更新阅读进度

GET    /api/v1/crawl-sources                → 列出自定义源站
POST   /api/v1/crawl-sources                → 创建自定义源站
GET    /api/v1/crawl-sources/{id}           → 获取自定义源站详情
PUT    /api/v1/crawl-sources/{id}           → 更新自定义源站
DELETE /api/v1/crawl-sources/{id}           → 删除自定义源站
POST   /api/v1/crawl-sources/test           → 测试自定义规则
"""

import asyncio
import ipaddress
import json
import logging
import os
import tempfile
from datetime import datetime
from math import ceil
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.error_handler import AppException
from app.models.user import User
from app.schemas.book import (
    BookCreateRequest,
    BookResponse,
    ChapterDetailResponse,
    ChapterResponse,
    CrawlSourceCreate,
    CrawlSourceResponse,
    CrawlSourceTestRequest,
    CrawlSourceTestResponse,
    CrawlSourceUpdate,
    CrawlStatusResponse,
    ReadingProgressResponse,
    ReadingProgressUpdateRequest,
    SearchResultItem,
    SourceItem,
)
from app.schemas.common import ApiResponse, PaginationMeta
from app.models.book import Book
from app.models.chapter import Chapter
from app.services.book_service import (
    BookService,
    book_to_response,
    chapter_to_detail_response,
    chapter_to_response,
)
from app.services.crawl_source_service import CrawlSourceService
from app.services.epub_service import epub_service
from app.services.import_service import import_service
from app.services.txt_service import txt_service
from app.services.crawl_manager import (
    get_crawl_progress,
    subscribe_crawl,
    unsubscribe_crawl,
)
from app.services.crawler_service import crawler
from app.services.search_service import search_service
from app.utils.deps import get_current_user, get_current_user_flexible

router = APIRouter(tags=["书架 / 搜索 / 抓取"])

logger = logging.getLogger(__name__)


# ============================================================
# HTTP 缓存辅助（ETag / If-None-Match / 304）
# ============================================================

def _safe_ts(dt: datetime | None) -> int:
    """将 datetime 转为 POSIX 时间戳（秒）用于 ETag；None 或异常时返回 0。

    兼容 MySQL / SQLite：两者返回的均为 naive datetime，.timestamp() 按本地时区解释，
    对同一条记录稳定一致，适合作缓存校验标识（无需跨机器可比）。
    """
    if dt is None:
        return 0
    try:
        return int(dt.timestamp())
    except Exception:  # noqa: BLE001 时间戳转换失败不应阻断主流程
        return 0


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    """判断 If-None-Match 请求头是否命中给定 ETag。

    支持逗号分隔的多候选值与通配符 *；比较时忽略弱校验前缀 W/，
    使强/弱 ETag 均可命中（客户端通常原样回传服务端下发的 ETag）。
    """
    if not if_none_match:
        return False
    if if_none_match.strip() == "*":
        return True

    def _norm(v: str) -> str:
        v = v.strip()
        return v[2:] if v.startswith("W/") else v

    target = _norm(etag)
    return any(_norm(c) == target for c in if_none_match.split(","))


# ============================================================
# 书架 CRUD
# ============================================================

@router.get(
    "/books",
    response_model=ApiResponse[list[BookResponse]],
    summary="获取书架列表",
)
async def list_books(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=500, description="每页数量"),
    marked: bool | None = Query(default=None, description="筛选：仅已标记/全部"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的书架列表，已标记书籍置顶，支持按标记筛选。

    返回弱 ETag（总数 + 本页最新更新时间）+ 短缓存；命中 If-None-Match 时返回 304，
    书架无变化时避免重复传输整个列表。
    """
    books, total = await BookService.get_books(
        db, current_user, page, page_size, filter_marked=marked,
    )

    # 弱 ETag：总数变化或本页任一书籍更新即失效（书架通常单页，max 取本页已足够）
    max_updated = max((_safe_ts(b.updated_at) for b in books), default=0)
    etag = f'W/"{total}-{max_updated}"'
    cache_headers = {
        "Cache-Control": "private, max-age=60",
        "ETag": etag,
    }
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=cache_headers)

    items = [book_to_response(b) for b in books]
    body = ApiResponse.ok(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        ),
    )
    return JSONResponse(content=jsonable_encoder(body), headers=cache_headers)


@router.post(
    "/books",
    response_model=ApiResponse[BookResponse],
    summary="添加书籍",
)
async def create_book(
    data: BookCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动添加一本书到书架；若提供源站链接，自动抓取封面/简介等元数据。"""
    book = await BookService.create_book(db, current_user, data)
    # 添加时自动抓取源站元数据（封面/简介/分类/最新章节/更新时间）。
    # 有界超时保护，失败静默降级——不阻断添加流程。
    if book.source_url:
        try:
            await asyncio.wait_for(BookService.enrich_metadata(db, book), timeout=30)
        except asyncio.TimeoutError:
            logger.warning(f"元数据抓取超时（30s），已跳过: book_id={book.id}")
        except Exception:  # noqa: BLE001 元数据异常不影响添加
            logger.exception(f"元数据抓取异常，已跳过: book_id={book.id}")
    return ApiResponse.ok(data=book_to_response(book))


# ============================================================
# 本地文件导入
# ============================================================

# 允许导入的扩展名与单文件大小上限（50MB）
ALLOWED_IMPORT_EXTS = {".txt", ".epub", ".pdf", ".docx"}
MAX_IMPORT_SIZE = 50 * 1024 * 1024


@router.post(
    "/books/import",
    response_model=ApiResponse[BookResponse],
    summary="导入本地小说文件",
)
async def import_book(
    file: UploadFile = File(..., description="本地小说文件（.txt/.epub/.pdf/.docx）"),
    title: str | None = Form(default=None, max_length=500, description="书名（选填，覆盖自动推断）"),
    author: str | None = Form(default=None, max_length=255, description="作者（选填，覆盖自动推断）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传本地小说文件，解析章节入库并生成 .epub/.txt，导入后即可在线阅读。

    元数据优先级：表单 title/author（非空）> 文件内嵌元数据 > 文件名推断。
    解析为同步执行（≤50MB 本地文件耗时可控）；失败时书籍状态置 failed。
    """
    # ── 1. 校验扩展名 ──
    original_name = file.filename or "upload.txt"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_IMPORT_EXTS:
        raise AppException(
            status_code=400,
            detail=f"不支持的文件格式：{ext or '未知'}，仅支持 .txt/.epub/.pdf/.docx",
        )

    # ── 2. 读取内容并校验大小 ──
    raw = await file.read()
    if len(raw) > MAX_IMPORT_SIZE:
        raise AppException(status_code=413, detail="文件超过 50MB 上限，请压缩或拆分后重试")
    if not raw:
        raise AppException(status_code=400, detail="文件内容为空")

    # ── 3. 写入临时文件（保留扩展名供解析器识别） ──
    tmp_path: str | None = None
    book: Book | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        # ── 4. 解析（传入原始文件名，避免元数据被随机临时文件名污染） ──
        parsed = import_service.parse(tmp_path, ext, original_name)
        if not parsed.chapters:
            raise AppException(status_code=400, detail="未能从文件解析出有效内容")

        # ── 5. 元数据裁决：表单 > 内嵌 > 文件名 ──
        inferred_title, inferred_author = _infer_metadata_from_name(original_name)
        final_title = (title or "").strip() or (parsed.title or "").strip() or inferred_title or Path(original_name).stem
        final_author = (author or "").strip() or (parsed.author or "").strip() or inferred_author or "未知"
        final_title = final_title[:500]
        final_author = final_author[:255]

        # ── 6. 创建书籍（source_url 为空，标识本地导入） ──
        book = await BookService.create_book(
            db, current_user,
            BookCreateRequest(title=final_title, author=final_author, source_url=None),
        )
        book_id = book.id

        # ── 7. 批量写入章节 ──
        for idx, ch in enumerate(parsed.chapters, 1):
            db.add(Chapter(
                book_id=book_id,
                index=idx,
                title=(ch.title or f"第{idx}章")[:500],
                content=ch.content,
                word_count=len(ch.content),
            ))
        book.chapter_count = len(parsed.chapters)

        # ── 8. 复用现有服务生成 .epub / .txt ──
        chapter_dicts = [{"title": ch.title, "content": ch.content} for ch in parsed.chapters]
        book.epub_path = epub_service.generate(book_id, final_title, final_author, chapter_dicts)
        book.txt_path = txt_service.generate(book_id, final_title, final_author, chapter_dicts)

        # ── 9. 状态置 done 并提交 ──
        book.status = "done"
        await db.commit()
        await db.refresh(book)
        return ApiResponse.ok(data=book_to_response(book))

    except AppException:
        # 业务异常：若书籍已创建则标记 failed
        if book is not None:
            book.status = "failed"
            await db.commit()
        raise
    except Exception as exc:  # noqa: BLE001 解析/生成异常统一回滚
        logger.exception("导入本地文件失败: %s", original_name)
        if book is not None:
            book.status = "failed"
            try:
                await db.commit()
            except Exception:  # noqa: BLE001
                await db.rollback()
        else:
            await db.rollback()
        raise AppException(status_code=500, detail=f"导入失败：{exc}") from exc
    finally:
        # ── 10. 清理临时文件 ──
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _infer_metadata_from_name(filename: str) -> tuple[str | None, str | None]:
    """文件名推断兜底（与 import_service 内部逻辑一致，供接口层裁决使用）。"""
    from app.services.import_service import _infer_from_filename
    t, a = _infer_from_filename(filename)
    return t, a


@router.get(
    "/books/{book_id}",
    response_model=ApiResponse[BookResponse],
    summary="查看书籍详情",
)
async def get_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单本小说详情"""
    book = await BookService.get_book_detail(db, current_user, book_id)
    return ApiResponse.ok(data=book_to_response(book))


@router.get(
    "/books/{book_id}/cover",
    summary="获取书籍封面图片",
)
async def get_book_cover(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """返回本地缓存的封面图片，供前端 <img> 直接加载。

    浏览器无法为 <img> 请求附加 Authorization 头，因此鉴权支持
    ?token= 查询参数（见 get_current_user_flexible）；仍校验书籍归属。
    """
    book = await BookService.get_book_detail(db, current_user, book_id)
    if not book.cover_path or not os.path.exists(book.cover_path):
        raise AppException(status_code=404, detail="该书籍暂无封面")
    # 封面图片内容固定（以 book_id 命名、覆盖式写入），可长期强缓存
    return FileResponse(
        book.cover_path,
        media_type=_guess_image_media_type(book.cover_path),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def _guess_image_media_type(path: str) -> str:
    """根据文件头字节推断图片 MIME 类型（下载时统一存为 .jpg，实际可能为 png/webp 等）。"""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return "image/jpeg"


@router.delete(
    "/books/{book_id}",
    response_model=ApiResponse[None],
    summary="删除书籍",
)
async def delete_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """软删除书架上的指定书籍，同时清理本地 .epub/.txt 文件"""
    await BookService.delete_book(db, current_user, book_id)
    return ApiResponse.ok(data=None)


# ============================================================
# v1.2 新增：标记与置顶
# ============================================================

@router.put(
    "/books/{book_id}/mark",
    response_model=ApiResponse[BookResponse],
    summary="标记/取消标记书籍",
)
async def toggle_mark_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换书籍的标记状态，已标记的书籍自动置顶到书架顶部"""
    book = await BookService.toggle_mark(db, current_user, book_id)
    return ApiResponse.ok(data=book_to_response(book))


# ============================================================
# v1.2 新增：在线阅读器
# ============================================================

@router.get(
    "/books/{book_id}/chapters",
    response_model=ApiResponse[list[ChapterResponse]],
    summary="获取章节列表",
)
async def list_chapters(
    request: Request,
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取书籍的全部章节列表（按序号升序排列，不含正文内容）。

    目录随书籍更新/抓取进度变化，返回短缓存 + ETag（书籍更新时间 + 章节数）；
    命中 If-None-Match 时返回 304，边爬边看场景下可显著降低目录轮询开销。
    """
    # 轻量获取书籍元数据（列查询，不触发 chapters 关系的 selectin 正文加载）并校验归属
    updated_at, chapter_count = await BookService.get_book_cache_meta(
        db, current_user, book_id,
    )
    etag = f'"{_safe_ts(updated_at)}-{chapter_count}"'
    cache_headers = {
        "Cache-Control": "private, max-age=300",
        "ETag": etag,
    }
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=cache_headers)

    # 仅查询目录元数据（load_only 排除 MEDIUMTEXT 正文），降低内存与传输开销
    chapters = await BookService.get_chapters_list(db, book_id)
    body = ApiResponse.ok(data=[chapter_to_response(c) for c in chapters])
    return JSONResponse(content=jsonable_encoder(body), headers=cache_headers)


@router.get(
    "/books/{book_id}/chapters/{chapter_index}",
    response_model=ApiResponse[ChapterDetailResponse],
    summary="获取章节内容",
)
async def get_chapter_content(
    request: Request,
    book_id: str,
    chapter_index: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定章节的正文内容，用于在线阅读器渲染。

    正文写入后不可变，返回 immutable 长缓存头 + ETag（章节 id + 创建时间）；
    命中 If-None-Match 时返回 304，重读同章无需重复传输大段正文。
    """
    chapter = await BookService.get_chapter_content(
        db, current_user, book_id, chapter_index,
    )
    cache_headers = {
        "Cache-Control": "private, max-age=604800, immutable",
        "ETag": f'"{chapter.id}-{_safe_ts(chapter.created_at)}"',
    }
    if _etag_matches(request.headers.get("if-none-match"), cache_headers["ETag"]):
        return Response(status_code=304, headers=cache_headers)
    body = ApiResponse.ok(data=chapter_to_detail_response(chapter))
    return JSONResponse(content=jsonable_encoder(body), headers=cache_headers)


@router.get(
    "/books/{book_id}/progress",
    response_model=ApiResponse[ReadingProgressResponse],
    summary="获取阅读进度",
)
async def get_reading_progress(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户在该书的最后阅读章节序号"""
    progress = await BookService.get_reading_progress(db, current_user, book_id)
    return ApiResponse.ok(data=progress)


@router.put(
    "/books/{book_id}/progress",
    response_model=ApiResponse[ReadingProgressResponse],
    summary="更新阅读进度",
)
async def update_reading_progress(
    book_id: str,
    data: ReadingProgressUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户在该书的阅读进度（upsert），下次进入时自动恢复"""
    progress = await BookService.update_reading_progress(
        db, current_user, book_id, data.chapter_index,
    )
    return ApiResponse.ok(data=progress)


# ============================================================
# 在线搜索
# ============================================================

@router.get(
    "/search",
    response_model=ApiResponse[list[BookResponse]],
    summary="在线搜索小说（书架内）",
)
async def search_books(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=500, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    在已有书架中按书名模糊搜索。

    注意: v1.0 暂为书架内搜索，v2.0 使用 /api/v1/search/external 进行全网搜索。
    """
    books, total = await BookService.search_books(db, current_user, q, page, page_size)
    items = [book_to_response(b) for b in books]

    return ApiResponse.ok(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        ),
    )


@router.get(
    "/search/external",
    response_model=ApiResponse[list[SearchResultItem]],
    summary="外部源站在线搜索小说",
)
async def search_books_external(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    source_id: int | None = Query(default=None, description="指定源站ID，不传则搜索所有源站"),
    search_limit: int = Query(default=30, ge=1, le=100, description="每个源站最大结果数"),
    current_user: User = Depends(get_current_user),
):
    """
    在全网小说源站中搜索小说。

    支持指定源站搜索或遍历所有已配置的源站。
    返回合并去重后的搜索结果，包括书名、作者、源站名称、详情页URL等信息。
    """
    results = await search_service.search(
        keyword=q,
        source_id=source_id,
        search_limit=search_limit,
    )
    items = [
        SearchResultItem(
            title=r.title,
            author=r.author,
            source_url=r.source_url,
            source_name=r.source_name,
            source_id=r.source_id,
            category=r.category,
            word_count=r.word_count,
            status=r.status,
            latest_chapter=r.latest_chapter,
            last_update_time=r.last_update_time,
        )
        for r in results
    ]
    return ApiResponse.ok(
        data=items,
        meta=PaginationMeta(
            page=1,
            page_size=len(items),
            total=len(items),
            total_pages=1,
        ),
    )


@router.get(
    "/search/external/stream",
    summary="外部源站搜索流式返回（SSE，v2.7 阶段1a）",
)
async def search_books_external_stream(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    source_id: int | None = Query(default=None, description="指定源站ID，不传则搜索所有源站"),
    search_limit: int = Query(default=30, ge=1, le=100, description="每个源站最大结果数"),
    current_user: User = Depends(get_current_user),
):
    """
    以 Server-Sent Events 按源站增量推送搜索结果。

    事件类型（data 均为 JSON）：
    - meta:  {"sources":[{id,name}], "cached":bool}  本次参与的源站清单（cached=命中后端缓存）
    - source:{"source_id","source_name","results":[SearchResultItem...]}  单源完成即推送
    - done:  {"total":n}  合并去重后的总结果数，流结束

    前端使用 fetch + ReadableStream 消费（携带 Authorization 头），
    连接失败时回退同步端点 GET /search/external。
    """

    def _item(r) -> dict:
        return SearchResultItem(
            title=r.title, author=r.author, source_url=r.source_url,
            source_name=r.source_name, source_id=r.source_id,
            category=r.category, word_count=r.word_count, status=r.status,
            latest_chapter=r.latest_chapter, last_update_time=r.last_update_time,
        ).model_dump()

    async def event_generator():
        async for kind, payload in search_service.search_stream(q, source_id, search_limit):
            if kind == "ping":
                yield ": ping\n\n"  # 心跳注释行，防代理/浏览器空闲断连
                continue
            data = {"type": kind, **payload}
            if kind == "source" and data.get("results"):
                data["results"] = [_item(r) for r in payload["results"]]
            else:
                data["results"] = []
            yield "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲，保证结果即时下发
            "Connection": "keep-alive",
        },
    )


# ============================================================
# 源站列表
# ============================================================

@router.get(
    "/sources",
    response_model=ApiResponse[list[SourceItem]],
    summary="获取可用源站列表",
)
async def list_sources(
    current_user: User = Depends(get_current_user),
):
    """返回所有已配置的小说源站信息"""
    sources = crawler.list_sources()
    items = [SourceItem(**s) for s in sources]
    return ApiResponse.ok(data=items)


# ============================================================
# 抓取 & EPUB 生成
# ============================================================

@router.post(
    "/books/{book_id}/crawl",
    response_model=ApiResponse[BookResponse],
    summary="触发抓取",
)
async def crawl_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发对指定小说的内容抓取（后台异步执行）"""
    book = await BookService.trigger_crawl(db, current_user, book_id)
    return ApiResponse.ok(data=book_to_response(book))


@router.get(
    "/books/{book_id}/crawl-status",
    response_model=ApiResponse[CrawlStatusResponse],
    summary="查询抓取进度",
)
async def get_crawl_status(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询指定小说的实时抓取进度"""
    status = await BookService.get_crawl_status(db, current_user, book_id)
    return ApiResponse.ok(data=status)


@router.get(
    "/books/{book_id}/crawl-stream",
    summary="抓取进度实时推送（SSE）",
)
async def crawl_stream(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    以 Server-Sent Events 实时推送抓取事件（边爬边看 v1.4）。

    事件类型：
    - snapshot:      订阅时的当前状态快照（含目录计划 plan）
    - plan:          章节列表就绪（完整目录标题）
    - chapter_ready: 单章抓取完成并已写库（可立即阅读）
    - done:          全部章节完成
    - failed:        抓取失败

    无活跃抓取任务时返回 status=none 的 snapshot 后关闭流。
    前端使用 fetch + ReadableStream 消费（携带 Authorization 头）。
    """
    # 所有权校验：非本人书籍返回 404
    await BookService.get_book_detail(db, current_user, book_id)

    async def event_generator():
        q = subscribe_crawl(book_id)
        try:
            progress = get_crawl_progress(book_id)
            if progress is None:
                # 无活跃任务：发送空快照后结束（前端回退到常规加载/轮询）
                yield "data: " + json.dumps({
                    "type": "snapshot", "status": "none",
                    "current": 0, "total": 0, "percentage": 0.0, "plan": [],
                }, ensure_ascii=False) + "\n\n"
                return

            total = progress.get("total") or 0
            current = progress.get("current") or 0
            yield "data: " + json.dumps({
                "type": "snapshot",
                "status": progress.get("status"),
                "current": current,
                "total": total,
                "percentage": round(current / total * 100, 1) if total else 0.0,
                "plan": progress.get("plan", []),
                "error": progress.get("error"),
            }, ensure_ascii=False) + "\n\n"

            if progress.get("status") in ("done", "failed"):
                return

            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    # 心跳保活，防止代理/浏览器空闲断连
                    yield ": ping\n\n"
                    continue
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                if event.get("type") in ("done", "failed"):
                    break
        except asyncio.CancelledError:
            # 客户端断开连接
            raise
        finally:
            unsubscribe_crawl(book_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲，保证事件即时下发
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/books/{book_id}/download",
    summary="下载电子书文件",
)
async def download_book(
    book_id: str,
    format: str = Query(default="epub", pattern="^(epub|txt)$", description="下载格式：epub 或 txt"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    下载已生成的电子书文件。

    支持 EPUB 和 TXT 两种格式，通过 format 参数指定。
    如果对应格式文件不存在则返回 404。
    """
    book = await BookService.get_book_detail(db, current_user, book_id)

    if format == "txt":
        if not book.txt_path:
            raise AppException(status_code=404, detail="该书籍尚未生成 TXT 文件，请先抓取")
        file_path = book.txt_path
        if not os.path.exists(file_path):
            raise AppException(status_code=404, detail="TXT 文件已被清理，请重新抓取")
        filename = f"{book.title}-{book.author}.txt"
        media_type = "text/plain; charset=utf-8"
    else:
        if not book.epub_path:
            raise AppException(status_code=404, detail="该书籍尚未生成 EPUB 文件，请先抓取")
        file_path = book.epub_path
        if not os.path.exists(file_path):
            raise AppException(status_code=404, detail="EPUB 文件已被清理，请重新抓取")
        filename = f"{book.title}-{book.author}.epub"
        media_type = "application/epub+zip"

    return FileResponse(
        file_path,
        filename=filename,
        media_type=media_type,
    )


# ============================================================
# URL 连通性预检
# ============================================================

def _validate_public_url(url: str) -> None:
    """SSRF 防护：仅允许 http/https 协议，拒绝环回/私网/链路本地地址的 URL。

    防止认证用户利用本服务探测内网（如 127.0.0.1、169.254.169.254 等）。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise AppException(status_code=400, detail="仅支持 http/https 协议的网络地址")
    try:
        ip = ipaddress.ip_address(parsed.hostname or "")
    except ValueError:
        # 域名不做 DNS 解析（避免引入解析依赖），仅拦截 IP 字面量
        ip = None
    if ip is not None and (
        ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast
    ):
        raise AppException(status_code=400, detail="不允许访问内网或保留地址")


class CheckUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048, description="要检查的小说源站 URL")


class CheckUrlResponse(BaseModel):
    reachable: bool
    status_code: int | None
    content_length: int
    error_message: str | None
    suggested_fix: str | None


@router.post(
    "/crawl/check-url",
    response_model=ApiResponse[CheckUrlResponse],
    summary="检查源站 URL 连通性",
)
async def check_url(
    body: CheckUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    在触发抓取之前检查源站 URL 是否可达。

    返回连通性检测结果和建议，帮助用户判断 URL 是否有效。
    """
    _validate_public_url(body.url)
    result = await crawler.check_connectivity(body.url)
    return ApiResponse.ok(data=CheckUrlResponse(
        reachable=result.reachable,
        status_code=result.status_code,
        content_length=result.content_length,
        error_message=result.error_message,
        suggested_fix=result.suggested_fix,
    ))


# ============================================================
# 自定义抓取源站 CRUD
# ============================================================

crawl_source_router = APIRouter(prefix="/crawl-sources", tags=["自定义源站"])


@crawl_source_router.get(
    "",
    response_model=ApiResponse[list[CrawlSourceResponse]],
    summary="列出自定义源站",
)
async def list_crawl_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户创建的所有自定义源站规则"""
    items = await CrawlSourceService.list_sources(db, current_user)
    return ApiResponse.ok(data=items)


@crawl_source_router.post(
    "",
    response_model=ApiResponse[CrawlSourceResponse],
    summary="创建自定义源站",
)
async def create_crawl_source(
    data: CrawlSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建一条自定义源站抓取规则"""
    source = await CrawlSourceService.create(db, current_user, data)
    return ApiResponse.ok(data=source)


@crawl_source_router.get(
    "/{source_id}",
    response_model=ApiResponse[CrawlSourceResponse],
    summary="获取自定义源站详情",
)
async def get_crawl_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个自定义源站规则详情"""
    source = await CrawlSourceService.get(db, current_user, source_id)
    return ApiResponse.ok(data=source)


@crawl_source_router.put(
    "/{source_id}",
    response_model=ApiResponse[CrawlSourceResponse],
    summary="更新自定义源站",
)
async def update_crawl_source(
    source_id: int,
    data: CrawlSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新自定义源站抓取规则"""
    source = await CrawlSourceService.update(db, current_user, source_id, data)
    return ApiResponse.ok(data=source)


@crawl_source_router.delete(
    "/{source_id}",
    response_model=ApiResponse[None],
    summary="删除自定义源站",
)
async def delete_crawl_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除自定义源站规则"""
    await CrawlSourceService.delete(db, current_user, source_id)
    return ApiResponse.ok(data=None)


@crawl_source_router.post(
    "/test",
    response_model=ApiResponse[CrawlSourceTestResponse],
    summary="测试自定义源站规则",
)
async def test_crawl_source(
    data: CrawlSourceTestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    测试自定义规则是否能正确解析指定 URL 的章节列表。

    返回章节总数和前 5 条章节信息，帮助用户验证规则配置是否有效。
    """
    _validate_public_url(data.url)
    result = await CrawlSourceService.test_rule(data.url, data.rule_json)
    return ApiResponse.ok(data=CrawlSourceTestResponse(**result))
