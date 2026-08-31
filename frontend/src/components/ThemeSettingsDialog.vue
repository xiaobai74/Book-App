<!-- ═══════════════════════════════════════════════════
     小说管理App · 自定义背景设置弹窗（v1.8）
     参考「参考项目/Colorful-master」动态换肤 + MicaForEveryone
     细粒度调参设计：
     · 预设主题卡片：一键切换（立即生效并持久化）
     · 自定义图片：本地上传（IndexedDB 存储），
       拖拽/点击上传，更换 / 设为背景 / 移除
     · 自定义调色板：8 项颜色选择器 + 场景切换，
       改动实时预览到全局背景层，点「保存」落盘
     · 粒子开关 / 数量：雪花（水墨场景）或星光（星夜场景）
     打开/关闭由 theme store settingsVisible 驱动（v-model）
     ═══════════════════════════════════════════════════ -->
<template>
  <el-dialog
    :model-value="themeStore.settingsVisible"
    width="640px"
    class="theme-dialog"
    :close-on-click-modal="false"
    append-to-body
    aria-label="自定义背景设置"
    @update:model-value="onVisibleChange"
    @open="onOpen"
    @closed="themeStore.closeSettings()"
  >
    <template #header>
      <span class="dialog-title">自定义背景</span>
    </template>

    <!-- ① 预设主题：一键切换，即时生效 -->
    <section class="theme-section" aria-labelledby="preset-heading">
      <h3 id="preset-heading" class="section-title">预设主题</h3>
      <div class="preset-grid" role="radiogroup" aria-label="预设主题列表">
        <button
          v-for="preset in THEME_PRESETS"
          :key="preset.id"
          type="button"
          class="preset-card"
          :class="{ 'is-active': isPresetActive(preset) }"
          role="radio"
          :aria-checked="isPresetActive(preset)"
          @click="applyPreset(preset)"
        >
          <span class="preset-thumb" :style="thumbStyle(preset.palette)" aria-hidden="true"></span>
          <span class="preset-label">{{ preset.label }}</span>
          <span class="preset-desc">{{ preset.description }}</span>
        </button>
      </div>
    </section>

    <!-- ② 自定义图片：本地上传（v1.8+ 新增）。
         图片 Blob 存 IndexedDB（无大小上限压力），运行时 object URL 渲染 -->
    <section class="theme-section" aria-labelledby="image-heading">
      <h3 id="image-heading" class="section-title">自定义图片</h3>

      <!-- 未上传：拖拽 + 点击上传区 -->
      <div
        v-if="!themeStore.active.imageUrl"
        class="image-dropzone"
        role="button"
        tabindex="0"
        :aria-label="`上传背景图片，支持 JPG、PNG、WebP，最大 ${MAX_IMAGE_SIZE_MB}MB`"
        :class="{ 'is-dragging': isDragging }"
        @click="fileInput?.click()"
        @keydown.enter.prevent="fileInput?.click()"
        @keydown.space.prevent="fileInput?.click()"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <span class="dropzone-icon" aria-hidden="true">🖼️</span>
        <span class="dropzone-text">点击或拖拽图片到此处上传</span>
        <span class="dropzone-help">支持 JPG / PNG / WebP / GIF，最大 {{ MAX_IMAGE_SIZE_MB }}MB，仅保存在本机浏览器</span>
      </div>

      <!-- 已上传：缩略图 + 操作按钮 -->
      <div v-else class="image-preview-row">
        <img
          :src="themeStore.active.imageUrl"
          class="image-preview-thumb"
          alt=""
          draggable="false"
        />
        <div class="image-preview-meta">
          <span class="image-preview-name">{{ themeStore.active.imageName || '我的背景' }}</span>
          <span v-if="themeStore.active.scene === 'image'" class="image-preview-state">正在使用</span>
          <span v-else class="image-preview-state">已保存，可一键设为背景</span>
        </div>
        <div class="image-preview-actions">
          <el-button size="small" @click="fileInput?.click()">更换</el-button>
          <el-button
            v-if="themeStore.active.scene !== 'image'"
            size="small"
            type="primary"
            @click="handleUseImage"
          >
            设为背景
          </el-button>
          <el-button size="small" @click="handleRemoveImage">移除</el-button>
        </div>
      </div>

      <!-- 隐藏的原生文件选择（拖拽与点击共用） -->
      <input
        ref="fileInput"
        type="file"
        class="visually-hidden-input"
        accept="image/jpeg,image/png,image/webp,image/gif"
        aria-hidden="true"
        tabindex="-1"
        @change="onFileChange"
      />
    </section>

    <!-- ③ 自定义调色板：细粒度调参，实时预览（图片背景激活时禁用，避免改动被静默丢弃） -->
    <section class="theme-section" aria-labelledby="palette-heading">
      <h3 id="palette-heading" class="section-title">自定义配色</h3>
      <p v-if="themeStore.active.scene === 'image'" class="section-help">
        当前使用图片背景，选择预设主题后即可编辑配色
      </p>
      <div class="palette-grid">
        <label v-for="item in paletteItems" :key="item.key" class="palette-item">
          <span class="palette-item-label">{{ item.label }}</span>
          <el-color-picker
            v-model="paletteDraft[item.key]"
            size="small"
            :predefine="predefineColors"
            :disabled="themeStore.active.scene === 'image'"
            :aria-label="`${item.label}颜色`"
            @change="onPaletteChange"
          />
        </label>
      </div>

      <div class="scene-switch">
        <span class="scene-switch-label">场景</span>
        <el-radio-group
          :model-value="sceneDraft"
          :disabled="themeStore.active.scene === 'image'"
          @update:model-value="onSceneChange"
        >
          <el-radio-button value="inkSnow">水墨雪景</el-radio-button>
          <el-radio-button value="starryNight">静谧星夜</el-radio-button>
          <el-radio-button value="none">无场景</el-radio-button>
        </el-radio-group>
      </div>
    </section>

    <!-- ③ 粒子（雪花 / 星光） -->
    <section class="theme-section" aria-labelledby="particle-heading">
      <h3 id="particle-heading" class="section-title">飘落粒子</h3>
      <div class="particle-row">
        <el-switch
          :model-value="themeStore.active.particles"
          size="small"
          aria-label="粒子开关"
          @update:model-value="onParticlesToggle"
        />
        <el-slider
          class="particle-slider"
          :model-value="themeStore.active.particleCount"
          :min="PARTICLE_MIN"
          :max="PARTICLE_MAX"
          :step="3"
          :show-tooltip="false"
          :disabled="!themeStore.active.particles"
          aria-label="粒子数量"
          @update:model-value="onParticleCountChange"
        />
        <span class="particle-count" aria-live="polite">{{ particleLabel }}</span>
      </div>
      <p class="section-help">
        {{ themeStore.displayed.scene === 'starryNight' ? '星夜场景下粒子渲染为闪烁星光' : '关闭后背景不再渲染飘落粒子' }}
      </p>
    </section>

    <!-- ④ 背景透明度（v2.5.1）：控制背景场景层不透明度，即时生效并持久化 -->
    <section class="theme-section" aria-labelledby="opacity-heading">
      <h3 id="opacity-heading" class="section-title">背景透明度</h3>
      <div class="particle-row">
        <el-slider
          class="particle-slider"
          :model-value="Math.round(themeStore.active.bgOpacity * 100)"
          :min="BG_OPACITY_MIN_PCT"
          :max="100"
          :step="5"
          :show-tooltip="false"
          aria-label="背景透明度"
          @update:model-value="onBgOpacityChange"
        />
        <span class="particle-count" aria-live="polite">{{ Math.round(themeStore.active.bgOpacity * 100) }}%</span>
      </div>
      <p class="section-help">调低后背景场景/图片逐渐隐去，画面更素雅，页面内容不受影响</p>
    </section>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleReset">恢复默认</el-button>
        <span class="footer-spacer"></span>
        <el-button @click="themeStore.closeSettings()">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useThemeStore, THEME_PRESETS, PARTICLE_MIN, PARTICLE_MAX, BG_OPACITY_MIN } from '@/stores/theme'
