# 日常小说管理App -- 产品需求文档（PRD）

> **版本**：v2.3.1
> **作者**：小白74
> **日期**：2026-07-21
> **最后更新**：2026-08-23
> **状态**：v1.2 / v1.3 已完成；v1.3.2 书架搜索按钮触发（已完成）；v1.4 前端视觉重构（冷暖双基调设计系统 + WCAG 2.2 无障碍规范）—— 已完成；v1.5 移动端适配 —— 已完成；v1.6 设置页下线、头像下拉菜单 —— 已完成；v1.7 全局水墨雪景背景 —— 已完成；v1.8 自定义背景（预设主题 / 自定义图片 / 自定义配色）—— 已完成；v1.9 书架搜索框合并到主搜索框 —— 已完成；v2.0 AI 搜索开关（头像下拉菜单，开启后书架内搜索可搭配普通搜索）—— 已完成；v2.1 智能搜索模式路由（AI 开启后按查询意图自动选择搜索方式）—— 已完成；v2.2 Android 移动版（Capacitor 封装 APK，连接云端后端）—— 已完成；v2.3 Windows 桌面版（Electron + PyInstaller，SQLite 本地数据）+ 抓取修复（燃文 base64 正文解码、书海阁/梦书中文搜索恢复）—— 已完成；v2.3.1 移动端搜索修复（CORS 白名单补 `http://localhost`，Android WebView 源）—— 已完成

---

## 1. 产品概述

### 1.1 产品定位

一款面向日常小说阅读爱好者的**小说管理工具**（v2.3 起覆盖 Web / Windows 桌面 / Android 移动三端），帮助用户一站式完成小说搜索、抓取、格式化为 `.epub` 电子书并集中管理个人书架。桌面版（Electron + PyInstaller 内嵌后端，SQLite 本地数据）与移动版（Capacitor 封装 APK，连接云端部署后端）与 Web 版共享同一套 Vue 3 前端代码，仅运行时环境适配不同。

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
- **三端覆盖**（v2.2 / v2.3 新增）：Windows 桌面版（本地 SQLite 数据零依赖自包含）与 Android 移动版（Capacitor APK）与 Web 版共享同一套代码，满足不同场景的阅读管理需求

---

## 2. 功能需求

### 2.1 用户认证模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| AUTH-001 | 注册 | 用户通过邮箱 + 密码注册账号。密码长度 8-64 位，需包含字母和数字 | P0 |
| AUTH-002 | 登录 | 已注册用户通过邮箱 + 密码登录，登录后获取 JWT Token | P0 |
| AUTH-003 | 退出登录 | 清除本地 Token，返回登录页 | P0 |
| AUTH-004 | 密码修改 | 登录后可在「我的」页面修改密码（v2.4；v1.6~v2.3 在顶栏用户头像下拉菜单） | P1 |

**验收标准**：
- 注册时邮箱去重，重复邮箱提示"该邮箱已注册"
- 密码前端做格式校验，后端做哈希存储（bcrypt, saltRounds=12）
- 登录失败提示"邮箱或密码错误"，不区分具体原因（防枚举）
- Token 有效期：Access Token 2小时，Refresh Token 7天

### 2.2 书架管理模块（P0）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| SHELF-001 | 查看书架 | 以列表形式展示已有小说，每项显示书名、作者、添加时间、是否有 `.epub` 文件。支持顶部主搜索框书架内搜索（v1.9 合并：普通 + AI 语义双模式，跳转统一搜索页执行；v2.1：AI 开启后按查询意图自动选择搜索方式） | P0 |
| SHELF-002 | 添加小说 | 用户手动输入书名和作者，将小说加入书架 | P0 |
| SHELF-003 | 删除小说 | 从书架中删除指定小说（软删除，同时清理本地 `.epub`/`.txt` 文件，释放存储空间），前端提示确认 | P0 |
| SHELF-004 | 书架快速检索 | 通过顶部主搜索框（搜索范围选「书架内」）搜索已有书籍，输入关键词后点击「搜索」按钮或按 Enter 触发（≥2 字符），支持书名+作者双字段模糊搜索，支持普通搜索和 AI 语义搜索（v1.9：搜索框合并到主搜索框；v2.0：AI 搜索开关放用户头像下拉菜单（v2.4 迁入「我的」页面）；v2.1：AI 开关开启后按查询意图自动选择搜索方式——自然语言描述走 AI 语义搜索，书名/作者走普通搜索，结果页可一次性手动切换另一种方式）。新增 Ctrl+K 全局命令面板（类 VS Code 快速打开） | P0 |

**验收标准**：
- 书架列表按添加时间倒序排列（v1.2：已标记书籍置顶优先，详见 2.6 节）
- 顶部主搜索框选择「书架内」后输入关键词（≥2 字符），点击「搜索」按钮或按 Enter 跳转统一搜索页触发搜索（v1.9）；普通模式支持书名+作者双字段模糊匹配，AI 模式支持自然语言语义匹配（v2.0：AI 搜索开关在用户头像下拉菜单，v2.4 迁入「我的」页面；v2.1：AI 开关开启后按查询意图自动选择搜索方式——自然语言描述走 AI 语义搜索，书名/作者走普通搜索；未开启时默认普通搜索）
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
- 章节顺序与源站一致，无缺章漏章；章节按序号从小到大排列，同时兼容多卷小说（每卷从「第一章」重新计数，如《诛仙》），卷重置不打断原有阅读顺序；中文数字章节标题（如「第十一章」）与阿拉伯数字正确排序；「序幕」「尾声」等无序号章节保持在原位
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
- 阅读器双主题（v1.4）：日间模式使用暖纸背景 `#f8f3e8`、正文 `#2e2a24`（暖调纸感，对比度 12.9:1）；夜间模式使用深色背景 `#1a2332`、文字 `#cbd5e1`（冷调护眼，对比度 10.6:1）

### 2.6 标记与置顶模块（P1 — v1.2 新增）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| MARK-001 | 标记书籍 | 在书架列表中，用户可点击星标图标将书籍标记为"喜欢/收藏" | P0 |
| MARK-002 | 取消标记 | 再次点击星标取消标记，恢复普通状态 | P0 |
| MARK-003 | 标记置顶 | 被标记的书籍自动置顶到书架列表最上方，按标记时间倒序排列 | P0 |
| MARK-004 | 标记筛选 | 书架顶部提供筛选标签："全部 / 已标记"，方便快速查看收藏书籍 | P2 |

**验收标准**：
- 书架列表排序规则：已标记书籍优先显示（按标记时间倒序），未标记书籍在后（按添加时间倒序）
- 星标图标使用空心 ☆（未标记）和实心 ★（已标记），颜色使用暖金 `#b08d4f`（白底对比度 3.1:1，满足 WCAG 1.4.11 非文本对比度 ≥3:1）；状态同时通过形状（空心/实心）传达，不依赖单一通道
- 标记/取消标记操作即时响应，无需二次确认
- 标记状态与用户账号绑定，更换设备后保持同步

