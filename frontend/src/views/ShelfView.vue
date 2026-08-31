<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书架首页
     v1.2 — 新增书架快速检索：搜索栏、快捷筛选标签
     v1.3.2 — 搜索改为点击「搜索」按钮 / 按 Enter 触发
     v1.9 — 书架搜索栏合并到顶部主搜索框（TopNav，普通 / AI 双模式），
           本页保留筛选标签与书籍列表展示
     v2.2 — 书架缓存优化（books store.ensureShelf）：切页返回瞬间恢复
           缓存数据，仅首次进入展示加载骨架；超过 60s 后返回自动
           后台静默刷新（不阻断展示）；客户端模式筛选标签零请求
     v2.3 — 移动端：九宫格视图模式（持久化）；长按书籍唤起详情
           底部弹层（BookActionSheet），标记 / 删除移入弹层，
           弹层底部预留后续功能扩展空间
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav />

    <section class="section">
      <div class="container">
        <!-- v2.5.2：页头直置背景上，文字颜色走自适应墨色变量（深色背景自动换暖白） -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <div>
            <h2 class="ink-title" style="font-size:clamp(22px,3vw,28px);font-weight:600">我的书架</h2>
            <p class="lead" style="margin-top:4px">共 <span class="num" style="font-family:var(--font-mono)">{{ booksStore.bookCount }}</span> 本小说</p>
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <!-- v2.3：视图模式切换（列表 / 九宫格，持久化） -->
            <el-button
              circle
              :icon="viewMode === 'list' ? Grid : List"
              :title="viewMode === 'list' ? '切换九宫格视图' : '切换列表视图'"
              :aria-label="viewMode === 'list' ? '切换九宫格视图' : '切换列表视图'"
              @click="toggleViewMode"
            />
            <el-button type="primary" class="shelf-add-btn" @click="showAddDialog = true">
              <el-icon style="margin-right:6px"><Plus /></el-icon>
              添加小说
            </el-button>
          </div>
        </div>

        <!-- ── v1.9：书架搜索栏已合并到顶部主搜索框（TopNav） ── -->

        <!-- 加载中（仅首次加载无缓存时展示；切页返回直接恢复缓存，v2.2） -->
        <div v-if="booksStore.loading && !booksStore.shelfLoaded" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 书架内容（非加载中） -->
        <template v-else>
          <!-- ── v1.2 增强：筛选标签 ── -->
          <div class="shelf-filter" v-if="displayBooks.length > 0 || filterTab !== 'all'">
            <div class="scroll-x shelf-filter-tabs">
              <el-radio-group v-model="filterTab" size="small" class="filter-group" @change="handleFilterChange">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="marked">已标记</el-radio-button>
                <el-radio-button value="done">抓取完成</el-radio-button>
                <el-radio-button value="has_epub">有 EPUB</el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="displayBooks.length === 0 && !booksStore.loading" class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--onbg-muted)">
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
              </svg>
            </div>
            <p>书架空空如也，去搜索一本小说吧～</p>
            <el-button type="primary" style="margin-top:16px" @click="$router.push('/search')">
              去搜索
            </el-button>
          </div>

          <!-- 书籍列表（v2.3：列表 / 九宫格双模式；长按唤起详情弹层） -->
          <div v-else>
            <!-- 列表模式 -->
            <div v-if="viewMode === 'list'" class="stack" style="gap:12px">
              <div
                v-for="book in displayBooks" :key="book.id"
                class="book-card pressable"
                role="link"
                tabindex="0"
                :aria-label="`《${book.title}》，点击查看详情，长按打开操作面板`"
                @pointerdown="onPressStart($event, book)"
                @pointermove="onPressMove"
                @pointerup="onPressEnd"
                @pointercancel="onPressEnd"
                @click="onCardClick(book)"
                @contextmenu.prevent="openSheet(book)"
                @keyup.enter="goDetail(book)"
              >
                <div class="book-card-main" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
                  <div class="book-card-left" style="display:flex;align-items:flex-start;gap:16px;min-width:0">
                    <div class="shelf-cover">
                      <BookCover :title="book.title" :author="book.author" />
                    </div>
                    <div class="book-card-info" style="min-width:0">
                      <div class="book-title">{{ book.title }}</div>
                      <div class="book-author">{{ book.author }}</div>
                    </div>
                  </div>
                  <div class="book-card-actions" style="display:flex;align-items:center;gap:10px">
                    <!-- v1.2: 阅读按钮（v1.6：填充样式 + 图标 + 圆角） -->
                    <el-button
                      v-if="book.chapter_count > 0"
                      size="small"
                      type="primary"
                      round
                      :icon="Reading"
                      @click.stop="goRead(book)"
                    >
                      阅读
                    </el-button>
                  </div>
                </div>
                <div class="book-meta-row">
                  <span>{{ formatDate(book.added_at) }}</span>
                  <StatusBadge :status="book.status" />
                  <span>{{ book.chapter_count }} 章</span>
                  <span v-if="book.has_epub" style="color:var(--accent-ice)">.epub 可下载</span>
                  <span v-if="book.has_txt" style="color:var(--muted)">.txt</span>
                </div>
              </div>
            </div>

            <!-- 九宫格模式（v2.3） -->
            <div v-else class="shelf-grid">
              <div
                v-for="book in displayBooks" :key="book.id"
                class="grid-item pressable"
                role="link"
                tabindex="0"
                :aria-label="`《${book.title}》，点击查看详情，长按打开操作面板`"
                @pointerdown="onPressStart($event, book)"
                @pointermove="onPressMove"
                @pointerup="onPressEnd"
                @pointercancel="onPressEnd"
                @click="onCardClick(book)"
                @contextmenu.prevent="openSheet(book)"
                @keyup.enter="goDetail(book)"
              >
                <div class="grid-cover">
                  <BookCover :title="book.title" :author="book.author" />
                  <span v-if="book.is_marked" class="grid-star" title="已标记">★</span>
                </div>
                <div class="grid-title">{{ book.title }}</div>
                <div class="grid-author">{{ book.author }}</div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </section>

    <footer class="pagefoot">
      <div class="container">© 小说管理App · 个人学习用途</div>
    </footer>

    <!-- 添加书籍对话框（v1.5：去掉固定宽度，全局小屏规则自适应） -->
    <el-dialog v-model="showAddDialog" title="添加小说" @opened="resetAddForm">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-position="top" @submit.prevent="handleAddBook">
        <el-form-item label="书名" prop="title">
          <el-input v-model="addForm.title" placeholder="请输入书名" />
        </el-form-item>
        <el-form-item label="作者" prop="author">
          <el-input v-model="addForm.author" placeholder="请输入作者" />
        </el-form-item>
        <el-form-item label="源站链接" prop="source_url">
          <el-input v-model="addForm.source_url" placeholder="https://… 小说目录页网址（任意网站均可，系统自动解析）">
            <template #append>
              <el-button
                :loading="checkingUrl"
                :disabled="!addForm.source_url.trim()"
                @click="handleCheckUrl"
              >
                检测
              </el-button>
            </template>
          </el-input>
          <div style="margin-top: 4px; font-size: 11px; color: var(--muted);">
            支持任意小说网站 URL。已配置的源站使用精确规则，未配置的网站自动使用通用解析策略。
            <router-link to="/crawl-sources" style="color: var(--accent-ice); text-decoration: underline;">
              管理自定义源站规则
            </router-link>
          </div>
          <div v-if="urlCheckResult !== null" style="margin-top: 6px; font-size: 12px;">
            <span v-if="urlCheckResult.reachable" style="color: var(--success)">✓ 源站可达 (HTTP {{ urlCheckResult.status_code }})</span>
            <span v-else style="color: var(--danger)">✗ {{ urlCheckResult.error_message }}</span>
            <div v-if="urlCheckResult.suggested_fix" style="color: var(--muted); margin-top: 2px;">
              💡 {{ urlCheckResult.suggested_fix }}
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="addingBook" @click="handleAddBook">添加到书架</el-button>
      </template>
    </el-dialog>

    <!-- v2.3：书籍详情底部弹层（长按唤起；标记 / 删除 / 预留扩展） -->
    <BookActionSheet v-model="sheetVisible" :book-id="sheetBookId" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Reading, Grid, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import { checkSourceUrl } from '@/api/books'
