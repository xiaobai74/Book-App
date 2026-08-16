# 日常小说管理App -- 产品需求文档（PRD）

> **版本**：v1.3
> **作者**：资深产品经理
> **日期**：2026-07-21
> **最后更新**：2026-08-07
> **状态**：v1.2 已完成，v1.3 已完成，文档已反映当前实现

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

- **搜得到**：内置搜索引擎，一键查找目标小说；支持书架快速检索（模糊搜索 + AI 语义搜索）和外部源站全网搜索
- **抓得下**：自动爬取正文内容，无需手动复制粘贴
- **通用抓取**：支持任意小说网站 URL，自动适配未配置的源站
- **管得住**：私人书架管理，支持添加、删除、浏览、标记置顶
- **阅得了**：输出标准 `.epub` 和 `.txt` 格式，兼容主流电子书设备；同时支持 App 内直接在线阅读已下载的书籍，自动记录阅读进度
- **可扩展**：支持用户自定义源站抓取规则，提高特定网站的抓取精确度
- **AI 赋能**（v1.3 新增）：AI 语义搜索用自然语言在书架中找书，AI 自动生成小说摘要（含角色列表和风格标签）

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
| SHELF-001 | 查看书架 | 以列表形式展示已有小说，每项显示书名、作者、添加时间、是否有 `.epub` 文件。支持书架内嵌搜索栏模糊搜索（v1.2），支持 AI 语义搜索（v1.3） | P0 |
| SHELF-002 | 添加小说 | 用户手动输入书名和作者，将小说加入书架 | P0 |
| SHELF-003 | 删除小说 | 从书架中删除指定小说（软删除，同时清理本地 `.epub`/`.txt` 文件，释放存储空间），前端提示确认 | P0 |
| SHELF-004 | 书架快速检索 | 在书架页内嵌搜索栏实时搜索已有书籍，支持书名+作者双字段模糊匹配（300ms 防抖，≥2 字符触发），支持普通搜索和 AI 语义搜索模式切换。新增 Ctrl+K 全局命令面板（类 VS Code 快速打开） | P0 |

**验收标准**：
- 书架列表按添加时间倒序排列（v1.2：已标记书籍置顶优先，详见 2.6 节）
- 书架页顶部内嵌搜索栏，支持普通搜索（书名+作者，300ms 防抖）和 AI 语义搜索模式切换（v1.3）
- Ctrl+K 唤起全局命令面板，支持键盘导航、最近阅读快捷入口（v1.2）
- 书架支持筛选标签：全部 / 已标记 / 抓取完成 / 有 EPUB（v1.2）
- 删除操作需弹出二次确认弹窗："确定要删除《xxx》吗？`.epub` 和 `.txt` 文件将同时被删除"
- 删除时后端自动检查并删除对应的 `backend/epub_output/` 和 `backend/txt_output/` 中的本地文件，释放磁盘空间
- 文件删除失败不影响数据库删除（文件不存在时跳过，权限不足时记录日志）
- 空书架时展示占位提示文案："书架空空如也，去搜索一本小说吧～"

### 2.3 在线搜索模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| SEARCH-001 | 小说搜索 | 输入关键词（书名/作者），调用搜索引擎或内容站点检索匹配的小说 | P0 |
| SEARCH-002 | 搜索结果展示 | 以卡片列表展示搜索结果，每项包含书名、作者、最新章节 | P0 |
| SEARCH-003 | 搜索结果上限 | 每个源站最多返回 30 条结果（`search_limit` 参数，默认 30、上限 100），合并去重后一次性展示；书架内搜索（`/api/v1/search`）支持分页 | P1 |

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
- 抓取失败时对单章节重试 3 次，全部失败时该章写入占位文本 `[本章抓取失败: …]`，书籍仍标记为抓取完成（其余章节可用）；仅章节列表整体获取失败时才将书籍标记为"抓取失败"并提示用户
- `.epub` 文件必须符合 EPUB 3.2 规范，可在主流阅读器（Apple Books、Calibre、Kindle）正常打开
- `.txt` 文件 UTF-8 编码，可在任意文本编辑器打开
- 章节顺序与源站一致，无缺章漏章
- 文件名格式：`(book_id)书名-作者.epub` / `(book_id)书名-作者.txt`（book_id 为书籍 UUID 前缀，防止同名书覆盖）
- 通用抓取：任意小说网站 URL 应当至少能成功解析章节列表（成功率取决于目标网站 HTML 结构的规范性）

