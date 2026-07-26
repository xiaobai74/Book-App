/* ═══════════════════════════════════════════════════════
   小说管理App · 书架状态管理 (Pinia)
   ═══════════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getBooks,
  addBook as addBookApi,
  deleteBook as deleteBookApi,
  searchBooks,
  triggerCrawl,
  getCrawlStatus,
  getBookDetail
} from '@/api/books'
import type { Book, BookDetail, CrawlStatus, AddBookRequest, PaginationMeta } from '@/types'

export const useBooksStore = defineStore('books', () => {
  const books = ref<Book[]>([])
  const currentBook = ref<BookDetail | null>(null)
  const crawlStatus = ref<CrawlStatus | null>(null)
  const loading = ref(false)
  const pagination = ref<PaginationMeta>({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const searchResults = ref<Book[]>([])
  const searchPagination = ref<PaginationMeta>({ page: 1, page_size: 20, total: 0, total_pages: 0 })

  const bookCount = computed(() => pagination.value.total)

  /** 加载书架 */
  async function fetchBooks(page = 1, page_size = 20) {
    loading.value = true
    try {
      const { data } = await getBooks(page, page_size)
      if (data.success) {
        books.value = data.data || []
        pagination.value = data.meta || { page: 1, page_size: 20, total: 0, total_pages: 0 }
      }
    } finally {
      loading.value = false
    }
  }

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
      pagination.value.total--
    } else {
      throw new Error(data.error || '删除失败')
    }
  }

  /** 搜索 */
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

  /** 触发抓取 */
  async function startCrawl(bookId: string) {
    const { data } = await triggerCrawl(bookId)
    if (data.success && data.data) {
      // 更新列表中对应书籍
      const idx = books.value.findIndex((b) => b.id === bookId)
      if (idx >= 0) books.value[idx] = data.data
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
    bookCount,
    fetchBooks,
    fetchBookDetail,
    addBook,
    removeBook,
    search,
    startCrawl,
    fetchCrawlStatus
  }
})