import type { BackgroundScene, BackgroundPalette, ThemePreset } from '@/stores/theme'

const themeStore = useThemeStore()

/** 背景透明度滑杆下限（百分比，对应 BG_OPACITY_MIN，v2.5.1） */
const BG_OPACITY_MIN_PCT = Math.round(BG_OPACITY_MIN * 100)

/** 图片上传限制：类型白名单 + 10MB（IndexedDB 足够承载，Blob 不膨胀） */
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const MAX_IMAGE_SIZE_MB = 10

/** 自定义调色板草稿（打开弹窗时同步为当前背景） */
const paletteDraft = reactive<BackgroundPalette>({ ...themeStore.active.palette })

/** 场景草稿（打开弹窗时同步为当前背景） */
const sceneDraft = ref<BackgroundScene>(themeStore.active.scene)

/** 是否处于自定义编辑（改动过任一色板/场景后为 true） */
const hasCustomEdit = ref(false)

/** 隐藏文件输入框引用 */
const fileInput = ref<HTMLInputElement | null>(null)

/** 拖拽悬停态 */
const isDragging = ref(false)

/** 图片上传处理中（防重复提交） */
const isUploading = ref(false)

/** 颜色选择器的预定义快捷色（冷→暖，符合项目色系） */
const predefineColors = [
  '#e9eef2', '#f1f3f5', '#aebcc8', '#93a5b4',
  '#e7c2cd', '#f7f1ee', '#c97a63', '#eee7e4',
  '#101726', '#18233a', '#2a2c52', '#dbe6f5', '#f6e9c9'
]

