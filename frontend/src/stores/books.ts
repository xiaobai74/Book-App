/* ═══════════════════════════════════════════════════════
   小说管理App · 书架状态管理 (Pinia)
   v1.2 — 新增书架快速检索：全量缓存、客户端过滤、混合搜索模式
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getBooks,
  addBook as addBookApi,
  deleteBook as deleteBookApi,
  searchBooks,
  searchBooksExternal,
  getSources,
  triggerCrawl,
  getCrawlStatus,
  getBookDetail
} from '@/api/books'
import type { Book, BookDetail, CrawlStatus, AddBookRequest, PaginationMeta, SearchResultItem, SourceItem, ChapterSummary } from '@/types'

/** 客户端搜索阈值：书架总量超过此值自动切换为服务端搜索 */
const CLIENT_SEARCH_THRESHOLD = 200

/**
 * 书架排序：与后端 list_books 一致 — 已标记置顶（按标记时间倒序），未标记按添加时间倒序
 */
function compareBooks(a: Book, b: Book): number {
  if (a.is_marked !== b.is_marked) return a.is_marked ? -1 : 1
  const aTime = a.is_marked
    ? new Date(a.marked_at || 0).getTime()
    : new Date(a.added_at || 0).getTime()
  const bTime = b.is_marked
    ? new Date(b.marked_at || 0).getTime()
    : new Date(b.added_at || 0).getTime()
  return bTime - aTime
}

