<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 顶部导航栏组件
     v1.5 — 移动端适配：≤760px 搜索框收进可展开行（汉堡按钮唤起），
           导航操作按钮换为图标+aria-label（触摸目标 ≥36px）
     v1.6 — 设置与退出合并为用户头像下拉菜单（移动端不再溢出）
     v1.9 — 书架内搜索合并到主搜索框：点击搜索携带 q/mode/ai 参数
           跳转统一搜索页执行
     v2.0 — AI 搜索开关放用户头像下拉菜单：开启后书架内搜索可搭配
           普通搜索（搜索页书架内 tab 显示普通 / AI 切换），
           未开启时书架内搜索默认普通搜索
     v2.1 — 智能搜索模式路由：AI 开关开启时，书架内搜索提交前按
           查询内容自动选择搜索方式（自然语言描述 → AI 语义，
           书名/作者 → 普通），不再需要手动切换模式
     v2.4 — 「我的书架」logo 改为纯展示（不再承担跳转）；用户头像
           点击跳转「我的」页面，原下拉菜单功能（自定义背景 / AI 搜索 /
           修改密码 / 退出登录）全部迁入「我的」页面
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <header class="topnav">
    <div class="topnav-inner">
      <!-- logo 纯展示（v2.4：移除跳转功能，回书架走底部 TabBar / 页内返回按钮） -->
      <div class="logo-area">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          <line x1="8" y1="7" x2="16" y2="7"/>
          <line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
        我的书架
      </div>

      <!-- 桌面搜索框（v1.6：自定义 flex 容器替代 input-group，prepend/append 有内部负 margin hack 导致错位；
           v1.9：书架内搜索合并至此；v2.0：AI 搜索开关在头像菜单，此处仅保留范围选择） -->
      <div v-if="showSearch" class="desktop-search-box">
        <el-select
          v-model="searchTarget"
          size="small"
          class="desktop-target-select"
          aria-label="搜索范围"
        >
          <el-option label="书架内" value="shelf" />
          <el-option label="全网搜索" value="web" />
        </el-select>
        <el-input
          v-model="searchQuery"
          :placeholder="inputPlaceholder"
          :prefix-icon="Search"
          class="desktop-search-input"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button
          aria-label="搜索"
          @click="handleSearch"
        >
          <el-icon><Search /></el-icon>
        </el-button>
      </div>

      <div class="nav-right">
        <router-link v-if="showBackToShelf" to="/shelf" class="nav-back-link">
          <!-- v2.5.1：水墨玻璃返回按钮（移动端保留纯图标形态） -->
          <el-button text size="small" class="nav-btn back-btn">
            <span class="nav-btn-text">← 返回书架</span>
            <span class="nav-btn-icon" aria-hidden="true">←</span>
          </el-button>
        </router-link>

        <!-- 桌面端排行榜入口（移动端走底部 TabBar，避免重复入口；v2.0 图标换为描边奖杯） -->
        <router-link v-if="!showBackToShelf" to="/ranking" class="desktop-ranking-link">
          <el-button text size="small" class="nav-btn">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M8 21h8"/>
              <path d="M12 17v4"/>
              <path d="M7 4h10v4a5 5 0 0 1-10 0V4z"/>
              <path d="M7 6H4a3 3 0 0 0 3 4"/>
              <path d="M17 6h3a3 3 0 0 1-3 4"/>
            </svg>
            <span class="nav-btn-text">排行榜</span>
          </el-button>
        </router-link>

        <!-- 移动端搜索按钮：位于用户头像左侧（v1.6），汉堡图标唤起搜索行 -->
        <el-button
          v-if="showSearch"
          class="mobile-search-toggle"
          text
          aria-label="搜索"
          :aria-expanded="mobileSearchOpen"
          @click="mobileSearchOpen = !mobileSearchOpen"
        >
          <el-icon><Search /></el-icon>
        </el-button>

        <!-- 用户头像（v2.4：点击跳转「我的」页面，原下拉菜单功能已迁入该页） -->
        <button
          type="button"
          class="user-avatar user-avatar-btn"
          :aria-label="`进入我的页面（${authStore.userEmail || '未登录'}）`"
          @click="router.push('/profile')"
        >
          {{ authStore.avatarLetter }}
        </button>
      </div>
    </div>

    <div v-if="showSearch && mobileSearchOpen" class="mobile-search-row">
      <div class="mobile-search-box">
        <el-select v-model="searchTarget" size="small" class="mobile-target-select">
          <el-option label="书架内" value="shelf" />
          <el-option label="全网搜索" value="web" />
        </el-select>
        <el-input
          v-model="searchQuery"
          :placeholder="inputPlaceholder"
          :prefix-icon="Search"
          class="mobile-search-input"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button
          type="primary"
          size="small"
          aria-label="搜索"
          @click="handleSearch"
        >
          <el-icon><Search /></el-icon>
        </el-button>
      </div>
    </div>

  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useAuthStore, useShelfSearchStore } from '@/stores'