### 2.7 AI 功能模块（P1 — v1.3 新增）

| ID | 功能 | 描述 | 优先级 |
|----|------|------|--------|
| AI-001 | AI 语义搜索 | AI 搜索功能开关位于「我的」页面（v2.4；v2.0 原在用户头像下拉菜单）：开启后书架搜索（顶部主搜索框，v1.9 合并）按查询意图自动选择搜索方式（v2.1）——用自然语言描述想找的书（如"最近看的那本修仙小说"）时自动走 AI 语义搜索，输入书名/作者名时自动走普通模糊搜索；点击「搜索」按钮（或按 Enter）触发，后端通过 AI 语义匹配返回关联书籍，含匹配原因和置信度；未开启时书架内搜索默认普通搜索；结果页可一次性手动切换另一种搜索方式 | P0 |
| AI-002 | AI 摘要生成 | 对已完成抓取的书籍，触发 AI 自动生成小说摘要，包括角色列表和风格标签（如"仙侠、爽文、系统流"），在书籍详情页展示 | P1 |

**验收标准**：
- AI 语义搜索通过点击「搜索」按钮或按 Enter 触发（v1.3.2）；编辑关键词后旧结果立即失效，需重新点击搜索
- AI 搜索开关开启后，书架内搜索自动识别查询意图（v2.1）：自然语言描述（含口语词/语气词/标点/题材描述等信号）走 AI 语义搜索，书名/作者名走普通模糊搜索；识别存疑时按普通搜索（保守回退）
- 统一搜索页结果区显示「自动使用 AI 语义搜索 / 已使用普通搜索」标识，可点击「改用 xx 搜索」一次性切换另一种方式重新搜索；手动切换仅对当前查询生效，修改关键词后恢复自动识别（v2.1）
- AI 语义搜索输入框在搜索中时禁用，显示进度动画和"AI 正在理解…"提示文字
- AI 语义搜索通常 5-15 秒返回结果，超时或服务不可用时显示友好错误提示
- 搜索结果含 match_reason（匹配原因）和 score（置信度百分比）
- AI 摘要生成后展示在书籍详情页，包含角色列表和风格标签
- AI 摘要生成中显示 loading 状态，失败时显示重试按钮
- 相关 API：`POST /api/v1/ai/search`、`POST /api/v1/ai/summary/{book_id}`、`GET /api/v1/ai/summary/{book_id}`

---

## 3. 非功能需求

### 3.1 视觉设计（v1.4 重构：冷暖双基调）

**设计理念**：整体以「**冷色为骨架、暖色为点缀**」的双基调思路重新设计 —— 冷色调（深蓝灰 / 冰蓝 / 石板灰）构成页面结构层，保证界面冷静、专业、不刺眼；暖色调（暖金、陶土红、纸感米色）作为小面积点缀，出现在星标、重点标记、阅读器纸感背景等处，为页面注入温度，避免纯冷色带来的单调感。冷暖色形成"**书卷气**"的视觉隐喻：冷色像书房的墙与书架，暖色像台灯的暖光与泛黄的纸页。

**设计令牌表**（完整色值、对比度见第 10 章色板参考）：

| 令牌 | 冷色（骨架） | 暖色（点缀） |
|------|------------|------------|
| 背景 | `--bg` `#f4f6f8` 浅灰蓝 | 阅读器日间 `--reader-warm-bg` `#f8f3e8` 暖纸 |
| 表面/卡片 | `--surface` `#ffffff` | — |
| 主文字 | `--fg` `#1e293b` 深石板灰 | 阅读器正文 `#2e2a24` 暖褐灰 |
| 主色 | `--accent` `#3d7ea8` 冰蓝（按钮/链接/选中态） | `--accent-warm` `#b08d4f` 暖金（星标、重点标记） |
| 强调 | `--accent-hover` `#35688c` 冰蓝加深 | `--warm-hover` `#96713b` 暖金加深 |
| 状态 | `--success` `#2e7d5b` 苔绿、`--danger` `#b4523f` 陶土红 | 陶土红本身即暖调，替代旧版灰蓝错误色 |
| 分隔 | `--border` `#e2e8f0` 浅灰蓝 | 封面插画渐变中混入暖色系（暖金/陶土/杏色） |

**设计原则**：

| 约束 | 说明 |
|------|------|
| **冷主暖辅** | 页面 80% 面积保持冷色调（背景、导航、卡片、表单），暖色仅作小面积点缀（图标、徽标、选中高亮、阅读器纸感背景），暖色单元素面积 ≤ 卡片面积的 10%，不允许暖色大面积平铺（阅读器纸感背景除外——那是功能性的"纸张"隐喻） |
| **暖色点缀清单** | 星标 ★、AI 语义匹配标签（暖金底）、阅读器纸感背景与正文（`#f8f3e8` / `#2e2a24`）、错误/警告态（陶土红 `#b4523f`）、封面渐变中混入的暖色系 |
| **对比度门槛** | 正文文字 ≥ 4.5:1；大字（≥18.66px 粗体或 ≥24px）与 UI 组件/图形 ≥ 3:1（WCAG 2.2 AA）。每笔颜色入板前用对比度校验，不合规一律加深/加灰后使用 |
| **颜色不是唯一信息通道** | 任何状态不得仅靠颜色传达：星标用空心☆/实心★形状区分、错误信息必须同时有图标和文字、抓取状态用徽章文字+图标 |
| **动画** | 界面以极简为主，不引入装饰性动画。允许的动效仅限：加载指示动画（AI 搜索三点跳动、加载进度条）、反馈类微交互（≤150ms 的 hover/active 色阶即时反馈）、全局水墨雪景的雪花飘落（v1.7，唯一装饰性动效，见 3.1a）；其余 transition 全局禁用。注意：动效不得违反 WCAG 2.3.3（`prefers-reduced-motion: reduce` 时停用全部非必要动画） |
| **界面风格** | 极简整洁。卡片式布局，充足留白，信息层次通过字号/字重/间距区分，不用装饰性元素；暖色点缀即唯一的"装饰" |
| **字体** | 系统默认无衬线字体（system-ui, -apple-system, sans-serif），字号 14px 正文 / 12px 辅助文字（详见 3.3 字号规范） |

### 3.1a 水墨雪景背景（v1.7 新增：全局页面背景）

**所有页面**（登录/注册/书架/搜索/详情/源站管理）使用一幅**水墨画风格的冬日雪景**作为全局背景，纯 CSS + 内联 SVG 绘制（`frontend/src/components/InkSnowBackground.vue`），零外部图片资源，在根组件 `App.vue` 全局挂载（整个应用仅渲染一份，路由切换不重建）：

