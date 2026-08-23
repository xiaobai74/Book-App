<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 统一搜索页面（v2.0：书架内搜索 + 全网源站搜索）
     v1.9 — 书架内 tab 支持普通 / AI 语义双模式：模式状态与
            TopNav 主搜索框共享（shelfSearch store），AI 结果
            展示匹配分数与原因（不分页），普通模式维持服务端分页
     v2.0 — AI 搜索开关（头像菜单）开启时，书架内 tab 下方显示
            普通 / AI 切换；未开启则书架内搜索默认普通搜索；
            全网搜索移除源站下拉筛选（始终搜索全部源站）
     v2.1 — 智能搜索模式路由：AI 开关开启后按查询意图自动选择
            搜索方式（自然语言描述 → AI 语义，书名/作者 → 普通），
            移除手动模式切换；结果区显示「自动使用 xx 搜索」标识，
            并提供一次性改用另一种方式重新搜索；全网搜索 tab 左上角
            原「搜索：」标题位置改为「← 返回书架」按钮
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-search="false" />

    <section class="section">
      <div class="container">
        <!-- 搜索栏：全网搜索 tab 显示返回书架按钮，书架内 tab 显示搜索标题 -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <el-button
            v-if="searchMode === 'web'"
            text
            size="small"
            class="back-to-shelf-btn"
            aria-label="返回书架"
            @click="$router.push('/shelf')"
          >
            ← 返回书架
          </el-button>
          <h2 v-else style="font-size:clamp(22px,3vw,28px);font-weight:600">
            {{ hasSearched ? `搜索："${currentQ}"` : '搜索小说' }}
          </h2>
          <div class="search-controls" style="display:flex;align-items:center;gap:8px;flex:0 1 480px">
            <!-- 搜索标签切换 -->
            <el-radio-group v-model="searchMode" size="small" class="mode-group" style="flex-shrink:0">
              <el-radio-button value="shelf">书架内</el-radio-button>
              <el-radio-button value="web">全网搜索</el-radio-button>
            </el-radio-group>
            <el-input
              v-model="searchQuery"
              :placeholder="queryPlaceholder"
              :prefix-icon="Search"
              clearable
              class="query-input"
              @keyup.enter="doSearch"
            >
              <template #append>
                <el-button
                  :icon="Search"
                  :loading="isSearching || (searchMode === 'shelf' && aiActive && shelfSearch.aiSearching)"
                  aria-label="搜索"
                  @click="doSearch"
                />
              </template>
            </el-input>
          </div>
        </div>

        <!-- ── 书架内搜索 tab（v1.9：普通搜索 + AI 语义搜索双模式） ── -->
        <template v-if="searchMode === 'shelf'">
          <!-- 初始状态 -->
          <div v-if="!hasSearched" class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
                <circle cx="11" cy="11" r="7"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
            <p v-if="shelfSearch.aiEnabled">输入书名、作者，或自然语言描述想找的书，自动匹配搜索方式</p>
            <p v-else>在已有书架中按书名或作者模糊搜索</p>
          </div>

          <!-- AI 搜索进度提示（aria-live：搜索状态由读屏软件播报） -->
          <div v-else-if="aiActive && shelfSearch.aiSearching" class="empty-state">
            <div class="ai-search-progress" aria-live="polite">
              <span class="ai-search-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </span>
              <span class="ai-search-text">AI 正在理解"{{ currentQ }}"的含义，在书架中匹配相关书籍…</span>
            </div>
          </div>

          <!-- 加载中（普通模式服务端搜索） -->
          <div v-else-if="!aiActive && booksStore.loading" class="empty-state">
            <div class="loading-bar"></div>
            <p style="margin-top:12px">正在搜索中…</p>
          </div>

          <!-- 无结果（普通 / AI 分开渲染：AI 结果带匹配分数与原因，不参与分页） -->
          <div v-else-if="shelfResultList.length === 0" class="empty-state">
            <template v-if="aiActive">
              <p>书架中没有找到符合"{{ currentQ }}"语义的书籍，试试<a href="#" @click.prevent="searchMode = 'web'" style="color:var(--accent-ice);text-decoration:underline">全网搜索</a></p>
              <el-button size="small" text type="primary" style="margin-top:12px" @click="switchSearchMethod">
                改用普通搜索
              </el-button>
            </template>
            <template v-else>
              <p>书架中未找到相关小说，试试<a href="#" @click.prevent="searchMode = 'web'" style="color:var(--accent-ice);text-decoration:underline">全网搜索</a></p>
              <el-button v-if="shelfSearch.aiEnabled" size="small" text type="primary" style="margin-top:12px" @click="switchSearchMethod">
                改用 🤖 AI 语义搜索
              </el-button>
            </template>
          </div>

          <!-- 搜索结果（AI 模式：卡片列表；普通模式：三列网格）
               v2.1：结果上方显示「自动使用 xx 搜索」标识，可一次性改用另一种方式 -->
          <template v-else>
            <div v-if="aiActive" class="ai-auto-indicator" role="status">
              <span>🤖 自动使用 AI 语义搜索</span>
              <el-button size="small" text type="primary" @click="switchSearchMethod">改用普通搜索</el-button>
            </div>
            <div v-else-if="shelfSearch.aiEnabled" class="ai-auto-indicator" role="status">
              <span>已使用普通搜索（书名 / 作者）</span>
              <el-button size="small" text type="primary" @click="switchSearchMethod">改用 🤖 AI 语义搜索</el-button>
            </div>
            <div v-if="aiActive" class="stack" style="gap:12px">
              <div v-for="r in shelfSearch.aiResults" :key="r.book_id" class="search-card">
                <div style="display:flex;align-items:flex-start;gap:16px">
                  <router-link :to="`/detail/${r.book_id}`" style="flex-shrink:0">
                    <BookCoverSmall :title="r.title" />
                  </router-link>
                  <div style="flex:1;min-width:0">
                    <div class="search-title">{{ r.title }}</div>
                    <div class="search-author">{{ r.author }}</div>
                    <div class="ai-match-info">
                      <span class="ai-match-score">{{ r.score }}%</span>
                      <span class="ai-match-reason">{{ r.match_reason }}</span>
                    </div>
                    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
                      <el-button size="small" type="primary" @click="$router.push(`/detail/${r.book_id}`)">
                        查看详情
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="grid-3">
              <div v-for="book in booksStore.searchResults" :key="book.id" class="search-card">
                <div style="display:flex;align-items:flex-start;gap:16px">
                  <router-link :to="`/detail/${book.id}`" style="flex-shrink:0">
                    <BookCoverSmall :title="book.title" />
                  </router-link>
                  <div style="flex:1">
                    <div class="search-title">{{ book.title }}</div>
                    <div class="search-author">{{ book.author }} · {{ book.chapter_count }} 章</div>
                    <div style="margin-top:4px">
                      <StatusBadge :status="book.status" />
                    </div>
                    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
                      <el-button size="small" type="primary" @click="$router.push(`/detail/${book.id}`)">
                        查看详情
                      </el-button>
                      <el-button
                        v-if="book.has_epub || book.has_txt"
                        size="small"
                        @click="downloadBook(book.id, book.has_epub ? 'epub' : 'txt', `${book.title}-${book.author}`)"
                      >
                        下载
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 分页（仅普通模式，AI 结果一次性返回不参与分页） -->
          <div v-if="!aiActive && booksStore.searchPagination.total_pages > 1" class="pagination">
            <el-pagination
              v-model:current-page="searchPage"
              :page-size="booksStore.searchPagination.page_size"
              :total="booksStore.searchPagination.total"
              layout="prev, pager, next"
              background
              @current-change="handleShelfSearchPageChange"
            />
          </div>
        </template>

        <!-- ── 全网搜索 tab ──────────────────────────────── -->
        <template v-if="searchMode === 'web'">
          <!-- 初始状态 -->
          <div v-if="!hasSearched" class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
                <circle cx="11" cy="11" r="7"/>
                <path d="m21 21-4.35-4.35"/>
                <line x1="15" y1="3" x2="19" y2="7"/>
                <line x1="19" y1="3" x2="15" y2="7"/>
              </svg>
            </div>
            <p>
              <template v-if="!booksStore.sourcesLoaded">正在加载源站列表…</template>
              <template v-else>输入书名或作者，在 {{ booksStore.sources.length || '多' }} 个源站中搜索</template>
            </p>
            <p style="font-size:12px;margin-top:6px;color:var(--muted)">搜索结果可一键添加到书架，然后抓取生成电子书</p>
          </div>

          <!-- 加载中 -->
          <div v-else-if="booksStore.externalLoading" class="empty-state">
            <div class="loading-bar"></div>
            <p style="margin-top:12px">正在搜索 {{ booksStore.sources.length }} 个源站…</p>
          </div>

          <!-- 搜索出错 -->
          <div v-else-if="booksStore.externalError" class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--danger)">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
            <p style="color:var(--danger)">{{ booksStore.externalError }}</p>
            <el-button size="small" style="margin-top:12px" @click="doSearch">重新搜索</el-button>
          </div>

          <!-- 无结果 -->
          <div v-else-if="booksStore.externalResults.length === 0" class="empty-state">
            <p>全网未找到相关小说，请尝试其他关键词</p>
          </div>

          <!-- 搜索结果列表 -->
          <div v-else>
            <div style="margin-bottom:12px;font-size:13px;color:var(--muted)">
              找到 <span class="num" style="font-family:var(--font-mono)">{{ booksStore.externalResults.length }}</span> 条结果
            </div>
            <div class="stack" style="gap:12px">
              <div v-for="(item, idx) in booksStore.externalResults" :key="idx" class="external-result-card">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px">
                  <div style="flex:1;min-width:0">
                    <div class="external-title">{{ item.title }}</div>
                    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:6px;font-size:13px;color:var(--muted)">
                      <span>作者：{{ item.author }}</span>
                      <span v-if="item.status">状态：{{ item.status }}</span>
                      <span v-if="item.category">分类：{{ item.category }}</span>
                      <span v-if="item.word_count">字数：{{ item.word_count }}</span>
                    </div>
                    <div style="margin-top:4px;font-size:12px;color:var(--muted)">
                      来源：<span class="source-tag">{{ item.source_name }}</span>
                      <span v-if="item.latest_chapter" style="margin-left:12px">最新：{{ item.latest_chapter }}</span>
                    </div>
                  </div>
                  <div class="result-actions" style="display:flex;align-items:center;gap:8px;flex-shrink:0">
                    <el-button
                      v-if="isAddedToShelf(item.source_url)"
                      size="small"
                      disabled
                    >
                      已在书架
                    </el-button>
                    <el-button
                      v-else
                      type="primary"
                      size="small"
                      :loading="addingIdx === idx"
                      @click="addToShelf(item, idx)"
                    >
                      添加到书架
                    </el-button>
                  </div>
                </div>
                <!-- 添加后显示跳转提示 -->
                <div v-if="addedBookIds[idx]" style="margin-top:8px;font-size:12px;display:flex;align-items:center;gap:12px">
                  <span style="color:var(--success)">✓ 已添加到书架</span>
                  <el-button size="small" text type="primary" @click="$router.push(`/detail/${addedBookIds[idx]}`)">
                    去详情页抓取 →
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div style="text-align:center;margin-top:40px">
          <el-button @click="$router.push('/shelf')">← 返回书架</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useBooksStore, useShelfSearchStore } from '@/stores'
