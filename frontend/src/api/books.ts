/* ═══════════════════════════════════════════════════════
   小说管理App · 书架 & 搜索 API
   ═══════════════════════════════════════════════════════ */
import http from './http'
import type { ApiResponse, Book, BookDetail, ChapterSummary, ChapterDetail, ReadingProgress, AddBookRequest, CrawlStatus, SearchParams, SearchResultItem, SourceItem, CrawlSource, CrawlSourceFormData, CrawlSourceTestRequest, CrawlSourceTestResult, AiSearchResult } from '@/types'

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

/** 下载 EPUB/TXT（返回直接下载链接） */
export function getDownloadUrl(bookId: string, format: 'epub' | 'txt' = 'epub') {
  return `/api/v1/books/${bookId}/download?format=${format}`
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

/** 获取单个自定义源站 */
export function getCrawlSource(id: number) {
  return http.get<ApiResponse<CrawlSource>>(`/crawl-sources/${id}`)
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

/** 触发 AI 摘要生成 */
export function generateAiSummary(bookId: string) {
  return http.post<ApiResponse<{ status: string; ai_summary?: string | null; ai_summary_at?: string | null; error?: string | null }>>(`/ai/summary/${bookId}`)
}

/** 获取 AI 摘要 */
export function getAiSummary(bookId: string) {
  return http.get<ApiResponse<{ status: string; ai_summary?: string | null; ai_summary_at?: string | null; error?: string | null }>>(`/ai/summary/${bookId}`)
}
