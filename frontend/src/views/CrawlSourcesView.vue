<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 自定义抓取源站管理页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div>
    <TopNav :show-search="false" />

    <section class="section">
      <div class="container">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px">
          <h2 style="font-size:clamp(22px,3vw,28px);font-weight:600">自定义抓取源站</h2>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon style="margin-right:6px"><Plus /></el-icon>
            添加源站
          </el-button>
        </div>

        <p class="lead" style="margin-bottom:16px; color:var(--muted); font-size:13px;">
          在这里配置额外的源站抓取规则。未配置的网站将自动使用通用解析策略。
        </p>

        <!-- 加载中 -->
        <div v-if="loading" class="empty-state">
          <div class="loading-bar"></div>
          <p style="margin-top:12px">加载中…</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="sources.length === 0" class="empty-state">
          <p>暂无自定义源站规则</p>
          <p style="font-size:12px;margin-top:6px;color:var(--muted)">
            系统内置了通用解析策略，大部分网站不配置也能抓取。如果通用策略效果不佳，可在此添加精确规则。
          </p>
        </div>

        <!-- 源站列表 -->
        <div v-else class="stack" style="gap:12px">
          <div v-for="source in sources" :key="source.id" class="source-card">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
              <div>
                <div style="font-weight:600">{{ source.name }}</div>
                <div style="font-size:12px;color:var(--muted);word-break:break-all">{{ source.url }}</div>
                <div style="font-size:11px;color:var(--muted);margin-top:2px">
                  添加于 {{ formatDate(source.created_at) }}
                </div>
              </div>
              <div style="display:flex;gap:8px">
                <el-button size="small" text @click="openEdit(source)">编辑</el-button>
                <el-button size="small" text type="danger" @click="confirmDelete(source)">删除</el-button>
              </div>
            </div>
          </div>
        </div>

        <div style="text-align:center;margin-top:40px">
          <el-button @click="$router.push('/shelf')">← 返回书架</el-button>
        </div>
      </div>
    </section>

    <!-- 添加 / 编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="isEditing ? '编辑源站规则' : '添加源站规则'"
      width="560px"
      @opened="resetEditForm"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top" @submit.prevent="handleSave">
        <el-form-item label="源站名称" prop="name">
          <el-input v-model="editForm.name" placeholder="例如：笔趣阁镜像站" />
        </el-form-item>
        <el-form-item label="源站 URL" prop="url">
          <el-input v-model="editForm.url" placeholder="https://www.example.com/" />
        </el-form-item>
        <el-form-item label="抓取规则 (JSON)" prop="rule_json">
          <el-input
            v-model="editForm.rule_json"
            type="textarea"
            :rows="10"
            placeholder='{"toc":{"item":"#list > dl > dd > a"},"chapter":{"title":"h1","content":"#content"}}'
            style="font-family:var(--font-mono);font-size:12px"
          />
          <div style="font-size:11px;color:var(--muted);margin-top:4px">
            参考下方说明配置 CSS 选择器。点击「测试」按钮验证规则是否有效。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <el-button
            :loading="testingRule"
            :disabled="!editForm.rule_json.trim()"
            @click="handleTestRule"
          >
            测试规则
          </el-button>
          <div style="display:flex;gap:8px">
            <el-button @click="showEditDialog = false">取消</el-button>
            <el-button type="primary" :loading="savingSource" @click="handleSave">
              {{ isEditing ? '更新' : '添加' }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 测试结果 -->
      <div v-if="testResult !== null" class="test-result" style="margin-top:12px;padding:12px;border-radius:6px;background:var(--bg);font-size:13px">
        <div v-if="testResult.success" style="color:var(--accent-ice)">
          ✓ 测试通过！成功解析 {{ testResult.chapter_count }} 章
          <ul v-if="testResult.sample_chapters.length" style="margin-top:6px;list-style:decimal;margin-left:20px">
            <li v-for="(ch, i) in testResult.sample_chapters" :key="i">{{ ch.title }}</li>
            <li v-if="testResult.chapter_count > 5" style="color:var(--muted)">... 共 {{ testResult.chapter_count }} 章</li>
          </ul>
        </div>
        <div v-else style="color:#f56c6c">
          ✗ 测试失败：{{ testResult.error }}
        </div>
      </div>
    </el-dialog>

    <!-- 规则帮助 -->
    <div class="container" style="margin-top:40px">
      <div class="help-box">
        <h3>规则配置说明</h3>
        <p>规则以 JSON 格式编写，支持 CSS 选择器。常用字段：</p>
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px">
          <thead>
            <tr style="text-align:left;border-bottom:1px solid var(--border)">
              <th style="padding:6px 8px">字段</th>
              <th style="padding:6px 8px">说明</th>
              <th style="padding:6px 8px">示例</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid var(--border)">
              <td style="padding:6px 8px;font-family:var(--font-mono)">toc.item</td>
              <td style="padding:6px 8px">目录页章节链接选择器</td>
              <td style="padding:6px 8px;font-family:var(--font-mono)">#list > dl > dd > a</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border)">
              <td style="padding:6px 8px;font-family:var(--font-mono)">chapter.title</td>
              <td style="padding:6px 8px">章节内容页标题选择器</td>
              <td style="padding:6px 8px;font-family:var(--font-mono)">.bookname > h1</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border)">
              <td style="padding:6px 8px;font-family:var(--font-mono)">chapter.content</td>
              <td style="padding:6px 8px">章节正文内容选择器</td>
              <td style="padding:6px 8px;font-family:var(--font-mono)">#content</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border)">
              <td style="padding:6px 8px;font-family:var(--font-mono)">chapter.filterTxt</td>
              <td style="padding:6px 8px">需要过滤的广告文本正则（|分隔）</td>
              <td style="padding:6px 8px;font-family:var(--font-mono)">记住本站网址[^\n]*|\(本章完\)</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border)">
              <td style="padding:6px 8px;font-family:var(--font-mono)">chapter.filterTag</td>
              <td style="padding:6px 8px">需要移除的 HTML 标签（逗号分隔）</td>
              <td style="padding:6px 8px;font-family:var(--font-mono)">script, div, ins</td>
            </tr>
          </tbody>
        </table>
        <p style="margin-top:8px;font-size:11px;color:var(--muted)">
          如果不配置这些字段或留空，系统将使用内置的通用解析策略。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { formatDate } from '@/utils'