import { getDownloadUrl, addBook, getBooks } from '@/api/books'
import type { SearchResultItem } from '@/types'
import { detectQueryIntent } from '@/lib/queryIntent'
import TopNav from '@/components/TopNav.vue'
import BookCoverSmall from '@/components/BookCoverSmall.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()
/** v1.9：书架内 AI 语义搜索状态与 TopNav 主搜索框共享 */
const shelfSearch = useShelfSearchStore()

const searchMode = ref<'shelf' | 'web'>('web')
const searchQuery = ref('')
const hasSearched = ref(false)
const currentQ = ref('')
const searchPage = ref(1)
const addingIdx = ref<number | null>(null)
const addedBookIds = reactive<Record<number, string>>({})

// 已有书架书籍的 source_url 集合，用于判断搜索结果是否已在书架
const shelfUrls = ref<Set<string>>(new Set())

const isSearching = ref(false)

/** v2.0：AI 开关（头像菜单）开启 + 书架内选择 AI 模式时，AI 语义搜索才生效 */
const aiActive = computed(() => shelfSearch.aiEnabled && shelfSearch.aiMode)

/** 输入框占位文案：书架内按开关状态区分自动识别 / 普通搜索（v2.1） */
const queryPlaceholder = computed(() => {
  if (searchMode.value === 'shelf') {
    return shelfSearch.aiEnabled
      ? '输入书名、作者或自然语言描述…'
      : '在书架中按书名或作者搜索…'
  }
  return '输入书名或作者，全网搜索…'
})

