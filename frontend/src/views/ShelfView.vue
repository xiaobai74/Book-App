<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书架首页
     v1.2 — 新增书架快速检索：搜索栏、快捷筛选标签
     v1.3.2 — 搜索改为点击「搜索」按钮 / 按 Enter 触发
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

        <!-- ── v1.2 新增：书架搜索栏 ──────────────────────────── -->
        <div class="shelf-search" v-if="booksStore.bookCount > 0 || searchKeyword">
          <div class="shelf-search-row">
            <el-input
              v-model="searchKeyword"
              :placeholder="aiSearchMode ? '用自然语言描述你想找的书…' : '搜索书名或作者…'"
              clearable
              :prefix-icon="Search"
              size="large"
              :disabled="aiSearching"
              @input="onSearchInput"
              @keyup.enter="onSearchKeyup"
              @clear="onSearchClear"
              class="shelf-search-input"
            />
            <el-button
              type="primary"
              size="large"
              class="search-submit-btn"
              :loading="aiSearchMode && aiSearching"
              :disabled="searchKeyword.trim().length < 2"
              @click="performSearch"
            >
              {{ aiSearchMode ? 'AI 搜索' : '搜索' }}
            </el-button>
            <el-radio-group
              v-model="aiSearchMode"
              size="small"
              class="search-mode-toggle"
              @change="onAiModeChange"
            >
              <el-radio-button :value="false">普通</el-radio-button>
              <el-radio-button :value="true">
                <span class="ai-label">🤖 AI 语义</span>
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- 关键词已编辑但尚未点击搜索的提示 -->
          <div v-if="hasPendingSearch" class="search-pending-hint" role="status">
            输入已更新，点击「{{ aiSearchMode ? 'AI 搜索' : '搜索' }}」按钮或按 Enter 查看结果
          </div>

          <!-- AI 搜索进度提示（aria-live：搜索状态由读屏软件播报） -->
          <div v-if="aiSearching" class="ai-search-progress" aria-live="polite">
            <span class="ai-search-dots">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </span>
            <span class="ai-search-text">AI 正在理解"{{ searchKeyword }}"的含义，在书架中匹配相关书籍…</span>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="booksStore.loading" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 书架内容（非加载中） -->
        <template v-else>
          <!-- ── v1.2 增强：筛选标签（AI 搜索模式下隐藏，因为不适用） ── -->
          <div class="shelf-filter" v-if="!aiSearchMode && (displayBooks.length > 0 || filterTab !== 'all')">
            <div class="scroll-x shelf-filter-tabs">
              <el-radio-group v-model="filterTab" size="small" class="filter-group" @change="handleFilterChange">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="marked">已标记</el-radio-button>
                <el-radio-button value="done">抓取完成</el-radio-button>
                <el-radio-button value="has_epub">有 EPUB</el-radio-button>
              </el-radio-group>
            </div>
            <span v-if="hasAppliedSearch && displayBooks.length > 0" class="search-hint">
              搜索 "{{ appliedSearchKeyword }}" 找到 {{ displayBooks.length }} 本
            </span>
          </div>

          <!-- 空状态 -->
          <div v-if="displayBooks.length === 0 && !booksStore.loading" class="empty-state">
            <!-- AI 搜索中：显示等待提示 -->
            <template v-if="aiSearching">
              <div class="loading-bar"></div>
              <p style="margin-top:12px">AI 正在理解你的需求…</p>
              <p style="font-size:12px;margin-top:6px;color:var(--muted)">一般情况下 5-15 秒可完成，请耐心等待</p>
            </template>
            <template v-else-if="hasAppliedSearch">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
                  <circle cx="11" cy="11" r="7"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </div>
              <p>未找到匹配 "{{ appliedSearchKeyword }}" 的书籍</p>
              <p style="font-size:12px;margin-top:6px;color:var(--muted)">试试其他关键词，或检查拼写是否正确</p>
              <div style="margin-top:16px;display:flex;gap:12px;justify-content:center">
                <el-button @click="clearSearch">清除搜索</el-button>
                <el-button type="primary" @click="$router.push('/search')">去外部搜索</el-button>
              </div>
            </template>
            <template v-else>
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
            </template>
          </div>

          <!-- 书籍列表 -->
          <div v-else class="stack" style="gap:12px">
          <div v-for="book in displayBooks" :key="book.id" class="book-card" :class="{ 'ai-result': isAiSearchResult(book) }">
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
                    <!-- v1.2: 搜索结果高亮匹配文本（仅对已生效的搜索词高亮） -->
                    <span v-if="hasAppliedSearch" v-html="highlightMatch(book.title)"></span>
                    <span v-else>{{ book.title }}</span>
                  </router-link>
                  <div class="book-author">
                    <span v-if="hasAppliedSearch" v-html="highlightMatch(book.author)"></span>
                    <span v-else>{{ book.author }}</span>
                  </div>
                  <!-- v1.3: AI 搜索结果匹配原因和分数 -->
                  <div v-if="isAiSearchResult(book)" class="ai-match-info">
                    <span class="ai-match-score">{{ getAiScore(book) }}%</span>
                    <span class="ai-match-reason">{{ getAiReason(book) }}</span>
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
import { Plus, Delete, Search, Reading } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import { checkSourceUrl, toggleMarkBook, aiSearchBooks } from '@/api/books'
import type { Book, AiSearchResult } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const booksStore = useBooksStore()

