<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 命令面板（v1.2 新增）

     Ctrl+K 唤起，类 VS Code 快速打开文件面板。
     支持：实时搜索、键盘导航、最近阅读快捷入口、高亮匹配。
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <el-dialog
    v-model="visible"
    :show-close="false"
    width="560px"
    top="15vh"
    :close-on-click-modal="true"
    :destroy-on-close="false"
    class="command-palette-dialog"
    @opened="onOpened"
    @closed="onClosed"
  >
    <div class="command-palette">
      <!-- 搜索输入框 -->
      <el-input
        ref="inputRef"
        v-model="query"
        placeholder="搜索书架中的书籍…"
        size="large"
        :prefix-icon="Search"
        class="palette-input"
        @input="onSearchInput"
        @keydown="onKeydown"
      >
        <template #suffix>
          <kbd class="shortcut-hint">Esc 关闭</kbd>
        </template>
      </el-input>

      <!-- 搜索结果 -->
      <div class="results" v-if="displayResults.length > 0">
        <!-- 分类标签 -->
        <div v-if="!hasActiveQuery" class="section-label">最近阅读</div>
        <div v-else class="section-label">
          搜索结果 · {{ displayResults.length }} 本
        </div>

        <!-- 结果列表 -->
        <div
          v-for="(book, idx) in displayResults"
          :key="book.id"
          :class="['result-item', { active: idx === selectedIndex }]"
          @click="navigateTo(book)"
          @mouseenter="selectedIndex = idx"
        >
          <span class="book-icon">📖</span>
          <div class="book-info">
            <span class="book-name">
              <span v-if="hasActiveQuery" v-html="highlightMatch(book.title)"></span>
              <span v-else>{{ book.title }}</span>
            </span>
            <span class="book-author">{{ book.author }}</span>
          </div>
          <span v-if="book.is_marked" class="mark">★</span>
          <span v-if="book.chapter_count > 0" class="chapter-count">{{ book.chapter_count }}章</span>
        </div>
      </div>

      <!-- 无结果 -->
      <div v-else-if="hasActiveQuery" class="no-results">
        书架中未找到匹配 "{{ query.trim() }}" 的书籍
      </div>

      <!-- 底部提示 -->
      <div class="palette-footer">
        <span><kbd>↑↓</kbd> 导航</span>
        <span><kbd>Enter</kbd> 打开</span>
        <span><kbd>Esc</kbd> 关闭</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElInput } from 'element-plus'
import { useBooksStore } from '@/stores'
import { getRecentBookIds, recordRecentBook, MAX_RECENT } from '@/utils/recentBooks'
import { escapeHtml } from '@/utils'
import type { Book } from '@/types'

const router = useRouter()
const booksStore = useBooksStore()

// ── 状态 ──────────────────────────────────────────────
const visible = ref(false)
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<InstanceType<typeof ElInput> | null>(null)

// ── 计算属性 ──────────────────────────────────────────
const hasActiveQuery = computed(() => query.value.trim().length >= 2)

const displayResults = computed<Book[]>(() => {
  const all = booksStore.allBooks.length > 0
    ? booksStore.allBooks
    : booksStore.books
  const q = query.value.trim()

  if (!q || q.length < 2) {
    // 无搜索关键词：显示最近阅读
    const recentIds = getRecentBookIds()
    const recent: Book[] = []
    for (const id of recentIds) {
      const book = all.find(b => b.id === id)
      if (book) recent.push(book)
    }
    // 补足以防最近阅读不足
    const remaining = all
      .filter(b => !recentIds.includes(b.id))
      .sort((a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime())
      .slice(0, MAX_RECENT - recent.length)
    return [...recent, ...remaining].slice(0, MAX_RECENT)
  }

  // 有搜索关键词：客户端模糊匹配（书名 + 作者）
  const lower = q.toLowerCase()
  return all
    .filter(b =>
      b.title.toLowerCase().includes(lower)
      || b.author.toLowerCase().includes(lower)
    )
    .slice(0, 20)
})

// ── 搜索逻辑 ──────────────────────────────────────────
function onSearchInput() {
  // 结果列表为 computed 即时更新，无需防抖；仅重置键盘选中项。
  // 原 150ms 防抖会覆盖用户此期间的键盘导航，故移除。
  selectedIndex.value = 0
}

// ── 键盘导航 ──────────────────────────────────────────
function onKeydown(e: Event) {
  const ev = e as KeyboardEvent
  switch (ev.key) {
    case 'ArrowDown':
      e.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, displayResults.value.length - 1)
      scrollToSelected()
      break
    case 'ArrowUp':
      e.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      scrollToSelected()
      break
    case 'Enter':
      e.preventDefault()
      if (displayResults.value[selectedIndex.value]) {
        navigateTo(displayResults.value[selectedIndex.value])
      }
      break
    case 'Escape':
      visible.value = false
      break
  }
}