### 2.5 在线阅读器模块（P0 — v1.2 新增）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| READER-001 | 章节列表 | 在书籍详情页展示完整章节列表，显示章节序号和标题，点击进入阅读 | P0 |
| READER-002 | 阅读器页面 | 专用阅读器页面，展示章节正文内容，上下滚动连续阅读 | P0 |
| READER-003 | 章节导航 | 阅读器底部提供"上一章 / 下一章"按钮，支持键盘左右方向键翻章 | P0 |
| READER-004 | 进度记录 | 自动记录用户每本书的最后阅读章节，下次打开时恢复到上次阅读位置 | P1 |
| READER-005 | 目录跳转 | 阅读器侧边栏或顶部提供目录入口，点击章节标题直接跳转 | P1 |
| READER-006 | 阅读设置 | 支持字体大小调节（小/中/大）、行间距调节、日间/夜间主题切换 | P2 |

**验收标准**：
- 阅读器页面加载章节内容后，页面滚动到顶部
- 章节切换不需要整页刷新，通过前端路由参数或状态切换实现
- 若书籍尚未抓取（无章节内容），在详情页提示"请先抓取内容后再阅读"
- 进度记录通过后端 API 持久化，跨设备/浏览器保持同步
- 字体大小和主题设置存储在本地 localStorage，无需登录即可保持偏好
- 阅读器夜间主题使用深色背景 `#1a2332`，文字使用浅灰 `#cbd5e1`，保持冷色调

### 2.6 标记与置顶模块（P1 — v1.2 新增）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| MARK-001 | 标记书籍 | 在书架列表中，用户可点击星标图标将书籍标记为"喜欢/收藏" | P0 |
| MARK-002 | 取消标记 | 再次点击星标取消标记，恢复普通状态 | P0 |
| MARK-003 | 标记置顶 | 被标记的书籍自动置顶到书架列表最上方，按标记时间倒序排列 | P0 |
| MARK-004 | 标记筛选 | 书架顶部提供筛选标签："全部 / 已标记"，方便快速查看收藏书籍 | P2 |

**验收标准**：
- 书架列表排序规则：已标记书籍优先显示（按标记时间倒序），未标记书籍在后（按添加时间倒序）
- 星标图标使用空心 ☆（未标记）和实心 ★（已标记），颜色使用冷调金色 `#c9a96e`，不刺眼
- 标记/取消标记操作即时响应，无需二次确认
- 标记状态与用户账号绑定，更换设备后保持同步

### 2.7 AI 功能模块（P1 — v1.3 新增）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| AI-001 | AI 语义搜索 | 在书架搜索栏切换到 AI 模式，用自然语言描述想找的书（如"最近看的那本修仙小说"），后端通过 AI 语义匹配返回关联书籍，含匹配原因和置信度 | P0 |
| AI-002 | AI 摘要生成 | 对已完成抓取的书籍，触发 AI 自动生成小说摘要，包括角色列表和风格标签（如"仙侠、爽文、系统流"），在书籍详情页展示 | P1 |

**验收标准**：
- AI 语义搜索输入框在搜索中时禁用，显示进度动画和"AI 正在理解…"提示文字
- AI 语义搜索通常 5-15 秒返回结果，超时或服务不可用时显示友好错误提示
- 搜索结果含 match_reason（匹配原因）和 score（置信度百分比）
- AI 摘要生成后展示在书籍详情页，包含角色列表和风格标签
- AI 摘要生成中显示 loading 状态，失败时显示重试按钮
- 相关 API：`POST /api/v1/ai/search`、`POST /api/v1/ai/summary/{book_id}`、`GET /api/v1/ai/summary/{book_id}`

---

## 3. 非功能需求

### 3.1 视觉设计

| 约束 | 说明 |
|------|------|
| **色彩基调** | 冷色调为主。主色采用冰蓝 `#4a8bb5`（按钮/链接，hover 加深 `#3a7096`），辅色以青灰、冰蓝点缀（`#5ba3cc`）。不出现暖色大面积元素（星标金色 `#c9a96e` 为唯一暖色点缀） |
| **动画** | 界面以极简冷色调为主，不引入装饰性动画。允许的动效仅限：加载指示动画（AI 搜索三点跳动、加载进度条）；其余 transition 全局禁用，悬停反馈（如星标按钮 hover 微缩放、卡片 hover 高亮）以即时状态切换实现 |
| **界面风格** | 极简整洁。卡片式布局，充足留白，信息层次通过字号/字重/间距区分，不用装饰性元素 |
| **字体** | 系统默认无衬线字体（system-ui, -apple-system, sans-serif），字号 14px 正文 / 12px 辅助文字 |

### 3.2 响应式适配

