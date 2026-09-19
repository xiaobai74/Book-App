<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 本地文件导入对话框
     - Web / 桌面端：系统文件选择器（input[type=file]）多选导入
     - 移动端（Capacitor）：扫描设备存储列出小说文件，勾选导入
     支持格式：.txt / .epub / .pdf / .docx
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <el-dialog
    :model-value="modelValue"
    title="从本地文件导入小说"
    :width="isMobile ? '92%' : '640px'"
    :close-on-click-modal="false"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @closed="reset"
  >
    <!-- ── 平台分支：文件获取方式 ────────────────────────── -->
    <!-- Web / 桌面 -->
    <div v-if="!isMobile">
      <div
        class="drop-zone"
        role="button"
        tabindex="0"
        @click="triggerFileInput"
        @keyup.enter="triggerFileInput"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        :class="{ 'drop-active': dragOver }"
      >
        <el-icon style="font-size:32px;color:var(--accent-ice)"><UploadFilled /></el-icon>
        <p style="margin-top:8px">点击选择或拖拽文件到此处</p>
        <p class="tip">支持 .txt / .epub / .pdf / .docx，可多选，单文件 ≤ 50MB</p>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,.epub,.pdf,.docx"
        multiple
        style="display:none"
        @change="onFilesSelected"
      />
    </div>

    <!-- 移动端 -->
    <div v-else>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <el-button type="primary" :icon="Search" :loading="scanning" @click="startScan">
          扫描设备小说文件
        </el-button>
        <span class="tip">扫描 Download / Documents 等公共目录</span>
      </div>

      <el-alert
        v-if="permDenied"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top:12px"
        title="未获得存储权限"
        description="请在系统设置中授予「所有文件访问」权限后重试。"
      />

      <template v-if="scanned.length">
        <!-- 扩展名过滤 -->
        <el-radio-group v-model="extFilter" size="small" style="margin:12px 0 8px">
          <el-radio-button value="all">全部 ({{ scanned.length }})</el-radio-button>
          <el-radio-button v-for="e in presentExts" :key="e" :value="e">
            {{ e }} ({{ countByExt(e) }})
          </el-radio-button>
        </el-radio-group>

        <el-checkbox-group v-model="selectedPaths" class="scan-list">
          <div v-for="f in filteredScanned" :key="f.path" class="scan-row">
            <el-checkbox :value="f.path" class="scan-check">
              <div class="scan-info">
                <div class="scan-name">{{ f.name }}</div>
                <div class="scan-meta">{{ f.ext.toUpperCase() }} · {{ fmtSize(f.size) }}</div>
              </div>
            </el-checkbox>
          </div>
        </el-checkbox-group>

        <el-button
          style="margin-top:10px"
          :disabled="!selectedPaths.length"
          :loading="addingSelected"
          @click="addSelectedToImport"
        >
          添加选中到导入列表 ({{ selectedPaths.length }})
        </el-button>
      </template>
      <p v-else-if="scanDone && !scanning" class="tip" style="margin-top:12px">
        未扫描到小说文件，请确认文件中存在 .txt/.epub/.pdf/.docx 文件。
      </p>
    </div>

    <!-- ── 待导入列表（书名/作者可编辑） ──────────────────── -->
    <div v-if="items.length" class="import-list">
      <div class="import-head">
        <span>待导入（{{ items.length }}）</span>
        <span class="tip">书名/作者已自动推断，可修改</span>
      </div>
      <div v-for="(item, i) in items" :key="i" class="import-row">
        <div class="import-fields">
          <el-input v-model="item.title" size="small" placeholder="书名" :disabled="item.status === 'uploading' || item.status === 'done'" />
          <el-input v-model="item.author" size="small" placeholder="作者" :disabled="item.status === 'uploading' || item.status === 'done'" />
        </div>
        <div class="import-status">
          <el-tag v-if="item.status === 'pending'" type="info" size="small">待导入</el-tag>
          <el-tag v-else-if="item.status === 'uploading'" type="warning" size="small">导入中…</el-tag>
          <el-tag v-else-if="item.status === 'done'" type="success" size="small">已导入</el-tag>
          <el-tooltip v-else :content="item.error || '导入失败'" placement="top">
            <el-tag type="danger" size="small">失败</el-tag>
          </el-tooltip>
          <el-button
            v-if="item.status !== 'uploading'"
            size="small"
            text
            :icon="Close"
            @click="removeItem(i)"
          />
        </div>
        <div class="import-filename">{{ item.filename }}</div>
      </div>
    </div>

    <p class="tip" style="margin-top:12px">
      导入后系统将自动解析章节，可立即在线阅读并下载 .epub / .txt；章节划分由系统自动推断。
    </p>

    <template #footer>
      <el-button @click="close">{{ items.length ? '关闭' : '取消' }}</el-button>
      <el-button
        type="primary"
        :loading="importing"
        :disabled="!importableCount"
        @click="startImport"
      >
        开始导入{{ importableCount ? ` (${importableCount})` : '' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Search, Close } from '@element-plus/icons-vue'
import { useBooksStore } from '@/stores'
import { isCapacitorPlatform } from '@/api/http'
import type { ImportItem, ScannedFile } from '@/types'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'imported'): void
}>()

