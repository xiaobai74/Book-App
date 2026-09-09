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
cd frontend && npm test         # 前端单元测试（vitest：queryIntent 意图识别）

# 后端开发
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 桌面版打包（Windows）
cd backend && pyinstaller build.spec   # 生成 backend/dist/novel-backend.exe
cd frontend && npm run build           # 生成 frontend/dist（桌面版前端入口）
cd desktop && npm run dist             # Electron 打包为 NSIS 安装包（desktop/release/）

# 移动版打包（Android APK）
cd frontend && npm run build && npx cap sync android   # 构建前端并同步到原生工程
cd frontend/android && ./gradlew assembleDebug          # 生成 debug APK（先改 src/config.ts 的 MOBILE_API_BASE）

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
| **数据库** | MySQL / SQLite（双引擎，v2.3） | Web 部署用 MySQL（ACID 保证）；桌面版默认 SQLite（用户数据目录自动建表），`DATABASE_URL` 可覆盖 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于多端（Web/桌面/移动）对接 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP + HTML 解析 |
| **EPUB** | EbookLib | 标准 `.epub` 3.2 格式生成 |
| **桌面版** | Electron 33 + PyInstaller（v2.3） | `desktop/` 主进程拉起内嵌后端 exe，SQLite 本地数据，零外部依赖 |
| **移动版** | Capacitor 8（v2.2） | `frontend/android/` 封装 APK，连接云端部署后端 |

### 当前文件结构

- **`PRD-小说管理App.md`** — 产品需求文档（v2.3），含功能需求、信息架构、API 设计、数据库表设计、色板参考（含 v1.7 水墨雪景背景色板）、多端运行时说明
- **`frontend/`** — Vue 3 前端工程（组件、路由、状态管理、API 封装），三端（Web/桌面/移动）共用
  - `frontend/src/config.ts` — 全局常量：`MOBILE_API_BASE`（移动版云端后端地址，打包 APK 前修改）
  - `frontend/src/lib/` — 纯函数工具：queryIntent.ts（v2.1 查询意图识别）、backgroundImages.ts（IndexedDB 图片存取）
  - `frontend/test/` — 前端单元测试（vitest）：queryIntent.test.ts（v2.1，70 用例，`npm test` 运行）
  - `frontend/android/` + `frontend/capacitor.config.ts` — Capacitor 8 Android 原生工程（v2.2，`npx cap sync` 同步）
- **`backend/`** — Python FastAPI 后端（路由、模型、服务、中间件）
  - `backend/run.py` + `backend/build.spec` — PyInstaller 打包入口与配置（v2.3，产物 `backend/dist/novel-backend.exe`）
  - `backend/app/config.py` — 双数据库配置：默认 SQLite（`%AppData%/NovelManager/`），`DATABASE_URL` 可覆盖回 MySQL；导出目录也在此统一配置
  - `backend/app/models/` — ORM 模型：User、Book、Chapter、RefreshToken、CrawlSource、ReadingProgress（v1.2 新增）
  - `backend/app/services/` — 服务层：crawler_service（规则驱动爬虫引擎 + 卷重置感知章节排序 + qsbs base64 正文解码）、search_service（外部源站搜索）、crawl_manager（后台抓取流水线 v5，边爬边看：单章完成即增量写库 + SSE 事件总线实时推送）、epub_service、txt_service、book_service（含标记/阅读进度逻辑 + 双字段搜索，v1.2 扩展）、ai_service（AI 语义搜索/摘要，v1.3 新增）、crawl_source_service（自定义源站 CRUD）
  - `backend/app/api/v1/ai.py` — AI 功能路由（v1.3 新增）：语义搜索、摘要生成
  - `frontend/src/stores/shelfSearch.ts` — 书架 AI 语义搜索共享状态（v1.9 新增，TopNav 与 SearchView 共用）
  - `backend/rules/` — 规则引擎 + main.json（11 个内置源站规则）+ custom_sources.json（用户自定义规则）；frozen 模式规则从 `_MEIPASS` 读取、自定义规则写入用户数据目录
  - `backend/rules/rule_engine.py` — 规则加载、域名匹配、通用回退规则生成、自定义规则持久化
  - `backend/epub_output/` — 生成的 EPUB 文件（桌面版存用户数据目录）
  - `backend/txt_output/` — 生成的 TXT 文件（桌面版存用户数据目录）
  - `backend/dify-workflows/` — Dify AI 工作流定义（v1.3 新增）：语义搜索、摘要生成
  - `backend/migrations/` — 数据库迁移脚本（v1.2 标记+进度 + v1.3 AI 摘要字段）