const props = withDefaults(defineProps<{
  showSearch?: boolean
  showBackToShelf?: boolean
  searchPlaceholder?: string
}>(), {
  showSearch: true,
  showBackToShelf: false,
  searchPlaceholder: '输入书名，全网搜索…'
})

const authStore = useAuthStore()
/** v2.0：AI 搜索开关状态（v2.4 起开关本体在「我的」页，此处仅用于占位文案与搜索参数） */
const shelfSearch = useShelfSearchStore()
const router = useRouter()
const searchQuery = ref('')
const searchTarget = ref<'shelf' | 'web'>('web')
const mobileSearchOpen = ref(false)

/** 输入框占位文案：书架内按开关状态区分自动识别 / 普通搜索（v2.1，AI 开启时自动识别） */
const inputPlaceholder = computed(() => {
  if (searchTarget.value === 'shelf') {
    return shelfSearch.aiEnabled
      ? '输入书名、作者或自然语言描述…'
      : '搜索书名或作者…'
  }
  return props.searchPlaceholder
})

/** 执行搜索：书架内跳转 /search（v2.1：提交前按查询意图自动选择 AI / 普通并携带 ai 参数），全网搜索同 v1.9 前行为 */
function handleSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  mobileSearchOpen.value = false
  if (searchTarget.value === 'web') {
    router.push(`/search?q=${encodeURIComponent(q)}`)
  } else {
    // v2.1：AI 开关开启时按查询内容自动识别搜索方式（用户未在结果页手动覆盖的前提下）
    shelfSearch.applySearchMode(q)
    const ai = shelfSearch.aiEnabled && shelfSearch.aiMode ? '1' : '0'
    router.push(`/search?q=${encodeURIComponent(q)}&mode=shelf&ai=${ai}`)
  }
}

</script>

<style scoped>
/* ── 桌面搜索框（v1.6：自定义 flex 容器，三件套严格等高） ── */
.desktop-search-box {
  display: flex;
  align-items: stretch;
  gap: 0;
  flex: 0 1 520px;
  height: 32px;
  background: var(--el-input-bg-color, #fff);
  border: 1px solid var(--el-input-border-color, var(--border));
  border-radius: var(--el-input-border-radius, 4px);
  box-shadow: var(--el-input-box-shadow, none);
  transition: box-shadow 0.2s, border-color 0.2s;
}

.desktop-search-box:focus-within {
  border-color: var(--el-input-focus-border-color, var(--accent));
  box-shadow: 0 0 0 1px var(--el-input-focus-border-color, var(--accent)) inset;
}

.desktop-target-select {
  width: 100px;
  flex-shrink: 0;
}

.desktop-target-select :deep(.el-select__wrapper) {
  height: 100%;
  border-radius: 0;
  box-shadow: none;
  border-right: 1px solid var(--border);
}

.desktop-search-input {
  flex: 1;
  min-width: 0;
}

.desktop-search-input :deep(.el-input__wrapper) {
  flex-grow: 1;
  border-radius: 0;
  box-shadow: none;
}

.desktop-search-box > .el-button {
  height: 100%;
  min-height: 0;
  border: none;
  border-radius: 0 3px 3px 0;
}

/* ── 用户头像（v1.6：样式由 global.css 迁入组件，头像即下拉触发器） ── */
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--seal);   /* v2.0：朱砂印章红，水墨点缀 */
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.65), 0 2px 6px rgba(176, 58, 46, 0.35);
}

