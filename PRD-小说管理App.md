# 日常小说管理App -- 产品需求文档（PRD）

> **版本**：v1.1
> **作者**：资深产品经理
> **日期**：2026-07-21
> **最后更新**：2026-07-26
> **状态**：草案

---

## 1. 产品概述

### 1.1 产品定位

一款面向日常小说阅读爱好者的 **Web 端小说管理工具**，帮助用户一站式完成小说搜索、抓取、格式化为 `.epub` 电子书并集中管理个人书架。

### 1.2 目标用户

| 用户画像 | 典型场景 |
|---------|---------|
| 在线阅读读者 | 在多平台追更，想统一管理已读/在读小说 |
| 离线阅读爱好者 | 想把网络小说下载为 `.epub`，方便在电子书设备上阅读 |
| 轻度整理癖用户 | 希望有一个清爽的私人书架，随时增删书名 |

### 1.3 核心价值

- **搜得到**：内置搜索引擎，一键查找目标小说
- **抓得下**：自动爬取正文内容，无需手动复制粘贴
- **通用抓取**：支持任意小说网站 URL，自动适配未配置的源站
- **管得住**：私人书架管理，支持添加、删除、浏览
- **阅得了**：输出标准 `.epub` 和 `.txt` 格式，兼容主流电子书设备
- **可扩展**：支持用户自定义源站抓取规则，提高特定网站的抓取精确度

---

## 2. 功能需求

### 2.1 用户认证模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| AUTH-001 | 注册 | 用户通过邮箱 + 密码注册账号。密码长度 8-64 位，需包含字母和数字 | P0 |
| AUTH-002 | 登录 | 已注册用户通过邮箱 + 密码登录，登录后获取 JWT Token | P0 |
| AUTH-003 | 退出登录 | 清除本地 Token，返回登录页 | P0 |
| AUTH-004 | 密码修改 | 登录后可在个人设置中修改密码 | P1 |

**验收标准**：
- 注册时邮箱去重，重复邮箱提示"该邮箱已注册"
- 密码前端做格式校验，后端做哈希存储（bcrypt, saltRounds=12）
- 登录失败提示"邮箱或密码错误"，不区分具体原因（防枚举）
- Token 有效期：Access Token 2小时，Refresh Token 7天

### 2.2 书架管理模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| SHELF-001 | 查看书架 | 以列表形式展示已有小说，每项显示书名、作者、添加时间、是否有 `.epub` 文件 | P0 |
| SHELF-002 | 添加小说 | 用户手动输入书名和作者，将小说加入书架 | P0 |
| SHELF-003 | 删除小说 | 从书架中删除指定小说（软删除，前端提示确认） | P0 |
| SHELF-004 | 书架搜索 | 在已有书架中按书名模糊搜索 | P2 |

**验收标准**：
- 书架列表按添加时间倒序排列
- 删除操作需弹出二次确认弹窗："确定要删除《xxx》吗？"
- 空书架时展示占位提示文案："书架空空如也，去搜索一本小说吧～"

### 2.3 在线搜索模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| SEARCH-001 | 小说搜索 | 输入关键词（书名/作者），调用搜索引擎或内容站点检索匹配的小说 | P0 |
| SEARCH-002 | 搜索结果展示 | 以卡片列表展示搜索结果，每项包含书名、作者、简介（截断50字）、最新章节 | P0 |
| SEARCH-003 | 搜索结果分页 | 搜索结果分页展示，每页 20 条 | P1 |

**验收标准**：
- 输入关键词后点击搜索或按 Enter 触发搜索
- 搜索中展示 loading 状态
- 无结果时展示"未找到相关小说，请尝试其他关键词"
- 搜索失败时展示"搜索失败，请稍后重试"

