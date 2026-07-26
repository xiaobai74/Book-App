# 小说管理App — API 文档

> **版本**：v1.0
> **基础地址**：`http://localhost:8000`
> **接口协议**：RESTful，请求/响应均为 JSON
> **在线文档**：[Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)

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
4. [搜索接口](#4-搜索接口)
   - [GET /api/v1/search — 搜索小说](#get-apiv1search--搜索小说)
5. [抓取与 EPUB 接口](#5-抓取与-epub-接口)
   - [POST /api/v1/books/{book_id}/crawl — 触发抓取](#post-apiv1booksbook_idcrawl--触发抓取)
   - [GET /api/v1/books/{book_id}/crawl-status — 查询抓取进度](#get-apiv1booksbook_idcrawl-status--查询抓取进度)
   - [GET /api/v1/books/{book_id}/download — 下载 EPUB](#get-apiv1booksbook_iddownload--下载-epub)
6. [系统接口](#6-系统接口)
   - [GET /health — 健康检查](#get-health--健康检查)
7. [附录：数据字典](#7-附录数据字典)

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

除注册和登录外，所有接口均需在请求头中携带 JWT Access Token：

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
  "error": "未提供认证凭证"
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
| `200` | 成功 | GET、PUT、DELETE 请求成功 |
| `201` | 已创建 | POST 请求创建资源成功 |
| `400` | 请求错误 | 业务逻辑异常（如邮箱已注册、密码错误） |
| `401` | 未认证 | 缺少或无效的 Authorization Header |
| `404` | 未找到 | 资源不存在或 EPUB 文件未生成 |
| `409` | 冲突 | 重复添加同名书籍 |
| `422` | 参数验证失败 | 请求体不符合 Schema 定义 |
| `500` | 服务器内部错误 | 未预期的运行时异常 |
| `501` | 未实现 | 下载功能开发中 |

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
| `400` | `该邮箱已注册` |
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
| `400` | `邮箱或密码错误` |
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
| `400` | `无效的 Refresh Token` |
| `400` | `Token 已过期` |
| `400` | `Token 已被吊销` |

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
| `400` | `当前密码错误` |
| `422` | `请求参数验证失败: body → new_password: 密码长度需为 8-64 位` |
| `422` | `请求参数验证失败: body → new_password: 密码必须包含至少一个字母` |
| `422` | `请求参数验证失败: body → new_password: 密码必须包含至少一个数字` |

---

## 3. 书架接口

所有书架接口的基础路径为 `/api/v1`。

### GET /api/v1/books — 获取书架列表

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

获取当前用户的书籍列表，按添加时间倒序排列，支持分页。

**请求**

```
GET /api/v1/books?page=1&page_size=20
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `page` | `int` | 否 | `1` | >= 1 | 页码 |
| `page_size` | `int` | 否 | `20` | 1-100 | 每页条数 |

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
| `401` | `未提供认证凭证` / `Token 已过期` |

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
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `409` | `该书名已在书架中` |
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
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或无权访问` |

---

### DELETE /api/v1/books/{book_id} — 删除书籍

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

从书架中软删除指定书籍。数据保留在数据库中，可通过 `deleted_at` 字段标记为已删除。

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
| `404` | `书籍不存在或无权访问` |

---

## 4. 搜索接口

### GET /api/v1/search — 搜索小说

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

在当前用户书架中按书名进行模糊搜索。**v1.0 仅支持书架内搜索**，v1.1 将接入外部搜索引擎实现全网搜索。

**请求**

```
GET /api/v1/search?q=诡秘&page=1&page_size=20
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| `q` | `string` | 是 | - | 最少 1 字符 | 搜索关键词，按书名模糊匹配 |
| `page` | `int` | 否 | `1` | >= 1 | 页码 |
| `page_size` | `int` | 否 | `20` | 1-100 | 每页条数 |

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

**无结果响应**

```json
{
  "success": true,
  "data": [],
  "meta": { "page": 1, "page_size": 20, "total": 0, "total_pages": 0 },
  "error": null
}
```

---

## 5. 抓取与 EPUB 接口

> **状态说明**：以下接口目前为 **占位实现**，核心逻辑将在后续版本中完成。

### POST /api/v1/books/{book_id}/crawl — 触发抓取

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

对指定书籍触发内容抓取任务。当前实现将书籍状态置为 `crawling`，异步抓取功能开发中。

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
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或无权访问` |
| `400` | `缺少 source_url，无法抓取` |

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
| `total_chapters` | `int` / `null` | 总章节数（爬虫未实现时返回 `null`） |
| `percentage` | `float` | 抓取进度百分比（0.0 - 100.0） |

---

### GET /api/v1/books/{book_id}/download — 下载 EPUB

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

下载已生成的 `.epub` 电子书文件。**当前为占位实现，返回 501**。

**请求**

```
GET /api/v1/books/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download
Authorization: Bearer <access_token>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `book_id` | `string`（path） | 是 | 书籍 UUID |

**成功响应 `200`**（后续实现后）

```
Content-Type: application/epub+zip
Content-Disposition: attachment; filename="诡秘之主-爱潜水的乌贼.epub"

<binary epub data>
```

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `该书籍尚未生成 .epub 文件，请先抓取` |
| `501` | `下载功能开发中` |

---

## 6. 系统接口

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
  "version": "1.0.0"
}
```

> **说明**：该接口不走统一 `ApiResponse` 格式，直接返回简单 JSON 对象。

---

## 7. 附录：数据字典

### 7.1 书籍抓取状态

| 状态值 | 含义 | 说明 |
|--------|------|------|
| `idle` | 待抓取 | 初始状态，尚未触发抓取 |
| `crawling` | 抓取中 | 爬虫正在工作 |
| `done` | 已完成 | 内容抓取并生成 EPUB 成功 |
| `failed` | 失败 | 抓取过程出错 |

### 7.2 JWT Token 规范

| 属性 | Access Token | Refresh Token |
|------|-------------|---------------|
| 有效期 | 2 小时 | 7 天 |
| `sub` 字段 | 用户 UUID | 用户 UUID |
| `type` 字段 | `"access"` | `"refresh"` |
| 签名算法 | HS256 | HS256 |
| 存储方式 | 客户端内存/Storage | 服务端 `refresh_tokens` 表存 SHA-256 哈希 |

### 7.3 密码规则

| 约束 | 值 |
|------|-----|
| 最小长度 | 8 位 |
| 最大长度 | 64 位 |
| 必含字符 | 至少一个字母 **且** 至少一个数字 |
| 存储方式 | bcrypt，salt rounds = 12 |

### 7.4 认证流程图

```
注册 → 登录 → 获得 Access Token + Refresh Token
                     │
                     ├──> 携带 Access Token 调用业务接口
                     │    （2 小时内有效）
                     │
                     └──> Access Token 过期后
                          POST /auth/refresh
                          使用 Refresh Token 换取新 Token Pair
                          （旧 Refresh Token 自动吊销）
```

---

> **文档版本**：v1.0 | **最后更新**：2026-07-25