const booksStore = useBooksStore()
const isMobile = isCapacitorPlatform

// ── 待导入列表 ──────────────────────────────────────
const items = ref<ImportItem[]>([])
const importing = ref(false)
const importableCount = computed(() => items.value.filter(i => i.status === 'pending' || i.status === 'error').length)

// ── Web / 桌面：文件选择 ────────────────────────────
const fileInputRef = ref<HTMLInputElement>()
const dragOver = ref(false)

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFilesSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) addFiles(Array.from(input.files))
  input.value = '' // 允许重复选择同一文件
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files) addFiles(Array.from(e.dataTransfer.files))
}

const ALLOWED = ['.txt', '.epub', '.pdf', '.docx']
function addFiles(files: File[]) {
  for (const f of files) {
    const ext = extOf(f.name)
    if (!ALLOWED.includes(ext)) {
      ElMessage.warning(`已跳过不支持的文件：${f.name}`)
      continue
    }
    if (f.size > 50 * 1024 * 1024) {
      ElMessage.warning(`已跳过超过 50MB 的文件：${f.name}`)
      continue
    }
    const { title, author } = inferTitle(f.name)
    items.value.push({ file: f, filename: f.name, title, author, status: 'pending' })
  }
}

// ── 移动端：设备扫描 ────────────────────────────────
const scanning = ref(false)
const scanDone = ref(false)
const permDenied = ref(false)
const scanned = ref<ScannedFile[]>([])
const selectedPaths = ref<string[]>([])
const extFilter = ref<string>('all')
const addingSelected = ref(false)

const presentExts = computed(() => {
  const set = new Set(scanned.value.map(f => f.ext))
  return Array.from(set).sort()
})
const filteredScanned = computed(() =>
  extFilter.value === 'all' ? scanned.value : scanned.value.filter(f => f.ext === extFilter.value)
)
function countByExt(ext: string) {
  return scanned.value.filter(f => f.ext === ext).length
}

async function startScan() {
  scanning.value = true
  permDenied.value = false
  scanDone.value = false
  try {
    const mod = await import('@/utils/deviceScan')
    const ok = await mod.ensurePermissions()
    if (!ok) {
      permDenied.value = true
      return
    }
    scanned.value = await mod.scanNovelFiles()
    selectedPaths.value = []
    scanDone.value = true
    if (scanned.value.length) ElMessage.success(`扫描到 ${scanned.value.length} 个小说文件`)
  } catch (e: any) {
    ElMessage.error('扫描失败：' + (e?.message || e))
  } finally {
    scanning.value = false
  }
}

async function addSelectedToImport() {
  addingSelected.value = true
  try {
    const mod = await import('@/utils/deviceScan')
    const chosen = scanned.value.filter(f => selectedPaths.value.includes(f.path))
    for (const f of chosen) {
      try {
        const blob = await mod.readFileAsBlob(f)
        const { title, author } = inferTitle(f.name)
        items.value.push({ file: blob, filename: f.name, title, author, status: 'pending' })
      } catch {
        ElMessage.error(`读取失败：${f.name}`)
      }
    }
    selectedPaths.value = []
  } finally {
    addingSelected.value = false
  }
}