### 2.4 内容抓取与 `.epub` 生成模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| EPUB-001 | 抓取小说内容 | 从搜索结果中选择一本小说，自动抓取所有章节的正文内容 | P0 |
| EPUB-002 | 抓取进度展示 | 展示实时抓取进度（当前章/总章数、百分比） | P1 |
| EPUB-003 | 生成 .epub | 将抓取到的内容整理为标准 `.epub` 格式电子书，包含元数据（书名、作者、封面占位图）和目录 | P0 |
| EPUB-004 | 下载 .epub | 提供下载按钮，用户可将 `.epub` 文件保存到本地 | P0 |
| EPUB-005 | 重新抓取 | 对已有小说支持重新抓取/更新内容 | P2 |
| EPUB-006 | 通用抓取 | 未配置的网站自动使用通用解析策略，无需手动添加规则 | P0 |
| EPUB-007 | 自定义源站 | 用户可添加自定义 CSS 选择器规则，提高特定网站抓取精确度 | P1 |

**验收标准**：
- 抓取失败时对单章节重试 3 次，全部失败则标记"抓取失败"并提示用户
- `.epub` 文件必须符合 EPUB 3.2 规范，可在主流阅读器（Apple Books、Calibre、Kindle）正常打开
- `.txt` 文件 UTF-8 编码，可在任意文本编辑器打开
- 章节顺序与源站一致，无缺章漏章
- 文件名格式：`《书名》-作者.epub` / `《书名》-作者.txt`
- 通用抓取：任意小说网站 URL 应当至少能成功解析章节列表（成功率取决于目标网站 HTML 结构的规范性）

---

## 3. 非功能需求

### 3.1 视觉设计

| 约束 | 说明 |
|------|------|
| **色彩基调** | 冷色调为主。主色建议使用深蓝 `#1a2332` 或石板灰 `#2c3e50`，辅色以青灰、冰蓝点缀。不出现暖色大面积元素 |
| **动画** | 禁止所有过渡动画、CSS transition、animation、hover 动效。交互反馈使用即时状态切换（如按钮 disabled 态、loading 文字） |
| **界面风格** | 极简整洁。卡片式布局，充足留白，信息层次通过字号/字重/间距区分，不用装饰性元素 |
| **字体** | 系统默认无衬线字体（system-ui, -apple-system, sans-serif），字号 14px 正文 / 12px 辅助文字 |

### 3.2 响应式适配

| 约束 | 说明 |
|------|------|
| **Web 端优先** | v1.0 目标平台为桌面浏览器（>= 1280px 宽）。同时采用响应式布局，确保 768px（平板）和 375px（手机）下可正常使用 |
| **移动端预留** | CSS 使用 rem/em 相对单位，布局使用 Flexbox + Grid，为后续 React Native / Flutter 迁移降低适配成本 |
| **断点策略** | `< 768px` 单列布局；`768-1024px` 双列布局；`> 1024px` 多列布局（搜索页最多 4 列卡片） |

### 3.3 性能

- 首屏加载 <= 2s（Lighthouse Performance >= 90）
- 搜索接口响应 <= 3s
- 单本小说抓取（假设 500 章）耗时 <= 5 分钟

### 3.4 安全

- 所有 API 必须通过 HTTPS 传输
- API 请求携带 JWT Authorization Header
- 用户输入统一在后端做 XSS 清洗
- 爬虫模块设置合理频率限制（单源站请求间隔 >= 2s），避免被封 IP

---

## 4. 信息架构与页面结构

```
/          -- 根路径重定向到 /shelf
├── /login              -- 登录页
├── /register           -- 注册页
├── /shelf              -- 书架首页（默认登录后跳转）
│   ├── 顶栏：Logo + 搜索框 + 用户头像/退出
│   ├── 列表区：小说卡片列表
│   └── 添加按钮：手动添加小说
├── /search?q=xxx       -- 搜索结果页
│   ├── 搜索框（可修改关键词重新搜索）
│   ├── 结果卡片列表（分页）
│   └── 每张卡片可"加入书架"或"抓取"
├── /book/:id           -- 小说详情页
│   ├── 基本信息：书名、作者、添加时间
│   ├── 操作区：抓取按钮、下载 .epub 按钮
│   └── 章节列表（抓取后可预览）
└── /settings           -- 个人设置（修改密码）
```