| 约束 | 说明 |
|------|------|
| **Web 端优先** | v1.0 目标平台为桌面浏览器（>= 1280px 宽）。同时采用响应式布局，确保 768px（平板）和 375px（手机）下可正常使用 |
| **移动端预留** | CSS 使用 rem/em 相对单位，布局使用 Flexbox + Grid，为后续 React Native / Flutter 迁移降低适配成本 |
| **断点策略** | `< 920px` 单列布局；`>= 920px` 多列布局（搜索页 3 列卡片；书架/其他页面按容器宽度自适应）。响应式适配覆盖平板（768px）与手机（375px） |

### 3.3 性能

- 首屏加载 <= 2s（Lighthouse Performance >= 90）
- 搜索接口响应 <= 3s
- 单本小说抓取（假设 500 章）耗时 <= 5 分钟

### 3.4 安全

- 所有 API 必须通过 HTTPS 传输
- API 请求携带 JWT Authorization Header
- XSS 防护：后端统一 JSON 序列化输出（不注入 HTML）；前端在渲染用户内容处转义（`escapeHtml`），搜索高亮仅对转义后的文本加 `<mark>` 标签
- 爬虫模块设置频率限制与随机延迟：章节抓取随机间隔 0.2-0.4s、默认并发 5、失败重试指数退避 2-4s（v1.1 调整为平衡抓取速度与封禁风险；连接预检、目录翻页均带随机间隔）

---

## 4. 信息架构与页面结构

