<!-- ═══════════════════════════════════════════════════════
     小说管理App · 源站排行榜页面
     两级交互：① 选择源站 → ② Tab 切换榜单浏览 → 加入书架
     ═══════════════════════════════════════════════════════ -->
<template>
  <div class="ranking-page">
    <TopNav :show-search="false" />

    <main class="ranking-main">
      <!-- ══ ① 源站选择态 ══ -->
      <template v-if="!selectedSource">
        <div class="ranking-header">
          <h2 class="ink-title">源站排行榜</h2>
          <el-button type="primary" :loading="loadingSources" @click="refreshSources">
            {{ sources.length ? '刷新列表' : '获取排行榜' }}
          </el-button>
          <!-- v2.5.1：水墨玻璃返回按钮 -->
          <router-link to="/shelf" class="back-link">
            <span class="back-btn">← 返回书架</span>
          </router-link>
        </div>

        <el-skeleton v-if="loadingSources" :rows="4" animated />

        <el-empty v-else-if="loaded && sources.length === 0"
          description="暂无支持排行榜的源站，请在规则中配置 ranking 段" />

        <div v-else class="source-grid">
          <div
            v-for="s in sources"
            :key="s.id"
            class="source-card"
            role="button"
            tabindex="0"
            @click="selectSource(s)"
            @keyup.enter="selectSource(s)"
          >
            <div class="source-name">{{ s.name }}</div>
            <div class="source-boards">{{ s.board_names.length }} 个榜单</div>
            <div class="source-board-tags">
              <el-tag v-for="b in s.board_names.slice(0, 3)" :key="b" size="small">
                {{ b }}
              </el-tag>
            </div>
          </div>
        </div>
      </template>

      <!-- ══ ② 榜单浏览态 ══ -->
      <template v-else>
        <!-- 移动端优化：返回源站列表独占一行；榜单名称与刷新按钮同行（返回书架由底部 TabBar / 顶栏 logo 承担） -->
        <div class="ranking-header ranking-header--col">
          <button type="button" class="back-btn back-sources-btn" @click="rankingStore.backToSources()">← 返回源站列表</button>
          <div class="ranking-title-row">
            <h2 class="ink-title">{{ selectedSource.name }}排行榜</h2>
            <el-button :loading="loadingBoard" @click="onRefreshBoard">
              刷新榜单
            </el-button>
          </div>
        </div>

        <el-tabs v-model="activeBoard" @tab-change="onBoardChange">
          <el-tab-pane
            v-for="(name, idx) in selectedSource.board_names"
            :key="idx"
            :label="name"
            :name="String(idx)"
          />
        </el-tabs>

        <el-skeleton v-if="loadingBoard" :rows="8" animated />

        <el-alert v-else-if="boardError" type="error" :title="boardError"
          :closable="false" show-icon class="board-error">
          <template #default>
            <span>{{ boardError }}</span>
            <el-button size="small" text type="primary" @click="onRefreshBoard">
              重试
            </el-button>
          </template>
        </el-alert>

        <template v-else-if="currentBoard">
          <p v-if="currentBoard.from_cache" class="cache-tip">
            数据来自缓存（15 分钟内）·共 {{ currentBoard.items.length }} 条
          </p>
          <p v-else class="cache-tip">共抓取到 {{ currentBoard.items.length }} 条榜单数据</p>
          <ol class="rank-list">
            <li v-for="item in pagedItems" :key="item.rank" class="rank-item">
              <span class="rank-badge" :class="{ top: item.rank <= 3 }">{{ item.rank }}</span>
              <div class="rank-info">
                <div class="rank-title">
                  {{ item.title }}
                  <el-tag v-if="item.category" size="small" type="info">{{ item.category }}</el-tag>
                </div>
                <div class="rank-meta">
                  {{ item.author }}
                  <template v-if="item.latest_chapter"> · 最新：{{ item.latest_chapter }}</template>
                  <template v-if="item.last_update"> · {{ item.last_update }}</template>
                </div>
              </div>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="addingBookId === item.rank"
                @click="addToShelf(item)"
              >
                加入书架
              </el-button>
            </li>
          </ol>
          <div v-if="currentBoard.items.length > PAGE_SIZE" class="rank-pagination">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="PAGE_SIZE"
              :total="currentBoard.items.length"
              layout="prev, pager, next, jumper, total"
              background
            />
          </div>
        </template>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import TopNav from '@/components/TopNav.vue'
import { useRankingStore, useBooksStore } from '@/stores'
import { triggerCrawl } from '@/api/books'
import type { RankingSource, RankingBook } from '@/types'

// keep-alive include 匹配所需（v2.7：Tab 页缓存）
defineOptions({ name: 'RankingView' })

/**
 * 抓取结果与页面状态全部存于 rankingStore：
 * 切换页面再回来直接恢复，不会重新抓取；
 * 仅用户点击「刷新列表 / 刷新榜单」才发起新请求。
 */
const rankingStore = useRankingStore()
const booksStore = useBooksStore()

const sources = computed(() => rankingStore.sources)
const loadingSources = computed(() => rankingStore.loadingSources)
const loaded = computed(() => rankingStore.sourcesLoaded)
const selectedSource = computed(() => rankingStore.selectedSource)
const loadingBoard = computed(() => rankingStore.loadingBoard)
const boardError = computed(() => rankingStore.boardError)
const currentBoard = computed(() => rankingStore.currentBoard)
/** el-tabs v-model 需要字符串；store 内持有数字索引 */
const activeBoard = computed({
  get: () => String(rankingStore.activeBoard),
  set: (v: string) => { rankingStore.activeBoard = Number(v) }
})
const addingBookId = ref<number | null>(null)