- **画面构成**：一棵梅花树静静伫立在雪地中，枝头绽放淡粉色和白色的梅花；天空中轻柔的雪花纷纷扬扬飘落；背景是朦胧的远山和模糊的树影，笼罩在一层淡淡的雾气中，营造空灵梦幻的氛围
- **水墨手法**：整体色调清冷淡雅，以水墨画的留白手法表现；画面简洁干净，构图疏朗有致；近景梅花清晰细腻，背景渐隐于雾中
- **实现约束**：
  - 背景为纯装饰层（`aria-hidden="true"` + `pointer-events: none` + `position: fixed` + `z-index: 0`），不参与焦点顺序、不遮挡交互；页面内容统一经 `#app-main`（`z-index: 1`，背景透明）叠于其上，雪景透过内容区与卡片间隙
  - 内容卡片保持不透明，文字/控件对比度不受影响；阅读器（日间暖纸/夜间冷调）因自身为功能性满幅背景，覆盖雪景层；登录卡片为 92% 透明白 + 轻投影浮起
  - 全场景保持静态；雪花飘落为仅有的装饰动效（淡蓝灰圆点，≥17s 慢速飘落，不同尺寸/起点/时长随机错落），`prefers-reduced-motion: reduce` 时雪花静止、场景完整保留
  - 色板见第 10.6 节；所有背景色为装饰性用色，不承载信息（WCAG 1.4.3 豁免）

### 3.2 响应式适配

| 约束 | 说明 |
|------|------|
| **Web 端优先** | v1.0 目标平台为桌面浏览器（>= 1280px 宽）。同时采用响应式布局，确保 768px（平板）和 375px（手机）下可正常使用 |
| **移动端预留** | CSS 使用 rem/em 相对单位，布局使用 Flexbox + Grid，为后续 React Native / Flutter 迁移降低适配成本 |
| **断点策略** | `< 920px` 单列布局；`>= 920px` 多列布局（搜索页 3 列卡片；书架/其他页面按容器宽度自适应）。响应式适配覆盖平板（768px）与手机（375px） |
| **可回流（WCAG 1.4.10）** | 内容区宽度限制在可读范围（正文 ≤ 780px），浏览器 400% 缩放或 320px 窄视口下不出现横向滚动条、不丢失功能 |

### 3.3 无障碍设计（WCAG 2.2 AA — v1.4 新增）

所有界面遵循 WCAG 2.2 AA 级标准，按 POUR 四原则落实：

#### 3.3.1 可感知（Perceivable）

| 项 | 规范 | 适用位置 |
|----|------|---------|
| **文字对比度** | 正文 ≥ 4.5:1；大字（≥18.66px 粗体 / ≥24px 任意字重）≥ 3:1 | 全部页面 |
| **非文字对比度（1.4.11）** | 图标、星标、状态徽章、进度条、输入框边框等 UI 组件 ≥ 3:1 | 星标 `#b08d4f`、徽章、进度条 |
| **图标替代文本** | 所有纯图标按钮加 `aria-label`（中文）；装饰性 SVG 用 `aria-hidden="true"`，不写 "图片/图像" 等冗余前缀 | 顶栏、星标、搜索、设置 |
| **颜色非唯一通道（1.4.1）** | 状态同时用文字/形状/图标传达 | 抓取状态徽章（文字+图标）、错误提示（图标+文字）、星标（形状☆/★） |
| **响应式回流（1.4.10）** | 400% 缩放 / 320px 视口无横向滚动、无功能丢失 | 全局布局 |
| **文本缩放（1.4.4）** | 支持浏览器 200% 文本缩放，不截断、不重叠 | 阅读器正文 |

#### 3.3.2 可操作（Operable）

| 项 | 规范 | 适用位置 |
|----|------|---------|
| **键盘可达（2.1.1）** | 所有交互控件可用 Tab/Shift+Tab 访问、Enter/Space 激活，不依赖鼠标 | 全部页面 |
| **焦点可见（2.4.7 / 2.4.11）** | 焦点指示器清晰可见：统一使用冰蓝 `#3d7ea8` 2px 描边（对比度 ≥3:1），覆盖所有键盘导航元素 | 全局 `:focus-visible` |
| **焦点顺序（2.4.3）** | 焦点移动顺序与视觉顺序一致；对话框/抽屉打开时焦点移入内部，关闭后焦点回到触发元素 | 目录抽屉、删除确认弹窗、命令面板 |
| **目标尺寸（2.5.8）** | 所有可点击控件 ≥ 24×24 CSS px（推荐 ≥ 32×32 以便触屏） | 星标、翻页按钮、图标按钮 |
| **单指针操作（2.5.1/2.5.2）** | 任何功能不依赖拖拽/长按等复杂手势，点击即可完成 | 全部功能 |
| **跳过导航（2.4.1）** | 顶栏前提供"跳到主要内容"跳过链接，聚焦时可见 | 全局布局 |

#### 3.3.3 可理解（Understandable）

| 项 | 规范 | 适用位置 |
|----|------|---------|
| **语义化 HTML** | 正确使用 `header` / `nav` / `main` / `footer` 地标，页面有且仅有一个 `main`；表单控件必须与 `<label>` 关联 | 全部页面 |
| **表单错误提示** | 错误信息必须为文字形式（不能只有颜色/图标变化），说明错误原因并给出修正建议；服务端返回的 `error` 字段原样展示 | 登录/注册/自定义源站 |
| **易读性** | 正文使用 1.5–1.8 倍行距、段落间距 1.2em、合理的字重对比与留白 | 全局文字 |
| **一致性（3.2.3/3.2.4）** | 相同功能的图标、文案、位置保持一致：返回始终"← 返回详情"，删除确认文案统一，页面标题与导航一致 | 导航、按钮、空状态 |

#### 3.3.4 健壮性（Robust）

| 项 | 规范 | 适用位置 |
|----|------|---------|
| **名称/角色/值（4.1.2）** | 自定义控件（星标按钮、命令面板、模式切换）必须带正确的 `role` / `aria-pressed` / `aria-expanded` 等状态属性；ARIA 仅用于改变语义，样式交给 CSS | 星标、模式切换、目录 |
| **动态更新（4.1.3）** | 状态变化（抓取进度、AI 搜索结果、错误提示）用 `aria-live="polite"` 播报，错误信息可用 `role="alert"` | 抓取进度、AI 搜索、表单 |
| **技术兼容** | 标签闭合、`lang="zh-CN"`、HTML 校验；不依赖 JS 的特性也有回退（无 JS 时内容仍可读） | 全局 |
| **动效偏好（2.3.3）** | 支持 `prefers-reduced-motion: reduce`，用户开启后停用加载动画以外的全部动效（所有动画必须同时提供 `animation`/`transition: none` 的回退） | 全局 |