- **`desktop/`** — Windows 桌面版（v2.3）：main.js（拉起后端子进程 + 窗口管理）、preload.js（注入 electronAPI）、build.ps1 / electron-builder 配置（NSIS 安装包）
- **`deploy/`** — 部署脚本（v2.3）：deploy.sh + nginx 配置 + systemd 服务（移动版云端后端部署）
- **`docs/`** — 文档目录
  - `docs/书架快速检索工作流-知识库.md` — 书架快速检索功能知识库（SHELF-001）
  - `docs/dify-knowledge/` — Dify 知识库拆分文档（01-08 共 8 个章节）
- **`test/`** — 测试目录
  - `test/test plan/` — 前后端测试计划
  - `test/test report/` — 测试报告
  - `test/e2e_live_crawl_test.py` — 边爬边看端到端验证（v2.6：SSE 事件/增量写库/抓取中可读，需后端运行）
- **`api/API文档.md`** — API 接口完整文档（已更新至 v1.4，含标记/章节/进度/AI 接口与 SSE 实时推送接口 crawl-stream）
- **`pyproject.toml`** — 项目元数据（Python ≥ 3.12，含 brotli/brotlicffi 等依赖）
- **`.gitignore`** — 排除虚拟环境、IDE 配置、环境变量文件、构建产物（backend/dist、desktop/release、frontend/android 构建目录、*.apk、调试输出 txt）
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

## v1.7 变更（✅ 已完成）

v1.7 全页面新增水墨雪景背景（纯 CSS + 内联 SVG，零外部图片资源）：

- 新增 `frontend/src/components/InkSnowBackground.vue`：远山雾影（两重淡墨灰蓝 + 雾层渐隐）、雪地模糊树影、右侧近景梅花树（淡粉/白梅）、雪花飘落（淡蓝灰圆点，≥17s 慢速飘落）
- 根组件 `App.vue` 全局挂载（整个应用仅渲染一份），所有页面共用；`global.css` 中 `#app-main` 内容层 `z-index: 1` + 背景透明叠于其上；阅读器（日间暖纸/夜间冷调满幅功能性背景）覆盖雪景层；登录卡片 92% 透明白 + 轻投影浮起
- 雪花动效豁免：keyframes `ink-snow-fall` 按项目惯例放 `global.css`（scoped keyframes 会被 Vue 重命名且受全局 `animation:none` 影响）；`prefers-reduced-motion: reduce` 时雪花静止、场景完整保留
- 背景层 `aria-hidden` + `pointer-events: none`，纯装饰不参与交互；设计规范见 PRD 3.1a / 10.6 节

## v1.8 变更（✅ 已完成）

v1.8 新增自定义背景功能（入口：顶栏头像下拉菜单「自定义背景」）：

- 新增 `frontend/src/components/ThemeSettingsDialog.vue`：预设主题包一键切换（水墨雪景/暮色红梅/静谧星夜/拂晓流霜/素白留影/素色留白）、本地上传图片背景（JPG/PNG/WebP/GIF ≤10MB，IndexedDB 存储）、8 项自定义配色（底色/主景/深景/点缀/点缀二/地面/剪影/雾层）实时预览、雪花/星光粒子开关与数量（0-48）
- 新增 `frontend/src/stores/theme.ts`：主题状态经 CSS 变量（`--theme-*`）驱动、实时生效；localStorage 持久化（图片 Blob 存 IndexedDB，运行时 object URL 渲染）；预览/保存/取消三态（预览不落盘，保存转正、关闭撤销）
- 新增 `frontend/src/lib/backgroundImages.ts`（IndexedDB 图片存取）、`frontend/src/components/ThemeBackground.vue`（场景编排）、`frontend/src/components/ParticleLayer.vue`（雪花/星光粒子）

## v1.9 变更（✅ 已完成）

v1.9 书架内搜索框合并到主搜索框（TopNav）：