```
/          -- 根路径重定向到 /shelf
├── /login              -- 登录页
├── /register           -- 注册页
├── /shelf              -- 书架首页（默认登录后跳转）
│   ├── 顶栏：Logo + 导航菜单 + 用户头像/退出
│   ├── 搜索栏（v1.2 新增）：搜索输入框 + 普通/AI 语义模式切换（v1.3）
│   ├── 筛选栏：全部 / 已标记 / 抓取完成 / 有 EPUB（v1.2 新增）
│   ├── 列表区：小说卡片列表（标记书籍置顶显示，v1.2 新增）
│   └── 添加按钮：手动添加小说
├── /search?q=xxx       -- 搜索结果页
│   ├── 搜索框（可修改关键词重新搜索）
│   ├── 结果卡片列表（分页）
│   ├── 书架内搜索 / 全网搜索标签页切换
│   └── 每张卡片可"加入书架"或去详情页
├── /detail/:id          -- 小说详情页
│   ├── 基本信息：书名、作者、添加时间、星标标记按钮（v1.2 新增）
│   ├── AI 摘要区（v1.3 新增）：角色列表 + 风格标签
│   ├── 操作区：抓取按钮、在线阅读按钮（v1.2 新增）、下载 .epub/.txt 按钮
│   └── 章节列表（抓取后可预览，点击进入阅读器，v1.2 新增）
├── /reader/:id/:chapterIndex  -- 在线阅读器页面（v1.2 新增）
│   ├── 顶部：章节标题 + 目录入口
│   ├── 正文区：章节正文内容
│   └── 底部导航：上一章 / 下一章 + 进度显示
├── /settings           -- 个人设置（修改密码）
└── /crawl-sources      -- 自定义源站管理
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
| **文件存储** | 本地文件系统 / MinIO（可选） | 本地存储 `.epub`/`.txt` 文件，后续可切换对象存储 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP 请求 + HTML 解析，规则驱动架构，支持通用回退 |
| **EPUB 生成** | EbookLib（Python） | 成熟的 `.epub` 生成库，支持元数据、目录、封面 |

---

## 6. 数据库表设计

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
    txt_path: Mapped[str | None] = mapped_column(
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
    is_marked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0",
    )
    marked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
    ai_summary: Mapped[str | None] = mapped_column(       # v1.3 新增
        Text, nullable=True, default=None
    )
    ai_summary_at: Mapped[datetime | None] = mapped_column( # v1.3 新增
        DateTime, nullable=True, default=None
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
    # 关联: 本书的所有章节
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter",
        back_populates="book",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    # 关联: 阅读进度
    reading_progress: Mapped["ReadingProgress | None"] = relationship(
        "ReadingProgress",
        back_populates="book",
        uselist=False,
        lazy="selectin",
    )


# ============================================================
# app/models/chapter.py  -- 章节表
# ============================================================
class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
    )
    index: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    word_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )

    # 关联: 所属书籍
    book: Mapped["Book"] = relationship(
        "Book", back_populates="chapters", lazy="selectin",
    )


# ============================================================
# app/models/reading_progress.py  -- 阅读进度表（v1.2 新增）
# ============================================================
class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 每本书只记录一条进度
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_chapter_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        onupdate=_now_utc,
        nullable=False,
    )

    # 关联: 所属书籍
    book: Mapped["Book"] = relationship(
        "Book", back_populates="reading_progress", lazy="selectin",
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

### 自定义抓取源站表 `crawl_sources`

> 对应实现 `backend/app/models/crawl_source.py`（v1.1 自定义源站功能新增）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `INT` 自增主键 | 源站 ID |
| `user_id` | `VARCHAR(36)` FK→users.id | 所属用户 |
| `name` | `VARCHAR(200)` | 源站名称 |
| `url` | `VARCHAR(2048)` | 源站域名/首页 URL |
| `rule_json` | `TEXT` | JSON 格式的抓取规则（toc/chapter 选择器） |
| `is_public` | `TINYINT(1)` 默认 0 | 是否公开给所有用户 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

`User` 模型含 `crawl_sources` 关联（`lazy="selectin"`）。

---

## 7. API 接口设计

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
    BookCreateRequest,
    BookResponse,
    ChapterDetailResponse,
    ChapterResponse,
    CrawlStatusResponse,
    ReadingProgressResponse,
    ReadingProgressUpdateRequest,
)
from app.services.book_service import (
    BookService,
    book_to_response,
    chapter_to_response,
    chapter_to_detail_response,
    progress_to_response,
)
from app.utils.deps import get_current_user

router = APIRouter(tags=["书架 / 搜索 / 抓取"])


@router.get(
    "/books",
    response_model=ApiResponse[list[BookResponse]],
    summary="获取书架列表",
)
async def list_books(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=500, description="每页数量（v1.2 客户端缓存时传 200）"),
    marked: bool | None = Query(default=None, description="筛选：仅已标记/全部（v1.2 新增）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/books -- 获取书架列表，已标记书籍置顶，支持按标记筛选"""
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
    """DELETE /api/v1/books/{book_id} -- 软删除小说，同时清理本地 .epub/.txt 文件"""
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
    page_size: int = Query(default=20, ge=1, le=500, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/search?q=&page= -- 在书架中按书名+作者模糊搜索（v1.2 已扩展为双字段）"""
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
    summary="下载 .epub/.txt 电子书文件",
)
async def download_book(
    book_id: str,
    format: str = Query(default="epub", pattern="^(epub|txt)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/books/{book_id}/download?format=epub|txt -- 下载电子书文件（v1.2 已实现）"""
    book = await BookService.get_book_detail(
        db, current_user, book_id
    )
    if format == "txt":
        if not book.txt_path:
            raise AppException(
                status_code=404,
                detail="该书籍尚未生成 TXT 文件，请先抓取",
            )
    else:
        if not book.epub_path:
            raise AppException(
                status_code=404,
                detail="该书籍尚未生成 EPUB 文件，请先抓取",
            )
    # 实际返回 FileResponse（见 books.py 实际实现）


# ── v1.2 新增：标记与置顶 ──────────────────────────────────

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
    """PUT /api/v1/books/{book_id}/mark -- 切换标记状态，被标记的书籍自动置顶"""
    book = await BookService.toggle_mark(db, current_user, book_id)
    return ApiResponse.ok(data=book_to_response(book))


# ── v1.2 新增：在线阅读器 ──────────────────────────────────

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
    """GET /api/v1/books/{book_id}/chapters -- 获取书籍的所有章节（按 index 升序）"""
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
    """GET /api/v1/books/{book_id}/chapters/{chapter_index} -- 获取单章正文内容"""
    chapter = await BookService.get_chapter_content(
        db, current_user, book_id, chapter_index
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
    """GET /api/v1/books/{book_id}/progress -- 获取用户在该书的阅读进度"""
    progress = await BookService.get_reading_progress(db, current_user, book_id)
    return ApiResponse.ok(data=progress_to_response(progress))


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
    """PUT /api/v1/books/{book_id}/progress -- 更新用户在该书的阅读进度"""
    progress = await BookService.update_reading_progress(
        db, current_user, book_id, data.chapter_index
    )
    return ApiResponse.ok(data=progress_to_response(progress))
```

### 7.2a 搜索与抓取扩展端点（v1.1 新增，位于 `books.py`）

