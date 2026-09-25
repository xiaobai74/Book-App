/**
 * 章节内容缓存（v2.6.2 新增，v2.6.3 扩展持久层）
 *
 * 三级取数：内存 LRU（同步、秒开）→ IndexedDB 持久缓存（毫秒级、跨会话）
 * → 网络。已抓取章节内容不可变，持久缓存无跨会话过期风险；
 * 重新抓取时由 clearBookCache 清空该书两级缓存。
 *
 * - 内存层：LRU 上限 200 章（Map 插入序 + 命中重插）
 * - 持久层：IDB `novel-chapter-cache` v1，全局上限 1500 章，超限按 lastReadAt 升序淘汰
 * - 降级：IDB 不可用（隐私模式/异常）时静默退化为纯内存缓存，功能不中断
 */
import { getChapterContent } from '@/api/books'
import type { ChapterDetail } from '@/types'

/** 内存层上限（约 200 章 × 5KB ≈ 1MB 量级，防止长读内存膨胀） */
const MAX_MEMORY_ENTRIES = 200
/** 持久层上限（约 1500 章 × 30KB ≈ 45MB，浏览器配额内安全） */
const MAX_IDB_ENTRIES = 1500
/** 预取默认并发上限 */
const PREFETCH_CONCURRENCY = 2

const DB_NAME = 'novel-chapter-cache'
const DB_VERSION = 1
const STORE_NAME = 'chapters'

interface StoredChapter {
  key: string
  bookId: string
  index: number
  detail: ChapterDetail
  savedAt: number
  lastReadAt: number
}

/** Map 保持插入顺序，配合"命中后重插"实现简单 LRU */
const cache = new Map<string, ChapterDetail>()

/**
 * 每书缓存代号：clearBookCache 时递增。
 * 发起网络取数前捕获代号、写回时校验，可丢弃「清空前发起、清空后返回」的
 * 过期写入，避免重新抓取时旧正文被回写并长期残留在持久层。
 */
const epochs = new Map<string, number>()

let dbPromise: Promise<IDBDatabase | null> | null = null

function makeKey(bookId: string, index: number): string {
  return `${bookId}:${index}`
}

/** 打开 IDB 连接（单例复用）；任何失败 resolve null，调用方静默降级 */
function getDb(): Promise<IDBDatabase | null> {
  if (!dbPromise) {
    dbPromise = new Promise<IDBDatabase | null>((resolve) => {
      if (typeof indexedDB === 'undefined') {
        resolve(null)
        return
      }
      try {
        const req = indexedDB.open(DB_NAME, DB_VERSION)
        req.onupgradeneeded = () => {
          const db = req.result
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            db.createObjectStore(STORE_NAME, { keyPath: 'key' })
          }
        }
        req.onsuccess = () => resolve(req.result)
        req.onerror = () => resolve(null)
        // 被其他连接的删库/升级阻塞：本次降级，但不永久禁用持久层
        req.onblocked = () => resolve(null)
      } catch {
        resolve(null)
      }
    })
    // 打开失败（含瞬时阻塞）时不缓存结果，后续调用可重试，避免整会话退化为纯内存
    dbPromise.then((db) => {
      if (!db) dbPromise = null
    })
  }
  return dbPromise
}

function idbGet(key: string): Promise<StoredChapter | undefined> {
  return getDb().then(
    (db) =>
      new Promise<StoredChapter | undefined>((resolve) => {
        if (!db) {
          resolve(undefined)
          return
        }
        try {
          const req = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(key)
          req.onsuccess = () => resolve(req.result as StoredChapter | undefined)
          req.onerror = () => resolve(undefined)
        } catch {
          resolve(undefined)
        }
      })
  )
}

function idbPut(entry: StoredChapter): Promise<void> {
  return getDb()
    .then(
      (db) =>
        new Promise<void>((resolve) => {
          if (!db) {
            resolve()
            return
          }
          try {
            const tx = db.transaction(STORE_NAME, 'readwrite')
            tx.objectStore(STORE_NAME).put(entry)
            tx.oncomplete = () => resolve()
            tx.onerror = () => resolve()
            tx.onabort = () => resolve()
          } catch {
            resolve()
          }
        })
    )
    .then(evictIdbOverflow)
}

/** 持久层超上限时按 lastReadAt 升序批量淘汰最久未读条目 */
function evictIdbOverflow(): Promise<void> {
  return getDb().then(
    (db) =>
      new Promise<void>((resolve) => {
        if (!db) {
          resolve()
          return
        }
        try {
          const req = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).getAll()
          req.onsuccess = () => {
            const all = (req.result as StoredChapter[]) || []
            if (all.length <= MAX_IDB_ENTRIES) {
              resolve()
              return
            }
            const victims = all
              .sort((a, b) => a.lastReadAt - b.lastReadAt)
              .slice(0, all.length - MAX_IDB_ENTRIES)
            const tx = db.transaction(STORE_NAME, 'readwrite')
            const store = tx.objectStore(STORE_NAME)
            victims.forEach((v) => store.delete(v.key))
            tx.oncomplete = () => resolve()
            tx.onerror = () => resolve()
            tx.onabort = () => resolve()
          }
          req.onerror = () => resolve()
        } catch {
          resolve()
        }
      })
  )
}