/** 滚动结果列表，确保选中项可见 */
function scrollToSelected() {
  nextTick(() => {
    const active = document.querySelector('.command-palette .result-item.active')
    active?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  })
}

// ── 导航 ──────────────────────────────────────────────
function navigateTo(book: Book) {
  visible.value = false
  recordRecentBook(book.id)
  router.push(`/reader/${book.id}/1`)
}

// ── 对话框生命周期 ────────────────────────────────────
function onOpened() {
  nextTick(() => {
    // 聚焦搜索输入框
    inputRef.value?.focus()
    inputRef.value?.select()
    // 确保全量数据已加载
    if (booksStore.allBooks.length === 0) {
      booksStore.fetchAllBooks()
    }
  })
}

function onClosed() {
  query.value = ''
  selectedIndex.value = 0
}

// ── 全局快捷键 Ctrl+K ─────────────────────────────────
function onGlobalKeydown(e: KeyboardEvent) {
  // 仅在未聚焦在输入框时拦截 Ctrl+K
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
    // 如果焦点在输入框中，让浏览器处理（例如搜索页的搜索框）
    if (tag === 'input' || tag === 'textarea') return
    e.preventDefault()
    visible.value = !visible.value
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})

// ── 高亮匹配 ──────────────────────────────────────────
function highlightMatch(text: string): string {
  const q = query.value.trim()
  if (!q || q.length < 2) return escapeHtml(text)
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return escapeHtml(text).replace(regex, '<mark class="palette-highlight">$1</mark>')
}
</script>

<style scoped>
/* ── 命令面板整体 ──────────────────────────────────── */
.command-palette {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ── 输入框 ────────────────────────────────────────── */
.palette-input {
  margin-bottom: 8px;
}

.palette-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  padding: 4px 12px;
}

.palette-input :deep(.el-input__inner) {
  font-size: 15px;
}

.shortcut-hint {
  font-size: 11px;
  color: var(--muted);
  background: var(--border);
  padding: 1px 6px;
  border-radius: 3px;
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
}

/* ── 结果区域 ──────────────────────────────────────── */
.results {
  max-height: 320px;
  overflow-y: auto;
}

/* 移动端：结果区上限随视口收缩，避免小屏滚动过深 */
@media (max-width: 640px) {
  .results {
    max-height: min(320px, 55vh);
  }
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 4px 4px;
}

/* ── 结果条目 ──────────────────────────────────────── */
.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
}

.result-item:hover,
.result-item.active {
  background: var(--accent-ice-soft, rgba(100, 180, 255, 0.1));
}

.book-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.book-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.book-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-author {
  font-size: 12px;
  color: var(--muted);
}

.mark {
  color: var(--accent-warm);
  font-size: 14px;
  flex-shrink: 0;
}

.chapter-count {
  font-size: 11px;
  color: var(--muted);
  flex-shrink: 0;
}

/* ── 高亮匹配 ──────────────────────────────────────── */
:deep(.palette-highlight) {
  background: var(--warm-mark-bg);
  color: var(--warm-mark-fg);
  padding: 0 1px;
  border-radius: 2px;
}

/* ── 无结果 ────────────────────────────────────────── */
.no-results {
  text-align: center;
  padding: 24px;
  color: var(--muted);
  font-size: 14px;
}

/* ── 底部快捷键提示 ────────────────────────────────── */
.palette-footer {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
}

.palette-footer kbd {
  display: inline-block;
  padding: 1px 5px;
  background: var(--border);
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 10px;
  margin-right: 2px;
}
</style>

/* ── 全局样式（非 scoped，因为 el-dialog 渲染在 body 下） ── */
<style>
.command-palette-dialog {
  border-radius: 12px;
  overflow: hidden;
}

.command-palette-dialog .el-dialog__header {
  display: none;
}

.command-palette-dialog .el-dialog__body {
  padding: 16px 20px;
}

/* ── 移动端：面板宽度贴屏 ── */
@media (max-width: 640px) {
  .command-palette-dialog {
    width: calc(100% - 16px) !important;
  }
  .command-palette-dialog .el-dialog__body {
    padding: 12px;
  }
}
</style>