// ── v1.2 新增：搜索状态（v1.3.2：由防抖自动搜索改为按钮/Enter 触发） ──
const searchKeyword = ref('')
/** 普通搜索已生效的关键词（点击搜索后更新；输入未生效时为空） */
const appliedKeyword = ref('')

// ── v1.3 新增：AI 搜索状态 ────────────────────────────
const aiSearchMode = ref(false)
const aiSearching = ref(false)
const aiSearchResults = ref<AiSearchResult[]>([])
// AI 请求序号：模式切换/连续搜索时丢弃过期响应，防止旧结果覆盖新结果
let aiRequestSeq = 0
// 已生效的 AI 搜索词：输入变更后立即失效旧结果，等待用户再次点击搜索
const appliedAiQuery = ref('')

/** AI 搜索是否已生效（点击搜索后为 true；编辑关键词或清除后为 false） */
const isAiApplied = computed(() => {
  if (!aiSearchMode.value) return false
  if (appliedAiQuery.value.trim().length < 2) return false
  return searchKeyword.value.trim() === appliedAiQuery.value.trim()
})

// ── v1.2 新增：筛选标签 ────────────────────────────────
type FilterTab = 'all' | 'marked' | 'done' | 'has_epub'
const filterTab = ref<FilterTab>('all')

// ── v1.2 新增：展示列表（根据搜索/筛选动态计算） ──
/** 高亮与空状态使用的"已生效"关键词：未点击搜索时为空，避免对未搜索内容高亮 */
const appliedSearchKeyword = computed(() => {
  if (aiSearchMode.value) return isAiApplied.value ? appliedAiQuery.value : ''
  return appliedKeyword.value
})
const hasAppliedSearch = computed(() => appliedSearchKeyword.value.trim().length >= 2)

/** 关键词已编辑但尚未点击搜索（提示用户按按钮或 Enter） */
const hasPendingSearch = computed(() => {
  if (hasAppliedSearch.value) return false
  const q = searchKeyword.value.trim()
  if (aiSearchMode.value) {
    return q.length >= 2 && q !== appliedAiQuery.value.trim()
  }
  return q.length >= 2 && q !== appliedKeyword.value
})

