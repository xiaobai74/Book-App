<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 在线阅读器页面 (v1.2 新增)
     v1.6 — 边爬边看：抓取中可进入阅读；未就绪章节显示等待态，
           章节就绪后 SSE 自动加载；目录合并展示待抓取章节
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div class="reader-root" :class="{ 'night-mode': isNightMode }">
    <!-- 顶部导航栏 -->
    <header class="reader-header">
      <div class="reader-header-left">
        <el-button text class="reader-back" @click="goBack">
          <span class="reader-back-text">← 返回详情</span>
          <span class="reader-back-icon" aria-hidden="true">←</span>
        </el-button>
      </div>
      <div class="reader-header-center">
        <span class="chapter-label">第 {{ currentIndex }} 章</span>
        <span class="chapter-title-text">{{ headerTitle }}</span>
        <!-- 边爬边看 v1.4：抓取中实时进度徽标 -->
        <span v-if="crawling" class="crawl-badge">抓取中 {{ crawlCurrent }}/{{ crawlTotal || '?' }}</span>
      </div>
      <div class="reader-header-right">
        <el-button text @click="toggleToc">目录</el-button>
        <el-button text @click="toggleNightMode">
          {{ isNightMode ? '日间' : '夜间' }}
        </el-button>
        <el-dropdown trigger="click" @command="handleFontSize">
          <el-button text>字号</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="small">小</el-dropdown-item>
              <el-dropdown-item command="medium">中</el-dropdown-item>
              <el-dropdown-item command="large">大</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- 行间距调节（PRD READER-006 要求独立可调） -->
        <el-dropdown trigger="click" @command="handleLineHeight">
          <el-button text>行距</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="compact">紧凑</el-dropdown-item>
              <el-dropdown-item command="normal">标准</el-dropdown-item>
              <el-dropdown-item command="relaxed">宽松</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 正文区域 -->
    <main class="reader-body" :style="{ fontSize: fontSizePx + 'px', lineHeight: lineHeight }">
      <div v-if="loading" class="reader-loading">
        <div class="loading-bar"></div>
        <p style="margin-top:12px;color:var(--muted)">加载章节内容…</p>
      </div>

      <!-- 边爬边看 v1.4：章节尚未抓取完成，等待自动加载 -->
      <div v-else-if="waitingForCrawl" class="reader-error">
        <div class="loading-bar"></div>
        <p style="margin-top:12px;color:var(--muted)">第 {{ currentIndex }} 章正在抓取中，就绪后自动加载…</p>
        <p style="font-size:12px;color:var(--muted);margin-top:4px">抓取进度：{{ crawlCurrent }} / {{ crawlTotal || '?' }}</p>
        <el-button style="margin-top:16px" @click="backToLatest">返回最新可用章节</el-button>
      </div>

      <div v-else-if="errorMsg" class="reader-error">
        <p>{{ errorMsg }}</p>
        <el-button type="primary" style="margin-top:16px" @click="fetchChapter">重试</el-button>
      </div>

      <div v-else class="reader-content">
        <h2 class="reader-chapter-heading">{{ chapter?.title }}</h2>
        <div class="reader-text" v-html="renderedContent"></div>
      </div>

      <!-- 移动端点击翻页热区（v1.5 新增） -->
      <button
        class="tap-zone tap-zone-prev"
        type="button"
        :aria-label="prevAriaLabel"
        :disabled="currentIndex <= 1"
        @click="prevChapter"
      ></button>
      <button
        class="tap-zone tap-zone-next"
        type="button"
        :aria-label="nextAriaLabel"
        :disabled="currentIndex >= effectiveTotal"
        @click="nextChapter"
      ></button>
    </main>

    <!-- 底部导航栏 -->
    <footer class="reader-footer">
      <el-button
        :disabled="currentIndex <= 1"
        @click="prevChapter"
      >
        ← 上一章
      </el-button>
      <span class="reader-progress">
        {{ currentIndex }} / {{ effectiveTotal || '?' }}
      </span>
      <el-button
        :disabled="currentIndex >= effectiveTotal"
        @click="nextChapter"
      >
        下一章 →
      </el-button>
    </footer>

    <!-- 目录侧边抽屉（v1.5：小屏宽度贴屏） -->
    <el-drawer
      v-model="tocVisible"
      title="章节目录"
      direction="ltr"
      size="320px"
      class="reader-toc-drawer"
    >
      <div v-if="tocLoading" style="text-align:center;padding:24px">
        <div class="loading-bar"></div>
        <p style="margin-top:12px;color:var(--muted)">加载目录…</p>
      </div>
      <div v-else class="toc-list">
        <div
          v-for="item in tocItems"
          :key="item.index"
          class="toc-item"
          :class="{ 'toc-active': item.index === currentIndex, 'toc-pending': !item.available }"
          @click="jumpToChapter(item.index)"
        >
          <span class="toc-num">第 {{ item.index }} 章</span>
          <span class="toc-title">{{ item.title }}</span>
          <span v-if="!item.available" class="toc-pending-tag">抓取中</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getChapterContent, getChapters, updateReadingProgress, getReadingProgress, getCrawlStatus, subscribeCrawlStream } from '@/api/books'