- `frontend/src/views/ShelfView.vue` 删除页面内嵌搜索栏（搜索输入框/搜索按钮/模式切换/进度提示）与相关状态逻辑，仅保留筛选标签与书籍列表
- `frontend/src/components/TopNav.vue` 主搜索框：搜索范围选「书架内」时显示普通 / 🤖 AI 语义模式切换（桌面嵌于搜索框内、移动端在搜索行下方），按钮 AI 模式带 loading + 「AI」文字；点击搜索携带 `q`/`mode=shelf`/`ai` 参数跳转 `/search`
- 新增 `frontend/src/stores/shelfSearch.ts`：AI 搜索模式/结果/进行中状态跨 TopNav 与 SearchView 共享（含请求序号防过期响应覆盖）
- `frontend/src/views/SearchView.vue` 书架内 tab 支持双模式：普通（服务端分页）/ AI 语义（结果卡片含匹配分数与原因，不分页）；模式切换后自动按新方式重新搜索；onMounted 读取 `ai` 查询参数恢复模式
- 接口无变化：`GET /api/v1/search`（普通）与 `POST /api/v1/ai/search`（AI）保持原样

## v2.0 变更（✅ 已完成）

v2.0 新增 AI 搜索功能开关（用户头像下拉菜单），开启后书架内搜索可搭配普通搜索：

- `frontend/src/stores/shelfSearch.ts`：新增 `aiEnabled` 开关状态（localStorage 键 `shelf_ai_search_enabled` 持久化，默认关闭）与 `setAiEnabled`（关闭时同步复位 `aiMode` 并清空 AI 结果/在途请求）
- `frontend/src/components/TopNav.vue`：头像下拉菜单新增「AI 搜索」开关项（`el-switch`，位于自定义背景与修改密码之间，`@click.stop` 防菜单关闭）；搜索范围下拉恢复「书架内 / 全网搜索」两项；点搜索书架内携带 `q`/`mode=shelf`/`ai` 参数跳转 `/search`（仅开关开启且上次为 AI 模式时 `ai=1`），输入框占位文案随 AI 状态切换
- `frontend/src/views/SearchView.vue`：书架内 tab 下方普通 / AI 语义切换仅在开关开启时显示；未开启时书架内搜索强制普通搜索（`aiActive = aiEnabled && aiMode` 计算属性统一驱动模板与搜索执行）；onMounted 仅在开关开启时读取 `ai` 参数；新增 aiEnabled 监听（开关变化且已有关键词时重新搜索）；全网搜索移除源站下拉筛选（`source-select` 及 `selectedSource` 状态），`searchExternal` 调用不再传 `source_id`，始终搜索全部源站
- 接口无变化

## v2.1 变更（✅ 已完成）

v2.1 智能搜索模式路由：AI 开关开启后，书架内搜索按查询意图自动选择搜索方式——自然语言描述走 AI 语义搜索，书名/作者名走普通搜索：

- 新增 `frontend/src/lib/queryIntent.ts`：`detectQueryIntent(q)` 意图识别纯函数（无副作用），信号包括口语词（想看/推荐/有没有）、语气词（吗/呢/吧）、标点、题材描述上下文匹配（「想看玄幻」→ AI，但《凡人修仙传》等含题材词的真实书名不受误伤）、英文口语/虚词（单词边界）、书名号包裹、多词段；识别存疑一律保守回退普通搜索（<2 或 >60 字符也回退普通）
- `frontend/src/stores/shelfSearch.ts`：新增 `aiModeSource`（'auto' 自动识别 / 'manual' 手动覆盖）与 `applySearchMode(q)`（TopNav 新查询提交前调用，无条件恢复自动识别）、`overrideAiMode(enabled)`（结果页一次性手动切换，同时清空旧结果）
- `frontend/src/components/TopNav.vue`：书架内搜索提交前调用 `applySearchMode(q)` 再携带 `ai` 参数跳转；占位文案改为「输入书名、作者或自然语言描述…」（仅开关开启时）
- `frontend/src/views/SearchView.vue`：移除手动普通 / AI 语义单选切换组；`doSearch` 按 `aiModeSource` 决定是否重新识别（手动覆盖沿用）；结果区新增「自动使用 xx 搜索 / 已使用普通搜索」标识 + 「改用 xx 搜索」一次性切换（`switchSearchMethod`）；AI 空结果提供「改用普通搜索」回退；编辑查询词后恢复自动识别；aiEnabled 关闭时复位模式并清空 AI 结果
- 新增 `frontend/test/queryIntent.test.ts`：意图识别单元测试（70 用例），devDependency 新增 vitest，`npm test` 运行
- 接口无变化