**无障碍验收清单**：星标按钮尺寸 ≥ 24×24 且带 `aria-pressed` 状态；所有纯图标按钮有 `aria-label`；错误提示全部为文字形式；焦点样式全局可见；页面只有一个 `main` 地标；动态内容有 `aria-live` 播报；色彩对比度全部通过 AA。

### 3.4 性能

- 首屏加载 <= 2s（Lighthouse Performance >= 90）
- 搜索接口响应 <= 3s
- 单本小说抓取（假设 500 章）耗时 <= 5 分钟

### 3.5 安全

- 所有 API 必须通过 HTTPS 传输
- API 请求携带 JWT Authorization Header
- XSS 防护：后端统一 JSON 序列化输出（不注入 HTML）；前端在渲染用户内容处转义（`escapeHtml`），搜索高亮仅对转义后的文本加 `<mark>` 标签
- 爬虫模块设置频率限制与随机延迟：章节抓取随机间隔 0.2-0.4s、默认并发 5、失败重试指数退避 2-4s（v1.1 调整为平衡抓取速度与封禁风险；连接预检、目录翻页均带随机间隔）

---

## 4. 信息架构与页面结构

```
/          -- 根路径重定向到 /shelf
├── /login              -- 登录页（全局水墨雪景背景：远山雾影 + 梅花树 + 飘雪，v1.7）
├── /register           -- 注册页（同全局水墨雪景背景，v1.7）
├── /shelf              -- 书架首页（默认登录后跳转）
│   ├── 顶栏：Logo（纯展示，v2.4 移除跳转）+ 主搜索框（v1.9：书架内搜索合并至此）+ 用户头像（点击跳转「我的」页面，v2.4）
│   ├── 筛选栏：全部 / 已标记 / 抓取完成 / 有 EPUB（v1.2 新增）
│   ├── 列表区：小说卡片列表（标记书籍置顶显示，v1.2 新增）
│   └── 添加按钮：手动添加小说
├── /search?q=xxx       -- 搜索结果页（统一搜索页）
│   ├── 搜索框（可修改关键词重新搜索；v2.1：AI 开关开启时自动识别查询意图选择搜索方式，结果区可一次性手动切换）
│   ├── 书架内 tab：普通搜索服务端分页结果 / AI 语义结果卡片（含匹配分数与原因，v1.9）
│   ├── 全网搜索 tab：结果卡片列表（分页，v1.9；v2.0：移除源站下拉筛选，始终搜索全部源站）
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
├── /crawl-sources      -- 自定义源站管理
├── /profile            -- 「我的」页面（v2.4）：用户信息（头像首字母 + 邮箱）+ App 设置（自定义背景 / AI 搜索开关 / 修改密码 / 退出登录），页面内不设标题；移动端底部 TabBar 常驻入口，桌面端页内提供「返回书架」链接；挂载 ChangePasswordDialog 与 ThemeSettingsDialog
└── （v1.6：原 /settings 个人设置页并入顶栏用户头像下拉菜单，改为弹窗交互；v2.4：下拉菜单功能迁入 /profile，头像改为页面跳转）
```

**多端运行时**（v2.2 / v2.3）：路由随运行环境自动切换——Web 用 history 模式（`/login`、`/shelf`…），Electron 桌面与 Capacitor 移动（含 `http://localhost` / `https://localhost` 源）用 hash 模式（`#/login`、`#/shelf`…），避免 file:// 或本地容器下刷新 404。

---