---

## 5. 技术栈建议

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue 3 + TypeScript + Vite | 组件化开发效率高，TypeScript 类型安全，Vite 构建快。配合 Element Plus 实现企业级后台管理 |
| **样式** | Element Plus + 自定义 CSS Tokens | Element Plus 提供成熟组件库；自定义冷色调 CSS 变量主题，零动画极简风格 |
| **后端** | Python FastAPI | 爬虫与文件处理是 Python 强项（BeautifulSoup / httpx / ebooklib），FastAPI 异步性能好 |
| **数据库** | MySQL | 用户数据、书架数据、自定义源站规则需 ACID 保证 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于后续移动端对接 |
| **状态管理** | Pinia | Vue 3 官方推荐状态管理库，模块化、类型安全 |
| **组件库** | Element Plus | Vue 3 生态最成熟的企业级 UI 组件库 |
| **文件存储** | 本地文件系统 / MinIO（可选） | v1.0 本地存储 `.epub`/`.txt` 文件，后续可切换对象存储 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP 请求 + HTML 解析，规则驱动架构，支持通用回退 |
| **EPUB 生成** | EbookLib（Python） | 成熟的 `.epub` 生成库，支持元数据、目录、封面 |

---

## 6. 数据库表设计（草案）

```python
# ============================================================
# app/models/user.py  -- 用户表
# ============================================================
import uuid
from datetime import UTC, datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def _now_utc() -> datetime:
    """返回当前 UTC 时间"""
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        onupdate=_now_utc,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )

    # 关联: 用户拥有的所有书籍(只含未删除的)
    books: Mapped[list["Book"]] = relationship(
        "Book",
        back_populates="user",
        lazy="selectin",
        primaryjoin="and_(User.id == Book.user_id, "
                    "Book.deleted_at.is_(None))",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        lazy="selectin",
    )


# ============================================================
# app/models/book.py  -- 书架表
# ============================================================
class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    author: Mapped[str] = mapped_column(
        String(255), nullable=False,
        default="未知", server_default="未知",
    )
    source_url: Mapped[str | None] = mapped_column(nullable=True)
    epub_path: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False,
        default="idle", server_default="idle",
        # idle | crawling | done | failed
    )
    chapter_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        onupdate=_now_utc,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )

    # 关联: 所属用户
    user: Mapped["User"] = relationship(
        "User", back_populates="books", lazy="selectin",
    )


# ============================================================
# app/models/refresh_token.py  -- 刷新令牌表
# ============================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )

    # 关联: 所属用户
    user: Mapped["User"] = relationship(
        "User", back_populates="refresh_tokens", lazy="selectin",
    )
```

---

## 7. API 接口设计（草案）

### 7.1 认证路由 `app/api/v1/auth.py`

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService
from app.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """POST /api/v1/auth/register -- 注册"""
    user = await AuthService.register(db, data)
    return ApiResponse.ok(data={"id": user.id, "email": user.email})


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """POST /api/v1/auth/login -- 登录"""
    tokens = await AuthService.login(db, data)
    return ApiResponse.ok(data=tokens)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="刷新 Token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """POST /api/v1/auth/refresh -- 刷新 Token（轮转策略）"""
    tokens = await AuthService.refresh(db, data)
    return ApiResponse.ok(data=tokens)


@router.put(
    "/password",
    response_model=ApiResponse[None],
    summary="修改密码",
)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PUT /api/v1/auth/password -- 修改密码（需要登录）"""
    await AuthService.change_password(db, current_user, data)
    return ApiResponse.ok(data=None)
```

### 7.2 书架路由 `app/api/v1/books.py`

```python
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.error_handler import AppException
from app.models.user import User
from app.schemas.book import (
    BookCreateRequest, BookResponse, CrawlStatusResponse,
)
from app.schemas.common import ApiResponse, PaginationMeta
from app.services.book_service import BookService, book_to_response
from app.utils.deps import get_current_user