/** 书架内结果列表：AI 模式用语义搜索结果（仅长度判断），普通模式用服务端分页结果 */
const shelfResultList = computed(() =>
  aiActive.value
    ? shelfSearch.aiResults.map((r) => ({ id: r.book_id, title: r.title, author: r.author }))
    : booksStore.searchResults
)

onMounted(async () => {
  // 读取 URL 参数中的搜索模式
  const modeParam = (route.query.mode as string) || ''
  if (modeParam === 'shelf') {
    searchMode.value = 'shelf'
  } else {
    searchMode.value = 'web'
  }
  // v2.1：书架内搜索方式由顶栏按查询意图识别后携带 ai 参数进入本页
  //（仅 AI 开关开启时读取 ai 参数；缺省沿用上次选择）
  if (modeParam === 'shelf') {
    const aiParam = (route.query.ai as string) === '1'
    shelfSearch.aiMode = shelfSearch.aiEnabled ? aiParam : false
    // 进入搜索页后恢复自动识别：下次新查询重新判断意图，不受上次手动覆盖影响
    shelfSearch.aiModeSource = 'auto'
  }

  // 初始化：获取源站列表 + 当前书架快照
  await Promise.all([
    booksStore.fetchSources(),
    loadShelfSnapshot()
  ])

  const initQ = (route.query.q as string) || ''
  if (initQ) {
    searchQuery.value = initQ
    doSearch()
  }
})

