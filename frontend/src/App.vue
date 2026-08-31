<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 根组件
     v1.2 — 新增全局命令面板 (Ctrl+K)
     v1.4 — 新增"跳到主要内容"跳过链接（WCAG 2.4.1）
     v1.7 — 新增全局水墨雪景背景（InkSnowBackground，全页面）
     v1.8 — 背景升级为主题背景层（ThemeBackground，支持自定义）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <!-- 跳过导航：仅键盘 Tab 时可见，直达各页面主要内容区 -->
  <a href="#app-main" class="skip-link">跳到主要内容</a>
  <!-- 主题背景层：全局挂载于内容层之下，所有页面共用（纯装饰，v1.8） -->
  <ThemeBackground />
  <div id="app-main" :class="{ 'has-tabbar': showTabBar }">
    <router-view />
  </div>
  <!-- 全局命令面板：Ctrl+K 唤起 -->
  <CommandPalette />
  <!-- 移动端底部导航：仅 Tab 页（书架/排行榜/我的）且已登录时显示 -->
  <TabBar v-if="showTabBar" />
</template>

<script setup lang="ts">
// App 根组件：全局背景 + 路由出口 + 全局命令面板
// CommandPalette 通过 window.addEventListener 监听 Ctrl+K 快捷键
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ThemeBackground from '@/components/ThemeBackground.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import TabBar from '@/components/TabBar.vue'

const route = useRoute()
/** 路由 meta.showTabBar 且有登录 token（与路由守卫判断一致） */
const showTabBar = computed(() =>
  Boolean(route.meta.showTabBar) && !!localStorage.getItem('access_token')
)
</script>
