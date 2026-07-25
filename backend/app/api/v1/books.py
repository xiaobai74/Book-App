"""
书架 & 搜索 & 抓取路由

GET    /api/v1/books                → 书架列表
POST   /api/v1/books                → 添加书籍
DELETE /api/v1/books/{book_id}      → 删除书籍
GET    /api/v1/books/{book_id}      → 书籍详情

GET    /api/v1/search?q=&page=1    → 在线搜索

POST   /api/v1/books/{book_id}/crawl        → 触发抓取
GET    /api/v1/books/{book_id}/crawl-status → 查询抓取进度
GET    /api/v1/books/{book_id}/download     → 下载 .epub
"""

from math import ceil

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.error_handler import AppException
from app.models.user import User
from app.schemas.book import BookCreateRequest, BookResponse, CrawlStatusResponse
from app.schemas.common import ApiResponse, PaginationMeta
from app.services.book_service import BookService, book_to_response
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
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的书架列表，按添加时间倒序"""
    books, total = await BookService.get_books(db, current_user, page, page_size)
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
    """软删除书架上的指定书籍"""
    await BookService.delete_book(db, current_user, book_id)
    return ApiResponse.ok(data=None)


# ============================================================
# 在线搜索
# ============================================================

@router.get(
    "/search",
    response_model=ApiResponse[list[BookResponse]],
    summary="在线搜索小说",
)
async def search_books(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    在已有书架中按书名模糊搜索。

    注意: v1.0 暂为书架内搜索，v1.1 将接入外部搜索引擎实现全网搜索。
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
    """触发对指定小说的内容抓取（异步任务占位）"""
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
    """查询指定小说的抓取进度"""
    status = await BookService.get_crawl_status(db, current_user, book_id)
    return ApiResponse.ok(data=status)


@router.get(
    "/books/{book_id}/download",
    summary="下载 .epub 文件",
)
async def download_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    下载已生成的 .epub 电子书文件。

    当前为占位实现，epub_path 为空时返回 404。
    后续爬虫模块实现后将返回实际文件。
    """
    book = await BookService.get_book_detail(db, current_user, book_id)

    if not book.epub_path:
        raise AppException(status_code=404, detail="该书籍尚未生成 .epub 文件，请先抓取")

    # TODO: 根据实际存储路径返回文件
    # return FileResponse(book.epub_path, filename=f"{book.title}-{book.author}.epub")
    raise AppException(status_code=501, detail="下载功能开发中")