import {
  getCrawlSources,
  createCrawlSource,
  updateCrawlSource,
  deleteCrawlSource,
  testCrawlSource
} from '@/api/books'
import type { CrawlSource, CrawlSourceTestResult } from '@/types'
import TopNav from '@/components/TopNav.vue'

const loading = ref(false)
const sources = ref<CrawlSource[]>([])
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const savingSource = ref(false)
const testingRule = ref(false)
const testResult = ref<CrawlSourceTestResult | null>(null)
const editFormRef = ref<FormInstance>()

const editForm = reactive({
  name: '',
  url: '',
  rule_json: ''
})

const editRules: FormRules = {
  name: [
    { required: true, message: '请输入源站名称', trigger: 'blur' },
    { min: 1, max: 200, message: '名称长度为 1-200 字符', trigger: 'blur' }
  ],
  url: [
    { required: true, message: '请输入源站 URL', trigger: 'blur' },
    { max: 2048, message: 'URL 最长 2048 字符', trigger: 'blur' }
  ],
  rule_json: [
    { required: true, message: '请输入抓取规则 JSON', trigger: 'blur' }
  ]
}

onMounted(() => {
  loadSources()
})

async function loadSources() {
  loading.value = true
  try {
    const { data } = await getCrawlSources()
    if (data.success && data.data) {
      sources.value = data.data
    }
  } catch (err: any) {
    ElMessage.error('加载自定义源站失败')
  } finally {
    loading.value = false
  }
}

function resetEditForm() {
  if (isEditing.value) return  // 编辑时保留已有数据
  editForm.name = ''
  editForm.url = ''
  editForm.rule_json = ''
  testResult.value = null
  editFormRef.value?.resetFields()
}

function openAdd() {
  isEditing.value = false
  editingId.value = null
  testResult.value = null
  resetEditForm()
  showEditDialog.value = true
}

function openEdit(source: CrawlSource) {
  isEditing.value = true
  editingId.value = source.id
  editForm.name = source.name
  editForm.url = source.url
  editForm.rule_json = source.rule_json
  testResult.value = null
  editFormRef.value?.clearValidate()
  showEditDialog.value = true
}

async function handleSave() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingSource.value = true
    try {
      const payload = {
        name: editForm.name.trim(),
        url: editForm.url.trim(),
        rule_json: editForm.rule_json.trim()
      }

      if (isEditing.value && editingId.value !== null) {
        await updateCrawlSource(editingId.value, payload)
        ElMessage.success('源站规则已更新')
      } else {
        await createCrawlSource(payload)
        ElMessage.success('源站规则已添加')
      }

      showEditDialog.value = false
      await loadSources()
    } catch (err: any) {
      const msg = err?.response?.data?.error || err.message || '操作失败'
      ElMessage.error(msg)
    } finally {
      savingSource.value = false
    }
  })
}

async function handleTestRule() {
  const ruleJson = editForm.rule_json.trim()
  if (!ruleJson) return
  testingRule.value = true
  testResult.value = null
  try {
    const { data } = await testCrawlSource({
      url: editForm.url.trim() || 'https://example.com/book/1',
      rule_json: ruleJson
    })
    if (data.success && data.data) {
      testResult.value = data.data
    }
  } catch (err: any) {
    testResult.value = {
      success: false,
      chapter_count: 0,
      sample_chapters: [],
      error: err?.response?.data?.error || err.message || '测试请求失败'
    }
  } finally {
    testingRule.value = false
  }
}

function confirmDelete(source: CrawlSource) {
  ElMessageBox.confirm(
    `确定要删除源站「${source.name}」吗？`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteCrawlSource(source.id)
      ElMessage.success('源站已删除')
      await loadSources()
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.error || err.message || '删除失败')
    }
  }).catch(() => {})
}
</script>

<style scoped>
.stack { display: flex; flex-direction: column; }
.lead { font-size: 14px; color: var(--muted); }

.source-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
}

.help-box {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px 24px;
  font-size: 13px;
  color: var(--muted);
}

.help-box h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.test-result {
  margin-bottom: 12px;
}
</style>
