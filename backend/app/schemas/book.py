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
    has_txt: bool = False
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
    total_chapters: int | None = None
    percentage: float = 0.0
    error: str | None = None  # v3: 失败时提供具体错误信息


class SourceItem(BaseModel):
    """源站摘要信息"""
    id: int
    name: str
    url: str
    has_search: bool = False
    comment: str = ""


class SearchResultItem(BaseModel):
    """外部搜索结果项"""
    title: str
    author: str = "未知"
    source_url: str = ""
    source_name: str = ""
    source_id: int = 0
    category: str = ""
    word_count: str = ""
    status: str = ""
    latest_chapter: str = ""
    last_update_time: str = ""


# ═══════════════════════════════════════════════════════════
# 自定义抓取源站
# ═══════════════════════════════════════════════════════════

class CrawlSourceCreate(BaseModel):
    """创建自定义源站请求"""
    name: str = Field(..., min_length=1, max_length=200, description="源站名称")
    url: str = Field(..., min_length=1, max_length=2048, description="源站域名/首页 URL")
    rule_json: str = Field(..., min_length=2, description="JSON 格式的抓取规则")


class CrawlSourceUpdate(BaseModel):
    """更新自定义源站请求"""
    name: str | None = Field(default=None, min_length=1, max_length=200, description="源站名称")
    url: str | None = Field(default=None, min_length=1, max_length=2048, description="源站域名/首页 URL")
    rule_json: str | None = Field(default=None, min_length=2, description="JSON 格式的抓取规则")
    is_public: bool | None = Field(default=None, description="是否公开")


class CrawlSourceResponse(BaseModel):
    """自定义源站响应"""
    id: int
    name: str
    url: str
    rule_json: str
    is_public: bool = False
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CrawlSourceTestRequest(BaseModel):
    """测试自定义源站规则请求"""
    url: str = Field(..., min_length=1, max_length=2048, description="要测试的小说目录页 URL")
    rule_json: str = Field(..., min_length=2, description="JSON 格式的抓取规则")


class CrawlSourceTestResponse(BaseModel):
    """测试自定义源站规则结果"""
    success: bool
    chapter_count: int = 0
    sample_chapters: list[dict] = []  # [{"title": "...", "url": "..."}]
    error: str | None = None