import type { Book } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import BookActionSheet from '@/components/BookActionSheet.vue'

const booksStore = useBooksStore()
const router = useRouter()

// ── v1.2 新增：筛选标签 ────────────────────────────────
type FilterTab = 'all' | 'marked' | 'done' | 'has_epub'
const filterTab = ref<FilterTab>('all')

// ── v1.2 新增：展示列表（根据筛选动态计算；v1.9 搜索已合并至主搜索框） ──
const displayBooks = computed<Book[]>(() => {
  const hasActiveFilter = filterTab.value !== 'all'
  if (hasActiveFilter && booksStore.isClientMode) {
    return booksStore.filteredBooks
  }
  // 正常浏览：客户端模式使用全量缓存（零延迟），服务端模式使用分页数据（>200 本时 allBooks 仅含前 200 条，不完整）
  return booksStore.isClientMode ? booksStore.allBooks : booksStore.books
})

onMounted(() => {
  // v2.2: 缓存优先加载——首次进入才发请求，切页返回瞬间恢复；
  // 超过 60s 未刷新时自动后台静默更新，不阻断展示
  booksStore.ensureShelf()
})

/** 应用当前筛选标签（不含搜索关键词；v1.9 搜索已合并至主搜索框） */
function applyCurrentFilter() {
  booksStore.clientFilter({
    marked: filterTab.value === 'marked' ? true : null,
    hasEpub: filterTab.value === 'has_epub' ? true : undefined,
    done: filterTab.value === 'done' ? true : undefined,
  })
}

