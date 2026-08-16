# 小说管理App — API 文档

> **版本**：v1.3
> **基础地址**：`http://localhost:8000`
> **接口协议**：RESTful，请求/响应均为 JSON
> **在线文档**：[Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)
> **v1.3.1**：章节排序增强（中文数字章节号 + 卷重置感知排序），见 [8.2 通用抓取规则说明](#82-通用抓取规则说明)

---

## 目录

1. [通用说明](#1-通用说明)
   - [1.1 统一响应格式](#11-统一响应格式)
   - [1.2 认证方式](#12-认证方式)
   - [1.3 错误处理](#13-错误处理)
   - [1.4 HTTP 状态码速查](#14-http-状态码速查)
2. [认证接口](#2-认证接口)
   - [POST /api/v1/auth/register — 用户注册](#post-apiv1authregister--用户注册)
   - [POST /api/v1/auth/login — 用户登录](#post-apiv1authlogin--用户登录)
   - [POST /api/v1/auth/refresh — 刷新 Token](#post-apiv1authrefresh--刷新-token)
   - [PUT /api/v1/auth/password — 修改密码](#put-apiv1authpassword--修改密码)
3. [书架接口](#3-书架接口)
   - [GET /api/v1/books — 获取书架列表](#get-apiv1books--获取书架列表)
   - [POST /api/v1/books — 添加书籍](#post-apiv1books--添加书籍)
   - [GET /api/v1/books/{book_id} — 查看书籍详情](#get-apiv1booksbook_id--查看书籍详情)
   - [DELETE /api/v1/books/{book_id} — 删除书籍](#delete-apiv1booksbook_id--删除书籍)
   - [PUT /api/v1/books/{book_id}/mark — 标记/取消标记](#put-apiv1booksbook_idmark--标记取消标记)
   - [GET /api/v1/books/{book_id}/chapters — 获取章节列表](#get-apiv1booksbook_idchapters--获取章节列表)
   - [GET /api/v1/books/{book_id}/chapters/{chapter_index} — 获取章节内容](#get-apiv1booksbook_idchapterschapter_index--获取章节内容)
   - [GET /api/v1/books/{book_id}/progress — 获取阅读进度](#get-apiv1booksbook_idprogress--获取阅读进度)
   - [PUT /api/v1/books/{book_id}/progress — 更新阅读进度](#put-apiv1booksbook_idprogress--更新阅读进度)
   - [POST /api/v1/ai/search — AI 语义搜索](#post-apiv1aisearch--ai-语义搜索)
   - [POST /api/v1/ai/summary/{book_id} — 触发 AI 摘要生成](#post-apiv1aisummarybook_id--触发-ai-摘要生成)
   - [GET /api/v1/ai/summary/{book_id} — 获取 AI 摘要](#get-apiv1aisummarybook_id--获取-ai-摘要)
4. [搜索接口](#4-搜索接口)
   - [GET /api/v1/search — 书架内搜索](#get-apiv1search--书架内搜索)
   - [GET /api/v1/search/external — 外部源站搜索](#get-apiv1searchexternal--外部源站搜索)
   - [GET /api/v1/sources — 获取可用源站列表](#get-apiv1sources--获取可用源站列表)
5. [抓取与下载接口](#5-抓取与下载接口)
   - [POST /api/v1/crawl/check-url — 检查 URL 连通性](#post-apiv1crawlcheck-url--检查-url-连通性)
   - [POST /api/v1/books/{book_id}/crawl — 触发抓取](#post-apiv1booksbook_idcrawl--触发抓取)
   - [GET /api/v1/books/{book_id}/crawl-status — 查询抓取进度](#get-apiv1booksbook_idcrawl-status--查询抓取进度)
   - [GET /api/v1/books/{book_id}/download — 下载电子书](#get-apiv1booksbook_iddownload--下载电子书)
6. [自定义源站接口](#6-自定义源站接口)
   - [GET /api/v1/crawl-sources — 列出自定义源站](#get-apiv1crawl-sources--列出自定义源站)
   - [POST /api/v1/crawl-sources — 创建自定义源站](#post-apiv1crawl-sources--创建自定义源站)
   - [GET /api/v1/crawl-sources/{id} — 获取自定义源站详情](#get-apiv1crawl-sourcesid--获取自定义源站详情)
   - [PUT /api/v1/crawl-sources/{id} — 更新自定义源站](#put-apiv1crawl-sourcesid--更新自定义源站)
   - [DELETE /api/v1/crawl-sources/{id} — 删除自定义源站](#delete-apiv1crawl-sourcesid--删除自定义源站)
   - [POST /api/v1/crawl-sources/test — 测试自定义源站规则](#post-apiv1crawl-sourcestest--测试自定义源站规则)
7. [系统接口](#7-系统接口)
   - [GET /health — 健康检查](#get-health--健康检查)
8. [附录：数据字典](#8-附录数据字典)
   - [8.1 书籍抓取状态](#81-书籍抓取状态)
   - [8.2 通用抓取规则说明](#82-通用抓取规则说明)
   - [8.3 自定义源站规则配置](#83-自定义源站规则配置)
   - [8.4 JWT Token 规范](#84-jwt-token-规范)
   - [8.5 密码规则](#85-密码规则)
   - [8.6 认证流程图](#86-认证流程图)

---

## 1. 通用说明

### 1.1 统一响应格式

所有接口均返回以下 JSON 结构：

```json
{
  "success": true,
  "data": { "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "email": "user@example.com" },
  "meta": { "page": 1, "page_size": 20, "total": 100, "total_pages": 5 },
  "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `boolean` | 请求是否成功。`true` 为成功，`false` 为失败 |
| `data` | `any` / `null` | 业务数据。成功时返回对应内容，失败时为 `null` |
| `meta` | `object` / `null` | 分页元信息，仅分页接口返回；非分页接口为 `null` |
| `error` | `string` / `null` | 错误描述。成功时为 `null`，失败时包含人类可读的错误信息（中文） |

**分页元信息 `PaginationMeta`**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | `int` | `1` | 当前页码 |
| `page_size` | `int` | `20` | 每页条数 |
| `total` | `int` | `0` | 总记录数 |
| `total_pages` | `int` | `0` | 总页数 |

### 1.2 认证方式

除注册、登录、`/health` 健康检查和 `/auth/refresh`（使用 Refresh Token）外，
所有接口均需在请求头中携带 JWT Access Token：

```
Authorization: Bearer <access_token>
```

- **Access Token** 有效期：2 小时（签发后不可吊销，过期后用 Refresh Token 换新）
- **Refresh Token** 有效期：7 天（采用轮转策略，每次刷新时旧 Token 自动吊销并签发新 Token）
- 获取方式：登录成功时返回 `access_token` 和 `refresh_token`

### 1.3 错误处理

所有错误均返回统一格式，HTTP 状态码由具体错误类型决定，`error` 字段携带中文描述。

**示例 — 401 未认证**：

```json
{
  "success": false,
  "data": null,
  "meta": null,
  "error": "认证方式错误，请使用 Bearer Token"
}
```

**示例 — 422 参数验证失败**：

```json
{
  "success": false,
  "data": null,
  "meta": null,
  "error": "请求参数验证失败: body → email: 邮箱格式不正确; body → password: 密码必须包含至少一个数字"
}
```

**示例 — 500 服务器内部错误**：

```json
{
  "success": false,
  "data": null,
  "meta": null,
  "error": "服务器内部错误"
}
```

### 1.4 HTTP 状态码速查

| 状态码 | 含义 | 触发场景 |
|--------|------|----------|
| `200` | 成功 | GET、PUT、DELETE 请求成功；添加书籍、创建源站等 POST 接口也返回 200 |
| `201` | 已创建 | 仅 `POST /auth/register` 用户注册成功时返回 |
| `400` | 请求错误 | 业务逻辑异常（如缺少 source_url、章节序号越界） |
| `401` | 未认证 | 缺少或无效的 Authorization Header、登录失败、Token 无效或已过期 |
| `404` | 未找到 | 资源不存在或已被删除 |
| `409` | 冲突 | 邮箱已注册、书籍正在抓取中 |
| `422` | 参数验证失败 | 请求体不符合 Schema 定义 |
| `500` | 服务器内部错误 | 未预期的运行时异常 |

---

## 2. 认证接口

所有认证接口的基础路径为 `/api/v1/auth`。

### POST /api/v1/auth/register — 用户注册

使用邮箱和密码创建新账号。

**请求**

```
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "Pass1234"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `email` | `string` | 是 | 5-255 字符，需含 `@` 和域名后缀 | 邮箱地址，自动转为小写并去除首尾空格 |
| `password` | `string` | 是 | 8-64 字符，必须同时包含字母和数字 | 登录密码 |

**成功响应 `201`**

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "email": "user@example.com"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `409` | `该邮箱已注册` |
| `422` | `请求参数验证失败: body → email: 邮箱格式不正确` |
| `422` | `请求参数验证失败: body → password: 密码长度需为 8-64 位` |
| `422` | `请求参数验证失败: body → password: 密码必须包含至少一个字母` |
| `422` | `请求参数验证失败: body → password: 密码必须包含至少一个数字` |

---

### POST /api/v1/auth/login — 用户登录

验证邮箱和密码，返回 JWT Token Pair。

**请求**

```
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "Pass1234"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `email` | `string` | 是 | 注册时使用的邮箱（自动转小写并去空格） |
| `password` | `string` | 是 | 登录密码 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwidHlwZSI6ImFjY2VzcyJ9.signature",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwidHlwZSI6InJlZnJlc2gifQ.signature",
    "token_type": "bearer"
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `access_token` | `string` | JWT Access Token，有效期 2 小时 |
| `refresh_token` | `string` | JWT Refresh Token，有效期 7 天 |
| `token_type` | `string` | 固定返回 `"bearer"` |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `401` | `邮箱或密码错误` |
| `422` | `请求参数验证失败: body → email: ...` |

---

### POST /api/v1/auth/refresh — 刷新 Token

使用 Refresh Token 换取新的 Token Pair（**轮转策略**：旧 Refresh Token 立即吊销，签发新的 Access Token 和 Refresh Token）。

> **安全说明**：每次成功刷新后，旧的 Refresh Token 即失效。建议客户端在收到新 Token 后立即替换本地存储的旧 Token。

**请求**

```
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwidHlwZSI6InJlZnJlc2gifQ.signature"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `refresh_token` | `string` | 是 | 当前持有的 Refresh Token |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwidHlwZSI6ImFjY2VzcyJ9.new_access_signature",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkIiwidHlwZSI6InJlZnJlc2gifQ.new_refresh_signature",
    "token_type": "bearer"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `401` | `Refresh Token 无效或已过期，请重新登录` |
| `401` | `Refresh Token 已被吊销或不存在，请重新登录` |
| `401` | `请使用 Refresh Token 刷新` / `Token 格式无效` |

---

### PUT /api/v1/auth/password — 修改密码

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

修改当前登录用户的密码（需提供旧密码验证身份）。

**请求**

```
PUT /api/v1/auth/password
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "old_password": "Pass1234",
  "new_password": "NewPass5678"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `old_password` | `string` | 是 | 至少 1 字符 | 当前密码，用于身份验证 |
| `new_password` | `string` | 是 | 8-64 字符，必须同时包含字母和数字 | 新密码 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": null,
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `400` | `当前密码不正确` |
| `422` | `请求参数验证失败: body → new_password: 密码长度需为 8-64 位` |
| `422` | `请求参数验证失败: body → new_password: 密码必须包含至少一个字母` |
| `422` | `请求参数验证失败: body → new_password: 密码必须包含至少一个数字` |

---

## 3. 书架接口

所有书架接口的基础路径为 `/api/v1`。

### GET /api/v1/books — 获取书架列表

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

获取当前用户的书籍列表，支持分页。

**排序规则（v1.2）**：已标记书籍置顶（按标记时间倒序），未标记书籍按添加时间倒序。

**请求**

```
GET /api/v1/books?page=1&page_size=20&marked=true
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `page` | `int` | 否 | `1` | >= 1 | 页码 |
| `page_size` | `int` | 否 | `20` | 1-500 | 每页条数 |
| `marked` | `boolean` | 否 | 无 | `true`/`false` | v1.2 新增：仅筛选已标记的书籍 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "诡秘之主",
      "author": "爱潜水的乌贼",
      "source_url": null,
      "status": "idle",
      "chapter_count": 0,
      "has_epub": false,
      "has_txt": false,
      "is_marked": false,
      "marked_at": null,
      "ai_summary": null,
      "ai_summary_at": null,
      "added_at": "2026-07-25T12:00:00"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  },
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `id` | `string` | 书籍 UUID |
| `title` | `string` | 书名 |
| `author` | `string` | 作者 |
| `source_url` | `string` / `null` | 源网站 URL |
| `status` | `string` | 抓取状态：`idle`（待抓取）、`crawling`（抓取中）、`done`（已完成）、`failed`（失败） |
| `chapter_count` | `int` | 已抓取章节数 |
| `has_epub` | `bool` | 是否已生成 EPUB 文件 |
| `has_txt` | `bool` | 是否已生成 TXT 文件（v1.2 新增返回字段） |
| `is_marked` | `bool` | 是否已标记（v1.2 新增） |
| `marked_at` | `string` / `null` | 标记时间（v1.2 新增，用于置顶排序） |
| `ai_summary` | `string` / `null` | AI 生成的摘要（v1.3 新增） |
| `ai_summary_at` | `string` / `null` | AI 摘要生成时间（v1.3 新增） |
| `added_at` | `string`（ISO 8601） | 添加时间 |

**空书架响应**

```json
{
  "success": true,
  "data": [],
  "meta": { "page": 1, "page_size": 20, "total": 0, "total_pages": 0 },
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `401` | `认证方式错误，请使用 Bearer Token` / `Token 无效或已过期，请重新登录` |

---

### POST /api/v1/books — 添加书籍

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

手动添加一本书到书架。

**请求**

```
POST /api/v1/books
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "title": "诡秘之主",
  "author": "爱潜水的乌贼",
  "source_url": "https://example.com/novel/123"
}
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `title` | `string` | 是 | - | 1-500 字符 | 书名 |
| `author` | `string` | 否 | `"未知"` | 最长 255 字符 | 作者 |
| `source_url` | `string` | 否 | `null` | 最长 2048 字符 | 源网站链接 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "诡秘之主",
    "author": "爱潜水的乌贼",
    "source_url": "https://example.com/novel/123",
    "status": "idle",
    "chapter_count": 0,
    "has_epub": false,
    "has_txt": false,
    "is_marked": false,
    "marked_at": null,
    "ai_summary": null,
    "ai_summary_at": null,
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `422` | `请求参数验证失败: body → title: ...` |

---

### GET /api/v1/books/{book_id} — 查看书籍详情

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

获取单本书的详细信息。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "诡秘之主",
    "author": "爱潜水的乌贼",
    "source_url": "https://example.com/novel/123",
    "status": "idle",
    "chapter_count": 0,
    "has_epub": false,
    "has_txt": false,
    "is_marked": false,
    "marked_at": null,
    "ai_summary": null,
    "ai_summary_at": null,
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |

---

### DELETE /api/v1/books/{book_id} — 删除书籍

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

从书架中软删除指定书籍（`deleted_at` 标记删除，书籍记录仍保留在数据库中）。
同时会物理删除该书的全部章节正文和阅读进度记录，并清理本地生成的 `.epub` / `.txt` 文件。

**请求**

```
DELETE /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`**

```json
{
  "success": true,
  "data": null,
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |

---

### PUT /api/v1/books/{book_id}/mark — 标记/取消标记

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.2 新增

切换书籍的标记状态（星标）。已标记的书籍在书架中置顶展示。

**请求**

```
PUT /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/mark
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`** — 返回更新后的书籍信息（结构同 `GET /api/v1/books` 的 data[] 元素）：

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "诡秘之主",
    "author": "爱潜水的乌贼",
    "source_url": "https://www.example.com/book/123/",
    "status": "done",
    "chapter_count": 1430,
    "has_epub": true,
    "has_txt": true,
    "is_marked": true,
    "marked_at": "2026-08-05T10:00:00",
    "ai_summary": null,
    "ai_summary_at": null,
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |

---

### GET /api/v1/books/{book_id}/chapters — 获取章节列表

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.2 新增

获取书籍的完整章节列表（仅摘要，不含正文），按章节序号升序排列（v1.3.1 起为卷重置感知排序，详见 [8.2 通用抓取规则说明](#82-通用抓取规则说明)）。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/chapters
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    { "index": 1, "title": "第一章 开端", "word_count": 3021 },
    { "index": 2, "title": "第二章 变故", "word_count": 2856 }
  ],
  "meta": null,
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `index` | `int` | 章节序号（从 1 开始） |
| `title` | `string` | 章节标题 |
| `word_count` | `int` | 章节字数 |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |

---

### GET /api/v1/books/{book_id}/chapters/{chapter_index} — 获取章节内容

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.2 新增

获取指定章节的正文内容。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/chapters/1
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |
| `chapter_index` | `int`（path） | 是 | 章节序号（从 1 开始） |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "index": 1,
    "title": "第一章 开端",
    "content": "周明远推开窗户，晨雾中的城市……",
    "word_count": 3021
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `第 1 章不存在` / `书籍不存在或已被删除` |

---

### GET /api/v1/books/{book_id}/progress — 获取阅读进度

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.2 新增

获取用户在某本书的阅读进度；无记录时返回默认值（第 1 章）。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/progress
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "book_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "last_chapter_index": 42,
    "updated_at": "2026-08-10T20:15:00"
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `book_id` | `string` | 书籍 UUID |
| `last_chapter_index` | `int` | 最后阅读的章节序号 |
| `updated_at` | `string` / `null` | 最后更新时间（无记录时为 `null`） |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |

---

### PUT /api/v1/books/{book_id}/progress — 更新阅读进度

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.2 新增

更新用户在某本书的阅读进度（不存在则创建，即 upsert）。

**请求**

```
PUT /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/progress
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "chapter_index": 42
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chapter_index` | `int` | 是 | 章节序号，必须在 1 到本书章节总数之间 |

**成功响应 `200`** — 返回结构同 `GET /progress`。

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `400` | `章节序号必须在 1 到 N 之间` |
| `404` | `书籍不存在或已被删除` |

---

### POST /api/v1/ai/search — AI 语义搜索

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.3 新增

使用自然语言在书架中语义匹配书籍（如"最近看的那本修仙小说"）。后端将书架数据发给 Dify 工作流进行 LLM 语义匹配，Dify 不可用时自动降级为本地关键词搜索。

**请求**

```
POST /api/v1/ai/search
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "query": "最近看的那本修仙小说"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `query` | `string` | 是 | 2-500 字符 | 自然语言搜索描述 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "book_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "凡人修仙传",
      "author": "忘语",
      "match_reason": "书名包含「修仙」，且已有阅读进度",
      "score": 92
    }
  ],
  "meta": null,
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `book_id` | `string` | 书籍 UUID |
| `title` | `string` | 书名 |
| `author` | `string` | 作者 |
| `match_reason` | `string` | 匹配原因说明（中文） |
| `score` | `int` | 匹配分数（0-100） |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `400` | `搜索关键词至少需要 2 个字符` |
| `401` | `认证方式错误，请使用 Bearer Token` / `Token 无效或已过期，请重新登录` |

---

### POST /api/v1/ai/summary/{book_id} — 触发 AI 摘要生成

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.3 新增

启动后台任务生成书籍摘要（情节摘要 + 角色列表 + 风格标签）。生成完成后自动存储，通过 GET 接口获取。已生成过摘要的书籍直接返回现有摘要。

**请求**

```
POST /api/v1/ai/summary/a1b2c3d4-e5f6-7890-abcd-ef1234567890
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "status": "queued",
    "ai_summary": null,
    "ai_summary_at": null,
    "error": null
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `status` | `string` | 状态：`queued`（排队中）/ `generating`（生成中）/ `running`（已有任务在进行中）/ `done`（完成）/ `failed`（失败）/ `none`（从未生成） |
| `ai_summary` | `string` / `null` | 已生成的摘要内容 |
| `ai_summary_at` | `string` / `null` | 摘要生成时间 |
| `error` | `string` / `null` | 错误信息 |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `400` | `该书暂无章节，请先抓取内容` |
| `404` | `书籍不存在或已被删除` |

---

### GET /api/v1/ai/summary/{book_id} — 获取 AI 摘要

> 🔒 **需要认证**：`Authorization: Bearer <access_token>` ｜ v1.3 新增

获取书籍的 AI 摘要。已生成则直接返回；生成中则返回当前进度；从未生成过返回 `status="none"`。前端通常以 3 秒间隔轮询此接口。

**请求**

```
GET /api/v1/ai/summary/a1b2c3d4-e5f6-7890-abcd-ef1234567890
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "status": "done",
    "ai_summary": "《凡人修仙传》是一部仙侠题材小说……",
    "ai_summary_at": "2026-08-12T09:30:00",
    "error": null
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在` |

---

## 4. 搜索接口

### GET /api/v1/search — 书架内搜索

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

在当前用户书架中按**书名或作者**进行模糊搜索（v1.2 起支持双字段匹配）。

**请求**

```
GET /api/v1/search?q=诡秘&page=1&page_size=20
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `q` | `string` | 是 | - | 最少 1 字符 | 搜索关键词，同时匹配书名和作者（匹配任一字段即返回） |
| `page` | `int` | 否 | `1` | >= 1 | 页码 |
| `page_size` | `int` | 否 | `20` | 1-500 | 每页条数 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "诡秘之主",
      "author": "爱潜水的乌贼",
      "source_url": null,
      "status": "idle",
      "chapter_count": 0,
      "has_epub": false,
      "has_txt": false,
      "added_at": "2026-07-25T12:00:00"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 },
  "error": null
}
```

---

### GET /api/v1/search/external — 外部源站搜索

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

在已配置的网络小说源站中搜索小说。支持指定源站搜索或遍历所有已配置源站，返回合并去重后的搜索结果。

**请求**

```
GET /api/v1/search/external?q=诡秘&source_id=1&search_limit=30
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `q` | `string` | 是 | - | 最少 1 字符 | 搜索关键词 |
| `source_id` | `int` | 否 | `null` | - | 指定源站 ID，不传则搜索所有源站 |
| `search_limit` | `int` | 否 | `30` | 1-100 | 每个源站最大结果数 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "title": "诡秘之主",
      "author": "爱潜水的乌贼",
      "source_url": "https://www.example.com/book/123",
      "source_name": "香书小说",
      "source_id": 1,
      "category": "玄幻",
      "word_count": "300万字",
      "status": "连载中",
      "latest_chapter": "第一千三百章 结局",
      "last_update_time": "2026-07-25"
    }
  ],
  "meta": { "page": 1, "page_size": 1, "total": 1, "total_pages": 1 },
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `title` | `string` | 书名 |
| `author` | `string` | 作者 |
| `source_url` | `string` | 书籍详情页/目录页 URL |
| `source_name` | `string` | 源站名称 |
| `source_id` | `int` | 源站 ID |
| `category` | `string` | 分类 |
| `word_count` | `string` | 字数 |
| `status` | `string` | 连载状态 |
| `latest_chapter` | `string` | 最新章节标题 |
| `last_update_time` | `string` | 最新更新时间 |

---

### GET /api/v1/sources — 获取可用源站列表

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

返回所有已配置的小说源站信息（包括内置规则和自定义规则）。

**请求**

```
GET /api/v1/sources
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "id": 0,
      "name": "笔趣阁(biquh)",
      "url": "https://www.biquh.com/",
      "has_search": false,
      "is_custom": false,
      "comment": "搜索为单结果重定向，不适合外部搜索；抓取可用"
    },
    {
      "id": 1,
      "name": "香书小说",
      "url": "http://www.xbiqugu.la/",
      "has_search": true,
      "is_custom": false,
      "comment": ""
    }
  ],
  "meta": null,
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `id` | `int` | 源站 ID |
| `name` | `string` | 源站名称 |
| `url` | `string` | 源站域名 |
| `has_search` | `bool` | 是否支持外部搜索 |
| `is_custom` | `bool` | 是否为用户自定义源站（v1.2 新增） |
| `comment` | `string` | 备注说明 |

> **注意**：本接口为非分页接口，`meta` 返回 `null`。

> **通用抓取说明**：即使源站不在列表中，系统也会自动使用内置通用解析策略尝试抓取任意小说网站的 URL（详见 [8.2 通用抓取规则说明](#82-通用抓取规则说明)）。源站列表中的规则主要用于提高特定网站的抓取精确度。

---

## 5. 抓取与下载接口

> **通用抓取支持**：v1.1 起，系统支持抓取任意小说网站 URL，不限于预配置源站。当 URL 匹配不到预配置规则时，自动使用通用解析策略尝试提取章节和正文。详见 [8.2 通用抓取规则说明](#82-通用抓取规则说明)。

### POST /api/v1/crawl/check-url — 检查 URL 连通性

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

在触发抓取之前检查源站 URL 是否可达，返回连通性检测结果和修复建议。

**请求**

```
POST /api/v1/crawl/check-url
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "url": "https://www.example.com/book/123"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `url` | `string` | 是 | 1-2048 字符 | 要检查的小说源站 URL |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "reachable": true,
    "status_code": 200,
    "content_length": 45678,
    "error_message": null,
    "suggested_fix": null
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `reachable` | `bool` | URL 是否可达 |
| `status_code` | `int` / `null` | HTTP 状态码 |
| `content_length` | `int` | 响应内容长度 |
| `error_message` | `string` / `null` | 错误描述 |
| `suggested_fix` | `string` / `null` | 修复建议 |

---

### POST /api/v1/books/{book_id}/crawl — 触发抓取

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

对指定书籍触发内容抓取任务。系统将在后台异步执行：连接预检 → 获取章节列表 → 并发抓取正文 → 写入数据库 → 生成 EPUB 和 TXT 文件。

**请求**

```
POST /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/crawl
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "诡秘之主",
    "author": "爱潜水的乌贼",
    "source_url": "https://example.com/novel/123",
    "status": "crawling",
    "chapter_count": 0,
    "has_epub": false,
    "has_txt": false,
    "is_marked": false,
    "marked_at": null,
    "ai_summary": null,
    "ai_summary_at": null,
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `data` | `object` | 书籍完整信息，字段结构同书架列表项：`id` / `title` / `author` / `source_url` / `status` / `chapter_count` / `has_epub` / `has_txt` / `is_marked` / `marked_at` / `ai_summary` / `ai_summary_at` / `added_at` |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |
| `400` | `缺少 source_url，无法抓取` |
| `409` | `该书籍正在抓取中，请勿重复操作` |

> **抓取流程**：
> 1. 系统先检查 URL 是否匹配预配置源站规则，匹配则使用精确规则
> 2. 未匹配时自动使用通用解析策略（内置 CSS 选择器枚举，覆盖常见小说站结构）
> 3. 章节列表按卷重置感知算法排序（v1.3.1）：多卷小说每卷重新从「第一章」计数时保持阅读顺序，详见 [8.2 通用抓取规则说明](#82-通用抓取规则说明)
> 4. 抓取完成后自动生成 EPUB 和 TXT 两种格式的电子书文件，章节顺序与数据库一致

---

### GET /api/v1/books/{book_id}/crawl-status — 查询抓取进度

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

返回指定书籍的实时抓取进度。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/crawl-status
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "status": "crawling",
    "chapter_count": 42,
    "total_chapters": 500,
    "percentage": 8.4
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `status` | `string` | 抓取状态：`idle` / `crawling` / `done` / `failed` |
| `chapter_count` | `int` | 已抓取章节数 |
| `total_chapters` | `int` / `null` | 总章节数（抓取中尚未探测到时为 `null`，`done` 时等于 `chapter_count`） |
| `error` | `string` / `null` | v1.1：失败时提供具体错误信息 |
| `percentage` | `float` | 抓取进度百分比（0.0 - 100.0） |

---

### GET /api/v1/books/{book_id}/download — 下载电子书

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

下载已生成的电子书文件。支持 EPUB 和 TXT 两种格式。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download?format=epub
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `book_id` | `string`（path） | 是 | - | 书籍 UUID |
| `format` | `string`（query） | 否 | `epub` | 下载格式：`epub` 或 `txt` |

**成功响应 `200`**

```
Content-Type: application/epub+zip  (或 text/plain; charset=utf-8)
Content-Disposition: attachment; filename="诡秘之主-爱潜水的乌贼.epub"

<binary file data>
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `该书籍尚未生成 EPUB 文件，请先抓取` / `该书籍尚未生成 TXT 文件，请先抓取` |
| `404` | `EPUB 文件已被清理，请重新抓取` / `TXT 文件已被清理，请重新抓取` |

---

## 6. 自定义源站接口

> **功能说明**：用户可以创建和管理自己的源站抓取规则（CSS 选择器配置），用于提高特定网站的抓取精确度。未配置的网站将自动使用内置通用解析策略。规则以 JSON 格式存储，支持目录页、章节内容页的选择器配置。

所有自定义源站接口的基础路径为 `/api/v1/crawl-sources`。

### GET /api/v1/crawl-sources — 列出自定义源站

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

获取当前用户创建的所有自定义源站规则。

**请求**

```
GET /api/v1/crawl-sources
Authorization: Bearer <access_token>
```

**成功响应 `200`**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "笔趣阁镜像站",
      "url": "https://www.bbiquge.net/",
      "rule_json": "{\"toc\":{\"item\":\"#list > dl > dd > a\"},\"chapter\":{\"title\":\"h1\",\"content\":\"#content\"}}",
      "is_public": false,
      "created_at": "2026-07-26T10:00:00"
    }
  ],
  "meta": null,
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `id` | `int` | 源站 ID |
| `name` | `string` | 源站名称 |
| `url` | `string` | 源站域名/首页 URL |
| `rule_json` | `string` | JSON 格式的抓取规则 |
| `is_public` | `bool` | 是否公开 |
| `created_at` | `string` | 创建时间 |

---

### POST /api/v1/crawl-sources — 创建自定义源站

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

创建一条自定义源站抓取规则。

**请求**

```
POST /api/v1/crawl-sources
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "name": "笔趣阁镜像站",
  "url": "https://www.bbiquge.net/",
  "rule_json": "{\"toc\":{\"item\":\"#list > dl > dd > a\"},\"chapter\":{\"title\":\"h1\",\"content\":\"#content\",\"filterTxt\":\"\\\\(本章完\\\\)\"}}"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `name` | `string` | 是 | 1-200 字符 | 源站名称 |
| `url` | `string` | 是 | 1-2048 字符 | 源站域名/首页 URL |
| `rule_json` | `string` | 是 | 最少 2 字符，需为有效 JSON | JSON 格式的抓取规则 |

**成功响应 `200`**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "笔趣阁镜像站",
    "url": "https://www.bbiquge.net/",
    "rule_json": "{...}",
    "is_public": false,
    "created_at": "2026-07-26T10:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `400` | `rule_json 不是有效的 JSON 格式: ...` |
| `422` | `请求参数验证失败: body → name: ...` |

---

### GET /api/v1/crawl-sources/{id} — 获取自定义源站详情

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

获取单个自定义源站规则的完整信息。

**请求**

```
GET /api/v1/crawl-sources/1
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `int`（path） | 是 | 源站 ID |

**成功响应 `200`**（格式同列表响应中的单个元素）

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `自定义源站不存在` |

---

### PUT /api/v1/crawl-sources/{id} — 更新自定义源站

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

更新自定义源站规则。所有字段均可选，只更新传入的字段。

**请求**

```
PUT /api/v1/crawl-sources/1
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "name": "笔趣阁新镜像",
  "url": "https://www.biquge.new/",
  "rule_json": "{...}",
  "is_public": false
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `int`（path） | 是 | 源站 ID |
| `name` | `string` | 否 | 新的源站名称 |
| `url` | `string` | 否 | 新的源站 URL |
| `rule_json` | `string` | 否 | 新的抓取规则 JSON |
| `is_public` | `bool` | 否 | 是否公开 |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `自定义源站不存在` |
| `400` | `rule_json 不是有效的 JSON 格式: ...` |

---

### DELETE /api/v1/crawl-sources/{id} — 删除自定义源站

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

删除一条自定义源站规则。

**请求**

```
DELETE /api/v1/crawl-sources/1
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `int`（path） | 是 | 源站 ID |

**成功响应 `200`**

```json
{
  "success": true,
  "data": null,
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `自定义源站不存在` |

---

### POST /api/v1/crawl-sources/test — 测试自定义源站规则

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

使用给定的规则尝试解析指定 URL 的章节列表，返回章节总数和前 5 条章节信息，帮助验证规则配置是否有效。

**请求**

```
POST /api/v1/crawl-sources/test
Content-Type: application/json
Authorization: Bearer <access_token>
```

```json
{
  "url": "https://www.bbiquge.net/book/12345/",
  "rule_json": "{\"toc\":{\"item\":\"#list > dl > dd > a\"},\"chapter\":{\"title\":\"h1\",\"content\":\"#content\"}}"
}
```

| 参数 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `url` | `string` | 是 | 1-2048 字符 | 要测试的小说目录页 URL |
| `rule_json` | `string` | 是 | 最少 2 字符，需为有效 JSON | JSON 格式的抓取规则 |

**成功响应 `200`（规则有效）**

```json
{
  "success": true,
  "data": {
    "success": true,
    "chapter_count": 1500,
    "sample_chapters": [
      {"title": "第一章 穿越", "url": "https://www.bbiquge.net/book/12345/1.html"},
      {"title": "第二章 觉醒", "url": "https://www.bbiquge.net/book/12345/2.html"},
      {"title": "第三章 出发", "url": "https://www.bbiquge.net/book/12345/3.html"}
    ],
    "error": null
  },
  "meta": null,
  "error": null
}
```

**成功响应 `200`（规则无效）**

```json
{
  "success": true,
  "data": {
    "success": false,
    "chapter_count": 0,
    "sample_chapters": [],
    "error": "选择器 '#list > dl > dd > a' 未匹配到任何章节链接"
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `success` | `bool` | 规则是否有效 |
| `chapter_count` | `int` | 解析到的章节总数 |
| `sample_chapters` | `array` | 前 5 条章节信息（含 `title` 和 `url`） |
| `error` | `string` / `null` | 失败时的错误描述 |

---

## 7. 系统接口

### GET /health — 健康检查

无需认证，返回服务运行状态。

**请求**

```
GET /health
```

**成功响应 `200`**

```json
{
  "status": "ok",
  "version": "1.3.0"
}
```

> **说明**：该接口不走统一 `ApiResponse` 格式，直接返回简单 JSON 对象。

---

## 8. 附录：数据字典

### 8.1 书籍抓取状态

| 状态值 | 含义 | 说明 |
|--------|------|------|
| `idle` | 待抓取 | 初始状态，尚未触发抓取 |
| `crawling` | 抓取中 | 爬虫正在工作 |
| `done` | 已完成 | 内容抓取并生成 EPUB/TXT 成功 |
| `failed` | 失败 | 抓取过程出错 |

### 8.2 通用抓取规则说明

当用户添加小说的 `source_url` 域名与预配置源站列表不匹配时，系统会自动使用**通用解析策略**，无需手动配置规则。

**工作原理**：

1. 系统使用内置的常见 CSS 选择器集合，按优先级尝试匹配章节列表区域
   - `#list`、`.listmain`、`.chapterlist`、`.chapter-list`、`#chapters`、`.catalog` 等
2. 如果上述选择器均未匹配，则尝试通过 URL 模式识别章节链接
   - 如 `/\d+\.html`、`/chapter/`、`/read/` 等
3. 对每个章节页面，同样使用常见选择器提取正文
   - `#content`、`#chaptercontent`、`#TextContent`、`.read-content` 等
4. 支持章节翻页和目录翻页，自动处理多页结构
5. 章节排序（v1.3.1）：章节号支持中文数字（「第十一章」与「第11章」等价）；采用卷重置感知排序 —— 按章节序号回落点切段（回落 = 新一卷开始），段内保持源站原始顺序，段间按最小序号稳定升序；多卷小说（如《诛仙》，每卷从「第一章」重新计数）的阅读顺序不被破坏，「序幕」「尾声」等无序号章节固定在原位置

**适用性**：通用规则适用于大多数模板化的网络小说站（特别是笔趣阁系列各类镜像站）。如果通用规则在某个特定网站上效果不佳，可以通过创建自定义源站规则来提高精确度。

### 8.3 自定义源站规则配置

自定义源站规则以 JSON 格式配置，参考 `backend/rules/main.json` 的格式。常用字段如下：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `toc.item` | `string` | 目录页章节链接选择器（CSS/XPath） | `"#list > dl > dd > a"` |
| `toc.pagination` | `bool` | 目录是否有分页 | `true` |
| `toc.nextPage` | `string` | 目录翻页按钮选择器 | `"#pagelink > a.next"` |
| `chapter.title` | `string` | 章节内容页标题选择器 | `".bookname > h1"` |
| `chapter.content` | `string` | 章节正文内容选择器 | `"#content"` |
| `chapter.filterTxt` | `string` | 需过滤的广告文本正则（\| 分隔） | `"记住本站网址[^\n]*\|\\\\(本章完\\\\)"` |
| `chapter.filterTag` | `string` | 需移除的 HTML 标签（逗号分隔，只去标签壳、保留文字） | `"script, div, ins"` |
| `chapter.filterElement` | `string` | 需整块删除的推广元素选择器（逗号分隔，元素及内部文字一并移除） | `"#content_tip, #content > p"` |
| `chapter.pagination` | `bool` | 章节内容是否有翻页 | `true` |
| `chapter.nextPage` | `string` | 章节翻页按钮选择器 | `"#next_url"` |
| `chapter.base64Decode` | `bool` | 正文是否被 base64 编码 | `true` |

### 8.4 JWT Token 规范

| 属性 | Access Token | Refresh Token |
|------|-------------|---------------|
| 有效期 | 2 小时 | 7 天 |
| `sub` 字段 | 用户 UUID | 用户 UUID |
| `type` 字段 | `"access"` | `"refresh"` |
| 签名算法 | HS256 | HS256 |
| 存储方式 | 客户端内存/Storage | 服务端 `refresh_tokens` 表存 SHA-256 哈希 |

### 8.5 密码规则

| 约束 | 值 |
|------|-----|
| 最小长度 | 8 位 |
| 最大长度 | 64 位 |
| 必含字符 | 至少一个字母 **且** 至少一个数字 |
| 存储方式 | bcrypt，salt rounds = 12 |

### 8.6 认证流程图

```
注册 → 登录 → 获得 Access Token + Refresh Token
                     │
                     ├──> 携带 Access Token 调用业务接口
                     │    （2 小时内有效）
                     │
                     └──> Access Token 过期后
                          POST /api/v1/auth/refresh
                          使用 Refresh Token 换取新 Token Pair
                          （旧 Refresh Token 自动吊销）
```

---

> **文档版本**：v1.3 | **最后更新**：2026-08-16
> 
> **v1.2/v1.3 更新内容**：
> - 新增标记/置顶接口 `PUT /api/v1/books/{book_id}/mark`（v1.2）
> - 新增章节接口 `GET /chapters` 与 `GET /chapters/{chapter_index}`（v1.2）
> - 新增阅读进度接口 `GET/PUT /progress`（v1.2）
> - 新增 AI 语义搜索 `POST /api/v1/ai/search`（v1.3）
> - 新增 AI 摘要接口 `POST/GET /api/v1/ai/summary/{book_id}`（v1.3）
> - 书架列表新增 `marked` 查询参数；响应字段补充 `has_txt`/`is_marked`/`marked_at`/`ai_summary`/`ai_summary_at`
> - 书架内搜索 `q` 参数同时匹配书名与作者（v1.2 增强）
> - 修正认证接口错误状态码（注册 409、登录/刷新 401）与各接口文案
