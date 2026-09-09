"""
书架 & 搜索 & 抓取路由

GET    /api/v1/books                → 书架列表
POST   /api/v1/books                → 添加书籍
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
import os
from math import ceil
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
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
from app.services.book_service import (
    BookService,
    book_to_response,
    chapter_to_detail_response,
    chapter_to_response,
)
from app.services.crawl_source_service import CrawlSourceService
from app.services.crawl_manager import (
    get_crawl_progress,
    subscribe_crawl,
    unsubscribe_crawl,
)
from app.services.crawler_service import crawler
from app.services.search_service import search_service
from app.utils.deps import get_current_user

router = APIRouter(tags=["书架 / 搜索 / 抓取"])


# ============================================================
# 书架 CRUD
# ============================================================

@router.get(
    "/books",
    response_model=ApiResponse[list[BookResponse]],
    summary="获取书架列表",
)
async def list_books(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=500, description="每页数量"),
    marked: bool | None = Query(default=None, description="筛选：仅已标记/全部"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的书架列表，已标记书籍置顶，支持按标记筛选"""
    books, total = await BookService.get_books(
        db, current_user, page, page_size, filter_marked=marked,
    )
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
    """手动添加一本书到书架"""
    book = await BookService.create_book(db, current_user, data)
    return ApiResponse.ok(data=book_to_response(book))


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
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取书籍的全部章节列表（按序号升序排列，不含正文内容）"""
    chapters = await BookService.get_chapters(db, current_user, book_id)
    return ApiResponse.ok(data=[chapter_to_response(c) for c in chapters])


@router.get(
    "/books/{book_id}/chapters/{chapter_index}",
    response_model=ApiResponse[ChapterDetailResponse],
    summary="获取章节内容",
)
async def get_chapter_content(
    book_id: str,
    chapter_index: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取指定章节的正文内容，用于在线阅读器渲染"""
    chapter = await BookService.get_chapter_content(
        db, current_user, book_id, chapter_index,
    )
    return ApiResponse.ok(data=chapter_to_detail_response(chapter))


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
