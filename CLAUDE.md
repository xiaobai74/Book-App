# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概览

一个日常小说管理 App（Web 端），帮助用户搜索、抓取网络小说，生成 `.epub`/`.txt` 电子书，支持 App 内在线阅读，集中管理个人书架。

- **产品需求文档**：`PRD-小说管理App.md`
- **远程仓库**：`https://github.com/xiaobai74/Book-App.git`
- **当前分支**：`master`，已关联远程 `origin/master`

## 常用命令

```bash
# 虚拟环境（如使用）
source .venv/Scripts/activate  # Windows Git Bash

# 前端开发
cd frontend && npm run dev      # 启动 Vite 开发服务器（localhost:5173）
cd frontend && npm run build    # 生产构建（类型检查 + 打包）
cd frontend && npx vue-tsc --noEmit  # 仅做 TypeScript 类型检查

# 后端开发
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Git 推送
git push origin master

# 注意：远程仓库使用 HTTPS，若推送时卡住，可尝试：
GIT_TERMINAL_PROMPT=0 git push origin master
```

## 架构与技术栈

### 技术栈（详见 PRD 第 5 章）

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue 3 + TypeScript + Vite | 组件化开发，Element Plus 企业级 UI |
| **状态管理** | Pinia | Vue 3 官方推荐，模块化、类型安全 |
| **路由** | Vue Router 4 | SPA 路由，全局导航守卫 |
| **样式** | Element Plus + 自定义 CSS | 冷暖双基调设计系统（v1.4）：冷色为骨架（深蓝/石板灰），暖色为点缀（星标/阅读器纸感/AI 标签），零动画，极简界面，WCAG 2.2 AA |
| **后端** | Python FastAPI | 异步高性能，爬虫与文件处理是 Python 强项 |
| **数据库** | MySQL | 用户与书架数据 ACID 保证 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于移动端对接 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP + HTML 解析 |
| **EPUB** | EbookLib | 标准 `.epub` 3.2 格式生成 |

### 当前文件结构

- **`PRD-小说管理App.md`** — 产品需求文档（v1.6），含功能需求、信息架构、API 设计、数据库表设计、色板参考
- **`frontend/`** — Vue 3 前端工程（组件、路由、状态管理、API 封装）
- **`backend/`** — Python FastAPI 后端（路由、模型、服务、中间件）
  - `backend/app/models/` — ORM 模型：User、Book、Chapter、RefreshToken、CrawlSource、ReadingProgress（v1.2 新增）
  - `backend/app/services/` — 服务层：crawler_service（规则驱动爬虫引擎 + 卷重置感知章节排序）、search_service（外部源站搜索）、crawl_manager（后台抓取流水线）、epub_service、txt_service、book_service（含标记/阅读进度逻辑 + 双字段搜索，v1.2 扩展）、ai_service（AI 语义搜索/摘要，v1.3 新增）、crawl_source_service（自定义源站 CRUD）
  - `backend/app/api/v1/ai.py` — AI 功能路由（v1.3 新增）：语义搜索、摘要生成
  - `backend/rules/` — 规则引擎 + main.json（11 个内置源站规则）+ custom_sources.json（用户自定义规则）
  - `backend/rules/rule_engine.py` — 规则加载、域名匹配、通用回退规则生成、自定义规则持久化
  - `backend/epub_output/` — 生成的 EPUB 文件
  - `backend/txt_output/` — 生成的 TXT 文件
  - `backend/dify-workflows/` — Dify AI 工作流定义（v1.3 新增）：语义搜索、摘要生成
  - `backend/migrations/` — 数据库迁移脚本（v1.2 标记+进度 + v1.3 AI 摘要字段）
- **`docs/`** — 文档目录
  - `docs/书架快速检索工作流-知识库.md` — 书架快速检索功能知识库（SHELF-001）
  - `docs/dify-knowledge/` — Dify 知识库拆分文档（01-08 共 8 个章节）
- **`test/`** — 测试目录
  - `test/test plan/` — 前后端测试计划
  - `test/test report/` — 测试报告
