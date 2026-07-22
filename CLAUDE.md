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

# Git 推送
git push origin master

# 注意：远程仓库使用 HTTPS，若推送时卡住，可尝试：
GIT_TERMINAL_PROMPT=0 git push origin master
```

## 架构与技术栈

### 规划技术栈（详见 PRD 第 5 章）

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite | 组件化开发，为后续 React Native 迁移留口 |
| **样式** | Tailwind CSS + CSS Modules | 冷色调（深蓝/石板灰），零动画，极简界面 |
| **后端** | Python FastAPI | 异步高性能，爬虫与文件处理是 Python 强项 |
| **数据库** | PostgreSQL | 用户与书架数据 ACID 保证 |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于移动端对接 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP + HTML 解析 |
| **EPUB** | EbookLib | 标准 `.epub` 3.2 格式生成 |

### 当前文件结构

- **`PRD-小说管理App.md`** — 产品需求文档，包含功能需求、信息架构、API 设计、数据库表设计、色板参考
- **`pyproject.toml`** — 项目元数据（Python ≥ 3.12，无依赖）
- **`.gitignore`** — 排除虚拟环境、IDE 配置、环境变量文件
- **`.venv/`** — 本地虚拟环境

## 自定义约束

- 删除文件时需给我提示，得到我的允许后才能删除
- 每次 review 以后，请告知我任务完成了。也就是要给我一个 ACK。ACK 的内容为：您好！当前任务已完成！
- 文档和代码注释优先使用中文