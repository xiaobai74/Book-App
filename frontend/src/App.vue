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
    <!-- v2.7：keep-alive 缓存三个底部 Tab 页（书架/排行榜/我的），
         切换 Tab 时复用已挂载的 DOM 与组件状态，避免重复渲染；
         其余页面（详情/阅读/搜索/登录等）不缓存，正常创建销毁 -->
    <router-view v-slot="{ Component, route }">
      <keep-alive :include="['ShelfView', 'RankingView', 'ProfileView']">
        <component :is="Component" :key="route.path" />
      </keep-alive>
    </router-view>
  </div>
  <!-- 全局命令面板：Ctrl+K 唤起 -->
  <CommandPalette />
  <!-- 移动端底部导航：仅 Tab 页（书架/排行榜/我的）且已登录时显示 -->
  <TabBar v-if="showTabBar" />
</template>

<script setup lang="ts">
// App 根组件：全局背景 + 路由出口 + 全局命令面板 + 移动端硬件返回键
// CommandPalette 通过 window.addEventListener 监听 Ctrl+K 快捷键
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { App as CapApp } from '@capacitor/app'
import { ElMessage } from 'element-plus'
import ThemeBackground from '@/components/ThemeBackground.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import TabBar from '@/components/TabBar.vue'

const route = useRoute()
const router = useRouter()
/** 路由 meta.showTabBar 且有登录 token（与路由守卫判断一致） */
const showTabBar = computed(() =>
  Boolean(route.meta.showTabBar) && !!localStorage.getItem('access_token')
)

/* ── 移动端硬件返回键（仅 Capacitor 原生平台注册） ── */
/** 双击退出判定窗口（ms）：判定与 toast 提示时长共用，保证提示可见期内可完成二次确认 */
const EXIT_DOUBLE_PRESS_MS = 2000
let lastBackPress = 0
let backListener: { remove: () => Promise<void> } | null = null
let unmounted = false

/** 双击退出：首按 toast（时长与双击窗口同步），窗口内再按退出 App */
function doublePressExit() {
  const now = Date.now()
  if (now - lastBackPress < EXIT_DOUBLE_PRESS_MS) {
    CapApp.exitApp()
  } else {
    lastBackPress = now
    ElMessage({ message: '再按一次退出应用', type: 'info', duration: EXIT_DOUBLE_PRESS_MS })
  }
}

function onHardwareBack() {
  // 1) 弹层开启时优先关闭最上层弹层，避免丢失用户输入（Android UX 规范）
  const overlay = document.querySelector(
    '.el-overlay:not([style*="display: none"]), .sheet-mask, .reader-settings-mask'
  )
  if (overlay) {
    // EP dialog 的 esc 监听在遮罩层、自定义底部弹层监听 window：
    // 从当前焦点节点派发 Escape 冒泡事件可两者兼顾（EP 焦点陷阱保证焦点在 dialog 内）
    const target = (document.activeElement as HTMLElement) ?? document.body
    target.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    return
  }
  // 2) 书架页：双击退出
  if (route.name === 'Shelf') {
    doublePressExit()
    return
  }
  // 3) 无历史可回退（冷启动直达登录/注册、深链等）：双击退出兜底，防返回键失灵被困
  if (window.history.state?.back == null) {
    doublePressExit()
    return
  }
  // 4) 默认返回上一页；离开书架即重置双击窗口，防跨路由「无提示秒退」
  lastBackPress = 0
  router.back()
}

onMounted(() => {
  // 首行注册，不依赖任何 await；Electron 无硬件返回键、Web 浏览器返回键由浏览器自身处理，故仅 Capacitor 原生平台注册
  if (!!(window as any).Capacitor?.isNativePlatform?.()) {
    CapApp.addListener('backButton', onHardwareBack).then((handle) => {
      if (unmounted) {
        handle.remove()
        return
      }
      backListener = handle
    }).catch((err) => console.warn('[App] backButton 监听注册失败:', err))
  }
})

onUnmounted(() => {
  unmounted = true
  backListener?.remove().catch(() => {})
  backListener = null
})
</script>
