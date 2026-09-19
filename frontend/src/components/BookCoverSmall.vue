<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍封面组件（小尺寸）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div :class="['book-cover-sm', coverColor]" role="img" :aria-label="`《${title}》封面`">
    <img
      v-if="coverOk"
      class="cover-img"
      :src="coverSrc!"
      :alt="`《${title}》封面`"
      loading="lazy"
      @error="imgFailed = true"
    />
    <!-- 仅当封面抓取失败/无封面时，才显示书名的渐变占位封面 -->
    <template v-if="!coverOk">
      <span class="cover-spine" aria-hidden="true"></span>
      <span class="cover-title" aria-hidden="true">{{ displayTitle }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { coverClass } from '@/utils'

const props = defineProps<{
  title: string
  /** 源站封面图片 URL（为空/加载失败时回退到渐变占位封面） */
  coverSrc?: string | null
}>()

const coverColor = computed(() => coverClass(props.title))
const displayTitle = computed(() =>
  props.title.length > 4 ? props.title.slice(0, 4) : props.title
)

const imgFailed = ref(false)
watch(() => props.coverSrc, () => { imgFailed.value = false })

// 封面抓取成功时只显示图片，不再叠加书名文字
const coverOk = computed(() => !!props.coverSrc && !imgFailed.value)
</script>

<style scoped>
.cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 3px 6px 6px 3px;
  z-index: 1;
}
</style>
