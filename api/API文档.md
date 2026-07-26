# 小说管理App — API 文档

> **版本**：v1.1
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

### GET /api/v1/search — 书架内搜索

> 🔒 **需要认证**：`Authorization: Bearer <access_token>`

在当前用户书架中按书名进行模糊搜索。

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
| `source_id` | `int` | 否 | `null` | >= 0 | 指定源站 ID，不传则搜索所有源站 |
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
      "comment": "搜索为单结果重定向，不适合外部搜索；抓取可用"
    },
    {
      "id": 1,
      "name": "香书小说",
      "url": "http://www.xbiqugu.la/",
      "has_search": true,
      "comment": ""
    }
  ],
  "meta": { "page": 1, "page_size": 2, "total": 2, "total_pages": 1 },
  "error": null
}
```

| 返回字段（data[]） | 类型 | 说明 |
|---------------------|------|------|
| `id` | `int` | 源站 ID |
| `name` | `string` | 源站名称 |
| `url` | `string` | 源站域名 |
| `has_search` | `bool` | 是否支持外部搜索 |
| `comment` | `string` | 备注说明 |

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
    "added_at": "2026-07-25T12:00:00"
  },
  "meta": null,
  "error": null
}
```

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `has_txt` | `bool` | 是否已生成 TXT 文件 |

**错误响应**

| 状态码 | error 内容 |
|--------|-----------|
| `404` | `书籍不存在或已被删除` |
| `400` | `缺少 source_url，无法抓取` |
| `409` | `该书籍正在抓取中，请勿重复操作` |

> **抓取流程**：
> 1. 系统先检查 URL 是否匹配预配置源站规则，匹配则使用精确规则
> 2. 未匹配时自动使用通用解析策略（内置 CSS 选择器枚举，覆盖常见小说站结构）
> 3. 抓取完成后自动生成 EPUB 和 TXT 两种格式的电子书文件

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
  "version": "1.0.0"
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
| `chapter.filterTag` | `string` | 需移除的 HTML 标签（逗号分隔） | `"script, div, ins"` |
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
                          POST /auth/refresh
                          使用 Refresh Token 换取新 Token Pair
                          （旧 Refresh Token 自动吊销）
```

---

> **文档版本**：v1.1 | **最后更新**：2026-07-26
> 
> **v1.1 更新内容**：
> - 新增外部源站搜索接口 `GET /api/v1/search/external` 和 `GET /api/v1/sources`
> - 新增 URL 连通性检查接口 `POST /api/v1/crawl/check-url`
> - 新增自定义源站 CRUD + 测试接口（6 个新端点）
> - 新增通用抓取规则说明 —— 支持任意小说网站的自动解析
> - 下载接口支持 EPUB 和 TXT 双格式
> - 完善数据字典（通用规则说明、自定义规则配置字段说明）