/** 筛选标签切换（客户端模式本地过滤零请求；服务端模式才走分页接口） */
function handleFilterChange(val: FilterTab) {
  if (val === 'all') {
    if (booksStore.isClientMode) {
      // 全部：本地恢复全量书架，无需请求
      booksStore.resetFilter()
    } else {
      booksStore.fetchBooks(1, 20, null)
    }
  } else {
    // 仅筛选
    applyCurrentFilter()
  }
}

// ── v2.3 视图模式：列表 / 九宫格（localStorage 持久化） ────────
type ViewMode = 'list' | 'grid'
const viewMode = ref<ViewMode>(localStorage.getItem('shelf_viewMode') === 'grid' ? 'grid' : 'list')

function toggleViewMode() {
  viewMode.value = viewMode.value === 'list' ? 'grid' : 'list'
  localStorage.setItem('shelf_viewMode', viewMode.value)
}

// ── v2.3 长按唤起详情弹层（标记 / 删除已移入弹层） ────────
const LONG_PRESS_MS = 480
let pressTimer: ReturnType<typeof setTimeout> | null = null
let pressX = 0
let pressY = 0
let suppressClick = false

const sheetVisible = ref(false)
const sheetBookId = ref<string | null>(null)

function openSheet(book: Book) {
  sheetBookId.value = book.id
  sheetVisible.value = true
}

// 弹层关闭时清理抑制标志：覆盖「长按后滑动手指不产生 click」的边界场景，
// 避免残留标志吞掉下一次正常点击
watch(sheetVisible, (v) => {
  if (!v) suppressClick = false
})

function clearPressTimer() {
  if (pressTimer) {
    clearTimeout(pressTimer)
    pressTimer = null
  }
}

function onPressStart(e: PointerEvent, book: Book) {
  // 按在卡片内按钮（阅读等）上不启动长按
  if ((e.target as HTMLElement).closest('.el-button')) return
  clearPressTimer()
  pressX = e.clientX
  pressY = e.clientY
  pressTimer = setTimeout(() => {
    pressTimer = null
    suppressClick = true
    navigator.vibrate?.(30) // 移动端长按震动反馈（设备支持时）
    openSheet(book)
  }, LONG_PRESS_MS)
}

/** 位移超 10px 视为滚动手势，取消长按 */
function onPressMove(e: PointerEvent) {
  if (Math.hypot(e.clientX - pressX, e.clientY - pressY) > 10) clearPressTimer()
}

function onPressEnd() {
  clearPressTimer()
}

/** 单击进详情；长按后的 click 事件被抑制 */
function onCardClick(book: Book) {
  if (suppressClick) {
    suppressClick = false
    return
  }
  goDetail(book)
}

function goDetail(book: Book) {
  router.push(`/detail/${book.id}`)
}

function goRead(book: Book) {
  router.push(`/reader/${book.id}/1`)
}

// ── 添加书籍 ────────────────────────────────────
const showAddDialog = ref(false)
const addingBook = ref(false)
const checkingUrl = ref(false)
const urlCheckResult = ref<{
  reachable: boolean
  status_code: number | null
  error_message: string | null
  suggested_fix: string | null
} | null>(null)
const addFormRef = ref<FormInstance>()

const addForm = reactive({
  title: '',
  author: '',
  source_url: ''
})