- **`api/API文档.md`** — API 接口完整文档（已更新至 v1.3，含标记/章节/进度/AI 接口）
- **`pyproject.toml`** — 项目元数据（Python ≥ 3.12，含 brotli/brotlicffi 等依赖）
- **`.gitignore`** — 排除虚拟环境、IDE 配置、环境变量文件
- **`.venv/`** — 本地虚拟环境

## v1.2 开发规划（✅ 已完成）

v1.2 已实现并合入 master，新增两大功能模块 + 删除功能增强：

### 在线阅读器
- 新增 **ReaderView.vue**（阅读器页面）路由 `/reader/:id/:chapterIndex`
- 新增 API 接口：
  - `GET /api/v1/books/{book_id}/chapters` — 获取章节列表
  - `GET /api/v1/books/{book_id}/chapters/{chapter_index}` — 获取章节内容
  - `GET /api/v1/books/{book_id}/progress` — 获取阅读进度
  - `PUT /api/v1/books/{book_id}/progress` — 更新阅读进度
- 新增数据库表：`reading_progress`（阅读进度持久化）
- 新增 ORM 模型：`ReadingProgress`

### 标记与置顶
- 新增 API 接口：`PUT /api/v1/books/{book_id}/mark` — 切换标记状态
- Book 模型新增字段：`is_marked`（Boolean）、`marked_at`（DateTime）
- 书架排序逻辑变更：已标记书籍置顶（按标记时间倒序），未标记书籍按添加时间倒序
- 书架新增筛选栏："全部 / 已标记"
- 星标图标：空心 ☆ / 实心 ★，颜色 `#b08d4f`（v1.4 暖金，原 `#c9a96e`）

### 删除功能增强
- `DELETE /api/v1/books/{book_id}` 行为变更：软删除数据库记录的同时，自动检查并删除 `backend/epub_output/` 和 `backend/txt_output/` 中的对应本地文件
- `BookService.delete_book` 已实现文件清理逻辑：
  - 查询 Book 的 `epub_path` 和 `txt_path` 字段
  - 逐个调用 `os.remove()` 删除文件
  - 文件不存在时跳过（不抛异常），权限不足时记录日志
  - 文件删除失败不影响数据库软删除的正常执行
- 删除确认弹窗文案："确定要删除《xxx》吗？`.epub` 和 `.txt` 文件将同时被删除"

### 书架快速检索（v1.2 新增，v1.3.2 交互调整）
- ShelfView.vue 新增搜索栏：书名+作者双字段模糊搜索，≥2 字符触发
- v1.3.2：由防抖自动搜索改为输入后点击「搜索」按钮（或按 Enter）触发；编辑关键词后旧结果立即失效
- Pinia Store 新增 `allBooks`/`filteredBooks` 客户端缓存和过滤
- `backend/app/services/book_service.py` `search_books` 扩展为书名+作者双字段 OR 搜索
- 新增 CommandPalette.vue：Ctrl+K 全局命令面板，支持键盘导航和最近阅读
- 筛选标签：全部 / 已标记 / 抓取完成 / 有 EPUB

详细的 Pydantic Schema 设计见 PRD 文档。

## v1.3 开发规划（✅ 已完成）

v1.3 已实现并合入 master，新增 AI 语义搜索：

### AI 语义搜索
- 新增 `backend/app/services/ai_service.py`：Dify 工作流集成，LLM 语义匹配搜索
- 新增 `backend/app/api/v1/ai.py`：`POST /api/v1/ai/search` 端点
- ShelfView.vue 新增搜索模式切换：普通 / 🤖 AI 语义
- types/index.ts 新增 `AiSearchResult` 类型（含 match_reason 和 score）
- `backend/dify-workflows/shelf-semantic-search.yml`：Dify 语义搜索工作流定义

### AI 摘要生成
- 新增 `POST /api/v1/ai/summary/{book_id}` — 触发 AI 摘要生成
- 新增 `GET /api/v1/ai/summary/{book_id}` — 获取 AI 摘要
- books 表新增 `ai_summary` 和 `ai_summary_at` 字段
- `backend/migrations/add_ai_summary.sql`：AI 摘要字段迁移脚本

## v1.3.1 变更（✅ 已完成）