## 5. 技术栈建议

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue 3 + TypeScript + Vite | 组件化开发效率高，TypeScript 类型安全，Vite 构建快。配合 Element Plus 实现企业级后台管理；`base: './'` 相对路径基准兼容桌面 file:// 与移动本地容器 |
| **样式** | Element Plus + 自定义 CSS Tokens | Element Plus 提供成熟组件库；自定义冷色调 CSS 变量主题，零动画极简风格 |
| **后端** | Python FastAPI | 爬虫与文件处理是 Python 强项（BeautifulSoup / httpx / ebooklib），FastAPI 异步性能好 |
| **数据库** | MySQL / SQLite（双引擎） | Web 部署用 MySQL（ACID 保证）；桌面版默认 SQLite（`%AppData%/NovelManager/novel_manager.db`，首次启动自动建表），`.env` 中 `DATABASE_URL` 可覆盖回 MySQL |
| **认证** | JWT（Access + Refresh Token） | 无状态认证，便于多端（Web / 桌面 / 移动）对接 |
| **状态管理** | Pinia | Vue 3 官方推荐状态管理库，模块化、类型安全 |
| **组件库** | Element Plus | Vue 3 生态最成熟的企业级 UI 组件库 |
| **文件存储** | 本地文件系统 / MinIO（可选） | 本地存储 `.epub`/`.txt` 文件，后续可切换对象存储；桌面版输出目录存用户数据目录（`%AppData%/NovelManager/epub_output|txt_output`），由 `config.py` 统一配置 |
| **爬虫** | httpx + BeautifulSoup4 | 异步 HTTP 请求 + HTML 解析，规则驱动架构，支持通用回退；燃文等源站正文 `qsbs.bb()` base64 内联解码（v2.3） |
| **EPUB 生成** | EbookLib（Python） | 成熟的 `.epub` 生成库，支持元数据、目录、封面 |
| **Windows 桌面** | Electron 33 + PyInstaller（v2.3 新增） | `desktop/` 主进程找空闲端口 → 拉起 `novel-backend.exe` 子进程 → 健康检查 → 加载 `frontend/dist`；前端经 preload 注入的 `electronAPI` 拿到动态端口拼接 API 地址 |
| **Android 移动** | Capacitor 8（v2.2 新增） | `frontend/android/` 原生工程，WebView 加载前端构建产物；API 根地址由 `frontend/src/config.ts` 的 `MOBILE_API_BASE` 常量指向云端后端，打包 APK 前修改 |

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
| **v1.3.1** | 章节排序增强：中文数字章节号支持（「第十一章」与「第11章」正确排序）、卷重置感知排序（多卷小说每卷从「第一章」重新计数时不打乱阅读顺序，如《诛仙》）、「序幕/尾声」等无序号章节保持原位 | ✅ 已完成 |
| **v1.3.2** | 书架搜索交互调整：普通搜索与 AI 语义搜索由防抖自动搜索改为输入后点击「搜索」按钮（或按 Enter）触发；编辑关键词后旧结果立即失效；搜索按钮在 AI 模式显示「AI 搜索」并带加载状态 | ✅ 已完成 |
| **v1.4** | 前端视觉重构：冷暖双基调设计系统（冷色为骨架、暖色为点缀）、新色板（加深冰蓝主色 `#3d7ea8`、暖金星标 `#b08d4f`、苔绿成功/陶土红错误、暖纸阅读器背景 `#f8f3e8`）、封面渐变冷-暖双色板、WCAG 2.2 AA 无障碍规范（对比度、键盘可达、焦点可见、目标尺寸 24×24、aria-live、reduced-motion） | ✅ 已完成 |
| **v1.5** | 移动端适配：全局小屏规则（对话框去固定宽度、卡片内边距收紧、筛选标签横向滚动）、阅读器/搜索/详情/源站管理页响应式布局（375px / 768px / 1280px） | ✅ 已完成 |
| **v1.6** | 设置页下线：原 `/settings` 个人设置页并入顶栏用户头像下拉菜单（修改密码弹窗 + 退出登录确认），新增 ChangePasswordDialog.vue；详情页星标与行间距调节、阅读/删除按钮样式增强 | ✅ 已完成 |
| **v1.7** | 全局水墨雪景背景：新增 InkSnowBackground.vue（纯 CSS + 内联 SVG，零外部资源）——远山雾影、雪地模糊树影、右侧近景梅花树（淡粉/白梅）、雪花轻缓飘落（reduced-motion 停用）；根组件 App.vue 全局挂载，所有页面共用（阅读器满幅功能性背景除外）；登录卡片 92% 透明白浮起 | ✅ 已完成 |
| **v1.8** | 自定义背景：新增 ThemeSettingsDialog.vue + theme store（预设主题包、本地上传图片背景、8 项自定义配色、雪花/星光粒子开关与数量），CSS 变量实时驱动，localStorage + IndexedDB 持久化 | ✅ 已完成 |
| **v1.9** | 书架搜索框合并到主搜索框：ShelfView 内嵌搜索栏移除，搜索范围选「书架内」时主搜索框显示普通 / AI 语义模式切换（桌面嵌于搜索框、移动端在搜索行下方），点击搜索携带 q/mode/ai 参数跳转统一搜索页；SearchView 书架内 tab 支持双模式（AI 结果含匹配分数与原因、不分页），模式状态经 shelfSearch store 跨组件共享 | ✅ 已完成 |
| **v2.0** | AI 搜索开关：开关放用户头像下拉菜单（默认关闭），开启后书架内搜索可搭配普通搜索使用（统一搜索页书架内 tab 下方显示普通 / AI 语义切换，TopNav 携带 q/mode/ai 参数跳转）；未开启时书架内搜索默认普通搜索；全网搜索移除源站下拉筛选，始终搜索全部源站（searchExternal 不再传 source_id） | ✅ 已完成 |
| **v2.1** | 智能搜索模式路由：AI 开关开启后书架内搜索按查询意图自动选择搜索方式——自然语言描述（口语词/语气词/标点/题材描述等信号）走 AI 语义搜索，书名/作者名走普通搜索（新增 lib/queryIntent.ts 意图识别，识别存疑保守回退普通）；移除手动普通/AI 模式切换，结果区显示「自动使用 xx 搜索」标识并支持一次性手动切换（修改关键词后恢复自动识别）；新增单元测试 queryIntent.test.ts（vitest，70 用例） | ✅ 已完成 |
| **v2.2** | Android 移动版：Capacitor 8 封装 APK（`frontend/android/` + `capacitor.config.ts`），WebView 加载前端构建产物，API 根地址由 `frontend/src/config.ts` 的 `MOBILE_API_BASE` 常量指向云端后端；前端环境探测（Electron / Capacitor / Web）动态选择 API baseURL；原生容器环境路由切换 hash 模式；Vite `base: './'` 相对路径基准 | ✅ 已完成 |
| **v2.3** | Windows 桌面版 + 抓取修复：① 桌面版（`desktop/`，Electron 33 + PyInstaller）：主进程找空闲端口 → 拉起 `novel-backend.exe` 子进程（`backend/run.py` 入口）→ 健康检查 → 加载 `frontend/dist`，preload 注入 `electronAPI`（`apiBaseUrl`），退出时优雅关闭后端；② 后端 SQLite 双引擎：默认 SQLite（`%AppData%/NovelManager/`，首次启动自动建表，`DATABASE_URL` 可覆盖回 MySQL），新增 `aiosqlite`/`platformdirs`/`pyinstaller` 依赖，导出目录迁至用户数据目录，CORS 增加本地动态端口/file:///Capacitor 源；③ 抓取修复：燃文等源站 `document.writeln(qsbs.bb('...'))` base64 内联正文解码（解析阶段 + 兜底双路径）；书海阁、梦书中文搜索恢复启用（`disabled: false`），燃文规则新增「章节-末尾章」选择器；④ 部署脚本：`deploy/`（`deploy.sh` + nginx 配置 + systemd 服务，移动端后端部署） | ✅ 已完成 |
| **v2.3.1** | 移动端搜索修复：Android WebView 实际源为 `http://localhost`（capacitor.config.ts `androidScheme: 'http'`），不在后端 CORS 白名单（仅 `https://localhost`）→ 预检 400、搜索/书架请求全部被拦。修复：`config.py` 白名单补 `http://localhost`；`deploy.sh` 生成的 `.env` 模板同步补上 + 部署提示（旧部署需手动改 `.env` 并重启服务）；`capacitor.config.ts` 注释更正 | ✅ 已完成 |
| **v2.4** | 「我的」页面重构：新增 /profile 完整页面（用户信息 + App 设置），原顶栏头像下拉菜单功能全部迁入（自定义背景 / AI 搜索开关 / 修改密码 / 退出登录），页内不设标题；顶栏「我的书架」 logo 改纯展示（移除跳转），用户头像点击跳转「我的」页面；移动端底部 TabBar 新增「我的」常驻入口，桌面端「我的」页提供「返回书架」链接 | ✅ 已完成 |
| **v2.5** | 水墨玻璃拟态视觉升级（web + 移动端全部页面，设计系统 global.css v2.0）：① 毛玻璃质感：`--surface` 升级为固定白色半透明底 + 全局统一 `backdrop-filter`（参数为常量，质感不随自定义背景变化），背景层新增恒定宣纸纹理（SVG 噪点 + 轻雾）；② 水墨风：墨色令牌（浓淡墨 / 朱砂印章红）、宋体系标题 + `.ink-title` 笔锋短线、用户头像改朱砂印章、榜单前三徽标朱砂化、顶栏细条改墨→黛→朱砂渐变；③ 层次与按钮突出：玻璃卡片墨影悬浮（悬浮加深）、主按钮黛蓝加粗 + 墨影、设置项图标水墨圆角垫；④ 对比度提升：正文改浓墨、次级文字/功能色/控件边框全部加深（满足 WCAG AA）；⑤ 图标统一为 1.8 描边圆角线帽风格（🏆 emoji 换 SVG）。接口无变化，阅读器纸感与主题机制不变 | ✅ 已完成 |
| **v2.5.1** | 水墨玻璃体验打磨：① 各页面返回按钮统一为水墨玻璃胶囊样式（`.back-btn`：半透明玻璃底 + 白描边 + 悬浮黛蓝提亮），覆盖顶栏返回、搜索、源站管理、排行榜两级返回、「我的」页；② 自定义背景新增「背景透明度」滑杆（20%~100%，即时生效并持久化，背景场景层隐入底色，宣纸纹理恒定不受影响），「恢复默认」同时重置为 100%（灰块面板方案于 v2.5.2 废弃）。接口无变化 | ✅ 已完成 |
| **v2.5.2** | 按反馈废弃 v2.5.1 灰块玻璃面板方案：① 背景明暗自适应墨色——theme store 检测背景亮度（调色板加权亮度 / 图片 16×16 采样）写入 `html[data-bg-tone]`，直置背景上的文字（页头标题+笔锋短线、副标题、九宫格书名/作者、空状态、页脚、缓存提示）在浓墨与暖白淡墨间自动切换，任意自定义背景下可读且无灰块；② 按钮全面水墨玻璃化：默认按钮玻璃底+白描边+悬浮黛蓝提亮，主按钮黛蓝玻璃光泽（顶部高光+墨影），筛选标签玻璃分段（选中黛蓝填充），分页器玻璃化；③ 九宫格书名/作者同步接入自适应墨色。接口无变化 | ✅ 已完成 |
| **v2.4+** | 离线阅读器内嵌（移动端本地缓存章节）、拼音搜索（pinyin-pro）、搜索历史与自动补全、全文搜索升级（MySQL FULLTEXT / Meilisearch）、语音搜索（Web Speech API） | 🔮 规划中 |

