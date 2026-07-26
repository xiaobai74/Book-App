<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍详情页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-settings-btn="false" :show-back-to-shelf="true" />

    <section class="section">
      <div class="container">
        <!-- 加载中 -->
        <div v-if="booksStore.loading && !book" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 不存在 -->
        <div v-else-if="!book && !booksStore.loading" class="empty-state">
          <p>该书籍不存在或已被删除</p>
          <el-button type="primary" style="margin-top:16px" @click="$router.push('/shelf')">返回书架</el-button>
        </div>

        <!-- 详情内容 -->
        <template v-if="book">
          <el-button text style="margin-bottom:16px" @click="$router.push('/shelf')">← 返回书架</el-button>

          <!-- 书籍信息卡片 -->
          <div class="card" style="margin-bottom:24px">
            <div class="detail-header">
              <div style="flex:1">
                <h1 style="font-size:clamp(28px,4vw,36px);font-weight:700">{{ book.title }}</h1>
                <p class="lead" style="margin-top:6px">作者：{{ book.author }}</p>
                <p v-if="book.source_url" style="font-size:12px;color:var(--muted);margin-top:2px">
                  来源：<a :href="book.source_url" target="_blank" rel="noopener">{{ book.source_url }}</a>
                </p>
                <div class="detail-meta" style="margin-top:12px">
                  <span class="meta">添加时间：{{ formatDate(book.added_at) }}</span>
                  <div style="display:flex;align-items:center;gap:8px">
                    <span class="meta">状态：</span>
                    <StatusBadge :status="book.status" />
                  </div>
                  <span class="meta">章节数：<span class="num">{{ book.chapter_count }}</span></span>
                </div>
                <div class="detail-actions">
                  <el-button
                    type="primary"
                    :disabled="book.status === 'crawling'"
                    :loading="crawling"
                    @click="handleCrawl"
                  >
                    {{ book.status === 'done' ? '重新抓取' : '抓取小说内容' }}
                  </el-button>
                  <el-button
                    type="success"
                    :disabled="!book.has_epub"
                    @click="handleDownload"
                  >
                    下载 .epub
                  </el-button>
                  <el-button @click="$router.push('/shelf')">返回书架</el-button>
                </div>

                <!-- 抓取进度 -->
                <div v-if="crawlProgressVisible" style="margin-top:16px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:12px;color:var(--muted)">抓取进度：{{ crawlText }}</span>
                    <span class="num" style="font-size:12px;color:var(--muted)">{{ crawlPercent }}%</span>
                  </div>
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: crawlPercent + '%' }"></div>
                  </div>
                </div>
              </div>

              <BookCover :title="book.title" :author="book.author" />
            </div>
          </div>

          <!-- 章节目录 -->
          <div v-if="chapters.length > 0" class="card">
            <h3 style="margin-bottom:16px;font-size:18px;font-weight:600">章节目录</h3>
            <div v-for="(ch, i) in chapters" :key="i" class="chapter-row">
              <span class="ch-num">第 {{ i + 1 }} 章</span>
              <span class="ch-title">{{ ch.title }}</span>
              <span style="font-size:12px;color:var(--muted)">{{ ch.wordCount || '—' }} 字</span>
            </div>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import type { Book, Chapter } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getDownloadUrl } from '@/api/books'

const route = useRoute()
const booksStore = useBooksStore()

const book = ref<Book | null>(null)
const chapters = ref<Chapter[]>([])
const crawling = ref(false)
const crawlProgressVisible = ref(false)
const crawlText = ref('')
const crawlPercent = ref(0)

let crawlTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  const id = route.params.id as string
  if (!id) {
    book.value = null
    return
  }
  try {
    const result = await booksStore.fetchBookDetail(id)
    book.value = result
    chapters.value = (result as any).chapters || []
    if (result?.status === 'crawling') {
      startCrawlPolling(id)
    }
  } catch {
    book.value = null
  }
})

onUnmounted(() => {
  stopCrawlPolling()
})

function stopCrawlPolling() {
  if (crawlTimer) {
    clearInterval(crawlTimer)
    crawlTimer = null
  }
}

function startCrawlPolling(bookId: string) {
  crawlProgressVisible.value = true
  stopCrawlPolling()
  crawlTimer = setInterval(async () => {
    try {
      const status = await booksStore.fetchCrawlStatus(bookId)
      if (status) {
        crawlText.value = `${status.chapter_count}/${status.total_chapters ?? '?'} 章`
        crawlPercent.value = Math.round(status.percentage)
        if (book.value) {
          book.value.status = status.status
          book.value.chapter_count = status.chapter_count
        }
        if (status.status === 'done' || status.status === 'failed') {
          stopCrawlPolling()
          if (status.status === 'done') {
            if (book.value) {
              book.value.has_epub = true
            }
            crawlProgressVisible.value = false
            ElMessage.success('抓取完成！.epub 文件已生成')
          } else {
            const errMsg = status.error || '抓取失败，请检查网络后重试'
            ElMessage.error(errMsg)
          }
        }
      }
    } catch {
      // 轮询失败不中断
    }
  }, 2000)
}

async function handleCrawl() {
  if (!book.value) return
  crawling.value = true
  try {
    const result = await booksStore.startCrawl(book.value.id)
    if (book.value) {
      book.value.status = result.status
    }
    crawlProgressVisible.value = true
    crawlText.value = `0/? 章`
    crawlPercent.value = 0
    startCrawlPolling(book.value.id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.error || err.message || '触发抓取失败')
  } finally {
    crawling.value = false
  }
}

async function handleDownload() {
  if (!book.value) return
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const url = getDownloadUrl(book.value.id)
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
    a.download = `${book.value.title}-${book.value.author}.epub`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
    ElMessage.success(`《${book.value.title}》开始下载`)
  } catch (err: any) {
    ElMessage.error(err.message || '下载失败')
  }
}
</script>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
}

.lead { font-size: 15px; color: var(--muted); max-width: 52ch; }

.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.meta {
  font-size: 12px;
  color: var(--muted);
}
</style>