const displayBooks = computed<Book[]>(() => {
  const hasActiveSearch = appliedKeyword.value && appliedKeyword.value.trim().length >= 2
  const hasActiveFilter = filterTab.value !== 'all'

  // v1.3.2: AI 搜索模式 — 仅在 AI 搜索已生效（点击过搜索且关键词未变更）时展示 AI 结果
  if (aiSearchMode.value && isAiApplied.value) {
    return aiSearchResults.value.map(r => ({
      id: r.book_id,
      title: r.title,
      author: r.author,
      source_url: null,
      status: 'idle' as const,
      chapter_count: 0,
      has_epub: false,
      has_txt: false,
      is_marked: false,
      marked_at: null,
      added_at: '',
      // 附加字段（非标准 Book 字段，仅用于展示）
      _match_reason: r.match_reason,
      _score: r.score,
    } as Book & { _match_reason: string; _score: number }))
  }

  // 服务端搜索模式：显示服务端搜索结果（书架 > 200 本时自动切换）
  if (hasActiveSearch && !booksStore.isClientMode) {
    return booksStore.searchResults
  }

  // 客户端搜索或筛选模式：显示客户端过滤结果
  if ((hasActiveSearch || hasActiveFilter) && booksStore.isClientMode) {
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

// ── v1.3.2 搜索逻辑：点击搜索按钮 / 按 Enter 触发（不再防抖自动搜索） ──

/** 输入处理：关键词变更时使旧搜索结果失效（等待用户点击搜索），避免展示过期结果 */
function onSearchInput() {
  if (aiSearchMode.value) {
    // AI 模式：输入变化立即失效旧 AI 结果
    if (searchKeyword.value.trim() !== appliedAiQuery.value.trim()) {
      aiRequestSeq++  // 使在途 AI 请求失效
      aiSearching.value = false
      aiSearchResults.value = []
    }
  } else {
    // 普通模式：编辑关键词后失效旧结果，恢复当前筛选状态（等待点击搜索）
    const newQ = searchKeyword.value.trim()
    if (newQ !== appliedKeyword.value) {
      appliedKeyword.value = ''
      applyCurrentFilter()
    }
  }
}

/** 输入框 Enter 键处理：IME 组合输入（中文选词）期间的回车不触发搜索 */
function onSearchKeyup(e: KeyboardEvent) {
  if ((e as KeyboardEvent & { isComposing?: boolean }).isComposing) return
  performSearch()
}

/** 执行搜索（搜索按钮 / Enter 键入口，按当前模式分发） */
function performSearch() {
  if (aiSearchMode.value) {
    performAiSearch()
  } else {
    performLocalSearch()
  }
}

/** 普通搜索：点击搜索后生效，展示结果 */
function performLocalSearch() {
  const q = searchKeyword.value.trim()

  if (!q || q.length < 2) {
    // 关键词不足 2 字符：按当前筛选标签恢复
    appliedKeyword.value = ''
    applyCurrentFilter()
    return
  }

  appliedKeyword.value = q

  if (booksStore.isClientMode) {
    // 客户端过滤：在 allBooks 中按书名和作者匹配，再叠加筛选条件
    booksStore.clientFilter({
      keyword: q,
      marked: filterTab.value === 'marked' ? true : null,
      hasEpub: filterTab.value === 'has_epub' ? true : undefined,
      done: filterTab.value === 'done' ? true : undefined,
    })
  } else {
    // 服务端搜索（书架超大时）
    booksStore.search(q, 1, 20)
  }
}

/** AI 自然语言搜索 */
async function performAiSearch() {
  const seq = ++aiRequestSeq
  const q = searchKeyword.value.trim()
  if (!q || q.length < 2) {
    appliedAiQuery.value = ''
    aiSearchResults.value = []
    // 恢复客户端过滤模式显示
    if (booksStore.isClientMode) {
      booksStore.resetFilter()
    }
    return
  }

  appliedAiQuery.value = q
  aiSearching.value = true
  try {
    const { data } = await aiSearchBooks(q)
    if (seq !== aiRequestSeq) return  // 已有更新的 AI 搜索，丢弃过期响应
    if (data.success && data.data) {
      aiSearchResults.value = data.data
    } else {
      aiSearchResults.value = []
      ElMessage.warning('AI 搜索未找到匹配结果')
    }
  } catch (err: any) {
    if (seq !== aiRequestSeq) return
    aiSearchResults.value = []
    const msg = err?.response?.data?.error || err?.message || 'AI 搜索请求失败'
    ElMessage.error(msg)
  } finally {
    if (seq === aiRequestSeq) {
      aiSearching.value = false
    }
  }
}

/** AI 模式切换 */
function onAiModeChange(val: boolean) {
  aiRequestSeq++  // 使所有在途 AI 请求失效，避免旧结果覆盖新模式
  if (!val) {
    // 关闭 AI 模式 → 清除 AI 结果，恢复普通搜索状态
    appliedAiQuery.value = ''
    aiSearchResults.value = []
    aiSearching.value = false
    if (searchKeyword.value && searchKeyword.value.trim().length >= 2) {
      // 输入框已有有效关键词 → 重新执行普通搜索，恢复切换前的状态
      performLocalSearch()
    } else {
      // 无关键词 → 恢复全量缓存（优先本地缓存，避免不必要的服务端请求）
      booksStore.resetFilter()
      if (booksStore.allBooks.length === 0) {
        booksStore.fetchBooks(1, 20, null)
      }
    }
  } else {
    // 开启 AI 模式 → 清除普通搜索生效状态、显示全量书架，等待用户点击「AI 搜索」
    appliedKeyword.value = ''
    appliedAiQuery.value = ''
    aiSearchResults.value = []
    booksStore.resetFilter()
  }
}

/** 清空搜索 */
function onSearchClear() {
  aiRequestSeq++
  searchKeyword.value = ''
  appliedKeyword.value = ''
  appliedAiQuery.value = ''
  aiSearchResults.value = []
  aiSearching.value = false
  filterTab.value = 'all'
  booksStore.resetFilter()
  booksStore.searchResults = []
  booksStore.fetchBooks(1, 20, null)
}

function clearSearch() {
  aiSearchMode.value = false
  onSearchClear()
}

/** 应用当前筛选标签（不含搜索关键词） */
function applyCurrentFilter() {
  booksStore.clientFilter({
    marked: filterTab.value === 'marked' ? true : null,
    hasEpub: filterTab.value === 'has_epub' ? true : undefined,
    done: filterTab.value === 'done' ? true : undefined,
  })
}

/** 筛选标签切换 */
function handleFilterChange(val: FilterTab) {
  if (searchKeyword.value && searchKeyword.value.trim().length >= 2) {
    // 有搜索关键词时：关键词 + 筛选条件叠加（同时更新已生效词）
    performLocalSearch()
  } else if (val === 'all') {
    // 全部：恢复全量书架
    appliedKeyword.value = ''
    booksStore.fetchBooks(1, 20, null)
  } else {
    // 仅筛选（无搜索关键词）
    appliedKeyword.value = ''
    applyCurrentFilter()
  }
}

// ── v1.2 新增：高亮匹配文本 ────────────────────────────

/** 高亮搜索关键词匹配的部分 */
function highlightMatch(text: string): string {
  const q = appliedSearchKeyword.value.trim()
  if (!q || q.length < 2) return escapeHtml(text)
  // 转义正则特殊字符
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return escapeHtml(text).replace(regex, '<mark class="search-highlight">$1</mark>')
}

// ── v1.3 新增：AI 搜索结果辅助函数 ────────────────────
type AiBook = Book & { _match_reason?: string; _score?: number }

/** 判断是否为 AI 搜索结果（含有 _match_reason / _score 扩展字段） */
function isAiSearchResult(book: Book): boolean {
  const ai = book as AiBook
  return !!(ai._match_reason || (ai._score !== undefined && ai._score !== null))
}

/** 获取 AI 搜索的匹配分数 */
function getAiScore(book: Book): number {
  return (book as AiBook)._score ?? 0
}

/** 获取 AI 搜索的匹配原因 */
function getAiReason(book: Book): string {
  return (book as AiBook)._match_reason ?? ''
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
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

/* ── v1.2 新增：搜索栏 ──────────────────────────────── */
.shelf-search {
  margin-bottom: 16px;
}

.shelf-search-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.shelf-search-input {
  flex: 1;
}

/* v1.3.2 新增：搜索触发按钮 */
.search-submit-btn {
  flex-shrink: 0;
  min-width: 96px;
}

/* v1.3.2 新增：关键词已编辑未搜索的提示 */
.search-pending-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}

.search-mode-toggle {
  flex-shrink: 0;
}

.ai-label {
  font-size: 12px;
  letter-spacing: 0.5px;
}

.shelf-search :deep(.el-input__wrapper) {
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s, border-color 0.2s;
}

.shelf-search :deep(.el-input__wrapper:hover) {
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

/* ── 筛选栏 ────────────────────────────────────────── */
.shelf-filter {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-hint {
  font-size: 13px;
  color: var(--muted);
}

/* ── 搜索高亮（暖黄底 + 深黄褐字，8.2:1 达标；统一使用暖色令牌） ── */
:deep(.search-highlight) {
  background: var(--warm-mark-bg);
  color: var(--warm-mark-fg);
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 500;
}

/* ── v1.3: AI 搜索结果样式（v1.4：匹配分数徽标改为暖金点缀） ── */
.ai-result {
  border-left: 3px solid var(--accent);
}

.ai-result:hover {
  border-left-color: var(--accent-hover);
}

.ai-match-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.ai-match-score {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  padding: 0 6px;
  background: var(--warm-soft);
  color: var(--warm-fg);
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  border-radius: 4px;
}

.ai-match-reason {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
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

/* ── AI 搜索进度提示 ────────────────────────────── */
.ai-search-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--accent-ice-soft, rgba(100, 180, 255, 0.06));
  border-radius: var(--radius-md);
  border: 1px solid var(--accent-ice-soft, rgba(100, 180, 255, 0.15));
}

.ai-search-text {
  font-size: 13px;
  color: var(--accent-ice);
  flex: 1;
}

/* 三点跳动动画的 keyframes 与 animation 声明已移至 global.css
   （全局零动画样式会禁用 scoped 动画，故在全局统一豁免） */
.ai-search-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.ai-search-dots .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-ice);
}

/* ── v1.5 移动端适配 ────────────────────────────── */
@media (max-width: 900px) {
  .shelf-search-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .search-submit-btn {
    width: 100%;
  }
  .search-mode-toggle {
    align-self: flex-start;
  }
}

@media (max-width: 640px) {
  /* 筛选标签整行横向滚动（含搜索提示） */
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
  .search-hint {
    font-size: 12px;
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
