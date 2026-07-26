# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概览

一个日常小说管理 App（Web 端），帮助用户搜索、抓取网络小说，生成 `.epub` 电子书并集中管理个人书架。

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
| **样式** | Element Plus + 自定义 CSS | 冷色调（深蓝/石板灰），零动画，极简界面 |
| **后端** | Python FastAPI | 异步高性能，爬虫与文件处理是 Python 强项 |
| **数据库** | MySQL | 用户与书架数据 ACID 保证 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于移动端对接 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP + HTML 解析 |
| **EPUB** | EbookLib | 标准 `.epub` 3.2 格式生成 |

### 当前文件结构

- **`PRD-小说管理App.md`** — 产品需求文档，包含功能需求、信息架构、API 设计、数据库表设计、色板参考
- **`api/API文档.md`** — 18 个 API 接口的完整文档（请求/响应示例、错误码、通用抓取规则说明、自定义源站配置说明）
- **`frontend/`** — Vue 3 前端工程（组件、路由、状态管理、API 封装）
- **`backend/`** — Python FastAPI 后端（路由、模型、服务、中间件）
  - `backend/app/models/` — ORM 模型：User、Book、Chapter、RefreshToken、CrawlSource
  - `backend/app/services/` — 服务层：crawler_service（规则驱动爬虫引擎）、search_service（外部源站搜索）、crawl_manager（后台抓取流水线）、epub_service、txt_service、crawl_source_service（自定义源站 CRUD）
  - `backend/rules/` — 规则引擎 + main.json（10 个内置源站规则）+ custom_sources.json（用户自定义规则）
  - `backend/rules/rule_engine.py` — 规则加载、域名匹配、通用回退规则生成、自定义规则持久化
  - `backend/epub_output/` — 生成的 EPUB 文件
  - `backend/txt_output/` — 生成的 TXT 文件
- **`pyproject.toml`** — 项目元数据（Python ≥ 3.12，无依赖）
- **`.gitignore`** — 排除虚拟环境、IDE 配置、环境变量文件
- **`.venv/`** — 本地虚拟环境

## 自定义约束

- 删除文件时需给我提示，得到我的允许后才能删除
- 每次 review 以后，请告知我任务完成了。也就是要给我一个 ACK。ACK 的内容为：您好！当前任务已完成！
- 文档和代码注释优先使用中文