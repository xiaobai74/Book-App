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
import type { Book, BookDetail, CrawlStatus, AddBookRequest, PaginationMeta, SearchResultItem, SourceItem } from '@/types'

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

  const bookCount = computed(() => pagination.value.total)

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

  /** v1.2 新增：全量加载书籍缓存（用于客户端快速检索） */
  async function fetchAllBooks(marked: boolean | null = null) {
    loading.value = true
    try {
      const { data } = await getBooks(1, CLIENT_SEARCH_THRESHOLD, marked)
      if (data.success) {
        allBooks.value = [...(data.data || [])].sort(compareBooks)
        filteredBooks.value = [...allBooks.value]
        // 书架总量超过阈值 → 服务端搜索；未超过 → 恢复客户端快速检索
        searchMode.value = (data.meta?.total || 0) > CLIENT_SEARCH_THRESHOLD ? 'server' : 'client'
      }
    } finally {
      loading.value = false
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

  /** 加载书籍详情 */
  async function fetchBookDetail(bookId: string) {
    loading.value = true
    try {
      const { data } = await getBookDetail(bookId)
      if (data.success && data.data) {
        currentBook.value = data.data
        return data.data
      }
      return null
    } finally {
      loading.value = false
    }
  }

  /** 添加书籍 */
  async function addBook(payload: AddBookRequest) {
    const { data } = await addBookApi(payload)
    if (data.success && data.data) {
      // 同步更新 allBooks 缓存（按书架优先级排序，保持标记置顶规则）
      allBooks.value = [...allBooks.value, data.data].sort(compareBooks)
      filteredBooks.value = [...allBooks.value]
      await fetchBooks(pagination.value.page)
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
      // 更新列表中对应书籍
      const idx = books.value.findIndex((b) => b.id === bookId)
      if (idx >= 0) books.value[idx] = data.data
      // 同步更新 allBooks
      const allIdx = allBooks.value.findIndex((b) => b.id === bookId)
      if (allIdx >= 0) allBooks.value[allIdx] = data.data
      // 同步更新 filteredBooks
      const filteredIdx = filteredBooks.value.findIndex((b) => b.id === bookId)
      if (filteredIdx >= 0) filteredBooks.value[filteredIdx] = data.data
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