/* ── 用户头像按钮（v2.4：下拉触发器改为「我的」页面跳转按钮） ── */
.user-avatar-btn {
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
}

.user-avatar-btn:hover {
  filter: brightness(1.08);
}

.user-avatar-btn:focus-visible {
  outline: 2px solid var(--accent-ice);
  outline-offset: 2px;
}

/* v2.0：导航描边图标（与 logo 同风格：1.8 描边 / 圆角线帽） */
.nav-icon {
  width: 16px;
  height: 16px;
  margin-right: 4px;
  vertical-align: -3px;
}

/* ── 桌面搜索框：prepend 下拉与 append 按钮撑满输入框高度（v1.6） ──
   已废弃：input-group 的 prepend/append 存在内部负 margin hack，改用 .desktop-search-box 自定义容器 */

/* ── 移动端搜索按钮（默认隐藏，≤760px 显示） ── */
.mobile-search-toggle {
  display: none;
  flex-shrink: 0;
  font-size: 18px;
  min-height: 36px;
  padding: 6px 10px;
}

/* ── 移动端搜索行（默认隐藏） ── */
.mobile-search-row {
  display: none;
  padding: 8px 12px calc(10px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.mobile-search-box {
  display: flex;
  align-items: stretch; /* 三件套（下拉/输入框/按钮）统一高度，v1.6 */
  gap: 8px;
  height: 40px;
  width: 100%;
  max-width: 560px;
  margin: 0 auto;
}

.mobile-target-select {
  width: 108px;
  flex-shrink: 0;
}

.mobile-target-select :deep(.el-select__wrapper) {
  min-height: 40px;
  height: 40px;
}

.mobile-search-input {
  flex: 1;
  min-width: 0;
}

.mobile-search-input :deep(.el-input__wrapper) {
  flex-grow: 1;
}

.mobile-search-input :deep(.el-input__inner) {
  height: 100%;
}

/* 搜索按钮与输入框严格等高（Element Plus 按钮有显式 height，需覆盖而非依赖 stretch） */
.mobile-search-box :deep(.el-button) {
  height: 40px;
  min-height: 40px;
  flex-shrink: 0;
}

/* ── 导航操作按钮：桌面显示文字，≤760px 仅显示图标 ── */
.nav-btn-icon {
  display: none;
}

/* v2.5.1：顶栏返回按钮复用全局 .back-btn 水墨玻璃样式，
   覆盖 el-button 默认的透明底/内边距，保持胶囊观感 */
.nav-btn.back-btn {
  padding: 7px 18px;
  height: auto;
  background: var(--surface);
  --el-button-hover-bg-color: var(--surface);
  --el-button-bg-color: var(--surface);
}
.nav-back-link {
  text-decoration: none;
}

@media (max-width: 900px) {
  .desktop-search-box { flex: 0 1 320px; }
}

@media (max-width: 760px) {
  /* 搜索框收进可展开行 */
  .desktop-search-box { display: none; }
  .mobile-search-toggle { display: inline-flex; }
  .mobile-search-row { display: block; }

  /* 排行榜入口仅桌面端显示，移动端走底部 TabBar */
  .desktop-ranking-link { display: none; }

  /* 操作按钮压缩为图标（触摸目标 ≥36px） */
  .nav-btn-text { display: none; }
  .nav-btn-icon {
    display: inline;
    font-size: 16px;
    line-height: 1;
  }
  .nav-btn { min-height: 36px; padding: 6px 8px; }
}

@media (max-width: 640px) {
  .topnav-inner { gap: 6px; }
  .topnav .logo-area { font-size: 16px; }
  .nav-btn { padding: 6px; }
  .mobile-search-row { padding-inline: 10px; }
  .mobile-target-select { width: 100px; }
}
</style>
