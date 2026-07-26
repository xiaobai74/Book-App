<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书架首页
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
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon style="margin-right:6px"><Plus /></el-icon>
            添加小说
          </el-button>
        </div>

        <!-- 加载中 -->
        <div v-if="booksStore.loading" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="booksStore.books.length === 0" class="empty-state">
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
          <div v-for="book in booksStore.books" :key="book.id" class="book-card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
              <div style="display:flex;align-items:flex-start;gap:16px">
                <router-link :to="`/detail/${book.id}`">
                  <BookCover :title="book.title" :author="book.author" />
                </router-link>
                <div>
                  <router-link :to="`/detail/${book.id}`" class="book-title">
                    {{ book.title }}
                  </router-link>
                  <div class="book-author">{{ book.author }}</div>
                </div>
              </div>
              <el-button type="danger" text :icon="Delete" size="small" @click="confirmDelete(book)">
                删除
              </el-button>
            </div>
            <div class="book-meta-row">
              <span>{{ formatDate(book.added_at) }}</span>
              <StatusBadge :status="book.status" />
              <span>{{ book.chapter_count }} 章</span>
              <span v-if="book.has_epub" style="color:var(--accent-ice)">.epub 可下载</span>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="booksStore.pagination.total_pages > 1" class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="booksStore.pagination.page_size"
            :total="booksStore.pagination.total"
            layout="prev, pager, next"
            background
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </section>

    <footer class="pagefoot">
      <div class="container">© 小说管理App · 个人学习用途</div>
    </footer>

    <!-- 添加书籍对话框 -->
    <el-dialog v-model="showAddDialog" title="添加小说" width="420px" @opened="resetAddForm">
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
            <span v-if="urlCheckResult.reachable" style="color: #67c23a">✓ 源站可达 (HTTP {{ urlCheckResult.status_code }})</span>
            <span v-else style="color: #f56c6c">✗ {{ urlCheckResult.error_message }}</span>
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
import { ref, reactive, onMounted } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useBooksStore } from '@/stores'
import { formatDate } from '@/utils'
import { checkSourceUrl } from '@/api/books'
import type { Book } from '@/types'
import TopNav from '@/components/TopNav.vue'
import BookCover from '@/components/BookCover.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const booksStore = useBooksStore()
const currentPage = ref(1)

onMounted(() => {
  booksStore.fetchBooks(currentPage.value)
})

function handlePageChange(page: number) {
  currentPage.value = page
  booksStore.fetchBooks(page)
  window.scrollTo({ top: 0, behavior: 'auto' })
}

// ─── 添加书籍 ────────────────────────────────────
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

// ─── 删除书籍 ────────────────────────────────────
function confirmDelete(book: Book) {
  ElMessageBox.confirm(
    `确定要删除《${book.title}》吗？`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await booksStore.removeBook(book.id)
      if (booksStore.books.length === 0 && booksStore.pagination.page > 1) {
        currentPage.value = Math.max(1, currentPage.value - 1)
        await booksStore.fetchBooks(currentPage.value)
      }
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
</style>
