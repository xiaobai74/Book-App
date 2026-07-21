# 日常小说管理App — 产品需求文档（PRD）

> **版本**：v1.0  
> **作者**：资深产品经理  
> **日期**：2026-07-21  
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
- **管得住**：私人书架管理，支持添加、删除、浏览
- **阅得了**：输出标准 `.epub` 格式，兼容主流电子书设备

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

**验收标准**：
- 抓取失败时对单章节重试 3 次，全部失败则标记"抓取失败"并提示用户
- `.epub` 文件必须符合 EPUB 3.2 规范，可在主流阅读器（Apple Books、Calibre、Kindle）正常打开
- 章节顺序与源站一致，无缺章漏章
- 文件名格式：`《书名》-作者.epub`

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
| **Web 端优先** | v1.0 目标平台为桌面浏览器（≥ 1280px 宽）。同时采用响应式布局，确保 768px（平板）和 375px（手机）下可正常使用 |
| **移动端预留** | CSS 使用 rem/em 相对单位，布局使用 Flexbox + Grid，为后续 React Native / Flutter 迁移降低适配成本 |
| **断点策略** | `< 768px` 单列布局；`768-1024px` 双列布局；`> 1024px` 多列布局（搜索页最多 4 列卡片） |

### 3.3 性能

- 首屏加载 ≤ 2s（Lighthouse Performance ≥ 90）
- 搜索接口响应 ≤ 3s
- 单本小说抓取（假设 500 章）耗时 ≤ 5 分钟

### 3.4 安全

- 所有 API 必须通过 HTTPS 传输
- API 请求携带 JWT Authorization Header
- 用户输入统一在后端做 XSS 清洗
- 爬虫模块设置合理频率限制（单源站请求间隔 ≥ 2s），避免被封 IP

---

## 4. 信息架构与页面结构

```
├── /login              → 登录页
├── /register           → 注册页
├── /shelf              → 书架首页（默认登录后跳转）
│   ├── 顶栏：Logo + 搜索框 + 用户头像/退出
│   ├── 列表区：小说卡片列表
│   └── 添加按钮：手动添加小说
├── /search?q=xxx       → 搜索结果页
│   ├── 搜索框（可修改关键词重新搜索）
│   ├── 结果卡片列表（分页）
│   └── 每张卡片可"加入书架"或"抓取"
├── /book/:id           → 小说详情页
│   ├── 基本信息：书名、作者、添加时间
│   ├── 操作区：抓取按钮、下载 .epub 按钮
│   └── 章节列表（抓取后可预览）
└── /settings           → 个人设置（修改密码）
```

---

## 5. 技术栈建议

| 层级 | 技术选项 | 选型理由 |
|------|---------|---------|
| **前端** | React 18 + TypeScript + Vite | 组件化开发效率高，TypeScript 类型安全，Vite 构建快。为后续 React Native 迁移保留技能栈一致性 |
| **样式** | Tailwind CSS + CSS Modules | Tailwind 快速搭建整洁界面，无动画默认行为符合要求；自定义冷色调主题配置 |
| **后端** | Python FastAPI | 爬虫与文件处理是 Python 强项（BeautifulSoup / httpx / ebooklib），FastAPI 异步性能好 |
| **数据库** | PostgreSQL | 用户数据、书架数据需要 ACID 保证；JSONB 字段可灵活存储小说元数据 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于后续移动端对接 |
| **文件存储** | 本地文件系统 / MinIO（可选） | v1.0 本地存储 `.epub` 文件，后续可切换对象存储 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP 请求 + HTML 解析，标准组合 |
| **EPUB 生成** | EbookLib（Python） | 成熟的 `.epub` 生成库，支持元数据、目录、封面 |

---

## 6. 数据库表设计（草案）

```sql
-- 用户表
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

-- 小说书架表
CREATE TABLE books (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    author      TEXT NOT NULL DEFAULT '未知',
    source_url  TEXT,                              -- 源网站 URL
    epub_path   TEXT,                              -- 生成的 .epub 文件路径
    status      TEXT NOT NULL DEFAULT 'idle'       -- idle | crawling | done | failed
        CHECK (status IN ('idle', 'crawling', 'done', 'failed')),
    chapter_count INTEGER DEFAULT 0,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX idx_books_user_id ON books(user_id) WHERE deleted_at IS NULL;
```

---

## 7. API 接口设计（草案）

```
POST   /api/v1/auth/register      → 注册
POST   /api/v1/auth/login          → 登录
POST   /api/v1/auth/refresh        → 刷新 Token
PUT    /api/v1/auth/password       → 修改密码

GET    /api/v1/books               → 获取书架列表
POST   /api/v1/books               → 添加小说
DELETE /api/v1/books/:id           → 删除小说
GET    /api/v1/books/:id           → 小说详情

GET    /api/v1/search?q=&page=1    → 在线搜索小说

POST   /api/v1/books/:id/crawl     → 触发抓取
GET    /api/v1/books/:id/crawl-status → 查询抓取进度
GET    /api/v1/books/:id/download  → 下载 .epub 文件
```

所有接口返回统一格式：
```json
{
    "success": true,
    "data": {},
    "meta": { "page": 1, "total": 100 },
    "error": null
}
```

---

## 8. 版本规划

| 版本 | 内容 | 时间 |
|------|------|------|
| **v1.0** | Web 端：注册/登录、书架增删查、在线搜索、抓取 + `.epub` 生成与下载 | — |
| **v1.1** | 书架搜索、批量删除、抓取进度优化、支持多源站搜索 | — |
| **v2.0** | 移动端（React Native / Flutter），离线阅读器内嵌 | — |

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
