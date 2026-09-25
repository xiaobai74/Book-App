/* ═══════════════════════════════════════════════════════
   小说管理App · 书架 & 搜索 API
   ═══════════════════════════════════════════════════════ */
import http, { API_BASE_URL } from './http'
import type { ApiResponse, Book, BookDetail, ChapterSummary, ChapterDetail, ReadingProgress, AddBookRequest, CrawlStatus, CrawlStreamEvent, SearchParams, SearchResultItem, SourceItem, CrawlSource, CrawlSourceFormData, CrawlSourceTestRequest, CrawlSourceTestResult, AiSearchResult, AiRecommendResult } from '@/types'

/** 获取书架列表 */
export function getBooks(page = 1, page_size = 20, marked?: boolean | null) {
  const params: Record<string, any> = { page, page_size }
  if (marked !== null && marked !== undefined) params.marked = marked
  return http.get<ApiResponse<Book[]>>('/books', { params })
}

/** 添加书籍 */
export function addBook(data: AddBookRequest) {
  return http.post<ApiResponse<Book>>('/books', data)
}

/** 导入本地小说文件（.txt/.epub/.pdf/.docx）
 *
 * 以 multipart/form-data 上传文件，可携带用户编辑后的书名/作者覆盖自动推断。
 * 大文件解析耗时较长，超时放宽至 120s。
 */
