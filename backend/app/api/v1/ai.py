"""
AI 功能路由（v1.3 新增）

POST   /api/v1/ai/search               → 自然语言书架搜索
POST   /api/v1/ai/summary/{book_id}     → 触发 AI 摘要生成
GET    /api/v1/ai/summary/{book_id}     → 获取 AI 摘要
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.error_handler import AppException
from app.models.book import Book
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.ai_service import ai_service
from app.utils.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["AI 功能"])


# ═══════════════════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════════════════

class AiSearchRequest(BaseModel):
    """AI 搜索请求"""
    # 长度约束放在验证器中而非 Field，保证返回中文错误文案（同 RegisterRequest）
    query: str = Field(..., description="自然语言搜索关键词")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if len(v.strip()) > 500:
            raise ValueError("搜索关键词最长 500 字符")
        return v


class AiSearchResultItem(BaseModel):
    """AI 搜索结果项"""
    book_id: str
    title: str
    author: str
    match_reason: str
    score: int


class SummaryStatusResponse(BaseModel):
    """摘要状态响应"""
    status: str  # queued | generating | running | done | failed | none
    ai_summary: str | None = None
    ai_summary_at: str | None = None
    error: str | None = None


# ═══════════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════════

@router.post(
    "/search",
    response_model=ApiResponse[list[AiSearchResultItem]],
    summary="AI 自然语言书架搜索",
)
async def ai_search(
    body: AiSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    使用自然语言在书架中搜索书籍。

    示例查询:
    - "最近看的那本修仙小说"
    - "主角姓林的"
    - "被标记的那几本书"

    后端将用户的书架数据传给 Dify Chatflow，由 LLM 进行语义匹配。
    """
    if not body.query or len(body.query.strip()) < 2:
        raise AppException(status_code=400, detail="搜索关键词至少需要 2 个字符")

    results = await ai_service.semantic_search(current_user, body.query.strip())
    return ApiResponse.ok(data=[AiSearchResultItem(**r) for r in results])


@router.post(
    "/summary/{book_id}",
    response_model=ApiResponse[SummaryStatusResponse],
    summary="触发 AI 摘要生成",
)
async def generate_summary(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    启动后台任务：AI 生成书籍的情节摘要和角色列表。

    摘要生成完成后自动存储到数据库，通过 GET 接口获取。
    """
    # 验证书籍存在且属于当前用户
    result = await db.execute(
        select(Book).where(
            Book.id == book_id,
            Book.user_id == current_user.id,
            Book.deleted_at.is_(None),
        )
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise AppException(status_code=404, detail="书籍不存在或已被删除")

    if book.chapter_count == 0:
        raise AppException(status_code=400, detail="该书暂无章节，请先抓取内容")

    # 如果已有摘要，直接返回
    if book.ai_summary:
        return ApiResponse.ok(data=SummaryStatusResponse(
            status="done",
            ai_summary=book.ai_summary,
            ai_summary_at=book.ai_summary_at.isoformat() if book.ai_summary_at else None,
        ))

    # 检查是否已有正在进行的任务
    progress = ai_service.get_summary_status(book_id)
    if progress and progress["status"] in ("queued", "generating"):
        return ApiResponse.ok(data=SummaryStatusResponse(
            status=progress["status"],
            error=progress.get("error"),
        ))

    # 启动后台生成
    result = await ai_service.start_summary_generation(book_id)
    return ApiResponse.ok(data=SummaryStatusResponse(
        status=result["status"],
        error=result.get("error"),
    ))


@router.get(
    "/summary/{book_id}",
    response_model=ApiResponse[SummaryStatusResponse],
    summary="获取 AI 摘要",
)
async def get_summary(
    book_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    获取该书的 AI 摘要。

    如果摘要已生成则直接返回；如果正在生成中则返回当前进度；
    如果从未生成过则返回 status="none"。
    """
    db_summary = await ai_service.get_summary_from_db(book_id, user_id=current_user.id)
    if db_summary is None:
        raise AppException(status_code=404, detail="书籍不存在")

    progress = ai_service.get_summary_status(book_id)

    return ApiResponse.ok(data=SummaryStatusResponse(
        status=db_summary["status"] if not progress else progress["status"],
        ai_summary=db_summary.get("ai_summary"),
        ai_summary_at=db_summary.get("ai_summary_at"),
        error=progress.get("error") if progress else None,
    ))
