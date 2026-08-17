<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍封面组件（大尺寸）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div :class="['book-cover', coverColor]" :style="coverStyle" role="img" :aria-label="`《${title}》封面`">
    <span class="cover-spine" aria-hidden="true"></span>
    <span class="cover-title" aria-hidden="true">{{ title }}</span>
    <span class="cover-author" aria-hidden="true">{{ author }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { coverClass } from '@/utils'

const props = withDefaults(defineProps<{
  title: string
  author?: string
  bgColor?: string
}>(), {
  author: '未知'
})

const coverColor = computed(() => coverClass(props.title))
const coverStyle = computed(() =>
  props.bgColor ? { background: props.bgColor } : {}
)
</script>
