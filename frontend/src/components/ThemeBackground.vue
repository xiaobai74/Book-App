<!-- ═══════════════════════════════════════════════════
     小说管理App · 主题背景层（v1.8）
     自定义背景功能（参考「参考项目/Colorful-master」动态换肤思路）：
     · 从 theme store 读取当前背景（预设 / 自定义调色板 / 用户图片）
     · 应用 CSS 变量（--theme-* 全部装饰色 + 场景类型）
     · 按场景渲染：水墨雪景 SVG / 星夜 / 用户图片 / 纯色底
     · 粒子层（雪花/星光）独立叠加，图片背景同样支持
     · 图片为 object-fit: cover 裁切铺满，天然适配任意屏幕比例
     · 图片加载中回退纯色底（--theme-bg），避免白屏闪烁
     纯装饰（aria-hidden / pointer-events: none），不参与交互
     ═══════════════════════════════════════════════════ -->
<template>
  <div class="theme-bg-layer" aria-hidden="true">
    <!-- ① 场景插图：scene === 'none' 时隐藏（背景底由纯色层渲染） -->
    <InkSnowBackground
      v-if="scene === 'inkSnow'"
      :particle-count="particleCount"
    />

    <!-- ② 星夜场景：深蓝夜空渐变 + 星光粒子 -->
    <div v-else-if="scene === 'starryNight'" class="star-scene">
      <ParticleLayer :count="particleCount" mode="star" />
    </div>

    <!-- ③ 用户图片背景：object URL 渲染（v1.8+ 新增）。
         loading 时由底层纯色兜底；alt 为空（纯装饰） -->
    <div v-else-if="scene === 'image'" class="image-scene">
      <img
        v-if="themeStore.active.imageUrl"
        :src="themeStore.active.imageUrl"
        class="bg-image"
        alt=""
        draggable="false"
      />
      <ParticleLayer :count="particleCount" mode="snow" />
    </div>

    <!-- ④ 底层纯色：场景未渲染/图片未就绪时兜底 -->
    <div v-if="!sceneRendered" class="theme-bg-fallback" :style="fallbackStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '@/stores'
import InkSnowBackground from '@/components/InkSnowBackground.vue'
import ParticleLayer from '@/components/ParticleLayer.vue'

const themeStore = useThemeStore()

/** 当前场景（预览态优先，store.displayed 已处理） */
const scene = computed(() => themeStore.displayed.scene)

/** 粒子数量（雪花 / 星光共用） */
const particleCount = computed(() =>
  themeStore.active.particles ? themeStore.active.particleCount : 0
)

/** 场景是否已就绪渲染（图片场景需 object URL 恢复完成） */
const sceneRendered = computed(() => {
  if (scene.value !== 'image') return scene.value !== 'none'
  return !!themeStore.active.imageUrl
})

/** 纯色底兜底样式：随 --theme-bg 变量 */
const fallbackStyle = computed(() => ({
  background: 'var(--theme-bg, #e9eef2)'
}))
</script>

<style scoped>
/* 背景层：覆盖整页（position: fixed），位于内容之下（global.css #app-main z-index:1） */
.theme-bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

/* ── 星夜场景：夜空渐变（场景专属底色） ── */
.star-scene {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    var(--theme-mist, #101726) 0%,
    var(--theme-scene, #18233a) 55%,
    var(--theme-ground, #10192c) 100%
  );
}

/* ── 用户图片场景 ── */
.image-scene {
  position: absolute;
  inset: 0;
}

/* 图片铺满 + 裁切（cover），任意屏幕比例均不变形 */
.bg-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  user-select: none;
}

/* 无场景/图片未就绪的纯色底：铺满背景层 */
.theme-bg-fallback {
  position: absolute;
  inset: 0;
}
</style>