## v2.2 变更（✅ 已完成）

v2.2 新增 Android 移动版（Capacitor 8 封装 APK，连接云端后端）：

- `frontend/capacitor.config.ts` + `frontend/android/`：Capacitor 原生工程，WebView 加载前端构建产物
- 新增 `frontend/src/config.ts`：`MOBILE_API_BASE` 常量指向云端部署的后端地址（打包 APK 前修改）
- `frontend/src/api/http.ts`：环境探测（`window.electronAPI` / `window.Capacitor` / `http(s)://localhost` 源）——桌面用动态端口、移动用云端地址、Web 走 Vite proxy；导出 `API_BASE_URL` 供 `getDownloadUrl` 拼接（桌面随机端口与移动云端下不能再用相对路径）
- `frontend/src/router/index.ts`：原生容器环境自动切换 hash 模式（`createWebHashHistory`），401 跳转登录兼容 hash 路由
- `frontend/vite.config.ts`：`base: './'` 相对路径基准（兼容 Electron file:// 与 Capacitor 本地容器）
- `frontend/package.json`：新增 `@capacitor/core|cli|android` 依赖

## v2.3 变更（✅ 已完成）

v2.3 Windows 桌面版（Electron + PyInstaller，SQLite 本地数据）+ 抓取修复：

### 桌面版
- 新增 `desktop/main.js`（Electron 33 主进程）：找空闲端口 → 拉起 `novel-backend.exe` 子进程（`BACKEND_PORT` 环境变量）→ 健康检查轮询 → 加载 `frontend/dist`；退出时关闭后端子进程；移除默认菜单、保留剪贴板快捷键、外链交系统浏览器
- 新增 `desktop/preload.js`：contextBridge 注入 `electronAPI.isElectron` / `electronAPI.apiBaseUrl`（动态端口）
- 新增 `backend/run.py`（PyInstaller 入口：frozen 模式切换 CWD 到 `_MEIPASS` 再启动 uvicorn）+ `backend/build.spec`
- `desktop/package.json` electron-builder 配置：extraResources 携带 `backend/dist/novel-backend.exe` 与 `frontend/dist`，NSIS 安装包输出到 `desktop/release/`

### 后端 SQLite 双引擎
- `backend/app/config.py`：默认 `sqlite+aiosqlite:///{DATA_DIR}/novel_manager.db`（`platformdirs` 定位 `%AppData%/NovelManager` 并自动创建；`.env` 的 `DATABASE_URL` 可覆盖回 MySQL）；`epub_output_dir`/`txt_output_dir` 迁至用户数据目录
- `backend/app/database.py`：按 URL 前缀分支创建引擎（SQLite 用 `check_same_thread=False`，MySQL 用连接池参数）
- `backend/app/main.py` lifespan：SQLite 首次启动自动建表（`Base.metadata.create_all`，免手动迁移）；关闭时 `engine.dispose()` 释放连接池
- CORS 新增：`http://localhost:*`、`http://127.0.0.1:*`、`file://`、`null`、`https://localhost`、`capacitor://localhost`（桌面 file:// 与 Capacitor WebView 源；v2.3.1 补 `http://localhost` — Android WebView 实际源，`androidScheme: 'http'`）
- `backend/rules/rule_engine.py`：frozen 模式内置规则从 `sys._MEIPASS/rules` 读取；自定义规则 `custom_sources.json` 持久化到用户数据目录（重启不丢失）
- `backend/requirements.txt`：新增 `aiosqlite`、`platformdirs`、`pyinstaller`
- `backend/app/services/epub_service.py` / `txt_service.py`：输出目录改由 `settings` 统一配置

### 抓取修复
- `backend/app/services/crawler_service.py` 新增 `_decode_qsbs_scripts`：燃文等源站将正文 base64 内联在 `<script>document.writeln(qsbs.bb('...'))</script>` 中，必须在清理 script 标签前解码回原位置（保留 `<br />` 换行与 `&nbsp;` 缩进）；另有兜底路径（正文仍为内联脚本形式时从文本匹配 `qsbs.bb('...')` 片段解码）
- `backend/rules/main.json`：书海阁小说网、梦书中文搜索恢复启用（`disabled: false`）；燃文规则新增「章节-末尾章」选择器（防目录页误收卷末注）

