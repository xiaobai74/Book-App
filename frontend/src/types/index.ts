/* ═══════════════════════════════════════════════════════
   小说管理App · 全局类型定义
   ═══════════════════════════════════════════════════════ */

/** 书籍抓取状态 */
export type BookStatus = 'idle' | 'crawling' | 'done' | 'failed'

/** 书籍数据 */
export interface Book {
  id: string
  title: string
  author: string
  source_url: string | null
  status: BookStatus
  chapter_count: number
  has_epub: boolean
  has_txt: boolean
  is_marked: boolean
  marked_at: string | null
  added_at: string
}

/** 书籍详情（含章节列表） */
export interface BookDetail extends Book {
  chapters: ChapterSummary[]
}

/** 章节摘要（列表中展示） */
export interface ChapterSummary {
  index: number
  title: string
  word_count: number
}

/** 章节详情（含正文） */
export interface ChapterDetail {
  index: number
  title: string
  content: string
  word_count: number
}

/** 章节数据（旧版兼容） */
export interface Chapter {
  title: string
  wordCount: number
}

/** 阅读进度 */
export interface ReadingProgress {
  book_id: string
  last_chapter_index: number
  updated_at: string | null
}

/** 抓取进度 */
export interface CrawlStatus {
  status: BookStatus
  chapter_count: number
  total_chapters: number | null
  percentage: number
  error: string | null  // 失败时的具体错误信息
}

/** 分页元信息 */
export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

/** 统一 API 响应 */
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T | null
  meta: PaginationMeta | null
  error: string | null
}

/** 登录 / 注册请求 */
export interface AuthRequest {
  email: string
  password: string
}

/** Token 响应 */
export interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
}

/** 用户信息 */
export interface UserInfo {
  id: string
  email: string
}

/** 注册响应 */
export interface RegisterData {
  id: string
  email: string
}

/** 修改密码请求 */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** 添加书籍请求 */
export interface AddBookRequest {
  title: string
  author?: string
  source_url?: string | null
}

/** 搜索参数 */
export interface SearchParams {
  q: string
  page?: number
  page_size?: number
}

/** 外部搜索结果项 */
export interface SearchResultItem {
  title: string
  author: string
  source_url: string
  source_name: string
  source_id: number
  category: string
  word_count: string
  status: string
  latest_chapter: string
  last_update_time: string
}

/** 源站信息 */
export interface SourceItem {
  id: number
  name: string
  url: string
  has_search: boolean
  comment: string
  is_custom: boolean
}

/** 自定义抓取源站 */
export interface CrawlSource {
  id: number
  name: string
  url: string
  rule_json: string
  is_public: boolean
  created_at: string | null
}

/** 创建/更新自定义源站请求 */
export interface CrawlSourceFormData {
  name: string
  url: string
  rule_json: string
  is_public?: boolean
}

/** 测试自定义源站规则请求 */
export interface CrawlSourceTestRequest {
  url: string
  rule_json: string
}

/** 测试自定义源站规则结果 */
export interface CrawlSourceTestResult {
  success: boolean
  chapter_count: number
  sample_chapters: { title: string; url: string }[]
  error: string | null
}

/** AI 搜索结果项（v1.3 新增） */
export interface AiSearchResult {
  book_id: string
  title: string
  author: string
  match_reason: string
  score: number
}

/** 排行榜源站信息 */
export interface RankingSource {
  id: number
  name: string
  url: string
  board_names: string[]
  is_custom: boolean
}

/** 排行榜条目 */
export interface RankingBook {
  rank: number
  title: string
  author: string
  book_url: string
  category: string
  latest_chapter: string
  last_update: string
}

/** 榜单抓取结果 */
export interface RankingBoardData {
  source_name: string
  board_name: string
  from_cache: boolean
  items: RankingBook[]
}