---

## 9. 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 目标网站反爬机制升级 | 抓取功能失效 | 多源站冗余；支持用户手动粘贴内容作为降级方案 |
| 版权合规风险 | 法律风险 | 产品仅作个人学习用途，不提供公开分享/分发功能；`.epub` 文件归属用户私有数据 |
| 大本小说抓取耗时过长 | 用户体验差 | 后端异步任务队列处理（Celery / ARQ），前端轮询进度，不阻塞操作 |
| 服务器存储压力 | 成本上升 | v1.0 单文件存储；后续接入对象存储 + 自动过期清理（超过 90 天未访问的文件自动归档） |

---

## 10. 附录：冷暖双基调色板参考（v1.4 重构）

> 对比度按 WCAG 2.2 AA 计算：正文文字 ≥ 4.5:1、大字/UI 组件 ≥ 3:1。全部色值已通过校验。

### 10.1 冷色系（骨架：背景 / 表面 / 文字 / 主色）

| 用途 | 色值 | 对比度（对白） | 说明 |
|------|------|--------------|------|
| 背景（主） | `#f4f6f8` | — | 浅灰蓝背景 |
| 卡片背景 | `#ffffff` | — | 纯白卡片 |
| 主文字 | `#1e293b` | 14.7:1 ✅ | 深石板灰 |
| 次强调文字 | `#334155` | 10.4:1 ✅ | 深蓝灰（`--fg-soft`） |
| 辅助文字 | `#64748b` | 4.7:1 ✅ | 中灰蓝（未变，已确认达标） |
| 主色调（按钮/链接） | `#3d7ea8` | 4.5:1 ✅ | 冰蓝（v1.4 由 `#4a8bb5` 加深而来，Element Plus primary 映射 `--accent`） |
| 强调（hover/active） | `#35688c` | 5.7:1 ✅ | 冰蓝加深（`--accent-hover`，v1.4 由 `#3a7096` 加深而来） |
| 边框/分割线 | `#e2e8f0` | 1.4:1 | 浅灰蓝（仅作装饰性分隔线，不承载信息；表单输入框边框使用 `#94a3b8` 3.0:1 ✅） |
| 成功状态 | `#2e7d5b` | 5.1:1 ✅ | 苔绿（v1.4 由中性灰蓝 `#475569` 替换，符合用户对绿色状态的直觉且保持低饱和不刺眼） |
| 错误状态 | `#b4523f` | 4.6:1 ✅ | 陶土红（v1.4 由灰蓝 `#94a3b8` 替换；暖色系，承担功能色且是暖点缀的一部分） |

### 10.2 暖色系（点缀：星标 / 阅读器纸感 / 重点标记）

| 用途 | 色值 | 对比度（对白） | 说明 |
|------|------|--------------|------|
| 暖色点缀主色（星标★/重点标记） | `#b08d4f` | 3.1:1 ✅ | 暖金（v1.4 由 `#c9a96e` 加深而来，满足非文本 ≥3:1） |
| 暖金 hover | `#96713b` | 4.5:1 ✅ | 暖金加深（`--warm-hover`） |
| 星标底色（选中态） | `#f3e8d5` | 1.4:1 | 暖金浅底（`--warm-soft`，标签/徽章底色，文字用深暖褐 `#6b4f2a` 7.4:1 ✅） |
| 阅读器纸感背景（日间） | `#f8f3e8` | — | 暖纸米色（`--reader-warm-bg`，功能性的"纸张"隐喻，唯一的暖色大面积区域） |
| 阅读器正文文字（日间） | `#2e2a24` | 12.9:1 ✅ | 暖褐灰，长文阅读友好 |
| 阅读器辅助文字（日间） | `#6b5d4f` | 5.7:1 ✅ | 暖褐辅助 |

### 10.3 夜间模式（阅读器）

| 用途 | 色值 | 对比度 | 说明 |
|------|------|--------|------|
| 夜间背景 | `#1a2332` | — | 冷调深蓝黑 |
| 夜间顶/底栏 | `#141d2a` | — | 背景加深 |
| 夜间正文 | `#cbd5e1` | 10.6:1 ✅ | 冷调浅灰蓝 |
| 夜间标题 | `#e2e8f0` | 12.4:1 ✅ | 更亮一级 |
| 夜间边框 | `#2d3a4a` | — | 仅装饰分隔 |

### 10.4 封面插画渐变（暖色点缀之一）

封面用书名/作者确定性哈希从 8 个色板中选取（保持纯 CSS、零动画）。色板以冷色为底、混入暖金/陶土/杏色，让书架在冷灰背景中呈现"彩色书脊"的层次：

| 编号 | 渐变（`oklch` 色相从冷到暖） | 基调 |
|------|------------------------------|------|
| 0 | `#dce8ef → #e8d9c4` | 冷蓝灰 → 暖杏 |
| 1 | `#cbd8e2 → #e3cfb4` | 冷青灰 → 暖沙金 |
| 2 | `#d5dfe6 → #ead5c8` | 冷灰蓝 → 暖陶杏 |
| 3 | `#c5d2dd → #ecd9c2` | 冷灰青 → 暖米金 |
| 4 | `#d8e2ea → #ead2c3` | 冷雾蓝 → 暖杏 |
| 5 | `#d0dbe4 → #e6d3bd` | 冷灰蓝 → 暖沙 |
| 6 | `#dae4ec → #ecdbc9` | 冷极浅蓝 → 暖米杏 |
| 7 | `#cdd8e0 → #e9d8c6` | 冷灰青 → 暖杏金 |

