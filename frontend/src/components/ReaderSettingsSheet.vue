<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 阅读器设置底部弹层（v2.6.4 移动端）
     阅读器底栏「设置」按钮唤起，承接原顶栏右区的字号 / 行距控件
     （移动端下沉）：
     · 两组分段胶囊选项：字号（小/中/大）、行距（紧凑/标准/宽松）
     · 组件仅持 label 映射并 emit 字符串值，由父组件既有 handleFontSize /
       handleLineHeight 校验并写 localStorage（单一写入路径，无双写）
     · 纯色面板无 backdrop-filter（WebView 友好）；v-if 懒渲染关闭即卸载；
       不加过渡动画（遵循 global.css 零动画设计系统）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <Teleport to="body">
    <div v-if="visible" class="reader-settings-mask" @click.self="close">
      <div
        class="reader-settings-panel"
        :class="{ 'night-mode': nightMode }"
        role="dialog"
        aria-modal="true"
        aria-label="阅读设置"
      >
        <!-- 字号分段选项 -->
        <div class="settings-group">
          <span class="settings-label">字号</span>
          <div class="settings-options">
            <button
              v-for="opt in FONT_SIZE_OPTIONS"
              :key="opt.value"
              type="button"
              class="settings-option"
              :class="{ active: opt.value === fontSize }"
              @click="$emit('select-font-size', opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- 行距分段选项（PRD READER-006 独立可调） -->
        <div class="settings-group">
          <span class="settings-label">行距</span>
          <div class="settings-options">
            <button
              v-for="opt in LINE_HEIGHT_OPTIONS"
              :key="opt.value"
              type="button"
              class="settings-option"
              :class="{ active: opt.value === lineHeight }"
              @click="$emit('select-line-height', opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps<{
  visible: boolean
  fontSize: string
  lineHeight: string
  nightMode: boolean
}>()

const emit = defineEmits<{
  close: []
  'select-font-size': [value: string]
  'select-line-height': [value: string]
}>()

/** label 映射：取值与 ReaderView 的 FONT_SIZES / LINE_HEIGHTS 枚举一致；
    组件不写 localStorage，由父组件既有 setter 统一校验 */
const FONT_SIZE_OPTIONS = [
  { value: 'small', label: '小' },
  { value: 'medium', label: '中' },
  { value: 'large', label: '大' }
]
const LINE_HEIGHT_OPTIONS = [
  { value: 'compact', label: '紧凑' },
  { value: 'normal', label: '标准' },
  { value: 'relaxed', label: '宽松' }
]

function close() {
  emit('close')
}

// 弹层打开时锁定背景滚动 + Esc 关闭（对照 BookActionSheet）
function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}
watch(() => props.visible, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) window.addEventListener('keydown', onEsc)
  else window.removeEventListener('keydown', onEsc)
}, { immediate: true })
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEsc)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* 遮罩：全屏半透明黑，点击空白区关闭 */
.reader-settings-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: color-mix(in oklch, black 45%, transparent);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

/* 面板：贴底纯色（无 backdrop-filter、不复用 .sheet-panel），
   日间 = 阅读器暖纸色，夜间 = 阅读器夜间栏色 */
.reader-settings-panel {
  width: 100%;
  max-width: 560px;
  background: var(--reader-warm-bg);
  color: var(--reader-warm-fg);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: 20px 20px 0 0;
  padding: 20px 16px calc(16px + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: 0 -8px 32px color-mix(in oklch, black 25%, transparent);
}
.reader-settings-panel.night-mode {
  background: var(--reader-night-bar);
  color: var(--reader-night-fg);
  border-color: var(--reader-night-border);
}

/* ── 分段选项组：label + 胶囊按钮行 ── */
.settings-group {
  display: flex;
  align-items: center;
  gap: 14px;
}
.settings-label {
  flex-shrink: 0;
  min-width: 36px;
  font-size: 13px;
  color: var(--reader-warm-muted);
}
.night-mode .settings-label {
  color: var(--reader-night-fg);
  opacity: 0.65;
}
.settings-options {
  flex: 1;
  display: flex;
  gap: 8px;
}
.settings-option {
  flex: 1;
  min-height: 40px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: transparent;
  color: inherit;
  font-size: 13px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.night-mode .settings-option {
  border-color: var(--reader-night-border);
}
/* 选中态：主题色高亮白字 */
.settings-option.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}
</style>