/** 调色板条目的中文标签 */
const paletteItems: { key: keyof BackgroundPalette; label: string }[] = [
  { key: 'bg', label: '底色' },
  { key: 'scene', label: '主景' },
  { key: 'sceneDeep', label: '深景' },
  { key: 'accent', label: '点缀' },
  { key: 'accentSoft', label: '点缀二' },
  { key: 'ground', label: '地面' },
  { key: 'silhouette', label: '剪影' },
  { key: 'mist', label: '雾层' }
]

/** 预设卡片缩略图：底色 + 主景色两段渐变 */
function thumbStyle(palette: BackgroundPalette) {
  return {
    background: `linear-gradient(160deg, ${palette.bg} 0%, ${palette.scene} 72%, ${palette.sceneDeep} 100%)`
  }
}

/** 预设是否处于激活态（预设来源且 id 匹配） */
function isPresetActive(preset: ThemePreset) {
  return themeStore.active.source === 'preset' && themeStore.active.presetId === preset.id
}

/** 粒子数量文案 */
const particleLabel = computed(() => {
  if (!themeStore.active.particles) return '已关闭'
  if (themeStore.active.particleCount === 0) return '0（无粒子）'
  return `${themeStore.active.particleCount} 个`
})

/** 草稿同步为当前生效背景（色板 + 场景），并清除自定义编辑态；
    scene 可显式指定（上传/切回图片后跟随 'image'） */
function syncDraft(scene?: BackgroundScene) {
  Object.assign(paletteDraft, themeStore.active.palette)
  sceneDraft.value = scene ?? themeStore.active.scene
  hasCustomEdit.value = false
}

/** 打开弹窗：草稿同步为当前背景（丢弃上次未保存改动） */
function onOpen() {
  syncDraft()
  isDragging.value = false
}

/** 弹窗显隐变化：非打开路径的关闭统一走 store.closeSettings（撤销预览） */
function onVisibleChange(visible: boolean) {
  if (!visible) themeStore.closeSettings()
}

/** 选择预设：立即生效 + 持久化，草稿同步 */
function applyPreset(preset: ThemePreset) {
  themeStore.applyPreset(preset)
  syncDraft()
}

/** 色板任一项改动：进入自定义编辑态，实时预览。
    图片背景激活时仅记录草稿（背景是图片，色板不可见；
    切回预设场景后保存的色板立即生效） */
function onPaletteChange() {
  hasCustomEdit.value = true
  if (sceneDraft.value === 'image') return
  themeStore.previewBackground(sceneDraft.value, { ...paletteDraft })
}

/** 场景切换：进入自定义编辑态，实时预览（无场景时保留色板草稿） */
function onSceneChange(scene: string | number | boolean | undefined) {
  sceneDraft.value = scene as BackgroundScene
  hasCustomEdit.value = true
  themeStore.previewBackground(sceneDraft.value, { ...paletteDraft })
}

/** 拖拽放入：取第一个图片文件走统一校验/上传 */
function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) void uploadImage(file)
}

/** 文件输入变更：取第一个文件 */
function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) void uploadImage(file)
  input.value = '' // 允许再次选择同一文件
}

/** 统一的上传校验 + 落库 + 生效 */
async function uploadImage(file: File) {
  if (isUploading.value) return
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    ElMessage.error('仅支持 JPG / PNG / WebP / GIF 格式的图片')
    return
  }
  if (file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024) {
    ElMessage.error(`图片大小不能超过 ${MAX_IMAGE_SIZE_MB}MB`)
    return
  }
  isUploading.value = true
  try {
    await themeStore.applyImageFile(file)
    // 上传后草稿跟随当前（图片）背景，避免遗留未保存的调色板预览
    syncDraft('image')
    ElMessage.success('图片背景已设置')
  } catch {
    ElMessage.error('图片保存失败，请重试')
  } finally {
    isUploading.value = false
  }
}

