/* ═══════════════════════════════════════════════════════
   小说管理App · 书架 & 搜索 API
   ═══════════════════════════════════════════════════════ */
import http from './http'
import type { ApiResponse, Book, BookDetail, AddBookRequest, CrawlStatus, SearchParams, SearchResultItem, SourceItem, CrawlSource, CrawlSourceFormData, CrawlSourceTestRequest, CrawlSourceTestResult } from '@/types'

/** 获取书架列表 */
export function getBooks(page = 1, page_size = 20) {
  return http.get<ApiResponse<Book[]>>('/books', { params: { page, page_size } })
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