v1.3.1 修复章节排序问题（`backend/app/services/crawler_service.py`）：

- `_chapter_sort_key` 支持中文数字章节号：「第一章」与「第1章」排序等价
- 新增 `sort_chapter_pairs` 卷重置感知排序：按章节序号回落点切段（回落 = 新一卷开始），段内保持源站原始顺序，段间按最小序号稳定升序 — 解决多卷小说（如《诛仙》）每卷从「第一章」重新计数导致章节被打乱的问题
- 「序幕」「尾声」等无序号条目固定在原位置；「第x卷 第y章」卷-章组合与纯卷标题正确区分
- 章节列表解析的三处排序调用（规则解析 / 通用解析 / 目录翻页去重）统一改用 `sort_chapter_pairs`
- `test/test_crawler.py` 新增 `test_chapter_sort_with_volume_reset` 覆盖 6 类排序场景

## v1.3.2 变更（✅ 已完成）

v1.3.2 调整书架搜索交互（`frontend/src/views/ShelfView.vue`）：普通搜索与 AI 语义搜索由防抖自动搜索改为按钮触发：

- 搜索栏新增「搜索」按钮（AI 模式显示「AI 搜索」，搜索中带 loading），输入 ≥2 字符后点击按钮或按 Enter 触发搜索
- 移除 300ms（普通）/ 800ms（AI）防抖定时器；编辑关键词后旧搜索结果立即失效（`appliedKeyword`/`appliedAiQuery` 区分输入词与已生效词），提示用户再次点击搜索
- 关键词高亮、空状态、搜索提示文案均基于「已生效」搜索词渲染，避免误读过期结果
- 筛选标签切换与模式切换仍即时响应（沿用已生效关键词或输入词重新搜索）

## v1.4 变更（✅ 已完成）

v1.4 前端视觉重构：冷暖双基调设计系统 + WCAG 2.2 AA 无障碍规范：

- `frontend/src/styles/global.css` 新色板：冰蓝主色 `#3d7ea8`（4.5:1）、暖金星标 `#b08d4f`、苔绿成功 `#2e7d5b`、陶土红错误 `#b4523f`、阅读器日间暖纸背景 `#f8f3e8` + 暖褐正文 `#2e2a24`、夜间冷调 `#1a2332` / `#cbd5e1`
- 冷暖双基调设计：冷色为骨架（背景/导航/卡片/表单），暖色为点缀（星标、AI 匹配标签、阅读器纸感、错误色、封面渐变），80/20 配比
- 无障碍：对比度全部达标（正文 ≥4.5:1、UI 组件 ≥3:1）、键盘焦点可见、目标尺寸 ≥24×24（关键操作 ≥32px）、aria-live 动态播报（AI 搜索进度）、prefers-reduced-motion 动画豁免、App.vue 新增「跳到主要内容」跳过链接
- 阅读器双主题（ReaderView.vue）：日间暖纸 / 夜间冷调深蓝黑，令牌统一定义在 global.css

## v1.5 变更（✅ 已完成）

v1.5 移动端适配（375px / 768px / 1280px 断点）：

- 全局小屏规则：对话框去掉固定宽度、卡片内边距收紧、书架筛选标签整行横向滚动
- 阅读器/搜索/详情/源站管理页响应式布局，搜索栏窄屏下纵向堆叠

## v1.6 变更（✅ 已完成）

v1.6 设置页下线，功能并入顶栏用户头像下拉菜单：

- `frontend/src/views/SettingsView.vue` 删除，`frontend/src/router/index.ts` 移除 `/settings` 路由
- `frontend/src/components/TopNav.vue` 新增用户头像下拉菜单：修改个人密码（弹窗）+ 退出登录（确认）
- 新增 `frontend/src/components/ChangePasswordDialog.vue`：当前/新/确认三个输入框 + 校验
- 详情页新增星标标记按钮与行间距调节，阅读/删除按钮样式增强（填充样式 + 圆角）

## 自定义约束

- 删除文件时需给我提示，得到我的允许后才能删除
- 每次 review 以后，请告知我任务完成了。也就是要给我一个 ACK。ACK 的内容为：您好！当前任务已完成！
- 文档和代码注释优先使用中文