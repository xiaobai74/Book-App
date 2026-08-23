<!-- ═══════════════════════════════════════════════════
     小说管理App · 水墨雪景背景（v1.7 引入，v1.8 变量化）
     v1.8 — 颜色全部改为 CSS 变量（--theme-*），由 theme store
            统一驱动；雪花粒子抽取为 ParticleLayer（v1.8+ 图片背景复用）。
     纯装饰背景：内联 SVG 绘制，无外部图片资源
     · 远山：两重淡墨灰蓝，蒙雾渐隐（水墨留白）
     · 雪地：近树淡墨剪影 + 雪坡，构图疏朗
     · 梅树：右侧近景，梅花错落点缀枝头
     · 雪花：ParticleLayer 轻缓飘落（仅有的动效，reduced-motion 停用）
     全部为 aria-hidden 装饰，不参与焦点与阅读顺序
     ═══════════════════════════════════════════════════ -->
<template>
  <div class="ink-snow-bg" aria-hidden="true">
    <!-- 水墨雪景：viewBox 锁定 16:9 构图，preserveAspectRatio 裁切填充 -->
    <svg
      class="ink-snow-scene"
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMax slice"
      focusable="false"
      role="presentation"
    >
      <defs>
        <!-- 雾：垂直渐变，用于远景渐隐（水墨"留白"） -->
        <linearGradient id="ink-mist" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="var(--theme-mist, #e8edf1)" />
          <stop offset="1" stop-color="var(--theme-mist, #e8edf1)" stop-opacity="0" />
        </linearGradient>
        <!-- 雪地：纸感白，向底部极浅蓝灰晕开 -->
        <linearGradient id="ink-snow-ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="var(--theme-ground, #f6f8fa)" stop-opacity="0" />
          <stop offset="1" stop-color="var(--theme-ground, #e9eef3)" />
        </linearGradient>
        <!-- 梅树主枝：近景用较深墨色，营造景深 -->
        <linearGradient id="ink-plum-trunk" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="var(--theme-sceneDeep, #6b7d8d)" />
          <stop offset="1" stop-color="var(--theme-sceneDeep, #4c5d6b)" />
        </linearGradient>
      </defs>

      <!-- ① 远山：淡墨灰蓝，两重轮廓由浅入深，交接处模糊过渡（蒙雾感） -->
      <path d="M0 470 Q230 320 460 455 T980 400 Q1180 330 1320 410 T1600 385 L1600 560 L0 560 Z"
            fill="var(--theme-scene, #aebcc8)" opacity="0.55" />
      <path d="M0 535 Q260 405 520 520 T1040 470 Q1250 410 1390 475 T1600 450 L1600 620 L0 620 Z"
            fill="var(--theme-sceneDeep, #93a5b4)" opacity="0.55" />

      <!-- ② 雪地（远雾中的模糊树影叠压其上） -->
      <path d="M0 600 Q420 560 860 615 Q1250 660 1600 585 L1600 900 L0 900 Z" fill="url(#ink-snow-ground)" />

      <!-- 树影：淡墨点景，越远越淡（fog 渐隐） -->
      <g fill="var(--theme-silhouette, #9fb0bd)">
        <ellipse cx="100" cy="615" rx="58" ry="30" opacity="0.35" />
        <ellipse cx="255" cy="590" rx="42" ry="22" opacity="0.3" />
        <ellipse cx="1270" cy="625" rx="52" ry="26" opacity="0.35" />
        <ellipse cx="1460" cy="595" rx="40" ry="20" opacity="0.28" />
      </g>
      <!-- 干枯树枝：极淡墨线，掩入雾中 -->
      <g stroke="var(--theme-silhouette, #9fb0bd)" stroke-width="4" stroke-linecap="round" fill="none" opacity="0.4">
        <path d="M100 635 v-64 M100 600 q-30 -12 -44 -34 M100 606 q28 -16 38 -42" />
        <path d="M1270 648 v-52 M1270 618 q-26 -10 -36 -30 M1270 622 q22 -12 30 -34" />
        <path d="M1460 612 v-44 M1460 588 q-20 -10 -28 -28" />
      </g>

      <!-- ③ 雾：远景渐隐层，覆盖山脚与树影上部（水墨留白手法） -->
      <rect x="0" y="430" width="1600" height="330" fill="url(#ink-mist)" />

      <!-- ④ 梅树：右侧近景（构图疏朗，画面重心偏右下） -->
      <g>
        <!-- 主枝：自右下向画面中央斜上伸展 -->
        <path d="M1600 900 C1500 820 1480 760 1420 680 C1360 600 1300 560 1220 505"
              stroke="url(#ink-plum-trunk)" stroke-width="20" stroke-linecap="round" fill="none" />
        <path d="M1505 745 C1440 690 1400 640 1378 585"
              stroke="var(--theme-sceneDeep, #4c5d6b)" stroke-width="13" stroke-linecap="round" fill="none" opacity="0.95" />
        <path d="M1350 645 C1310 600 1292 565 1285 520"
              stroke="var(--theme-sceneDeep, #5c6d7b)" stroke-width="10" stroke-linecap="round" fill="none" />
        <path d="M1260 540 C1240 495 1240 465 1258 428"
              stroke="var(--theme-sceneDeep, #5c6d7b)" stroke-width="8" stroke-linecap="round" fill="none" />
        <!-- 旁逸小枝（飞白般的细墨线） -->
        <path d="M1438 655 C1412 632 1394 615 1372 603"
              stroke="var(--theme-sceneDeep, #6b7d8d)" stroke-width="6" stroke-linecap="round" fill="none" opacity="0.85" />
        <path d="M1320 615 C1298 592 1282 574 1274 552"
              stroke="var(--theme-sceneDeep, #6b7d8d)" stroke-width="5" stroke-linecap="round" fill="none" opacity="0.85" />
        <path d="M1232 512 C1208 500 1186 496 1164 500"
              stroke="var(--theme-sceneDeep, #6b7d8d)" stroke-width="5" stroke-linecap="round" fill="none" opacity="0.8" />
        <!-- 地面老桩：主枝根部的短横（近景细节，淡墨） -->
        <path d="M1588 900 q-90 -14 -164 -6"
              stroke="var(--theme-sceneDeep, #6b7d8d)" stroke-width="9" stroke-linecap="round" fill="none" opacity="0.7" />
      </g>

      <!-- ⑤ 梅花：淡粉与白，错落点缀枝头 -->
      <g>
        <circle cx="1258" cy="428" r="5.5" fill="var(--theme-accent, #e7c2cd)" />
        <circle cx="1244" cy="452" r="4.5" fill="var(--theme-accentSoft, #f2d8e0)" />
        <circle cx="1220" cy="505" r="6" fill="var(--theme-accentSoft, #f7f1ee)" />
        <circle cx="1274" cy="552" r="5" fill="var(--theme-accent, #e7c2cd)" />
        <circle cx="1285" cy="520" r="5.5" fill="var(--theme-accentSoft, #f2d8e0)" />
        <circle cx="1372" cy="603" r="5" fill="var(--theme-accentSoft, #f7f1ee)" />
        <circle cx="1325" cy="578" r="4.5" fill="var(--theme-accent, #e7c2cd)" />
        <circle cx="1290" cy="585" r="4" fill="var(--theme-accentSoft, #f2d8e0)" />
        <circle cx="1358" cy="625" r="4.5" fill="var(--theme-accent, #e7c2cd)" />
        <circle cx="1405" cy="655" r="5" fill="var(--theme-accentSoft, #f7f1ee)" />
        <circle cx="1438" cy="655" r="4.5" fill="var(--theme-accent, #e7c2cd)" />
        <circle cx="1390" cy="680" r="4" fill="var(--theme-accentSoft, #f2d8e0)" />
        <!-- 待放花苞（更小的墨点，梅花树初雪含蓄） -->
        <circle cx="1268" cy="440" r="3" fill="var(--theme-accent, #c9a0ae)" />
        <circle cx="1338" cy="560" r="3" fill="var(--theme-accent, #c9a0ae)" />
        <circle cx="1380" cy="665" r="3" fill="var(--theme-accent, #c9a0ae)" />
      </g>

      <!-- ⑥ 雪坡：近处留白，两道极淡墨痕增加笔触（构图疏朗） -->
      <path d="M1200 900 Q1380 878 1600 896" stroke="var(--theme-silhouette, #c3cfd8)" stroke-width="5" fill="none" opacity="0.55" />
    </svg>

    <!-- 雪花：ParticleLayer 渲染（数量与开关由 theme store 控制，v1.8 抽取） -->
    <ParticleLayer :count="particleCount" mode="snow" />
  </div>
</template>

<script setup lang="ts">
import ParticleLayer from '@/components/ParticleLayer.vue'

withDefaults(defineProps<{
  /** 雪花粒子数量（0 = 无雪花，v1.8 新增） */
  particleCount?: number
}>(), {
  particleCount: 9
})
</script>

<style scoped>
/* 背景层：覆盖整页（position: fixed），位于内容之下。
   底色随 --theme-bg 变化（自定义背景 v1.8），
   未设置变量时回退 v1.7 竖向渐变 */
.ink-snow-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background: var(--theme-bg, linear-gradient(180deg, #e9eef2 0%, #f4f6f8 46%, #f6f8fa 100%));
}

/* 水墨场景：SVG 铺满整个背景层 */
.ink-snow-scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
</style>
