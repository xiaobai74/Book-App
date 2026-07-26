/* ═══════════════════════════════════════════════════════
   小说管理App · 工具函数
   ═══════════════════════════════════════════════════════ */

/** 格式化日期为 zh-CN 格式 */
export function formatDate(ts: string | number): string {
  return new Date(ts).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/** 根据书名生成封面颜色 class (c0-c7) */
export function coverClass(title: string): string {
  return `c${title.charCodeAt(0) % 8}`
}

/** 抓取状态映射 */
export const statusMap: Record<string, { class: string; label: string }> = {
  idle: { class: 'badge-idle', label: '待抓取' },
  crawling: { class: 'badge-crawl', label: '抓取中' },
  done: { class: 'badge-done', label: '已完成' },
  failed: { class: 'badge-failed', label: '抓取失败' }
}