/** 「设为背景」：把已保存的图片重新切回背景 */
async function handleUseImage() {
  const ok = await themeStore.reapplyImage()
  if (!ok) {
    ElMessage.error('图片读取失败，请重新上传')
  } else {
    syncDraft('image')
  }
}

/** 「移除」：删库 + 回退默认预设 */
async function handleRemoveImage() {
  await themeStore.removeImageBackground()
  syncDraft()
  ElMessage.success('图片背景已移除')
}

/** 粒子开关：即时生效并持久化 */
function onParticlesToggle(enabled: string | number | boolean) {
  themeStore.setParticles(!!enabled)
}

/** 粒子数量：即时生效并持久化 */
function onParticleCountChange(count: string | number | undefined) {
  themeStore.setParticleCount(Number(count) || 0)
}

/** 背景透明度（百分比）：即时生效并持久化（v2.5.1） */
function onBgOpacityChange(value: string | number | undefined) {
  themeStore.setBgOpacity((Number(value) || 100) / 100)
}

/** 保存：自定义草稿转正。
    图片背景激活时跳过色板保存（图片背景由图片区即时生效，
    草稿中的配色留待下次切回预设场景使用） */
function handleSave() {
  if (hasCustomEdit.value && sceneDraft.value !== 'image') {
    themeStore.saveCustom(sceneDraft.value, { ...paletteDraft })
  }
  themeStore.closeSettings()
}

/** 恢复默认预设 */
function handleReset() {
  themeStore.resetToDefault()
  syncDraft()
}
</script>

<style scoped>
/* ── 弹窗整体 ── */
.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg);
}

.theme-section {
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--fg-soft);
}

.section-help {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted);
}

/* ── 预设卡片 ── */
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.preset-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  font: inherit;
  transition: border-color 0.15s;
}

.preset-card:hover {
  border-color: var(--input-border);
}

.preset-card:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.preset-card.is-active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent) inset;
}

.preset-thumb {
  display: block;
  width: 100%;
  height: 52px;
  border-radius: var(--radius);
}

.preset-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg);
}

.preset-desc {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}

/* ── 自定义图片上传区 ── */
.image-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 22px 16px;
  border: 1px dashed var(--input-border);
  border-radius: var(--radius-md);
  background: var(--surface);
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.image-dropzone:hover,
.image-dropzone.is-dragging {
  border-color: var(--accent);
  background: var(--hover);
}

.image-dropzone:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.dropzone-icon {
  font-size: 26px;
  line-height: 1;
}

.dropzone-text {
  font-size: 13px;
  color: var(--fg-soft);
}

.dropzone-help {
  font-size: 12px;
  color: var(--muted);
}

/* 已上传：缩略图 + 元信息 + 操作 */
.image-preview-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.image-preview-thumb {
  width: 84px;
  height: 52px;
  object-fit: cover;
  border-radius: var(--radius);
  flex-shrink: 0;
  background: var(--bg);
}

.image-preview-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.image-preview-name {
  font-size: 13px;
  color: var(--fg);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-preview-state {
  font-size: 12px;
  color: var(--muted);
}

.image-preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 隐藏的原生文件输入（拖拽与点击共用同一输入） */
.visually-hidden-input {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  clip: rect(0 0 0 0);
  overflow: hidden;
}

/* ── 自定义调色板 ── */
.palette-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px 14px;
}

.palette-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--fg-soft);
}

.palette-item-label {
  flex-shrink: 0;
}

/* ── 场景切换 ── */
.scene-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.scene-switch-label {
  font-size: 12px;
  color: var(--fg-soft);
}

/* ── 粒子行 ── */
.particle-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.particle-slider {
  flex: 1;
  min-width: 0;
}

.particle-count {
  min-width: 72px;
  text-align: right;
  font-size: 12px;
  color: var(--muted);
}

/* ── 底部按钮 ── */
.dialog-footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-spacer {
  flex: 1;
}

/* ── 移动端适配（v1.5 断点惯例） ── */
@media (max-width: 640px) {
  .preset-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .palette-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .image-preview-row {
    flex-wrap: wrap;
  }
  .image-preview-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
