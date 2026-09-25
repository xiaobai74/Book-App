<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 书籍封面组件（大尺寸）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <div :class="['book-cover', coverColor]" :style="coverStyle" role="img" :aria-label="`《${title}》封面`">
    <img
      v-if="coverOk"
      class="cover-img"
      :src="coverSrc!"
      :alt="`《${title}》封面`"
      loading="lazy"
      decoding="async"
      fetchpriority="low"
      @error="imgFailed = true"
    />
    <!-- 仅当封面抓取失败/无封面时，才显示书名+作者的渐变占位封面 -->
    <template v-if="!coverOk">
      <span class="cover-spine" aria-hidden="true"></span>
      <span class="cover-title" aria-hidden="true">{{ title }}</span>
      <span class="cover-author" aria-hidden="true">{{ author }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { coverClass } from '@/utils'

const props = withDefaults(defineProps<{
  title: string
  author?: string
  bgColor?: string
  /** 源站封面图片 URL（为空/加载失败时回退到渐变占位封面） */
  coverSrc?: string | null
}>(), {
  author: '未知',
  coverSrc: null
})

const coverColor = computed(() => coverClass(props.title))
const coverStyle = computed(() =>
  props.bgColor ? { background: props.bgColor } : {}
)

// 图片加载失败时回退到渐变封面；coverSrc 变化时重置失败标记
const imgFailed = ref(false)
watch(() => props.coverSrc, () => { imgFailed.value = false })

// 封面抓取成功（有 URL 且未加载失败）时只显示图片，不再叠加书名/作者文字
const coverOk = computed(() => !!props.coverSrc && !imgFailed.value)
</script>

<style scoped>
.cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 1;
}
</style>
