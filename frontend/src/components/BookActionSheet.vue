<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍详情底部弹层（v2.3 移动端）
     书架页长按书籍唤起，样式参考起点 App 书籍详情弹层：
     · 头部：封面 + 书名 +「详情」入口 + 作者 + 开始阅读按钮
     · 操作九宫格：标记 / 移出书架（配置驱动，4 列网格，
       后续功能如下载 / 分组 / 置顶等只需向 actions 追加一项）
     · 书籍信息行：收录日期 / 状态 / 章节数 / 可下载格式
     · 底部预留区：为后续功能模块预留展示空间
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible && book" class="sheet-mask" @click.self="close">
        <div class="sheet-panel" role="dialog" aria-modal="true" :aria-label="`《${book.title}》详情`">
          <!-- 头部：封面 + 书名/作者 + 开始阅读 -->
          <div class="sheet-header">
            <div class="sheet-cover">
              <BookCover :title="book.title" :author="book.author" />
            </div>
            <div class="sheet-info">
              <div class="sheet-title-row">
                <span class="sheet-title">{{ book.title }}</span>
                <button class="sheet-detail-link" type="button" @click="goDetail">
                  详情 <el-icon><ArrowRight /></el-icon>
                </button>
              </div>
              <div class="sheet-author">{{ book.author }}</div>
            </div>
            <button
              v-if="book.chapter_count > 0"
              class="sheet-read-btn"
              type="button"
              @click="goRead"
            >
              开始阅读
            </button>
          </div>

          <!-- 操作网格（配置驱动：新增功能向 actions 追加即可，4 列自动排布） -->
          <div class="sheet-actions">
            <button
              v-for="act in actions"
              :key="act.key"
              type="button"
              class="sheet-action"
              :class="{ danger: act.danger, active: act.active }"
              @click="act.handler"
            >
              <el-icon class="sheet-action-icon"><component :is="act.icon" /></el-icon>
              <span>{{ act.label }}</span>
            </button>
          </div>

          <!-- 书籍信息 -->
          <div class="sheet-meta">
            <div class="sheet-meta-row">
              <span class="meta-label">收录日期</span>
              <span>{{ formatDate(book.added_at) }}</span>
            </div>
            <div class="sheet-meta-row">
              <span class="meta-label">抓取状态</span>
              <StatusBadge :status="book.status" />
            </div>
            <div class="sheet-meta-row">
              <span class="meta-label">章节数</span>
              <span>{{ book.chapter_count }} 章</span>
            </div>
            <div v-if="book.has_epub || book.has_txt" class="sheet-meta-row">
              <span class="meta-label">可下载</span>
              <span>
                <template v-if="book.has_epub">.epub</template>
                <template v-if="book.has_txt"> .txt</template>
              </span>
            </div>
          </div>

          <!-- 预留区：后续功能模块（分享 / 分组 / 订阅等）在此扩展 -->
          <div class="sheet-reserved" aria-hidden="true">· 更多功能敬请期待 ·</div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled, Delete, ArrowRight } from '@element-plus/icons-vue'
import { useBooksStore } from '@/stores'
import { toggleMarkBook } from '@/api/books'
import { formatDate } from '@/utils'
import type { Book } from '@/types'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const props = defineProps<{ bookId: string | null }>()
const visible = defineModel<boolean>({ default: false })

const router = useRouter()
const booksStore = useBooksStore()

/** 实时书籍数据（标记切换 / 删除后 store 同步，弹层自动刷新） */
const book = computed<Book | null>(() =>
  props.bookId ? booksStore.findShelfBook(props.bookId) : null
)

function close() {
  visible.value = false
}

function goDetail() {
  if (!book.value) return
  close()
  router.push(`/detail/${book.value.id}`)
}

function goRead() {
  if (!book.value) return
  close()
  router.push(`/reader/${book.value.id}/1`)
}