### 10.5 使用原则

1. **80/20 冷暖配比**：约 80% 面积为冷色系（背景、导航、卡片、表单、正文 UI），暖色只出现在 10.2 节列出的点缀位置，单元素 ≤ 卡片面积 10%。
2. **暖色是"台灯"不是"装修"**：暖色服务于功能（星标=收藏的温度、纸感=阅读的舒适、陶土红=错误的醒目），不为装饰而装饰——这是"不单调"和"不杂乱"之间的分界线。
3. **对比度即底线**：任何新颜色入板前必须过 AA 校验（正文 4.5:1 / UI 组件 3:1）；不达标的颜色一律加深或加灰，不允许"看着好看"凌驾于可读性之上。
4. **颜色不单独传意**：状态永远伴随文字/形状/图标（见 3.3.1）。

### 10.6 水墨雪景背景色板（v1.7：全局页面背景）

水墨雪景全部为装饰性背景色（无文字承载，WCAG 1.4.3 豁免），以清冷淡雅的灰蓝墨色铺底、淡粉与白梅为仅有的暖色点缀：

| 元素 | 色值 | 说明 |
|------|------|------|
| 背景天空（渐变） | `#e9eef2 → #f4f6f8 → #f6f8fa` | 清冷纸白，由上而下极浅过渡 |
| 远山（两重） | `#aebcc8` / `#93a5b4`（55% 透明度） | 淡墨灰蓝，前重后轻，渐隐于雾 |
| 雾层 | `#e8edf1 → 透明` 垂直渐变 | 覆盖山脚与树影上部，水墨留白手法 |
| 雪地 | `#f6f8fa → #e9eef3` | 近白留白，向底部极浅蓝灰晕开 |
| 模糊树影 | `#9fb0bd`（28%–40% 透明度） | 雪地淡墨点景 + 极淡墨线枯枝 |
| 梅树主枝 | `#4c5d6b → #6b7d8d` 渐变 | 近景用较深墨色，营造景深 |
| 旁枝/老桩 | `#5c6d7b` / `#6b7d8d` | 细墨线，飞白笔触感 |
| 梅花 | `#e7c2cd`（淡粉）/ `#f2d8e0`（浅粉）/ `#f7f1ee`（白） | 错落点缀枝头，画面唯一暖色 |
| 花苞 | `#c9a0ae` | 待放小墨点，含蓄留白 |
| 雪花 | `#bccdd9` + 半透明晕边 | 淡蓝灰圆点，轻缓飘落 |

---

