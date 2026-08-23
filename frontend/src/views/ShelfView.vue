<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书架首页
     v1.2 — 新增书架快速检索：搜索栏、快捷筛选标签
     v1.3.2 — 搜索改为点击「搜索」按钮 / 按 Enter 触发
     v1.9 — 书架搜索栏合并到顶部主搜索框（TopNav，普通 / AI 双模式），
           本页保留筛选标签与书籍列表展示
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav />

    <section class="section">
      <div class="container">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <div>
            <h2 style="font-size:clamp(22px,3vw,28px);font-weight:600">我的书架</h2>
            <p class="lead" style="margin-top:4px">共 <span class="num" style="font-family:var(--font-mono)">{{ booksStore.bookCount }}</span> 本小说</p>
          </div>
          <el-button type="primary" class="shelf-add-btn" @click="showAddDialog = true">
            <el-icon style="margin-right:6px"><Plus /></el-icon>
            添加小说
          </el-button>
        </div>

        <!-- ── v1.9：书架搜索栏已合并到顶部主搜索框（TopNav） ── -->

        <!-- 加载中 -->
        <div v-if="booksStore.loading" class="empty-state">
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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
              </svg>
            </div>
            <p>书架空空如也，去搜索一本小说吧～</p>
            <el-button type="primary" style="margin-top:16px" @click="$router.push('/search')">
              去搜索
            </el-button>
          </div>

          <!-- 书籍列表 -->
          <div v-else class="stack" style="gap:12px">
          <div v-for="book in displayBooks" :key="book.id" class="book-card">
            <div class="book-card-main" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
              <div class="book-card-left" style="display:flex;align-items:flex-start;gap:16px;min-width:0">
                <!-- 星标标记按钮 v1.2（v1.4：aria-pressed 状态 + ≥32px 目标尺寸） -->
                <button
                  class="mark-btn"
                  type="button"
                  :aria-pressed="book.is_marked"
                  :aria-label="book.is_marked ? '取消标记' : '标记此书'"
                  :title="book.is_marked ? '取消标记' : '标记此书'"
                  @click.stop="toggleMark(book)"
                >
                  <span v-if="book.is_marked" class="star star-filled">★</span>
                  <span v-else class="star star-empty">☆</span>
                </button>
                <router-link :to="`/detail/${book.id}`" class="shelf-cover">
                  <BookCover :title="book.title" :author="book.author" />
                </router-link>
                <div class="book-card-info" style="min-width:0">
                  <router-link :to="`/detail/${book.id}`" class="book-title">
                    {{ book.title }}
                  </router-link>
                  <div class="book-author">
                    {{ book.author }}
                  </div>
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
                  @click="$router.push(`/reader/${book.id}/1`)"
                >
                  阅读
                </el-button>
                <!-- 删除按钮（v1.6：plain danger 样式 + 圆角，文本颜色用自定义陶土红） -->
                <el-button type="danger" plain round :icon="Delete" size="small" class="card-delete-btn" @click="confirmDelete(book)">
                  删除
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus, Delete, Reading } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import { checkSourceUrl, toggleMarkBook } from '@/api/books'
import type { Book } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const booksStore = useBooksStore()

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

onMounted(async () => {
  // v1.2: 预加载全量数据用于客户端搜索
  try {
    await booksStore.fetchAllBooks(null)
  } catch {
    // 全量加载失败时回退——至少保证分页数据能用
    booksStore.searchMode = 'server'
  }
  try {
    await booksStore.fetchBooks(1, 20, null)
  } catch {
    // 分页加载失败时静默处理，页面显示空状态
  }
})

/** 应用当前筛选标签（不含搜索关键词；v1.9 搜索已合并至主搜索框） */
function applyCurrentFilter() {
  booksStore.clientFilter({
    marked: filterTab.value === 'marked' ? true : null,
    hasEpub: filterTab.value === 'has_epub' ? true : undefined,
    done: filterTab.value === 'done' ? true : undefined,
  })
}

/** 筛选标签切换 */
function handleFilterChange(val: FilterTab) {
  if (val === 'all') {
    // 全部：恢复全量书架
    booksStore.fetchBooks(1, 20, null)
  } else {
    // 仅筛选
    applyCurrentFilter()
  }
}

// ── 标记功能 v1.2 ────────────────────────────────────
async function toggleMark(book: Book) {
  try {
    const { data } = await toggleMarkBook(book.id)
    if (data.success && data.data) {
      // 更新本地状态 — books
      const idx = booksStore.books.findIndex(b => b.id === book.id)
      if (idx >= 0) {
        booksStore.books[idx] = data.data
      }
      // 同步更新 allBooks 缓存
      const allIdx = booksStore.allBooks.findIndex(b => b.id === book.id)
      if (allIdx >= 0) {
        booksStore.allBooks[allIdx] = data.data
      }
      // 同步更新 filteredBooks
      const filteredIdx = booksStore.filteredBooks.findIndex(b => b.id === book.id)
      if (filteredIdx >= 0) {
        booksStore.filteredBooks[filteredIdx] = data.data
      }
      // 同步更新 searchResults（服务端搜索模式下星标也应有反馈）
      const srIdx = booksStore.searchResults.findIndex(b => b.id === book.id)
      if (srIdx >= 0) {
        booksStore.searchResults[srIdx] = data.data
      }
      // 标记状态变更后按书架优先级（已标记置顶 → 时间倒序）重排
      booksStore.resortLists()
      ElMessage.success(data.data.is_marked ? '已标记' : '已取消标记')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || '操作失败')
  }
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

// ── 删除书籍 ────────────────────────────────────
function confirmDelete(book: Book) {
  ElMessageBox.confirm(
    `确定要删除《${book.title}》吗？\`.epub\` 和 \`.txt\` 文件将同时被删除`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await booksStore.removeBook(book.id)
      ElMessage.success('小说已删除')
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.error || err.message || '删除失败')
    }
  }).catch(() => {})
}
</script>

<style scoped>
.stack { display: flex; flex-direction: column; }
.lead { font-size: 15px; color: var(--muted); }
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

/* 删除按钮：plain danger 描边 + 自定义陶土红文本（对齐全局 --danger 令牌） */
.book-card-actions :deep(.card-delete-btn) {
  --el-button-text-color: var(--danger);
  --el-button-border-color: color-mix(in oklch, var(--danger) 40%, transparent);
  --el-button-hover-text-color: var(--surface);
  --el-button-hover-bg-color: var(--danger);
  --el-button-hover-border-color: var(--danger);
  --el-button-active-text-color: var(--surface);
  --el-button-active-bg-color: var(--danger);
  --el-button-active-border-color: var(--danger);
}

/* ── 标记按钮（v1.4：暖金星色 + ≥32px 目标尺寸，hover 用即时颜色反馈） ── */
.mark-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  min-width: 32px;
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mark-btn:hover .star-empty {
  color: var(--accent-warm);
}

.star {
  font-size: 22px;
  line-height: 1;
}

.star-empty {
  color: var(--muted);
}

.star-filled {
  color: var(--accent-warm);
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