以下端点已在代码中实现，属于书架路由的扩展（详见 `api/API文档.md` 各接口章节）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/search/external` | GET | 外部源站全网搜索（并发搜索所有已配置源站，合并去重） |
| `/api/v1/sources` | GET | 获取可用源站列表 |
| `/api/v1/crawl/check-url` | POST | 检查源站 URL 连通性（含 SSRF 防护：拒绝内网/环回地址） |
| `/api/v1/crawl-sources` | GET / POST | 列出自定义源站 / 创建自定义源站 |
| `/api/v1/crawl-sources/{source_id}` | GET / PUT / DELETE | 获取 / 更新 / 删除单个自定义源站 |
| `/api/v1/crawl-sources/test` | POST | 测试自定义源站抓取规则 |
| `/health` | GET | 健康检查（返回 `{"status": "ok", "version": "1.3.0"}`） |

> 注：自定义源站 CRUD 对应的数据表为 `crawl_sources`（见第 6 章末）；URL 连通性预检在触发抓取前由前端调用，用于提前发现 URL 不可达问题。

### 7.3 AI 功能路由 `app/api/v1/ai.py`（v1.3 新增）

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.ai_service import AiService
from app.utils.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["AI 功能"])


class AiSearchRequest(BaseModel):
    query: str


class AiSearchResultItem(BaseModel):
    book_id: str
    title: str
    author: str
    match_reason: str
    score: int


class SummaryStatusResponse(BaseModel):
    status: str            # "queued" | "generating" | "done" | "failed" | "none"
    ai_summary: str | None
    ai_summary_at: str | None
    error: str | None


@router.post(
    "/search",
    response_model=ApiResponse[list[AiSearchResultItem]],
    summary="AI 语义搜索",
)
async def ai_search(
    body: AiSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """POST /api/v1/ai/search -- 用自然语言在书架中语义搜索小说"""
    results = await ai_service.semantic_search(current_user, body.query)
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
    """POST /api/v1/ai/summary/{book_id} -- 触发 AI 自动生成小说摘要（角色列表+风格标签）"""
    result = await ai_service.start_summary_generation(book_id)
    return ApiResponse.ok(data=SummaryStatusResponse(status=result["status"], error=result.get("error")))


@router.get(
    "/summary/{book_id}",
    response_model=ApiResponse[SummaryStatusResponse],
    summary="获取 AI 摘要",
)
async def get_summary(
    book_id: str,
    current_user: User = Depends(get_current_user),
):
    """GET /api/v1/ai/summary/{book_id} -- 获取已生成的 AI 摘要"""
    db_summary = await ai_service.get_summary_from_db(book_id, user_id=current_user.id)
    return ApiResponse.ok(data=SummaryStatusResponse(**db_summary))
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
| **v1.0** | Web 端：注册/登录、书架增删查、在线搜索、抓取 + `.epub` 生成与下载 | ✅ 已完成 |
| **v1.1** | 书架搜索、抓取进度优化、多源站搜索、通用抓取、自定义源站、TXT 输出 | ✅ 已完成 |
| **v1.2** | App 内在线阅读器（章节列表、正文阅读、章节导航、进度记录、阅读设置）、标记与置顶（星标标记、取消标记、标记置顶排序）、书架快速检索（书架内嵌搜索栏 + Ctrl+K 命令面板）、删除功能增强（本地文件清理） | ✅ 已完成 |
| **v1.3** | AI 语义搜索（书架内自然语言搜索，Dify 工作流 + LLM 语义匹配）、AI 摘要生成（自动生成小说摘要、角色列表、风格标签）、书架搜索栏 AI 模式切换 | ✅ 已完成 |
| **v2.0** | 移动端适配（UniApp / 独立移动框架），离线阅读器内嵌 | 🔮 规划中 |
| **v2.1+** | 拼音搜索（pinyin-pro）、搜索历史与自动补全、全文搜索升级（MySQL FULLTEXT / Meilisearch）、语音搜索（Web Speech API） | 🔮 规划中 |

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
| 主色调（按钮/链接） | `#4a8bb5` | 冷调冰蓝（Element Plus primary 映射 `--accent`） |
| 强调（hover/active） | `#3a7096` | 冰蓝加深（`--accent-hover`） |
| 边框/分割线 | `#e2e8f0` | 浅灰蓝 |
| 成功状态 | `#475569` | 中性灰蓝（不用绿色） |
| 错误状态 | `#94a3b8` | 浅灰蓝（不用红色，保持冷调统一） |
| 次强调文字 | `#334155` | 深蓝灰（`--fg-soft`，辅助文字用） |

---

> **ACK**：您好！当前任务已完成！
>
> **v1.2 更新**：新增 App 内在线阅读器、章节列表与内容 API、阅读进度记录与恢复、星标标记与置顶功能、书架标记筛选、书架内嵌搜索栏（书名+作者双字段）+ Ctrl+K 命令面板。
>
> **v1.3 更新**：新增 AI 语义搜索（书架内自然语言搜索，Dify 工作流驱动）、AI 摘要生成（角色列表 + 风格标签）、书架搜索栏 AI 模式切换。
