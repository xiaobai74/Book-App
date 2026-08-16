/* ═══════════════════════════════════════════════════════
   小说管理App · 最近阅读记录（localStorage 持久化）
   由 CommandPalette（Ctrl+K 面板）与 ReaderView（进入阅读器时）共用
   ═══════════════════════════════════════════════════════ */

const RECENT_BOOKS_KEY = 'recent_books'

/** 最近阅读最大保留数量 */
export const MAX_RECENT = 5

/** 读取最近阅读的书 ID 列表 */
export function getRecentBookIds(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_BOOKS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

/** 记录一本最近阅读的书（最新在前，最多保留 MAX_RECENT 本） */
export function recordRecentBook(bookId: string): void {
  const ids = getRecentBookIds().filter(id => id !== bookId)
  ids.unshift(bookId)
  localStorage.setItem(RECENT_BOOKS_KEY, JSON.stringify(ids.slice(0, MAX_RECENT)))
}