/** 星标标记：同步书架各列表并按优先级重排（标记置顶） */
async function toggleMark() {
  if (!book.value) return
  try {
    const { data } = await toggleMarkBook(book.value.id)
    if (data.success && data.data) {
      booksStore.upsertShelfBook(data.data)
      booksStore.resortLists()
      ElMessage.success(data.data.is_marked ? '已标记' : '已取消标记')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || '操作失败')
  }
}

/** 移出书架：二次确认后删除并关闭弹层 */
function confirmDelete() {
  if (!book.value) return
  const target = book.value
  ElMessageBox.confirm(
    `确定要删除《${target.title}》吗？\`.epub\` 和 \`.txt\` 文件将同时被删除`,
    '确认删除',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    try {
      await booksStore.removeBook(target.id)
      close()
      ElMessage.success('小说已删除')
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.error || err.message || '删除失败')
    }
  }).catch(() => {})
}

/** 操作网格配置：新增功能在此追加（4 列网格自动排布，无需改布局） */
const actions = computed(() => {
  if (!book.value) return []
  return [
    {
      key: 'mark',
      label: book.value.is_marked ? '取消标记' : '标记',
      icon: book.value.is_marked ? StarFilled : Star,
      active: book.value.is_marked,
      danger: false,
      handler: toggleMark
    },
    {
      key: 'delete',
      label: '移出书架',
      icon: Delete,
      active: false,
      danger: true,
      handler: confirmDelete
    }
  ]
})

// 弹层打开时锁定背景滚动 + Esc 关闭
function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}
watch(visible, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) window.addEventListener('keydown', onEsc)
  else window.removeEventListener('keydown', onEsc)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEsc)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: color-mix(in oklch, black 45%, transparent);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.sheet-panel {
  width: 100%;
  max-width: 560px;
  max-height: 82vh;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: 20px 20px 0 0;
  padding: 20px 16px calc(env(safe-area-inset-bottom, 0px) + 20px);
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 -8px 32px color-mix(in oklch, black 25%, transparent);
}

/* 滑入 / 滑出动画 */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.22s ease;
}
.sheet-enter-active .sheet-panel,
.sheet-leave-active .sheet-panel {
  transition: transform 0.28s cubic-bezier(0.32, 0.72, 0.35, 1);
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from .sheet-panel,
.sheet-leave-to .sheet-panel {
  transform: translateY(100%);
}

/* ── 头部 ── */
.sheet-header {
  display: flex;
  align-items: center;
  gap: 14px;
}
.sheet-cover :deep(.book-cover) {
  width: 64px;
  height: 86px;
  padding: 8px 7px 7px;
}
.sheet-cover :deep(.cover-title) {
  font-size: 11px;
}
.sheet-info {
  flex: 1;
  min-width: 0;
}
.sheet-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.sheet-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--fg);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sheet-detail-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--accent-ice);
  font-size: 13px;
  padding: 4px 0;
}
.sheet-author {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}
.sheet-read-btn {
  flex-shrink: 0;
  border: none;
  cursor: pointer;
  background: color-mix(in oklch, var(--accent-warm) 16%, var(--surface));
  color: var(--accent-warm);
  font-weight: 600;
  font-size: 14px;
  padding: 10px 10px;
  border-radius: 999px;
}

/* ── 操作网格（4 列，后续功能追加自动排布） ── */
.sheet-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: color-mix(in oklch, var(--fg) 4%, var(--surface));
  border-radius: 14px;
  padding: 14px 6px;
}
.sheet-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--fg);
  font-size: 12px;
  padding: 6px 0;
  border-radius: 10px;
}
.sheet-action-icon {
  font-size: 24px;
}
.sheet-action.active {
  color: var(--accent-warm);
}
.sheet-action.danger {
  color: var(--danger);
}

/* ── 书籍信息行 ── */
.sheet-meta {
  display: flex;
  flex-direction: column;
}
.sheet-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 4px;
  font-size: 13px;
  color: var(--fg);
  border-bottom: 1px dashed var(--border);
}
.sheet-meta-row:last-child {
  border-bottom: none;
}
.meta-label {
  color: var(--muted);
}

/* ── 预留区 ── */
.sheet-reserved {
  text-align: center;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.12em;
}
</style>