import { recordRecentBook } from '@/utils/recentBooks'
import { escapeHtml } from '@/utils'
import type { ChapterSummary, ChapterDetail, CrawlStreamEvent } from '@/types'

const route = useRoute()
const router = useRouter()

const bookId = computed(() => route.params.id as string)
const currentIndex = ref(Number(route.params.chapterIndex) || 1)

const chapter = ref<ChapterDetail | null>(null)
const chapters = ref<ChapterSummary[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

// ── 边爬边看 v1.4：抓取态 ────────────────────────
const crawling = ref(false)
const crawlCurrent = ref(0)
const crawlTotal = ref(0)
const planTitles = ref<string[]>([])
/** 当前章节尚未抓取完成，等待就绪事件自动加载 */
const waitingForCrawl = ref(false)
let stopCrawlStreamFn: (() => void) | null = null
let crawlFallbackTimer: ReturnType<typeof setInterval> | null = null

/** 总章节数：抓取中用抓取计划总数（允许翻到待抓取章节进入等待态） */
const effectiveTotal = computed(() =>
  crawling.value
    ? Math.max(crawlTotal.value, chapters.value.length)
    : chapters.value.length
)

/** 头部标题：等待态用抓取计划中的标题，避免残留上一章标题 */
const headerTitle = computed(() => {
  if (waitingForCrawl.value) {
    return planTitles.value[currentIndex.value - 1] || '抓取中…'
  }
  return chapter.value?.title || '加载中…'
})

/** 合并目录：已就绪章节 + 抓取计划中的待抓取章节 */
const tocItems = computed(() => {
  const available = new Set(chapters.value.map(c => c.index))
  const items = chapters.value
    .slice()
    .sort((a, b) => a.index - b.index)
    .map(ch => ({ index: ch.index, title: ch.title, available: true }))
  if (crawling.value) {
    planTitles.value.forEach((title, i) => {
      const idx = i + 1
      if (!available.has(idx)) items.push({ index: idx, title, available: false })
    })
  }
  return items
})

// ─── 阅读设置 ────────────────────────────────────
const FONT_SIZES = ['small', 'medium', 'large'] as const
type FontSize = typeof FONT_SIZES[number]

// ── 行间距设置（独立调节，与字号解耦） ─────────────
const LINE_HEIGHTS = ['compact', 'normal', 'relaxed'] as const
type LineHeightOption = typeof LINE_HEIGHTS[number]

/** 从 localStorage 读取枚举型阅读设置，非法/缺失时回退默认值 */
function readStoredOption<T extends string>(key: string, options: readonly T[], fallback: T): T {
  const v = localStorage.getItem(key)
  return (options as readonly string[]).includes(v ?? '') ? (v as T) : fallback
}

const isNightMode = ref(localStorage.getItem('reader_nightMode') === 'true')
const fontSize = ref<FontSize>(readStoredOption('reader_fontSize', FONT_SIZES, 'medium'))
const lineHeightOption = ref<LineHeightOption>(readStoredOption('reader_lineHeight', LINE_HEIGHTS, 'normal'))

const fontSizeMap: Record<FontSize, number> = { small: 14, medium: 16, large: 20 }
const fontSizePx = computed(() => fontSizeMap[fontSize.value])
const lineHeightMap: Record<LineHeightOption, string> = {
  compact: '1.5',
  normal: '1.8',
  relaxed: '2.2'
}
const lineHeight = computed(() => lineHeightMap[lineHeightOption.value])

function handleFontSize(size: string) {
  if (!(FONT_SIZES as readonly string[]).includes(size)) return
  fontSize.value = size as FontSize
  localStorage.setItem('reader_fontSize', size)
}

function handleLineHeight(option: string) {
  if (!(LINE_HEIGHTS as readonly string[]).includes(option)) return
  lineHeightOption.value = option as LineHeightOption
  localStorage.setItem('reader_lineHeight', option)
}

function toggleNightMode() {
  isNightMode.value = !isNightMode.value
  localStorage.setItem('reader_nightMode', String(isNightMode.value))
}

// ─── 目录 ────────────────────────────────────
const tocVisible = ref(false)
const tocLoading = ref(false)

function toggleToc() {
  tocVisible.value = !tocVisible.value
  if (tocVisible.value && chapters.value.length === 0) {
    loadToc()
  }
}

async function loadToc() {
  tocLoading.value = true
  try {
    const { data } = await getChapters(bookId.value)
    if (data.success && data.data) {
      chapters.value = data.data
    }
  } catch {
    ElMessage.error('加载目录失败')
  } finally {
    tocLoading.value = false
  }
}

function jumpToChapter(index: number) {
  tocVisible.value = false
  if (index === currentIndex.value) return
  currentIndex.value = index
  router.replace(`/reader/${bookId.value}/${index}`)
  fetchChapter()
}

// ─── 内容渲染 ────────────────────────────────────
const renderedContent = computed(() => {
  if (!chapter.value?.content) return ''
  return chapter.value.content
    .split('\n')
    .map(line => line.trim() ? `<p>${escapeHtml(line)}</p>` : '<br>')
    .join('')
})

// 请求序号：快速翻章时丢弃过期响应，防止旧章节内容覆盖新章节
let fetchSeq = 0

async function fetchChapter() {
  const seq = ++fetchSeq
  const index = currentIndex.value
  loading.value = true
  errorMsg.value = null
  waitingForCrawl.value = false
  try {
    const { data } = await getChapterContent(bookId.value, index)
    if (seq !== fetchSeq) return  // 已有更新的请求，丢弃过期响应
    if (data.success && data.data) {
      chapter.value = data.data
      // 更新进度
      updateReadingProgress(bookId.value, index).catch(() => {})
      // 滚动到顶部
      window.scrollTo({ top: 0, behavior: 'auto' })
    } else if (crawling.value && index <= effectiveTotal.value) {
      // 边爬边看：章节在抓取计划中但尚未就绪 → 等待态
      waitingForCrawl.value = true
    } else {
      errorMsg.value = data.error || '章节加载失败'
    }
  } catch (err: any) {
    if (seq !== fetchSeq) return
    if (crawling.value && index <= effectiveTotal.value) {
      // 边爬边看：404 = 章节尚未写库，进入等待态而非报错
      waitingForCrawl.value = true
    } else {
      errorMsg.value = err?.response?.data?.error || err.message || '章节加载失败'
    }
  } finally {
    if (seq === fetchSeq) {
      loading.value = false
    }
  }
}

function prevChapter() {
  stepChapter(-1)
}

function nextChapter() {
  stepChapter(1)
}

/** 按偏移量翻章（越界时不处理），同步路由并重新拉取章节 */
function stepChapter(delta: number) {
  const next = currentIndex.value + delta
  if (next < 1 || next > effectiveTotal.value) return
  currentIndex.value = next
  router.replace(`/reader/${bookId.value}/${next}`)
  fetchChapter()
}

// 移动端点击翻页热区说明（v1.5）
const prevAriaLabel = computed(() =>
  currentIndex.value > 1 ? '上一章' : '已是第一章'
)
const nextAriaLabel = computed(() =>
  currentIndex.value < effectiveTotal.value ? '下一章' : '已是最后一章'
)

// ── 边爬边看 v1.4：抓取事件订阅 ────────────────────

/** 回到最新已就绪章节（等待态下的快捷出口） */
function backToLatest() {
  const latest = chapters.value.length
    ? chapters.value[chapters.value.length - 1].index
    : 1
  waitingForCrawl.value = false
  if (latest === currentIndex.value) {
    fetchChapter()
  } else {
    jumpToChapter(latest)
  }
}

function stopCrawlWatch() {
  if (stopCrawlStreamFn) {
    stopCrawlStreamFn()
    stopCrawlStreamFn = null
  }
  if (crawlFallbackTimer) {
    clearInterval(crawlFallbackTimer)
    crawlFallbackTimer = null
  }
}

function startCrawlWatch() {
  stopCrawlWatch()
  stopCrawlStreamFn = subscribeCrawlStream(bookId.value, (ev) => {
    if (ev.type === 'stream_error') {
      stopCrawlStreamFn = null
      startCrawlFallback()
      return
    }
    handleCrawlEvent(ev)
  })
}

function handleCrawlEvent(ev: CrawlStreamEvent) {
  switch (ev.type) {
    case 'snapshot':
      if (ev.status === 'none' || ev.status === 'done' || ev.status === 'failed') {
        // 订阅时任务已结束：对齐目录并解除等待
        crawling.value = false
        stopCrawlWatch()
        loadToc()
        if (waitingForCrawl.value) fetchChapter()
        return
      }
      crawling.value = true
      crawlCurrent.value = ev.current ?? 0
      crawlTotal.value = ev.total ?? 0
      if (ev.plan?.length) planTitles.value = ev.plan
      break
    case 'plan':
      crawlTotal.value = ev.total ?? 0
      planTitles.value = ev.plan ?? []
      break
    case 'chapter_ready': {
      crawlCurrent.value = ev.current ?? crawlCurrent.value
      crawlTotal.value = ev.total ?? crawlTotal.value
      // 目录实时增长（去重后按序插入）
      if (ev.index && !chapters.value.some(c => c.index === ev.index)) {
        chapters.value.push({
          index: ev.index,
          title: ev.title ?? '',
          word_count: ev.word_count ?? 0,
        })
        chapters.value.sort((a, b) => a.index - b.index)
      }
      // 等待中的当前章节就绪 → 自动加载
      if (waitingForCrawl.value && ev.index === currentIndex.value) {
        fetchChapter()
      }
      break
    }
    case 'done':
      crawling.value = false
      stopCrawlWatch()
      loadToc()  // 对齐最终目录
      if (waitingForCrawl.value) fetchChapter()
      break
    case 'failed':
      crawling.value = false
      stopCrawlWatch()
      if (waitingForCrawl.value) {
        waitingForCrawl.value = false
        errorMsg.value = ev.error || '抓取失败，该章节暂不可用'
      }
      break
  }
}

/** SSE 断连后的轮询回退：定期确认抓取状态并重试等待中的章节 */
function startCrawlFallback() {
  if (crawlFallbackTimer) return
  crawlFallbackTimer = setInterval(async () => {
    try {
      const { data } = await getCrawlStatus(bookId.value)
      if (!data.success || !data.data) return
      const st = data.data
      if (st.status === 'crawling') {
        crawling.value = true
        crawlCurrent.value = st.chapter_count
        crawlTotal.value = st.total_chapters ?? 0
        if (waitingForCrawl.value) fetchChapter()  // 重试：就绪则加载，否则重回等待
      } else {
        crawling.value = false
        stopCrawlWatch()
        await loadToc()
        if (waitingForCrawl.value) fetchChapter()
      }
    } catch { /* 静默 */ }
  }, 4000)
}

function goBack() {
  router.push(`/detail/${bookId.value}`)
}

// ─── 键盘导航 ────────────────────────────────────
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') prevChapter()
  else if (e.key === 'ArrowRight') nextChapter()
}

