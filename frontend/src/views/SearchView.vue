<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 统一搜索页面（v2.0：书架内搜索 + 全网源站搜索）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-search="false" />

    <section class="section">
      <div class="container">
        <!-- 搜索栏 -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <h2 style="font-size:clamp(22px,3vw,28px);font-weight:600">
            {{ hasSearched ? `搜索："${currentQ}"` : '搜索小说' }}
          </h2>
          <div class="search-controls" style="display:flex;align-items:center;gap:8px;flex:0 1 480px">
            <!-- 搜索标签切换 -->
            <el-radio-group v-model="searchMode" size="small" class="mode-group" style="flex-shrink:0">
              <el-radio-button value="shelf">书架内</el-radio-button>
              <el-radio-button value="web">全网搜索</el-radio-button>
            </el-radio-group>
            <!-- 源站筛选（仅全网搜索显示） -->
            <el-select
              v-if="searchMode === 'web'"
              v-model="selectedSource"
              placeholder="全部源站"
              size="small"
              clearable
              class="source-select"
              style="width:140px;flex-shrink:0"
            >
              <el-option label="全部源站" :value="undefined" />
              <el-option
                v-for="s in booksStore.sources"
                :key="s.id"
                :label="s.name"
                :value="s.id"
              />
            </el-select>
            <el-input
              v-model="searchQuery"
              :placeholder="searchMode === 'web' ? '输入书名或作者，全网搜索…' : '在书架中按书名搜索…'"
              :prefix-icon="Search"
              clearable
              class="query-input"
              @keyup.enter="doSearch"
            >
              <template #append>
                <el-button :icon="Search" :loading="isSearching" aria-label="搜索" @click="doSearch" />
              </template>
            </el-input>
          </div>
        </div>

        <!-- ── 书架内搜索 tab ──────────────────────────────── -->
        <template v-if="searchMode === 'shelf'">
          <!-- 初始状态 -->
          <div v-if="!hasSearched" class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
                <circle cx="11" cy="11" r="7"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
            <p>在已有书架中按书名模糊搜索</p>
          </div>

          <!-- 加载中 -->
          <div v-else-if="booksStore.loading" class="empty-state">
            <div class="loading-bar"></div>
            <p style="margin-top:12px">正在搜索中…</p>
          </div>

          <!-- 无结果 -->
          <div v-else-if="booksStore.searchResults.length === 0" class="empty-state">
            <p>书架中未找到相关小说，试试<a href="#" @click.prevent="searchMode = 'web'" style="color:var(--accent-ice);text-decoration:underline">全网搜索</a></p>
          </div>

          <!-- 搜索结果 -->
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

          <!-- 分页 -->
          <div v-if="booksStore.searchPagination.total_pages > 1" class="pagination">
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
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useBooksStore } from '@/stores'
import { getDownloadUrl, addBook, getBooks } from '@/api/books'
import type { SearchResultItem } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCoverSmall from '@/components/BookCoverSmall.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

const searchMode = ref<'shelf' | 'web'>('web')
const searchQuery = ref('')
const hasSearched = ref(false)
const currentQ = ref('')
const searchPage = ref(1)
const selectedSource = ref<number | undefined>(undefined)
const addingIdx = ref<number | null>(null)
const addedBookIds = reactive<Record<number, string>>({})

// 已有书架书籍的 source_url 集合，用于判断搜索结果是否已在书架
const shelfUrls = ref<Set<string>>(new Set())

const isSearching = ref(false)

onMounted(async () => {
  // 读取 URL 参数中的搜索模式
  const modeParam = (route.query.mode as string) || ''
  if (modeParam === 'shelf') {
    searchMode.value = 'shelf'
  } else {
    searchMode.value = 'web'
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
      searchPage.value = 1
      await booksStore.search(q, searchPage.value)
    } else {
      await booksStore.searchExternal(q, selectedSource.value)
    }
  } finally {
    isSearching.value = false
  }
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
</script>

<style scoped>
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
  .source-select {
    flex: 0 1 120px;
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