const addRules: FormRules = {
  title: [
    { required: true, message: '请输入书名', trigger: 'blur' },
    { min: 1, max: 500, message: '书名长度为 1-500 字符', trigger: 'blur' }
  ],
  author: [
    { max: 255, message: '作者最长 255 字符', trigger: 'blur' }
  ],
  source_url: [
    { max: 2048, message: '链接最长 2048 字符', trigger: 'blur' }
  ]
}

function resetAddForm() {
  addForm.title = ''
  addForm.author = ''
  addForm.source_url = ''
  urlCheckResult.value = null
  addFormRef.value?.resetFields()
}

async function handleCheckUrl() {
  const url = addForm.source_url.trim()
  if (!url) return
  checkingUrl.value = true
  urlCheckResult.value = null
  try {
    const { data } = await checkSourceUrl(url)
    if (data.success && data.data) {
      urlCheckResult.value = data.data
    }
  } catch {
    urlCheckResult.value = {
      reachable: false,
      status_code: null,
      error_message: '连通性检测请求失败',
      suggested_fix: '请稍后重试',
    }
  } finally {
    checkingUrl.value = false
  }
}

async function handleAddBook() {
  if (!addFormRef.value) return
  await addFormRef.value.validate(async (valid) => {
    if (!valid) return
    addingBook.value = true
    try {
      await booksStore.addBook({
        title: addForm.title.trim(),
        author: addForm.author.trim() || '未知',
        source_url: addForm.source_url.trim() || null
      })
      showAddDialog.value = false
      ElMessage.success(`《${addForm.title.trim()}》已添加到书架`)
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.error || err.message || '添加失败')
    } finally {
      addingBook.value = false
    }
  })
}

</script>

<style scoped>
.stack { display: flex; flex-direction: column; }
.lead { font-size: 15px; color: var(--onbg-muted); }   /* v2.5.2：直置背景，自适应墨色 */
.num { font-family: var(--font-mono); }

/* ── 筛选栏 ────────────────────────────────────────── */
.shelf-filter {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* ── 卡片操作按钮（v1.6：填充/描边样式，更像按钮） ── */
.book-card-actions :deep(.el-button) {
  font-weight: 500;
}

/* ── v2.3 长按交互：禁选中 + 按压微缩反馈 ── */
.pressable {
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  transition: transform 0.12s ease;
}
.pressable:active {
  transform: scale(0.985);
}

/* ── v2.3 九宫格模式 ── */
.shelf-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 12px;
}
.grid-cover {
  position: relative;
}
.grid-cover :deep(.book-cover) {
  width: 100%;
  height: auto;
  aspect-ratio: 3 / 4;
  padding: 12% 10% 10%;
}
.grid-cover :deep(.cover-title) {
  font-size: 14px;
}
.grid-cover :deep(.cover-author) {
  font-size: 10px;
}
.grid-star {
  position: absolute;
  top: 6px;
  right: 8px;
  color: var(--accent-warm);
  font-size: 14px;
  text-shadow: 0 1px 2px color-mix(in oklch, black 35%, transparent);
}
.grid-title {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--onbg-title);   /* v2.5.2：直置背景，深色背景下自动换暖白淡墨 */
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.grid-author {
  margin-top: 2px;
  font-size: 11px;
  color: var(--onbg-muted);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ── v1.5 移动端适配 ────────────────────────────── */
@media (max-width: 640px) {
  /* 筛选标签整行横向滚动 */
  .shelf-filter {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .shelf-filter-tabs {
    width: 100%;
    padding-bottom: 4px;
  }
  .filter-group {
    display: inline-flex;
    flex-wrap: nowrap;
  }

  /* 卡片内边距收紧 */
  .book-card {
    padding: 14px;
    gap: 10px;
  }

  /* 封面缩至 92px 高，给书名信息腾出空间 */
  .shelf-cover :deep(.book-cover) {
    width: 92px;
    height: 124px;
    padding: 10px 10px 10px;
  }
  .shelf-cover :deep(.book-cover .cover-title) {
    font-size: 13px;
  }

  /* 信息区允许换行，长标题不挤压操作按钮 */
  .book-card-left {
    flex: 1;
    gap: 10px;
  }
  .book-card-info {
    flex: 1;
  }
  .book-title {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.35;
  }

  /* 操作按钮压缩内边距，保证卡片一行放下 */
  .book-card-actions {
    gap: 6px;
  }
  .book-card-actions :deep(.el-button) {
    padding: 6px 10px;
    margin: 0;
  }

  .book-meta-row {
    gap: 8px;
    font-size: 11px;
  }
}
</style>
