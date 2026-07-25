"""书籍相关 Pydantic Schemas"""

from datetime import datetime

from pydantic import BaseModel, Field


class BookCreateRequest(BaseModel):
    """添加书籍请求"""
    title: str = Field(..., min_length=1, max_length=500, description="书名")
    author: str = Field(default="未知", max_length=255, description="作者")
    source_url: str | None = Field(default=None, max_length=2048, description="源网站 URL")


class BookResponse(BaseModel):
    """书籍响应"""
    id: str
    title: str
    author: str
    source_url: str | None = None
    status: str = "idle"
    chapter_count: int = 0
    has_epub: bool = False
    added_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 的 ORM 模式


class BookListResponse(BaseModel):
    """书架列表响应"""
    items: list[BookResponse]
    total: int
    page: int
    page_size: int


class CrawlStatusResponse(BaseModel):
    """抓取状态响应"""
    status: str
    chapter_count: int
    total_chapters: int | None = None  # 后续爬虫实现时填充
    percentage: float = 0.0
