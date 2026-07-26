<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书架搜索页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-search="false" />

    <section class="section">
      <div class="container">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <h2 style="font-size:clamp(22px,3vw,28px);font-weight:600">
            {{ hasSearched ? `搜索："${currentQ}"` : '书架搜索' }}
          </h2>
          <el-input
            v-model="searchQuery"
            placeholder="在书架中按书名搜索…"
            :prefix-icon="Search"
            style="flex:0 1 360px"
            clearable
            @keyup.enter="doSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="doSearch" />
            </template>
          </el-input>
        </div>

        <!-- 初始状态 -->
        <div v-if="!hasSearched" class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" style="width:48px;height:48px;stroke:var(--muted)">
              <circle cx="11" cy="11" r="7"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <p>在书架中按书名模糊搜索</p>
          <p style="font-size:12px;margin-top:6px;color:var(--muted)">v1.0 暂为书架内搜索，全文网络搜索将在后续版本接入</p>
        </div>

        <!-- 加载中 -->
        <div v-else-if="booksStore.loading" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">正在搜索中…</p>
        </div>

        <!-- 无结果 -->
        <div v-else-if="booksStore.searchResults.length === 0" class="empty-state">
          <p>未找到相关小说，请尝试其他关键词</p>
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
                <div style="margin-top:8px">
                  <el-button size="small" type="primary" @click="$router.push(`/detail/${book.id}`)">
                    查看详情
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
            @current-change="handleSearchPageChange"
          />
        </div>

        <div style="text-align:center;margin-top:40px">
          <el-button @click="$router.push('/shelf')">← 返回书架</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useBooksStore } from '@/stores'
import TopNav from '@/components/TopNav.vue'
import BookCoverSmall from '@/components/BookCoverSmall.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const route = useRoute()
const booksStore = useBooksStore()

const searchQuery = ref('')
const hasSearched = ref(false)
const currentQ = ref('')
const searchPage = ref(1)

onMounted(() => {
  const initQ = (route.query.q as string) || ''
  if (initQ) {
    searchQuery.value = initQ
    doSearch()
  }
})

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return

  hasSearched.value = true
  currentQ.value = q
  searchPage.value = 1
  await booksStore.search(q, searchPage.value)
}

async function handleSearchPageChange(page: number) {
  searchPage.value = page
  await booksStore.search(currentQ.value, page)
  window.scrollTo({ top: 0, behavior: 'auto' })
}
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
</style>