> **ACK**：您好！当前任务已完成！
>
> **v1.2 更新**：新增 App 内在线阅读器、章节列表与内容 API、阅读进度记录与恢复、星标标记与置顶功能、书架标记筛选、书架内嵌搜索栏（书名+作者双字段）+ Ctrl+K 命令面板。
>
> **v1.3 更新**：新增 AI 语义搜索（书架内自然语言搜索，Dify 工作流驱动）、AI 摘要生成（角色列表 + 风格标签）、书架搜索栏 AI 模式切换。
>
> **v1.3.1 更新**：章节排序增强 —— `_chapter_sort_key` 支持中文数字章节号（「第一章」与「第1章」等价），新增 `sort_chapter_pairs` 卷重置感知排序算法（按序号回落切段，段内保持源站原始顺序、段间按最小序号稳定升序），解决多卷小说（如《诛仙》）每卷重新从「第一章」计数导致章节被打乱的问题；「序幕」「尾声」「卷标题」等无序号条目固定在原位置；「第x卷 第y章」卷-章组合与纯卷标题正确区分。
>
> **v1.3.2 更新**：书架搜索交互调整 —— 普通搜索与 AI 语义搜索由防抖自动搜索改为输入后点击「搜索」按钮（AI 模式显示「AI 搜索」）或按 Enter 触发；编辑关键词后旧结果立即失效；关键词高亮/空状态/提示文案基于已生效搜索词渲染。
>
> **v1.4 更新**：前端视觉重构设计规范 —— ① 冷暖双基调设计系统：冷色为骨架（背景/导航/卡片/表单），暖色为点缀（星标、AI 匹配标签、阅读器纸感背景、陶土红错误色、封面渐变暖色），80/20 配比原则，让页面冷静而不单调；② 新色板（第 10 章）：冰蓝主色加深为 `#3d7ea8`（对比度 4.5:1 达标）、暖金星标 `#b08d4f`（3:1 达标）、成功色改为苔绿 `#2e7d5b`、错误色改为陶土红 `#b4523f`、阅读器日间纸感背景 `#f8f3e8` + 暖褐正文 `#2e2a24`；③ 新增 3.3 无障碍设计章节（WCAG 2.2 AA）：文字对比度 4.5:1 / UI 组件 3:1、键盘可达与焦点可见、目标尺寸 ≥24×24、aria-live 动态播报、prefers-reduced-motion 支持；④ 响应式章节补充可回流要求（400% 缩放无横向滚动）。✅ 代码已实施（`global.css` 新色板、阅读器双主题、跳过链接、aria-live 均已落地）。
>
> **v1.5 更新**：移动端适配 —— 全局小屏规则（对话框去固定宽度、卡片内边距收紧、筛选标签横向滚动），阅读器/搜索/详情/源站管理页响应式布局。
>
> **v1.6 更新**：设置页下线 —— 原 `/settings` 页面并入顶栏用户头像下拉菜单（修改密码弹窗 + 退出登录确认），新增 `ChangePasswordDialog.vue`；详情页星标与行间距调节、阅读/删除按钮样式增强。
>
> **v1.7 更新**：全局水墨雪景背景 —— 新增 `InkSnowBackground.vue`（纯 CSS + 内联 SVG，零外部资源）：远山雾影（两重淡墨灰蓝 + 雾层渐隐）、雪地模糊树影、右侧近景梅花树（淡粉/白梅）、雪花飘落（淡蓝灰圆点，≥17s 慢速飘落，reduced-motion 静止）；根组件 App.vue 全局挂载，所有页面共用（阅读器满幅功能性背景除外）；背景层 aria-hidden + pointer-events:none 纯装饰；登录卡片 92% 透明白浮起；色板见 10.6 节。
>
> **v1.8 更新**：自定义背景 —— 新增 `ThemeSettingsDialog.vue` + `theme` store（预设主题包一键切换、本地上传图片背景（IndexedDB 存储）、8 项自定义配色（底色/主景/深景/点缀/点缀二/地面/剪影/雾层）实时预览、雪花/星光粒子开关与数量调节），全部由 CSS 变量（`--theme-*`）驱动、实时生效，localStorage + IndexedDB 持久化；入口在顶栏头像下拉菜单「自定义背景」。
>
> **v1.9 更新**：书架搜索框合并到主搜索框 —— ShelfView 内嵌搜索栏移除，主搜索框（TopNav）搜索范围选「书架内」时显示普通 / AI 语义模式切换（桌面嵌于搜索框内、移动端在搜索行下方）；点击搜索携带 `q`/`mode=shelf`/`ai` 参数跳转统一搜索页（`/search`），AI 模式搜索按钮带加载态；SearchView 书架内 tab 支持普通（服务端分页）/ AI 语义（结果卡片含匹配分数与原因、不分页）双模式，模式切换后自动按新方式重新搜索；模式与 AI 结果状态经新增 `shelfSearch` store 跨 TopNav / SearchView 共享。
>
> **v2.0 更新**：AI 搜索开关 —— ① `shelfSearch` store 新增 `aiEnabled` 开关状态（localStorage 键 `shelf_ai_search_enabled` 持久化，默认关闭），关闭时同步复位 AI 模式并清空结果；② TopNav 用户头像下拉菜单新增「AI 搜索」开关项（`el-switch`，自定义背景与修改密码之间，点击不关闭菜单）；搜索范围下拉保持「书架内 / 全网搜索」两项；点搜索书架内携带 `q`/`mode=shelf`/`ai` 参数跳转（仅开关开启且上次为 AI 模式时 `ai=1`），输入框占位文案随 AI 状态切换；③ 统一搜索页：AI 开关开启时书架内 tab 下方显示普通 / AI 语义切换（`shelfSearch` store 跨页面沿用，onMounted 读取 `ai` 参数恢复模式），未开启时书架内搜索默认普通搜索（`aiActive = aiEnabled && aiMode` 统一驱动），开关变化且已有关键词时自动重新搜索；④ 全网搜索移除源站下拉筛选（`source-select`），`searchExternal` 不再传 `source_id`，始终搜索全部源站。✅ 代码已实施。
>
> **v2.1 更新**：智能搜索模式路由 —— 新增 `frontend/src/lib/queryIntent.ts`（`detectQueryIntent` 意图识别纯函数：口语词/语气词/标点/题材描述上下文/英文口语虚词/书名号/多词段等信号，识别存疑保守回退普通搜索）；`shelfSearch` store 新增 `aiModeSource`（'auto' 自动识别 / 'manual' 手动覆盖）、`applySearchMode`（新查询提交前无条件恢复自动识别）、`overrideAiMode`（结果页一次性手动切换并清空旧结果）；SearchView 移除手动普通/AI 单选切换组，结果区显示「自动使用 xx 搜索 / 已使用普通搜索」标识 +「改用 xx 搜索」一次性切换，AI 空结果提供「改用普通搜索」回退，编辑查询词后恢复自动识别；新增 `frontend/test/queryIntent.test.ts`（vitest，70 用例，`npm test` 运行）。✅ 代码已实施。
>
> **v2.2 更新**：Android 移动版 —— 引入 Capacitor 8（`frontend/android/` 原生工程 + `frontend/capacitor.config.ts`），WebView 加载前端构建产物；新增 `frontend/src/config.ts` 全局常量（`MOBILE_API_BASE` 指向云端部署的后端地址，打包 APK 前修改）；`http.ts` 增加环境探测（`window.electronAPI` / `window.Capacitor` / `http(s)://localhost` 源）：桌面用动态端口、移动用云端地址、Web 走 Vite proxy，统一导出 `API_BASE_URL` 供下载链接拼接；路由在原生容器环境自动切换 hash 模式（`createWebHashHistory`），401 跳转登录兼容 hash 路由；Vite `base: './'` 相对路径基准。✅ 代码已实施。
>
> **v2.3 更新**：Windows 桌面版 + 抓取修复 —— ① 桌面版：新增 `desktop/`（Electron 33 主进程 `main.js`：找空闲端口 → 拉起后端 exe 子进程 → 健康检查 → 加载 `frontend/dist`；`preload.js` 注入 `electronAPI.apiBaseUrl`；NSIS 安装包配置）；新增 `backend/run.py` PyInstaller 入口与 `backend/build.spec`（打包 `novel-backend.exe`）；② 后端 SQLite 双引擎：`config.py` 默认 SQLite（`%AppData%/NovelManager/novel_manager.db`，`platformdirs` 定位 + 自动创建；`DATABASE_URL` 可覆盖回 MySQL），`database.py` 按 URL 前缀选择引擎参数，`main.py` lifespan 中 SQLite 首次启动自动建表、关闭时释放连接池；导出目录迁至用户数据目录（`epub_output`/`txt_output` 由 `settings` 统一配置）；CORS 增加 `http://localhost:*`、`file://`、`null`、`https://localhost`、`capacitor://localhost`；`requirements.txt` 新增 `aiosqlite`/`platformdirs`/`pyinstaller`；③ 抓取修复：`crawler_service.py` 新增 `_decode_qsbs_scripts`（解析阶段解码 `document.writeln(qsbs.bb('...'))` base64 内联正文，替换回原位置保留 `<br>` 换行与 `&nbsp;` 缩进）+ 兜底路径（正文仍为内联脚本形式时从文本匹配解码）；`main.json` 书海阁、梦书中文搜索恢复启用（`disabled: false`），燃文规则新增「章节-末尾章」选择器（防目录页引用卷末注）；④ 部署：新增 `deploy/`（`deploy.sh` + `nginx-novel.conf` + `novel-backend.service`，用于移动端云端后端部署）。✅ 代码已实施。
>
> **v2.3.1 更新**：移动端搜索修复 —— Android WebView 实际源为 `http://localhost`（`capacitor.config.ts` 的 `androidScheme: 'http'`），但后端 CORS 白名单只放行了 `https://localhost`，导致移动端所有带 Authorization 头的请求（书架/搜索/详情等）预检 400、被浏览器拦截，表现为「移动端搜索不能用」。修复：① `backend/app/config.py` 默认 CORS 白名单补 `http://localhost`（同时保留 `https://localhost` 与 iOS `capacitor://localhost`）；② `deploy/deploy.sh` 生成的 `.env` 模板同步补上，并新增部署提示（旧版本部署的 `.env` 不会自动更新，需手动补该源并 `systemctl restart novel-backend`）；③ `frontend/capacitor.config.ts` 注释更正为与实际源一致。已本地实证：修复前 `Origin: http://localhost` 预检 400 且响应无 `access-control-allow-origin`；修复后预检 200、响应头正确回显。✅ 代码已实施。