### 部署脚本
- 新增 `deploy/deploy.sh` + `deploy/nginx-novel.conf` + `deploy/novel-backend.service`：移动版云端后端一键部署（nginx 反代 + systemd 服务）

## v2.3.1 变更（✅ 已完成）

v2.3.1 修复移动端搜索不可用（CORS 拦截）：

- 根因：Android WebView 实际源为 `http://localhost`（`frontend/capacitor.config.ts` 的 `androidScheme: 'http'`），后端 CORS 白名单仅放行 `https://localhost` → 带 Authorization 头的请求预检 400，移动端书架/搜索/详情全部请求被浏览器拦截（Web 端走 Vite 代理、桌面端 file:// 在白名单，故只有移动端受影响）
- `backend/app/config.py`：默认 CORS 白名单补 `http://localhost`（保留 `https://localhost`、`capacitor://localhost`）
- `deploy/deploy.sh`：`.env` 模板同步补 `http://localhost`；新增部署提示——旧版本部署的服务器 `.env` 不会自动更新，需手动补该源后 `systemctl restart novel-backend`（云端后端生效的关键步骤）
- `frontend/capacitor.config.ts`：注释更正为与实际源一致
- 本地实证：修复前 `Origin: http://localhost` 预检 400、响应无 `access-control-allow-origin`；修复后预检 200、响应头正确回显 `http://localhost`
- 注意：`backend/.env` 的 `CORS_ORIGINS` 会覆盖 `config.py` 默认值（pydantic-settings 优先级），本地开发 .env 已同步更新
- 注意：云端 ECS 停止再启动后按量付费公网 IP 会变（曾由 47.120.32.118 变为 47.120.44.192），届时需同步更新 `frontend/src/config.ts` 的 `MOBILE_API_BASE` 并重新打包 APK

## v2.4 变更（✅ 已完成）

v2.4 「我的」页面重构：原顶栏头像下拉菜单功能迁入独立的 /profile 页面，顶栏头像改为页面跳转：

- `frontend/src/views/ProfileView.vue`：由占位页升级为完整页面——用户信息卡片（头像首字母 + 邮箱）+ App 设置列表（自定义背景 / AI 搜索开关 / 修改个人密码 / 退出登录），页内不设标题；设置项触摸目标 ≥48px；挂载 `ChangePasswordDialog` 与 `ThemeSettingsDialog`（原顶栏挂载点迁入）；退出登录确认逻辑同原菜单行为（确认 → 清 Token → `/login`）
- `frontend/src/components/TopNav.vue`：「我的书架」logo 由 `router-link` 改为纯展示 `div`（移除跳转功能，回书架走底部 TabBar / 页内返回按钮）；移除头像 `el-dropdown` 下拉菜单，头像改为按钮 `router.push('/profile')`；删除 `handleUserCommand`/`handleLogout`/`changePasswordVisible` 及两个弹窗组件引用（仅保留 `shelfSearch` 供占位文案与搜索参数）
- 路由/TabBar 无需改动：`/profile` 路由（`showTabBar: true`）与底部 TabBar「我的」入口（书架/排行榜/我的）已提前就位，本次只补齐页面内容；桌面端「我的」页内提供「返回书架」链接（≤760px 隐藏，移动端由 TabBar 承担）
- 接口无变化；验证：`npm run build`（vue-tsc）通过 + 70/70 单测通过；文档同步：PRD（AUTH-004 / SHELF-004 / AI-001 / 页面结构图 / 版本表）
- 注意：前端测试计划中「2.8 顶栏头像下拉菜单（FE-USER-xx）」用例已失效，对应功能验证改在「我的」页面进行（用例未改，待测试计划下轮修订）

## v2.5 变更（✅ 已完成）

v2.5 水墨玻璃拟态视觉升级（web 端 + 移动端全部页面，设计系统 global.css v2.0）：