onMounted(async () => {
  // 记录最近阅读（供 Ctrl+K 命令面板"最近阅读"入口使用）
  recordRecentBook(bookId.value)
  // 先获取章节列表以确定总数（修复：统一走 loadToc，避免两处重复请求）
  try {
    await loadToc()
  } catch { /* 不影响阅读 */ }

  // 边爬边看 v1.4：书籍抓取中时订阅实时推送
  try {
    const { data } = await getCrawlStatus(bookId.value)
    if (data.success && data.data && data.data.status === 'crawling') {
      crawling.value = true
      crawlCurrent.value = data.data.chapter_count
      crawlTotal.value = data.data.total_chapters ?? 0
      startCrawlWatch()
    }
  } catch { /* 不影响阅读 */ }

  // 若未指定章节号，尝试恢复上次进度
  if (!route.params.chapterIndex || Number(route.params.chapterIndex) < 1) {
    try {
      const { data: progData } = await getReadingProgress(bookId.value)
      if (progData.success && progData.data) {
        currentIndex.value = progData.data.last_chapter_index || 1
        router.replace(`/reader/${bookId.value}/${currentIndex.value}`)
      }
    } catch { /* 使用默认值 */ }
  }

  fetchChapter()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  stopCrawlWatch()
})

// 监听路由参数变化（浏览器前进/后退、手动修改 URL 时）。
// 翻章函数内部已显式 fetch，此处 n === currentIndex 时跳过，避免重复请求。
watch(() => route.params.chapterIndex, (newVal) => {
  const n = Number(newVal)
  if (Number.isFinite(n) && n >= 1 && n !== currentIndex.value) {
    currentIndex.value = n
    fetchChapter()
  }
})
</script>