/** 前端分页：后端一次性返回完整榜单（最多 2000 条），前端每页 PAGE_SIZE 条展示 */
const PAGE_SIZE = 50
const currentPage = ref(1)
const pagedItems = computed<RankingBook[]>(() => {
  const items = currentBoard.value?.items ?? []
  const start = (currentPage.value - 1) * PAGE_SIZE
  return items.slice(start, start + PAGE_SIZE)
})

/**
 * v2.7: 首次挂载（onMounted）与从 keep-alive 缓存恢复（onActivated）均调用；
 * store 层已有 sourcesLoaded 标记与 boardCache，重复调用不会产生额外请求。
 */
function loadRankingData() {
  rankingStore.loadSources()  // 已加载过则跳过，直接恢复源站列表
  // 恢复榜单浏览态：当前榜单无缓存时才请求（15 分钟内命中后端缓存）
  if (rankingStore.selectedSource && !rankingStore.currentBoard && !rankingStore.boardError) {
    rankingStore.loadBoard(rankingStore.activeBoard)
  }
}

onMounted(loadRankingData)
onActivated(loadRankingData)

/** 用户点击刷新：强制重新获取源站列表 */
function refreshSources() {
  currentPage.value = 1
  rankingStore.loadSources(true)
}

function selectSource(s: RankingSource) {
  currentPage.value = 1
  rankingStore.selectSource(s)
  rankingStore.loadBoard(0)
  scheduleIdlePrefetch(s)
}

/**
 * v2.7 阶段2：进入某源站榜单后，浏览器空闲时串行预取该源站其余榜单，
 * 用户切 Tab 时直接命中 store 缓存秒开。串行避免并发抓取压垮源站。
 */
function scheduleIdlePrefetch(source: RankingSource) {
  const rest = source.board_names.slice(1).map((_, i) => i + 1)
  if (!rest.length) return
  const run = async () => {
    for (const idx of rest) {
      await rankingStore.prefetchBoard(source.id, idx)
    }
  }
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(() => { run() }, { timeout: 5000 })
  } else {
    setTimeout(run, 2000)  // Safari 等无 requestIdleCallback 环境的降级
  }
}

function onBoardChange(name: string | number) {
  currentPage.value = 1
  rankingStore.loadBoard(Number(name))
}

/** 刷新当前榜单：重置分页并跳过前后端缓存 */
function onRefreshBoard() {
  currentPage.value = 1
  rankingStore.loadBoard(rankingStore.activeBoard, true)
}

/** 加入书架：走 store 添加（本地同步书架缓存，返回书架即可见），成功后自动触发抓取 */
async function addToShelf(item: RankingBook) {
  if (!item.book_url) {
    ElMessage.warning('该条目缺少详情页链接，无法导入')
    return
  }
  addingBookId.value = item.rank
  try {
    const added = await booksStore.addBook({ title: item.title, author: item.author, source_url: item.book_url })
    ElMessage.success(`《${item.title}》已加入书架`)
    if (added?.id) {
      triggerCrawl(added.id).catch(() => {})  // 抓取失败不影响加书架结果
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || e?.message || '加入书架失败')
  } finally {
    addingBookId.value = null
  }
}
</script>

<style scoped>
.ranking-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* v2.5.2：页头直置背景（标题走自适应墨色变量），不再用灰块面板 */
.ranking-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.ranking-header h2 {
  margin: 0;
  font-size: 20px;
  flex: 1;
}
/* ② 态头部：返回按钮独占一行，标题行与刷新按钮同行 */
.ranking-header--col {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}
.back-sources-btn {
  align-self: flex-start;
  padding-left: 0;
}
.ranking-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.back-link { margin-left: auto; text-decoration: none; }

/* ── 源站卡片（v2.0：玻璃面，模糊/墨影由全局规则提供） ── */
.source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.source-card {
  background: var(--surface);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s;
}
.source-card:hover, .source-card:focus-visible {
  border-color: var(--accent);
  transform: translateY(-2px);
  outline: none;
  box-shadow: var(--shadow-glass-hover);
}
.source-name { font-size: 16px; font-weight: 600; color: var(--ink); }
.source-boards { font-size: 13px; color: var(--muted); margin: 4px 0 8px; }
.source-board-tags { display: flex; flex-wrap: wrap; gap: 4px; }

/* ── 榜单列表（v2.0：玻璃条目 + 朱砂榜首徽标） ── */
.cache-tip { font-size: 12px; color: var(--onbg-muted); margin: 0 0 8px; text-shadow: var(--onbg-halo-shadow); }   /* v2.5.2：直置背景，自适应墨色；v2.6 反色光晕 */
.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
}
/* 墨色序号徽标：默认淡墨底，前三名朱砂印章红突出（需求 4） */
.rank-badge {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  background: color-mix(in oklch, var(--ink) 10%, transparent);
  color: var(--ink-soft);
}
.rank-badge.top {
  background: var(--seal);
  color: #fff;
  box-shadow: 0 2px 8px rgba(176, 58, 46, 0.35);
}
.rank-info { flex: 1; min-width: 0; }
.rank-title { font-weight: 600; color: var(--ink); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.rank-meta {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.board-error { margin-bottom: 12px; }
.rank-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

@media (max-width: 760px) {
  .ranking-main { padding: 16px 12px; }
  .rank-item { flex-wrap: wrap; }
}
</style>