router = APIRouter(tags=["书架 / 搜索 / 抓取"])


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
    """GET /api/v1/books -- 获取书架列表，按添加时间倒序"""
    books, total = await BookService.get_books(
        db, current_user, page, page_size
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
    """POST /api/v1/books -- 手动添加小说到书架"""
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
    """GET /api/v1/books/{book_id} -- 小说详情"""
    book = await BookService.get_book_detail(
        db, current_user, book_id
    )
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
    """DELETE /api/v1/books/{book_id} -- 软删除小说"""
    await BookService.delete_book(db, current_user, book_id)
    return ApiResponse.ok(data=None)


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
    """GET /api/v1/search?q=&page= -- 在书架中按书名模糊搜索"""
    books, total = await BookService.search_books(
        db, current_user, q, page, page_size
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
    "/books/{book_id}/crawl",
    response_model=ApiResponse[BookResponse],
    summary="触发抓取",
)
async def crawl_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """POST /api/v1/books/{book_id}/crawl -- 触发内容抓取"""
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
    """GET /api/v1/books/{book_id}/crawl-status -- 查询抓取进度"""
    status = await BookService.get_crawl_status(
        db, current_user, book_id
    )
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
    """GET /api/v1/books/{book_id}/download -- 下载 .epub 文件（占位）"""
    book = await BookService.get_book_detail(
        db, current_user, book_id
    )
    if not book.epub_path:
        raise AppException(
            status_code=404,
            detail="该书籍尚未生成 .epub 文件，请先抓取",
        )
    raise AppException(status_code=501, detail="下载功能开发中")
```

所有接口返回统一格式：
```python
# app/schemas/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    success: bool = True
    data: T | None = None
    meta: PaginationMeta | None = None
    error: str | None = None

    @classmethod
    def ok(
        cls,
        data: T = None,
        meta: PaginationMeta | None = None,
    ) -> "ApiResponse[T]":
        """成功响应"""
        return cls(success=True, data=data, meta=meta, error=None)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse":
        """失败响应"""
        return cls(success=False, data=None, meta=None, error=error)
```

---

## 8. 版本规划

| 版本 | 内容 | 时间 |
|------|------|------|
| **v1.0** | Web 端：注册/登录、书架增删查、在线搜索、抓取 + `.epub` 生成与下载 | -- |
| **v1.1** | 书架搜索、批量删除、抓取进度优化、支持多源站搜索 | -- |
| **v2.0** | 移动端适配（UniApp / 独立移动框架），离线阅读器内嵌 | -- |

---

## 9. 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 目标网站反爬机制升级 | 抓取功能失效 | 多源站冗余；支持用户手动粘贴内容作为降级方案 |
| 版权合规风险 | 法律风险 | 产品仅作个人学习用途，不提供公开分享/分发功能；`.epub` 文件归属用户私有数据 |
| 大本小说抓取耗时过长 | 用户体验差 | 后端异步任务队列处理（Celery / ARQ），前端轮询进度，不阻塞操作 |
| 服务器存储压力 | 成本上升 | v1.0 单文件存储；后续接入对象存储 + 自动过期清理（超过 90 天未访问的文件自动归档） |

---

## 10. 附录：冷色调色板参考

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景（主） | `#f4f6f8` | 浅灰蓝背景 |
| 卡片背景 | `#ffffff` | 纯白卡片 |
| 主文字 | `#1e293b` | 深石板灰 |
| 辅助文字 | `#64748b` | 中灰蓝 |
| 主色调（按钮/链接） | `#334155` | 深蓝灰 |
| 强调（hover/active） | `#1e293b` | 更深的石板灰 |
| 边框/分割线 | `#e2e8f0` | 浅灰蓝 |
| 成功状态 | `#475569` | 中性灰蓝（不用绿色） |
| 错误状态 | `#94a3b8` | 浅灰蓝（不用红色，保持冷调统一） |

---

> **ACK**：您好！当前任务已完成！
>
> **v1.1 更新**：新增通用抓取支持、自定义源站规则管理、TXT 格式输出、外部源站搜索接口。