- `frontend/src/styles/global.css`：新增墨色令牌（`--ink`/`--ink-soft` 浓淡墨、`--seal` 朱砂印章红）、毛玻璃令牌（`--glass-blur: blur(18px) saturate(1.5)` 固定常量、`--glass-border`）、层次令牌（`--shadow-glass`/`--shadow-glass-hover` 墨影）；`--surface` 由纯白升级为 `rgba(255,255,255,0.66)` 玻璃底（所有引用处自动毛玻璃化，质感恒定不随自定义背景变化）；全局集中给 `.topnav/.tabbar/.book-card/.search-card/.auth-card/.source-card/.rank-item/.sheet-panel/.profile-*/.card/.external-result-card/.ai-summary-card/.mobile-search-row` 叠 `backdrop-filter`；新增 `.ink-title` 笔锋短线标题类；标题字体改宋体系（`--font-heading`）；主色加深为黛蓝 #2e688a，`--muted`/`--danger`/`--success` 全部加深提对比；EP 覆盖：控件边框加深（≥3:1）、`.el-dialog` 毛玻璃化、输入控件强制实心白底保可读、主按钮加粗 + 墨影突出；`.book-card` 悬浮加深层次；顶栏细条渐变改墨→黛→朱砂；logo 改浓墨宋体；头像改朱砂印章红 + 白圈描边；顶栏排行榜入口 🏆 emoji 换为同风格描边 SVG 奖杯
- `frontend/src/components/ThemeBackground.vue`：新增恒定宣纸纹理层 `.glass-veil`（SVG fractalNoise 噪点 + 底部轻雾，参数固定），任何背景主题下画面质感一致，与玻璃卡片共同构成水墨层次（需求：毛玻璃质感不随背景改变）
- `frontend/src/components/TabBar.vue`：毛玻璃底；未选中淡墨、选中黛蓝 + 图标上方笔锋短线指示（`.tab-item.active::before`）
- `frontend/src/views/ProfileView.vue`：头像改朱砂印章（白圈 + 宋体首字母）；设置项图标加黛蓝水墨圆角垫（退出登录为陶土红垫）；卡片玻璃高光描边；`--text-muted` 降级色全部换 `var(--muted)`
- `frontend/src/views/RankingView.vue`：两级标题加 `.ink-title`；源站卡片玻璃高光描边 + 悬浮加深墨影；榜单序号徽标改墨色，前三名改朱砂印章红 + 投影突出；次级文字换 `var(--muted)`
- `frontend/src/views/ShelfView.vue` / `SearchView.vue` / `CrawlSourcesView.vue`：页面主标题加 `.ink-title` 笔锋短线；九宫格书名改浓墨提对比；登录/注册页 `.auth-card` 自动玻璃化（全局规则）
- 阅读器（ReaderView）纸感配色与自定义背景主题机制（theme store / 预设 / 粒子）均不变；接口无变化；验证：`npm run build`（vue-tsc）通过 + 70/70 单测通过；文档同步：PRD 版本表新增 v2.5 行

## v2.5.1 变更（✅ 已完成）

水墨玻璃体验三项打磨：

- **统一水墨玻璃返回按钮**：`global.css` 新增 `.back-btn`（胶囊形玻璃药丸：半透明玻璃底 + 白描边 + 墨色文字 + 悬浮黛蓝描边提亮），并加入 150ms 微交互白名单。接入点：顶栏返回（TopNav）、搜索页两处、源站管理页底部、排行榜两级返回（返回书架 / 返回源站列表）、「我的」页返回链接；阅读器纸感页内返回按钮保持原样不动。原 `el-button text` 样式全部替换为原生 `button` / `router-link`，无接口变化。
- **文字防背景混淆**：新增全局 `.glass-panel` 玻璃面板托底，接入书架 / 搜索 / 源站管理 / 排行榜四处页头；`.empty-state` 改为玻璃卡（任意背景下可读）。用户更换深色图片背景后，所有页头标题与辅助文字仍在玻璃面上。
- **背景透明度设置**：theme store 新增 `bgOpacity`（0.2~1，越界裁剪、持久化、旧数据兜底 1，随预设/重置/存储全链路生效）；`ThemeBackground.vue` 场景层包入 `.theme-bg-content` 消费 `--theme-bg-opacity`，宣纸纹理层恒定不受影响；设置弹窗新增「背景透明度」滑杆（20%~100%，步进 5%，即时生效），「恢复默认」同时重置为 100%。
- 验证：`npm run build`（vue-tsc）7.25s 通过 + 70/70 单测通过；文档同步：PRD 版本表新增 v2.5.1 行。注意：本轮改动未打包进 APK，真机验证需重新打包

## v2.5.2 变更（✅ 已完成）

按用户反馈废弃 v2.5.1 的灰块玻璃面板方案，改为背景明暗自适应墨色 + 按钮全面玻璃化：

