<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 根组件
     v1.2 — 新增全局命令面板 (Ctrl+K)
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <router-view />
  <!-- 全局命令面板：Ctrl+K 唤起 -->
  <CommandPalette />
</template>

<script setup lang="ts">
// App 根组件：路由出口 + 全局命令面板
// CommandPalette 通过 window.addEventListener 监听 Ctrl+K 快捷键
import CommandPalette from '@/components/CommandPalette.vue'
</script>