/** 获取当前用户书架中所有书籍的 source_url，用于去重判断 */
async function loadShelfSnapshot() {
  try {
    // 分页加载全部书架数据，构建 source_url 集合
    let page = 1
    const pageSize = 100
    let hasMore = true
    while (hasMore) {
      const { data } = await getBooks(page, pageSize)
      if (data.success && data.data) {
        for (const b of data.data) {
          if (b.source_url) {
            shelfUrls.value.add(b.source_url.trim())
          }
        }
        // 用 total_pages 判断是否还有下一页，避免整百总数时多发一次空页请求
        const meta = data.meta
        hasMore = meta ? page < meta.total_pages : data.data.length === pageSize
        page++
      } else {
        hasMore = false
      }
    }
  } catch { /* 静默失败 */ }
}

function isAddedToShelf(sourceUrl: string): boolean {
  return shelfUrls.value.has(sourceUrl.trim())
}

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return

  hasSearched.value = true
  currentQ.value = q
  isSearching.value = true

  try {
    if (searchMode.value === 'shelf') {
      // v2.1：按查询意图自动选择搜索方式（用户在结果页手动切换后沿用其选择）
      if (shelfSearch.aiModeSource !== 'manual') {
        shelfSearch.aiMode = shelfSearch.aiEnabled && detectQueryIntent(q) === 'ai'
      }
      if (aiActive.value) {
        // AI 语义搜索：状态与结果在共享 store，加载态由 aiSearching 驱动
        await shelfSearch.performAiSearch(q)
      } else {
        searchPage.value = 1
        await booksStore.search(q, searchPage.value)
      }
    } else {
      // v2.0：全网搜索不再按源站筛选，始终搜索全部源站
      await booksStore.searchExternal(q)
    }
  } finally {
    isSearching.value = false
  }
}

/** v2.1：结果页一次性切换搜索方式（AI ⇄ 普通）并重新搜索 */
function switchSearchMethod() {
  shelfSearch.overrideAiMode(!shelfSearch.aiMode)
  doSearch()
}

async function handleShelfSearchPageChange(page: number) {
  searchPage.value = page
  await booksStore.search(currentQ.value, page)
  window.scrollTo({ top: 0, behavior: 'auto' })
}