- **废弃 `.glass-panel` 灰块托底**：书架/搜索/源站/排行榜页头恢复直置背景；`.empty-state` 同步去玻璃卡。
- **背景明暗自适应墨色**：theme store 新增 `updateBgTone()`——调色板背景按底色+深景加权亮度（WCAG 线性化）判定，图片背景缩样 16×16 canvas 异步采样平均亮度；向 `<html>` 写入 `data-bg-tone='dark'|'light'`。global.css 新增 `--onbg-title/--onbg-text/--onbg-muted` 变量组（默认=浓墨；dark 时=暖白淡墨 #f5f2e9 系），接入 `.ink-title`（含笔锋短线）、`.lead`、`.pagefoot`、`.empty-state`、九宫格 `.grid-title/.grid-author`、搜索/源站页直置提示文字、`.cache-tip`。玻璃卡片内文字不受影响（仍走 --ink/--muted）。
- **按钮全面水墨玻璃化**：默认 `.el-button` 半透明玻璃底+白描边+墨色文字+悬浮黛蓝提亮；`.el-button--primary` 黛蓝玻璃光泽（顶部高光+底部加深+内高光）；text/link 型保持透明；筛选标签 `.el-radio-button` 玻璃分段（选中黛蓝填充+墨影）；分页器玻璃化。`.back-btn` 不变。
- 验证：`npm run build` 6.51s 通过 + 70/70 单测通过；文档同步：PRD 版本表新增 v2.5.2 行

## v2.6 变更（✅ 已完成）

v2.6 边爬边看（后台异步爬取 + 实时数据推送），抓取过程中无需等待全量完成即可阅读已就绪章节：

### 后端（增量写库 + SSE 事件总线）
- `backend/app/services/crawler_service.py`：`crawl_book` 新增 `on_plan`（目录就绪）/ `on_chapter`（单章完成，锁外回调不阻塞并发抓取）回调
- `backend/app/services/crawl_manager.py` v5：单章抓取完成立即写库（write_lock 串行；首批写入前才删旧章节并归零 chapter_count，保证新内容可用前旧章节仍可读），SSE 订阅总线（`subscribe_crawl`/`unsubscribe_crawl`/`_publish`，QueueFull 丢最旧保最新）推送 `plan`/`chapter_ready`/`done`/`failed` 事件；书籍被删时 `aborted` 状态停止写库
- `backend/app/api/v1/books.py`：新增 `GET /books/{book_id}/crawl-stream` SSE 端点（所有权校验 404；订阅先发 `snapshot`，无活跃任务发 `status=none` 后关流；15s 心跳 `: ping`；`X-Accel-Buffering: no` 禁 nginx 缓冲）

### 前端（SSE 订阅 + 阅读等待态）
- `frontend/src/api/books.ts`：新增 `subscribeCrawlStream(bookId, onEvent)` —— `fetch` + `ReadableStream` 消费 SSE（`EventSource` 不支持 Authorization 头），异常时回调 `stream_error`，返回 abort 取消函数；`types/index.ts` 新增 `CrawlStreamEvent`
- `BookDetailView.vue` v2.4：轮询改 SSE 订阅（`stream_error`/`snapshot none` 自动回退 2s 轮询），`chapter_ready` 防抖 1.5s 重载目录（实时增长），抓取中显示「立即阅读」入口
- `ReaderView.vue` v1.6：抓取中可进入阅读（头部实时徽标）；`effectiveTotal` 用抓取计划总数允许翻到待抓取章节；未就绪章节（404）进入 `waitingForCrawl` 等待态而非报错，`chapter_ready` 命中当前章自动加载；目录合并已就绪章节 + 计划中待抓取章节（半透明+「抓取中」标签）；头部标题等待态显示计划标题（`headerTitle`）

### 验证
- `test/e2e_live_crawl_test.py`：真实源站（香书小说 149 章）端到端验证 10/10 通过——SSE 事件流、抓取中（5/149）章节已写库且可读、`chapter_ready` 数 == 库内章节数
- 浏览器实测通过：进度实时自增、目录 13→149 实时增长、待抓取章节等待态+就绪自动加载
- 文档同步：API 文档 v1.4（crawl-stream 章节）、PRD 版本表 v2.6 行


## 自定义约束

- 删除文件时需给我提示，得到我的允许后才能删除
- 每次 review 以后，请告知我任务完成了。也就是要给我一个 ACK。ACK 的内容为：您好！当前任务已完成！
- 文档和代码注释优先使用中文