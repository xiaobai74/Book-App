<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍封面组件（小尺寸）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div :class="['book-cover-sm', coverColor]" role="img" :aria-label="`《${title}》封面`">
    <span class="cover-spine" aria-hidden="true"></span>
    <span class="cover-title" aria-hidden="true">{{ displayTitle }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { coverClass } from '@/utils'

const props = defineProps<{
  title: string
}>()

const coverColor = computed(() => coverClass(props.title))
const displayTitle = computed(() =>
  props.title.length > 4 ? props.title.slice(0, 4) : props.title
)
</script>
