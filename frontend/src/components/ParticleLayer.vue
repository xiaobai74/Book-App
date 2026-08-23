<!-- ═══════════════════════════════════════════════════
     小说管理App · 飘落粒子层（雪花 / 星光，v1.8 抽取）
     从 InkSnowBackground 抽出，独立可复用：
     · 水墨雪景背景使用（雪花飘落）
     · 星夜背景使用（星光闪烁）
     · 用户图片背景叠加使用（图片上方飘雪花/星光）
     粒子数量与模式由 props 控制；动效 keyframes 在 global.css
     （豁免全局 animation:none，reduced-motion 时静止）。
     纯装饰（aria-hidden），不参与焦点与阅读顺序
     ═══════════════════════════════════════════════════ -->
<template>
  <div
    class="particle-layer"
    :class="{ 'is-star-mode': mode === 'star' }"
    aria-hidden="true"
  >
    <!-- 雪花 = 自上而下飘落；星光 = 分布画面上部静止闪烁。
         数量变化时 Vue 自动增删 DOM 元素；风格按序确定性生成，
         每个元素重新挂载时节奏一致 -->
    <span
      v-for="p in particles"
      :key="p.n"
      class="ink-snowflake"
      :style="p.style"
    ></span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** 粒子数量（0 = 无粒子） */
  count?: number
  /** 粒子模式：snow = 飘落雪花；star = 静止闪烁星光 */
  mode?: 'snow' | 'star'
}>(), {
  count: 9,
  mode: 'snow'
})

/** 粒子渲染列表 */
const particles = computed(() =>
  Array.from({ length: Math.max(0, Math.floor(props.count)) }, (_, i) => ({
    n: i + 1,
    style: particleStyle(i + 1)
  }))
)

/** 粒子位置与节奏：
    雪花：top 固定 -12px 自上而下，17~27s 慢速飘落。
    星光：分布在画面上部 72% 区域，3~9s 闪烁，每三颗取一枚暖色 */
function particleStyle(n: number) {
  const left = (n * 37) % 100 // 37 与 100 互质，铺满整宽且不重叠
  const isStar = props.mode === 'star'
  const dur = isStar ? 3 + ((n * 3) % 7) : 17 + ((n * 7) % 11)
  const delay = isStar ? (n * 2) % 5 : (n * 5) % 17
  const size = n % 3 === 0 ? 3 : n % 2 === 0 ? 5 : 4 // 3/4/5px 三档
  const style: Record<string, string> = {
    left: `${left}%`,
    width: `${size}px`,
    height: `${size}px`,
    '--ink-fall-dur': `${dur}s`,
    '--ink-fall-delay': `${delay}s`
  }
  if (isStar) {
    style.top = `${(n * 29) % 72}%`
    // 每三颗星取一枚暖色（晨星点缀），其余冷白
    style['--star-color'] = n % 3 === 0 ? 'var(--theme-accentSoft, #f6e9c9)' : 'var(--theme-accent, #dbe6f5)'
  }
  return style
}
</script>

<style scoped>
/* 粒子层：铺满父容器（父组件为 fixed 背景层） */
.particle-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* 雪花：淡墨色圆点（跟随主题剪影色，v1.8），边缘半透明晕开（水墨点染感）。
   飘落动画（keyframes + animation 声明）按项目惯例放在 global.css：
   组件内 scoped keyframes 会被 Vue 重命名，且全局 animation:none 规则会将其禁用。
   每个元素通过 --ink-fall-dur / --ink-fall-delay 定制节奏，供全局 animation 使用 */
.ink-snowflake {
  position: absolute;
  top: -12px;
  border-radius: 50%;
  background: var(--theme-silhouette, #bccdd9);
  box-shadow: 0 0 6px 1px color-mix(in srgb, var(--theme-silhouette, #bccdd9) 45%, transparent);
  opacity: 0.85;
}

/* ── 星光模式 ──
   亮白/暖金星点（颜色经 --star-color 传入）+ 光晕；
   闪烁动画 keyframes 在 global.css（同雪花飘落） */
.is-star-mode .ink-snowflake {
  background: var(--star-color, var(--theme-accent, #dbe6f5));
  box-shadow:
    0 0 4px 1px color-mix(in srgb, var(--star-color, #dbe6f5) 80%, transparent),
    0 0 10px 2px color-mix(in srgb, var(--star-color, #dbe6f5) 35%, transparent);
  opacity: 0.95;
}
</style>