export function importBookFile(
  file: File | Blob,
  filename: string,
  title?: string,
  author?: string,
) {
  const fd = new FormData()
  fd.append('file', file, filename)
  if (title && title.trim()) fd.append('title', title.trim())
  if (author && author.trim()) fd.append('author', author.trim())
  return http.post<ApiResponse<Book>>('/books/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

/** 查看书籍详情 */
export function getBookDetail(bookId: string) {
  return http.get<ApiResponse<BookDetail>>(`/books/${bookId}`)
}

/** 删除书籍 */
export function deleteBook(bookId: string) {
  return http.delete<ApiResponse<null>>(`/books/${bookId}`)
}

/** 标记/取消标记书籍 */
export function toggleMarkBook(bookId: string) {
  return http.put<ApiResponse<Book>>(`/books/${bookId}/mark`)
}

/** 获取章节列表 */
export function getChapters(bookId: string) {
  return http.get<ApiResponse<ChapterSummary[]>>(`/books/${bookId}/chapters`)
}

/** 获取章节内容 */
export function getChapterContent(bookId: string, chapterIndex: number) {
  return http.get<ApiResponse<ChapterDetail>>(`/books/${bookId}/chapters/${chapterIndex}`)
}

/** 获取阅读进度 */
export function getReadingProgress(bookId: string) {
  return http.get<ApiResponse<ReadingProgress>>(`/books/${bookId}/progress`)
}

/** 更新阅读进度 */
export function updateReadingProgress(bookId: string, chapter_index: number) {
  return http.put<ApiResponse<ReadingProgress>>(`/books/${bookId}/progress`, { chapter_index })
}

/** 搜索书籍（书架内） */
export function searchBooks(params: SearchParams) {
  return http.get<ApiResponse<Book[]>>('/search', { params })
}

/** 外部源站搜索小说 */
export function searchBooksExternal(params: { q: string; source_id?: number; search_limit?: number }) {
  return http.get<ApiResponse<SearchResultItem[]>>('/search/external', { params })
}

/** 获取可用源站列表 */
export function getSources() {
  return http.get<ApiResponse<SourceItem[]>>('/sources')
}

/** 触发抓取 */
export function triggerCrawl(bookId: string) {
  return http.post<ApiResponse<Book>>(`/books/${bookId}/crawl`)
}

/** 查询抓取进度 */
export function getCrawlStatus(bookId: string) {
  return http.get<ApiResponse<CrawlStatus>>(`/books/${bookId}/crawl-status`)
}

/** 订阅抓取实时推送（SSE，边爬边看 v1.4）
 *
 * 使用 fetch + ReadableStream 消费 text/event-stream（EventSource
 * 不支持自定义 Authorization 头）。连接/解析失败时推送
 * type='stream_error' 事件，由调用方回退到轮询。
 *
 * @returns 取消订阅函数
 */
export function subscribeCrawlStream(
  bookId: string,
  onEvent: (e: CrawlStreamEvent) => void,
): () => void {
  return startSse(
    `${API_BASE_URL}/books/${bookId}/crawl-stream`,
    (obj) => onEvent(obj as CrawlStreamEvent),
  )
}

/**
 * 通用 SSE 消费核心：fetch + ReadableStream 逐行解析 `data:` JSON，
 * 忽略心跳注释行。连接异常时推送 stream_error，正常收到 done 事件后关闭。
 *
 * @returns 取消函数（主动中断不再上报 stream_error）
 */
function startSse(url: string, onData: (obj: unknown) => void, onClosed?: () => void): () => void {
  const controller = new AbortController()
  let closed = false

  ;(async () => {
    try {
      const token = localStorage.getItem('access_token')
      const resp = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      })
      if (!resp.ok || !resp.body) {
        throw new Error(`SSE 连接失败: HTTP ${resp.status}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // 按行切分，末尾不完整行留待下一块
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data:')) continue  // 忽略心跳注释行
          try {
            onData(JSON.parse(trimmed.slice(5).trim()))
          } catch {
            // 忽略单条畸形数据
          }
        }
      }
      // 流被服务端正常关闭（未报错）
      if (!closed) onClosed?.()
    } catch (err) {
      // 主动取消不报错；其余异常通知调用方回退
      if (!closed && (err as Error)?.name !== 'AbortError') {
        onData({ type: 'stream_error' })
      }
    }
  })()

  return () => {
    closed = true
    controller.abort()
  }
}

/** 全网搜索流式事件（v2.7 阶段1a） */
export type ExternalSearchEvent =
  | { type: 'meta'; sources: { id: number; name: string }[]; cached: boolean }
  | { type: 'source'; source_id: number; source_name: string; results: SearchResultItem[] }
  | { type: 'done'; total: number }
  | { type: 'stream_closed' }
  | { type: 'stream_error' }

/**
 * 流式全网搜索（SSE）：每个源站完成即推送 source 事件，结束推 done。
 * stream_error=连接失败（调用方回退同步接口）；
 * stream_closed=流正常关闭但未收到 done（已收结果仍可用）。
 *
 * @returns 取消函数（用户切换关键词/离开页面时调用）
 */
export function searchBooksExternalStream(
  params: { q: string; source_id?: number; search_limit?: number },
  onEvent: (e: ExternalSearchEvent) => void,
): () => void {
  const qs = new URLSearchParams({ q: params.q })
  if (params.source_id !== undefined) qs.set('source_id', String(params.source_id))
  if (params.search_limit !== undefined) qs.set('search_limit', String(params.search_limit))
  let gotDone = false
  return startSse(
    `${API_BASE_URL}/search/external/stream?${qs.toString()}`,
    (obj) => {
      const e = obj as ExternalSearchEvent
      if (e.type === 'done') gotDone = true
      onEvent(e)
    },
    () => {
      // 流关闭但未收到 done（服务端异常中断等）→ 通知调用方以已收结果收尾
      if (!gotDone) onEvent({ type: 'stream_closed' })
    },
  )
}

/** 下载 EPUB/TXT（返回直接下载链接）
 *
 * 桌面版后端在随机动态端口、移动端在云端服务器，
 * 必须拼接当前环境的 API 根地址（见 http.ts 的 baseURL），
 * 不能硬编码 /api/v1 相对路径，否则 fetch 会打到本地页面的源上。
 */
export function getDownloadUrl(bookId: string, format: 'epub' | 'txt' = 'epub') {
  return `${API_BASE_URL}/books/${bookId}/download?format=${format}`
}

/** 获取封面图片 URL（供 <img src> 直接加载）
 *
 * <img> 无法携带 Authorization 头，因此将 Access Token 以 ?token=
 * 查询参数传递（后端 get_current_user_flexible 支持）。无封面或
 * 未登录时返回 null，由调用方回退到渐变占位封面。
 */
export function getCoverUrl(bookId: string, hasCover?: boolean): string | null {
  if (hasCover === false) return null
  const token = localStorage.getItem('access_token')
  if (!token) return null
  return `${API_BASE_URL}/books/${bookId}/cover?token=${encodeURIComponent(token)}`
}

/** 检查源站 URL 连通性 */
export function checkSourceUrl(url: string) {
  return http.post<ApiResponse<{
    reachable: boolean
    status_code: number | null
    content_length: number
    error_message: string | null
    suggested_fix: string | null
  }>>('/crawl/check-url', { url })
}

// ═══════════════════════════════════════════════════════
// 自定义抓取源站 API
// ═══════════════════════════════════════════════════════

/** 列出当前用户的自定义源站 */
export function getCrawlSources() {
  return http.get<ApiResponse<CrawlSource[]>>('/crawl-sources')
}

/** 创建自定义源站 */
export function createCrawlSource(data: CrawlSourceFormData) {
  return http.post<ApiResponse<CrawlSource>>('/crawl-sources', data)
}

/** 更新自定义源站 */
export function updateCrawlSource(id: number, data: Partial<CrawlSourceFormData>) {
  return http.put<ApiResponse<CrawlSource>>(`/crawl-sources/${id}`, data)
}

/** 删除自定义源站 */
export function deleteCrawlSource(id: number) {
  return http.delete<ApiResponse<null>>(`/crawl-sources/${id}`)
}

/** 测试自定义源站规则 */
export function testCrawlSource(data: CrawlSourceTestRequest) {
  return http.post<ApiResponse<CrawlSourceTestResult>>('/crawl-sources/test', data)
}

// ═══════════════════════════════════════════════════════
// AI 功能 API（v1.3 新增）
// ═══════════════════════════════════════════════════════

/** AI 自然语言搜索（书架内） */
export function aiSearchBooks(query: string) {
  return http.post<ApiResponse<AiSearchResult[]>>('/ai/search', { query })
}

/** AI 全网搜索题材推荐（按书籍类型推荐 2-3 本） */
export function aiRecommendBooks(query: string) {
  return http.post<ApiResponse<AiRecommendResult[]>>('/ai/recommend', { query })
}

/** 触发 AI 摘要生成 */
export function generateAiSummary(bookId: string) {
  return http.post<ApiResponse<{ status: string; ai_summary?: string | null; ai_summary_at?: string | null; error?: string | null }>>(`/ai/summary/${bookId}`)
}

/** 获取 AI 摘要 */
export function getAiSummary(bookId: string) {
  return http.get<ApiResponse<{ status: string; ai_summary?: string | null; ai_summary_at?: string | null; error?: string | null }>>(`/ai/summary/${bookId}`)
}