// ── 导入执行 ────────────────────────────────────────
async function startImport() {
  importing.value = true
  let success = 0
  let fail = 0
  for (const item of items.value) {
    if (item.status === 'done') continue
    item.status = 'uploading'
    try {
      await booksStore.importBook(item.file, item.filename, item.title, item.author)
      item.status = 'done'
      success++
    } catch (e: any) {
      item.status = 'error'
      item.error = e?.response?.data?.error || e?.message || '导入失败'
      fail++
    }
  }
  importing.value = false
  if (success) {
    ElMessage.success(`成功导入 ${success} 本${fail ? `，${fail} 本失败` : ''}`)
    emit('imported')
    if (!fail) close()
  } else if (fail) {
    ElMessage.error('导入失败，请检查文件后重试')
  }
}

function removeItem(i: number) {
  items.value.splice(i, 1)
}

function close() {
  emit('update:modelValue', false)
}

function reset() {
  items.value = []
  scanned.value = []
  selectedPaths.value = []
  scanDone.value = false
  permDenied.value = false
  extFilter.value = 'all'
  importing.value = false
}

// ── 工具函数 ────────────────────────────────────────
function extOf(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

function fmtSize(bytes: number): string {
  if (!bytes) return '—'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++ }
  return n.toFixed(i ? 1 : 0) + u[i]
}

/** 文件名 → 书名/作者推断（与后端 _infer_from_filename 行为一致） */
function inferTitle(filename: string): { title: string; author: string } {
  let stem = filename.replace(/\.[^.]+$/, '')
  stem = stem.replace(/[(（[][^)）\]]*[)）\]]/g, '').trim()
  stem = stem.replace(/^[-_—–·\s]+|[-_—–·\s]+$/g, '')
  if (!stem) stem = filename.replace(/\.[^.]+$/, '')

  const m = stem.match(/^《(.+?)》\s*(?:作者\s*[:：])?\s*(.*)$/)
  if (m) return { title: m[1].trim(), author: (m[2] || '').trim() }

  for (const sep of ['—', '－', '-', '_']) {
    const idx = stem.indexOf(sep)
    if (idx > 0) {
      const l = stem.slice(0, idx).trim()
      const r = stem.slice(idx + 1).trim()
      if (l && r) return { title: l, author: r }
      break
    }
  }
  return { title: stem, author: '' }
}
</script>

<style scoped>
.tip { font-size: 12px; color: var(--muted); }

.drop-zone {
  border: 2px dashed var(--border, #d0d7de);
  border-radius: 12px;
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.drop-zone:hover, .drop-active {
  border-color: var(--accent-ice);
  background: color-mix(in oklch, var(--accent-ice) 6%, transparent);
}

.scan-list {
  display: block;
  max-height: 240px;
  overflow-y: auto;
  width: 100%;
}
.scan-row { padding: 2px 0; }
.scan-check { width: 100%; height: auto; }
.scan-check :deep(.el-checkbox__label) { width: 100%; }
.scan-info { display: inline-block; vertical-align: middle; }
.scan-name { font-size: 13px; color: var(--onbg-title); word-break: break-all; }
.scan-meta { font-size: 11px; color: var(--muted); }

.import-list { margin-top: 16px; border-top: 1px solid var(--border, #eee); padding-top: 12px; }
.import-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 13px; font-weight: 600; margin-bottom: 8px;
}
.import-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 10px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border, #eee);
}
.import-fields { display: flex; gap: 8px; }
.import-fields :deep(.el-input) { flex: 1; }
.import-status { display: flex; align-items: center; gap: 6px; }
.import-filename {
  grid-column: 1 / -1;
  font-size: 11px; color: var(--muted);
  word-break: break-all;
}

@media (max-width: 640px) {
  .import-fields { flex-direction: column; }
}
</style>
