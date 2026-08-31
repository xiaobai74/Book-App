<!-- ═══════════════════════════════════════════════════
     小说管理App · 主题背景层（v1.8）
     自定义背景功能（参考「参考项目/Colorful-master」动态换肤思路）：
     · 从 theme store 读取当前背景（预设 / 自定义调色板 / 用户图片）
     · 应用 CSS 变量（--theme-* 全部装饰色 + 场景类型）
     · 按场景渲染：水墨雪景 SVG / 星夜 / 用户图片 / 纯色底
     · 粒子层（雪花/星光）独立叠加，图片背景同样支持
     · 图片为 object-fit: cover 裁切铺满，天然适配任意屏幕比例
     · 图片加载中回退纯色底（--theme-bg），避免白屏闪烁
     v2.0 — 新增恒定宣纸纹理层（glass-veil）：SVG 噪点 + 轻雾渐变，
     参数为固定常量，任何背景主题下质感一致，配合玻璃卡片形成水墨层次。
     v3.0 — 毛玻璃质感升级：双层噪点（粗颗粒 + 细颗粒）+ 加强雾霭，
     背景呈现粗糙磨砂触感与朦胧感。纯装饰（aria-hidden / pointer-events: none）
     ═══════════════════════════════════════════════════ -->
<template>
  <div class="theme-bg-layer" aria-hidden="true">
    <!-- v2.5.1：场景内容层，不透明度由 --theme-bg-opacity（用户设置的背景透明度）
         控制；宣纸纹理层在其外恒定，保证毛玻璃质感不随透明度/主题变化 -->
    <div class="theme-bg-content">
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
  
    <!-- ⑤ v2.0 恒定宣纸纹理：噪点 + 轻雾，不随背景主题变化（毛玻璃质感需求） -->
    <div class="glass-veil"></div>
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

/* v2.5.1：场景内容层，不透明度由用户设置（--theme-bg-opacity，默认 1）。
   调低后场景隐入底色，避免花哨背景干扰内容阅读 */
.theme-bg-content {
  position: absolute;
  inset: 0;
  opacity: var(--theme-bg-opacity, 1);
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

/* ── v2.0 恒定宣纸纹理层：多层 SVG 噪点 + 底部轻雾。
   所有参数为固定常量：无论用户选择哪个背景主题，画面质感恒定。
   v3.0 粗糙毛玻璃质感：
   · 粗颗粒层（baseFrequency 0.55）：大颗粒噪点，营造粗糙磨砂触感
   · 细颗粒层（baseFrequency 1.2）：细密噪点，增加表面质感层次
   · 雾霭渐变：底部白色轻雾，营造背景朦胧感
   三层叠加配合玻璃卡片的 backdrop-filter 共同构成水墨层次 ── */
.glass-veil {
  position: absolute;
  inset: 0;
  background-image:
    /* 雾霭层：底部朦胧白雾，营造朦胧感 */
    linear-gradient(180deg, rgba(255, 255, 255, 0) 40%, rgba(255, 255, 255, 0.18) 100%),
    /* 粗颗粒层：大颗粒噪点，粗糙磨砂质感 */
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='coarse'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.55' numOctaves='4' seed='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23coarse)'/%3E%3C/svg%3E"),
    /* 细颗粒层：细密噪点，丰富质感层次 */
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Cfilter id='fine'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='1.2' numOctaves='3' seed='7' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23fine)'/%3E%3C/svg%3E");
  background-size: 100% 100%, 200px 200px, 150px 150px;
  opacity: 0.14;
  mix-blend-mode: overlay;
}
</style>