export const useBooksStore = defineStore('books', () => {
  const books = ref<Book[]>([])
  const currentBook = ref<BookDetail | null>(null)
  const crawlStatus = ref<CrawlStatus | null>(null)
  const loading = ref(false)
  const pagination = ref<PaginationMeta>({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const searchResults = ref<Book[]>([])
  const searchPagination = ref<PaginationMeta>({ page: 1, page_size: 20, total: 0, total_pages: 0 })

  // ── 外部源站搜索状态 ───────────────────────────────────
  const externalResults = ref<SearchResultItem[]>([])
  const externalLoading = ref(false)
  const externalError = ref<string | null>(null)
  const sources = ref<SourceItem[]>([])
  const sourcesLoaded = ref(false)

  // ── v1.2 新增：书架快速检索状态 ────────────────────────
  /** 全量书籍缓存（page_size=CLIENT_SEARCH_THRESHOLD 一次性拉取），用于客户端过滤 */
  const allBooks = ref<Book[]>([])
  /** 客户端过滤后的展示列表 */
  const filteredBooks = ref<Book[]>([])
  /** 搜索模式：client=客户端过滤, server=后端搜索 */
  const searchMode = ref<'client' | 'server'>('client')

  // ── v2.2 新增：书架缓存状态（切页返回零等待） ─────────────
  /** 书架数据是否已加载过（store 生命周期内持久） */
  const shelfLoaded = ref(false)
  /** 静默后台刷新是否进行中（不打断已有内容的展示） */
  const silentRefreshing = ref(false)
  /** 上次全量加载时间戳（用于节流后台刷新） */
  let lastLoadAt = 0
  /** 后台静默刷新的最短间隔（毫秒） */
  const SILENT_REFRESH_INTERVAL = 60 * 1000

  const bookCount = computed(() => pagination.value.total)

  // ── v2.3 新增：详情页缓存（书架⇄详情⇄阅读器切换零等待） ──────
  /** 按书缓存详情基础信息 + 章节列表 */
  const detailCache = new Map<string, { book: Book; chapters: ChapterSummary[]; loadedAt: number }>()
  /** AI 摘要缓存（仅缓存已生成完成的，重新生成时覆写） */
  const summaryCache = new Map<string, { text: string; at: string | null }>()
  /** 详情缓存有效期（抓取完成/标记等变更会本地更新缓存，过期仅保险用） */
  const DETAIL_CACHE_TTL = 10 * 60 * 1000

  /** 从书架缓存查找书籍基础信息（详情页即时展示用） */
  function findShelfBook(bookId: string): Book | null {
    return allBooks.value.find(b => b.id === bookId)
      || books.value.find(b => b.id === bookId)
      || null
  }

  /** 读取详情缓存（过期返回 null） */
  function getCachedDetail(bookId: string): { book: Book; chapters: ChapterSummary[] } | null {
    const c = detailCache.get(bookId)
    if (c && Date.now() - c.loadedAt < DETAIL_CACHE_TTL) return c
    return null
  }

  /** 写入详情缓存 */
  function cacheDetail(bookId: string, book: Book, chapters: ChapterSummary[]) {
    detailCache.set(bookId, { book, chapters, loadedAt: Date.now() })
  }

  /** 失效详情缓存（删除书籍等场景） */
  function invalidateDetail(bookId: string) {
    detailCache.delete(bookId)
    summaryCache.delete(bookId)
  }

  /** 将变更后的书籍同步回书架各列表（详情页抓取完成/标记等变更） */
  function upsertShelfBook(updated: Book) {
    for (const list of [books, allBooks, filteredBooks, searchResults]) {
      const idx = list.value.findIndex(b => b.id === updated.id)
      if (idx >= 0) list.value[idx] = { ...list.value[idx], ...updated }
    }
  }

  /** 读取 AI 摘要缓存 */
  function getCachedSummary(bookId: string): { text: string; at: string | null } | null {
    return summaryCache.get(bookId) ?? null
  }

  /** 写入 AI 摘要缓存 */
  function cacheSummary(bookId: string, text: string, at: string | null) {
    summaryCache.set(bookId, { text, at })
  }

  /** 加载书架（分页） */
  async function fetchBooks(page = 1, page_size = 20, marked: boolean | null = null) {
    loading.value = true
    try {
      const { data } = await getBooks(page, page_size, marked)
      if (data.success) {
        books.value = data.data || []
        pagination.value = data.meta || { page: 1, page_size: 20, total: 0, total_pages: 0 }
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * v2.2 新增：书架统一加载入口（缓存优先）
   * - 无缓存：首次加载，展示 loading 骨架
   * - 有缓存：立即返回（页面瞬间恢复），距上次加载超过阈值时
   *   后台静默刷新（silentRefreshing），数据回来自动替换，用户无感知
   * force=true 时忽略节流强制后台刷新（不阻塞展示）
   */
  async function ensureShelf(force = false) {
    if (shelfLoaded.value && lastLoadAt > 0) {
      const stale = Date.now() - lastLoadAt > SILENT_REFRESH_INTERVAL
      if (!force && !stale) return
      // 后台静默刷新：不置 loading，页面继续展示旧数据
      silentRefreshing.value = true
      try {
        await fetchAllBooks(null, true)
        // 服务端模式下同步刷新首页分页数据（展示列表来源）
        if (searchMode.value === 'server') {
          await fetchBooks(pagination.value.page, pagination.value.page_size, null)
        }
      } catch { /* 静默刷新失败保留旧数据 */ }
      finally {
        silentRefreshing.value = false
      }
      return
    }
    // 首次加载：全量缓存 + 首页分页数据（服务端模式展示用）
    try {
      await fetchAllBooks(null)
    } catch {
      // 全量加载失败时回退——至少保证分页数据能用
      searchMode.value = 'server'
    }
    try {
      await fetchBooks(1, 20, null)
    } catch {
      // 分页加载失败时静默处理，页面显示空状态
    }
    shelfLoaded.value = true
  }

  /** v1.2 新增：全量加载书籍缓存（用于客户端快速检索）；silent=true 时不触发 loading（后台静默刷新用） */
  async function fetchAllBooks(marked: boolean | null = null, silent = false) {
    if (!silent) loading.value = true
    try {
      const { data } = await getBooks(1, CLIENT_SEARCH_THRESHOLD, marked)
      if (data.success) {
        allBooks.value = [...(data.data || [])].sort(compareBooks)
        filteredBooks.value = [...allBooks.value]
        // 书架总量超过阈值 → 服务端搜索；未超过 → 恢复客户端快速检索
        searchMode.value = (data.meta?.total || 0) > CLIENT_SEARCH_THRESHOLD ? 'server' : 'client'
        lastLoadAt = Date.now()
      }
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** v1.2 新增：客户端多条件筛选（关键词 + 标记状态 + 其他条件） */
  function clientFilter(opts: {
    keyword?: string
    marked?: boolean | null
    hasEpub?: boolean
    done?: boolean
  }) {
    let result = [...allBooks.value]

    if (opts.keyword && opts.keyword.trim().length >= 2) {
      const lower = opts.keyword.trim().toLowerCase()
      result = result.filter(
        b => (b.title && b.title.toLowerCase().includes(lower))
          || (b.author && b.author.toLowerCase().includes(lower))
      )
    }

    if (opts.marked === true) {
      result = result.filter(b => b.is_marked)
    }

    if (opts.hasEpub) {
      result = result.filter(b => b.has_epub)
    }

    if (opts.done) {
      result = result.filter(b => b.status === 'done')
    }

    filteredBooks.value = result
  }

  /** v1.2 新增：重置搜索/筛选，恢复全量书架 */
  function resetFilter() {
    filteredBooks.value = [...allBooks.value]
  }

  /** v1.2 新增：是否处于客户端搜索模式 */
  const isClientMode = computed(() => searchMode.value === 'client')

  /** 加载书籍详情；silent=true 时不触发全局 loading（详情页缓存优先时用） */
  async function fetchBookDetail(bookId: string, silent = false) {
    if (!silent) loading.value = true
    try {
      const { data } = await getBookDetail(bookId)
      if (data.success && data.data) {
        currentBook.value = data.data
        return data.data
      }
      return null
    } finally {
      if (!silent) loading.value = false
    }
  }

  /** 添加书籍（v2.2：本地同步三个列表，不再额外发分页请求） */
  async function addBook(payload: AddBookRequest) {
    const { data } = await addBookApi(payload)
    if (data.success && data.data) {
      // 同步更新 allBooks 缓存（按书架优先级排序，保持标记置顶规则）
      allBooks.value = [...allBooks.value, data.data].sort(compareBooks)
      filteredBooks.value = [...allBooks.value]
      // 分页列表本地插入首位（与后端「标记置顶→时间倒序」一致，新书未标记按时间最新）
      books.value = [data.data, ...books.value]
      pagination.value.total += 1
      return data.data
    }
    throw new Error(data.error || '添加失败')
  }

  /** 删除书籍 */
  async function removeBook(bookId: string) {
    const { data } = await deleteBookApi(bookId)
    if (data.success) {
      books.value = books.value.filter((b) => b.id !== bookId)
      // 同步更新 allBooks 缓存和过滤列表
      allBooks.value = allBooks.value.filter((b) => b.id !== bookId)
      filteredBooks.value = filteredBooks.value.filter((b) => b.id !== bookId)
      // 同步更新服务端搜索结果（可能从搜索结果列表删除）
      searchResults.value = searchResults.value.filter((b) => b.id !== bookId)
      pagination.value.total = Math.max(0, pagination.value.total - 1)
      // v2.3：同步清理详情/摘要缓存
      invalidateDetail(bookId)
    } else {
      throw new Error(data.error || '删除失败')
    }
  }

  /** 按书架优先级（已标记置顶 → 时间倒序）重排三个展示列表，保持与后端排序一致 */
  function resortLists() {
    books.value = [...books.value].sort(compareBooks)
    allBooks.value = [...allBooks.value].sort(compareBooks)
    filteredBooks.value = [...filteredBooks.value].sort(compareBooks)
  }

  /** 搜索（服务端） */
  async function search(q: string, page = 1, page_size = 20) {
    loading.value = true
    try {
      const { data } = await searchBooks({ q, page, page_size })
      if (data.success) {
        searchResults.value = data.data || []
        searchPagination.value = data.meta || { page: 1, page_size: 20, total: 0, total_pages: 0 }
        return searchResults.value
      }
      return []
    } finally {
      loading.value = false
    }
  }

  /** 外部源站搜索 */
  async function searchExternal(q: string, source_id?: number, search_limit = 30) {
    externalLoading.value = true
    externalError.value = null
    try {
      const { data } = await searchBooksExternal({ q, source_id, search_limit })
      if (data.success) {
        externalResults.value = data.data || []
        return externalResults.value
      }
      externalError.value = data.error || '搜索失败，请稍后重试'
      return []
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.message || '搜索请求失败，请检查网络连接'
      externalError.value = message
      return []
    } finally {
      externalLoading.value = false
    }
  }

  /** 获取可用源站列表 */
  async function fetchSources() {
    try {
      const { data } = await getSources()
      if (data.success) {
        sources.value = data.data || []
      }
    } catch { /* 静默失败 */ }
    finally {
      sourcesLoaded.value = true
    }
  }

  /** 触发抓取 */
  async function startCrawl(bookId: string) {
    const { data } = await triggerCrawl(bookId)
    if (data.success && data.data) {
      // 同步书架各列表
      upsertShelfBook(data.data)
      if (currentBook.value?.id === bookId) {
        currentBook.value = { ...currentBook.value, ...data.data }
      }
      return data.data
    }
    throw new Error(data.error || '抓取失败')
  }

  /** 查询抓取进度 */
  async function fetchCrawlStatus(bookId: string) {
    const { data } = await getCrawlStatus(bookId)
    if (data.success && data.data) {
      crawlStatus.value = data.data
      return data.data
    }
    return null
  }

  return {
    books,
    currentBook,
    crawlStatus,
    loading,
    pagination,
    searchResults,
    searchPagination,
    externalResults,
    externalLoading,
    externalError,
    sources,
    sourcesLoaded,
    bookCount,
    // v1.2 新增：快速检索
    allBooks,
    filteredBooks,
    searchMode,
    isClientMode,
    // v2.2 新增：书架缓存
    shelfLoaded,
    silentRefreshing,
    ensureShelf,
    // v2.3 新增：详情页缓存
    findShelfBook,
    getCachedDetail,
    cacheDetail,
    invalidateDetail,
    upsertShelfBook,
    getCachedSummary,
    cacheSummary,
    fetchBooks,
    fetchAllBooks,
    clientFilter,
    resetFilter,
    resortLists,
    // 原有方法
    fetchBookDetail,
    addBook,
    removeBook,
    search,
    searchExternal,
    fetchSources,
    startCrawl,
    fetchCrawlStatus
  }
})