function idbDeleteBook(bookId: string): Promise<void> {
  return getDb().then(
    (db) =>
      new Promise<void>((resolve) => {
        if (!db) {
          resolve()
          return
        }
        try {
          const tx = db.transaction(STORE_NAME, 'readwrite')
          const store = tx.objectStore(STORE_NAME)
          const prefix = `${bookId}:`
          const req = store.openCursor()
          req.onsuccess = () => {
            const cursor = req.result
            if (!cursor) return  // 遍历结束，由 tx.oncomplete 统一 resolve
            if (String(cursor.key).startsWith(prefix)) cursor.delete()
            cursor.continue()
          }
          tx.oncomplete = () => resolve()
          tx.onerror = () => resolve()
          tx.onabort = () => resolve()
        } catch {
          resolve()
        }
      })
  )
}

// ── 内存层 ────────────────────────────────────

/** 读取缓存章节（内存层，同步）；未命中返回 undefined */
export function getCachedChapter(bookId: string, index: number): ChapterDetail | undefined {
  const key = makeKey(bookId, index)
  const hit = cache.get(key)
  if (hit) {
    // 刷新 LRU 顺序：最近使用的条目移到末尾
    cache.delete(key)
    cache.set(key, hit)
  }
  return hit
}

function rememberInMemory(bookId: string, index: number, detail: ChapterDetail): void {
  const key = makeKey(bookId, index)
  if (cache.has(key)) cache.delete(key)
  cache.set(key, detail)
  while (cache.size > MAX_MEMORY_ENTRIES) {
    const oldest = cache.keys().next().value
    if (oldest === undefined) break
    cache.delete(oldest)
  }
}

// ── 三级取数 API ────────────────────────────────────

/** 内存 → 持久层查找；持久层命中时回填内存并刷新 lastReadAt（异步写回不阻塞返回） */
export async function getChapterStored(bookId: string, index: number): Promise<ChapterDetail | undefined> {
  const mem = getCachedChapter(bookId, index)
  if (mem) return mem
  const stored = await idbGet(makeKey(bookId, index))
  if (!stored) return undefined
  rememberInMemory(bookId, index, stored.detail)
  idbPut({ ...stored, lastReadAt: Date.now() }).catch(() => {})
  return stored.detail
}

/** 写入内存 + 持久层（持久层写为 fire-and-forget，失败静默）
 *
 * @param epoch 发起取数时捕获的缓存代号；与当前不一致则丢弃该写入（期间已清缓存）
 */
export function setCachedChapter(
  bookId: string,
  index: number,
  detail: ChapterDetail,
  epoch: number = cacheEpoch(bookId)
): void {
  if (epoch !== cacheEpoch(bookId)) return
  rememberInMemory(bookId, index, detail)
  const now = Date.now()
  idbPut({ key: makeKey(bookId, index), bookId, index, detail, savedAt: now, lastReadAt: now }).catch(() => {})
}

/** 读取当前缓存代号（发起网络取数前捕获，写回时回传校验） */
export function cacheEpoch(bookId: string): number {
  return epochs.get(bookId) ?? 0
}

/** 清空指定书籍的两级缓存（重新抓取时调用，防止旧内容残留） */
export async function clearBookCache(bookId: string): Promise<void> {
  // 先提升代号：使所有清空前发起的在飞行写入失效
  epochs.set(bookId, cacheEpoch(bookId) + 1)
  const prefix = `${bookId}:`
  for (const key of Array.from(cache.keys())) {
    if (key.startsWith(prefix)) cache.delete(key)
  }
  await idbDeleteBook(bookId)
}

// ── 预取 ────────────────────────────────────

/** 单章网络请求（在飞行去重用） */
type ChapterRequest = ReturnType<typeof getChapterContent>

/** 同一章节的在飞行请求表：并发调用共享同一 Promise，避免重复打后端 */
const inFlight = new Map<string, ChapterRequest>()

/**
 * 发起单章网络请求，并按 key 去重：同一章节已有请求在飞行时直接复用。
 * 快速翻章 / 预取窗口重叠时避免对慢接口发重复请求；成功后双写两级缓存。
 * 失败时 Promise 原样 reject（由调用方决定是静默还是提示）。
 */
export function fetchChapterOnce(bookId: string, index: number): ChapterRequest {
  const key = makeKey(bookId, index)
  const pending = inFlight.get(key)
  if (pending) return pending
  const req = getChapterContent(bookId, index).finally(() => {
    inFlight.delete(key)
  }) as ChapterRequest
  inFlight.set(key, req)
  return req
}

/**
 * 静默预取指定章节：跳过内存/持久层已缓存项与在飞行请求，
 * 其余以并发上限拉取并双写缓存；失败（章节未就绪/网络波动）静默忽略，不打扰阅读。
 */
export function prefetchChapters(
  bookId: string,
  indexes: number[],
  concurrency: number = PREFETCH_CONCURRENCY
): Promise<void> {
  const queue = indexes.filter((n, i) => Number.isInteger(n) && indexes.indexOf(n) === i)
  const epoch = cacheEpoch(bookId)  // 预取期间若发生清缓存，写入会被丢弃
  let cursor = 0
  const workers = Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (cursor < queue.length) {
      const n = queue[cursor++]
      if (getCachedChapter(bookId, n)) continue
      const stored = await getChapterStored(bookId, n)
      if (stored) continue
      try {
        const { data } = await fetchChapterOnce(bookId, n)
        if (data.success && data.data) setCachedChapter(bookId, n, data.data, epoch)
      } catch {
        // 章节未就绪 / 网络波动：预取失败静默忽略
      }
    }
  })
  return Promise.all(workers).then(() => undefined)
}
