<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 状态徽章组件
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <span :class="['badge', statusInfo.class]">
    {{ statusInfo.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { statusMap } from '@/utils'
import type { BookStatus } from '@/types'

const props = defineProps<{
  status: BookStatus
}>()

const statusInfo = computed(() => statusMap[props.status] || statusMap.idle)
</script>