<style scoped>
/* ── 根容器 ────────────────────────────────────
   v1.4：日间 = 暖纸背景（冷调界面中的暖色"纸张"区）；
         夜间 = 冷调深蓝黑。令牌统一在 global.css 中定义 */
.reader-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--reader-warm-bg);
  color: var(--reader-warm-fg);
}

/* ── 夜间模式（冷调） ───────────────────────────── */
.reader-root.night-mode {
  background: var(--reader-night-bg);
  color: var(--reader-night-fg);
}

.night-mode .reader-header,
.night-mode .reader-footer {
  background: var(--reader-night-bar);
  border-color: var(--reader-night-border);
}

.night-mode .reader-content {
  color: var(--reader-night-fg);
}

.night-mode .reader-chapter-heading {
  color: var(--reader-night-heading);
}

/* ── 顶部导航栏 ──────────────────────────────────── */
.reader-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  gap: 12px;
  flex-wrap: wrap;
}

.reader-header-left,
.reader-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.reader-header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.chapter-label {
  font-size: 11px;
  color: var(--reader-warm-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.night-mode .chapter-label {
  color: var(--muted);
}

.chapter-title-text {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}

/* ── 正文区域 ──────────────────────────────────── */
.reader-body {
  flex: 1;
  padding: 32px 24px 48px;
  max-width: 780px;
  width: 100%;
  margin: 0 auto;
}

.reader-loading,
.reader-error {
  text-align: center;
  padding: 80px 24px;
}

.reader-chapter-heading {
  font-size: 1.5em;
  font-weight: 700;
  margin-bottom: 32px;
  text-align: center;
  color: var(--reader-warm-fg);
}

.reader-text {
  font-size: inherit;
  text-align: justify;
  word-break: break-word;
}

.reader-text :deep(p) {
  margin: 0 0 1.2em 0;
  text-indent: 2em;
}

/* ── 底部导航栏 ──────────────────────────────────── */
.reader-footer {
  position: sticky;
  bottom: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--surface);
  border-top: 1px solid var(--border);
}

.reader-progress {
  font-size: 13px;
  color: var(--reader-warm-muted);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.night-mode .reader-progress {
  color: var(--muted);
}

/* ── 目录 ──────────────────────────────────── */
.toc-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
}

.toc-item:hover {
  background: var(--hover);
}

.toc-active {
  background: var(--accent);
  color: #fff;
}

.toc-active:hover {
  background: var(--accent);
}

.toc-num {
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
  min-width: 48px;
}

.toc-active .toc-num {
  color: rgba(255, 255, 255, 0.78);
}

/* ── 边爬边看 v1.4：待抓取章节与抓取进度徽标 ── */
.toc-pending {
  opacity: 0.55;
}

.toc-pending-tag {
  font-size: 11px;
  color: var(--muted);
  margin-left: auto;
  flex-shrink: 0;
}

.crawl-badge {
  font-size: 11px;
  color: var(--muted);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.toc-title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 移动端点击翻页热区（v1.5：默认隐藏） ── */
.tap-zone {
  display: none;
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  height: 60%;
  width: 33%;
  max-width: 120px;
  z-index: 5;
  background: transparent;
  border: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.tap-zone:disabled {
  cursor: default;
}
.tap-zone-prev { left: 0; }
.tap-zone-next { right: 0; }

/* 移动端返回按钮：桌面显示文字，≤640px 仅显示箭头图标 */
.reader-back-icon {
  display: none;
}

/* ── 响应式 ──────────────────────────────────── */
@media (max-width: 640px) {
  .reader-body {
    padding: 20px 14px 36px;
  }
  /* 含刘海屏安全区（global.css 同值被本 scoped 规则覆盖，这里显式带上） */
  .reader-header {
    padding: calc(8px + env(safe-area-inset-top)) 12px 8px;
  }
  .reader-footer {
    padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  }

  /* 头部文字压缩，保证一行放下 */
  .reader-header { gap: 4px; }
  .reader-header-left,
  .reader-header-right {
    gap: 0;
  }
  .chapter-title-text {
    max-width: 160px;
    font-size: 13px;
  }

  /* 返回按钮图标化 */
  .reader-back-text { display: none; }
  .reader-back-icon {
    display: inline;
    font-size: 16px;
  }
  .reader-back { min-height: 36px; padding: 6px 8px; }

  /* 触控翻页热区 */
  .tap-zone { display: block; }

  /* 目录条目触控友好 */
  .toc-item {
    min-height: 44px;
    padding: 10px 8px;
  }
}
</style>

<!-- 全局样式（非 scoped，因为 el-drawer 渲染在 body 下） -->
<style>
/* v1.5：小屏目录抽屉贴屏，不遮挡正文 */
@media (max-width: 640px) {
  .reader-toc-drawer {
    width: min(320px, 85vw) !important;
  }
}
</style>