/** 从外部搜索结果添加到书架 */
async function addToShelf(item: SearchResultItem, idx: number) {
  // 先检查是否已存在（通过 source_url）
  if (isAddedToShelf(item.source_url)) {
    ElMessage.info('该书已在书架中')
    return
  }

  addingIdx.value = idx
  try {
    const { data } = await addBook({
      title: item.title,
      author: item.author || '未知',
      source_url: item.source_url || null
    })
    if (data.success && data.data) {
      addedBookIds[idx] = data.data.id
      // 更新本地去重集合
      if (item.source_url) {
        shelfUrls.value.add(item.source_url.trim())
      }
      // 刷新书架数据
      booksStore.fetchBooks()
      ElMessage.success(`《${item.title}》已添加到书架，可前往详情页抓取生成电子书`)
    } else {
      throw new Error(data.error || '添加失败')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || err.message || '添加失败')
  } finally {
    addingIdx.value = null
  }
}

/** 下载电子书（书架内搜索结果直接下载） */
async function downloadBook(bookId: string, format: 'epub' | 'txt', filename: string) {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const url = getDownloadUrl(bookId, format)
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.error || '下载失败')
    }
    const blob = await response.blob()
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename + '.' + format
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
    ElMessage.success(`已开始下载`)
  } catch (err: any) {
    ElMessage.error(err.message || '下载失败')
  }
}

// 切换搜索模式时，若已有关键词则自动重新搜索
watch(searchMode, () => {
  booksStore.externalError = null
  if (hasSearched.value && currentQ.value) {
    doSearch()
  }
})

// v2.1：AI 搜索开关（头像菜单）变化后，书架内若已有关键词则按新状态重新搜索
watch(
  () => shelfSearch.aiEnabled,
  (enabled) => {
    if (!enabled) {
      // 关闭开关：复位 AI 模式与结果，避免旧语义结果残留
      shelfSearch.aiMode = false
      shelfSearch.aiModeSource = 'auto'
      shelfSearch.resetAiSearch()
    }
    if (searchMode.value === 'shelf' && hasSearched.value && currentQ.value) {
      doSearch()
    }
  }
)

// v2.1：编辑查询词后恢复自动识别——结果页的手动切换只对当前查询生效一次，
// 输入新内容时重新按意图判断搜索方式
watch(searchQuery, () => {
  if (searchQuery.value.trim() !== currentQ.value) {
    shelfSearch.aiModeSource = 'auto'
  }
})
</script>

<style scoped>
/* 全网搜索 tab 左上角返回书架按钮（替代原搜索标题位置） */
.back-to-shelf-btn {
  font-size: 15px;
  font-weight: 600;
  color: var(--fg);
  min-height: 32px;
}

.back-to-shelf-btn:hover {
  color: var(--accent);
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

@media (max-width: 920px) {
  .grid-3 { grid-template-columns: 1fr; }
}

.stack { display: flex; flex-direction: column; }

/* 外部搜索结果卡片 */
.external-result-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px 24px;
}

.external-result-card .external-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg);
}

.source-tag {
  display: inline-block;
  padding: 1px 8px;
  background: var(--accent-ice-soft);
  color: var(--accent-ice);
  border-radius: 4px;
  font-size: 12px;
}

/* ── v2.1：自动识别标识（结果上方提示当前搜索方式 + 一次性切换） ── */
.ai-auto-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--muted);
}

.ai-auto-indicator :deep(.el-button) {
  padding: 2px 4px;
  margin-left: 0;
}

/* ── v1.9：AI 语义搜索结果与进度提示（样式对齐书架页） ── */
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

.ai-search-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 480px;
  margin: 0 auto;
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
@media (max-width: 640px) {
  /* 搜索控件整行堆叠：标签切换一行，源站 + 输入框一行 */
  .search-controls {
    flex: 1 1 100% !important;
    flex-wrap: wrap;
    row-gap: 8px;
  }
  .mode-group {
    flex-basis: 100%;
    display: flex;
  }
  .mode-group :deep(.el-radio-button) {
    flex: 1;
  }
  .mode-group :deep(.el-radio-button__inner) {
    width: 100%;
    text-align: center;
  }
  .query-input {
    flex: 1;
    min-width: 0;
  }

  /* 搜索结果卡片：操作按钮独立一行 */
  .result-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .external-result-card {
    padding: 16px;
  }
}
</style>
