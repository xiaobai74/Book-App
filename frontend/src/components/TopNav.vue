<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 顶部导航栏组件
     v1.5 — 移动端适配：≤760px 搜索框收进可展开行（汉堡按钮唤起），
           导航操作按钮换为图标+aria-label（触摸目标 ≥36px）
     v1.6 — 设置与退出合并为用户头像下拉菜单（移动端不再溢出）
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <header class="topnav">
    <div class="topnav-inner">
      <router-link to="/shelf" class="logo-area" aria-label="返回书架首页">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          <line x1="8" y1="7" x2="16" y2="7"/>
          <line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
        我的书架
      </router-link>

      <!-- 桌面搜索框（v1.6：自定义 flex 容器替代 input-group，prepend/append 有内部负 margin hack 导致错位） -->
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
          :placeholder="searchPlaceholder"
          :prefix-icon="Search"
          class="desktop-search-input"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button aria-label="搜索" @click="handleSearch">
          <el-icon><Search /></el-icon>
        </el-button>
      </div>

      <div class="nav-right">
        <router-link v-if="showBackToShelf" to="/shelf">
          <el-button text size="small" class="nav-btn">
            <span class="nav-btn-text">← 返回书架</span>
            <span class="nav-btn-icon" aria-hidden="true">←</span>
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

        <!-- 用户头像下拉菜单：修改密码 / 退出登录（v1.6） -->
        <el-dropdown class="avatar-dropdown" trigger="click" @command="handleUserCommand">
          <button
            type="button"
            class="user-avatar user-avatar-btn"
            :aria-label="`用户菜单（${authStore.userEmail || '未登录'}），修改密码或退出登录`"
          >
            {{ authStore.avatarLetter }}
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <!-- 图标使用全局注册的字符串名，避免组件响应式警告 -->
              <el-dropdown-item icon="Key" command="changePassword">
                <span class="dropdown-item-text">修改个人密码</span>
              </el-dropdown-item>
              <el-dropdown-item icon="SwitchButton" command="logout" divided>
                <span class="dropdown-item-text dropdown-item-text--logout">退出登录</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
          :placeholder="searchPlaceholder"
          :prefix-icon="Search"
          class="mobile-search-input"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" size="small" aria-label="搜索" @click="handleSearch">
          <el-icon><Search /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 修改密码弹窗（由头像下拉菜单唤起，v1.6 新增） -->
    <ChangePasswordDialog v-model="changePasswordVisible" />
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores'
import { ElMessageBox } from 'element-plus'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'

withDefaults(defineProps<{
  showSearch?: boolean
  showBackToShelf?: boolean
  searchPlaceholder?: string
}>(), {
  showSearch: true,
  showBackToShelf: false,
  searchPlaceholder: '输入书名，全网搜索…'
})

const authStore = useAuthStore()
const router = useRouter()
const searchQuery = ref('')
const searchTarget = ref<'shelf' | 'web'>('web')
const mobileSearchOpen = ref(false)
const changePasswordVisible = ref(false)

function handleSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  mobileSearchOpen.value = false
  if (searchTarget.value === 'web') {
    router.push(`/search?q=${encodeURIComponent(q)}`)
  } else {
    router.push(`/search?q=${encodeURIComponent(q)}&mode=shelf`)
  }
}

/** 头像下拉菜单命令分发（v1.6） */
function handleUserCommand(command: string) {
  if (command === 'changePassword') {
    changePasswordVisible.value = true
  } else if (command === 'logout') {
    handleLogout()
  }
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'info'
  }).then(() => {
    authStore.logout()
    router.push('/login')
  }).catch(() => {})
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
  background: var(--accent);
  color: var(--surface);
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

/* ── 用户头像按钮（v1.6：普通 span 改为按钮，充当下拉触发器） ── */
.avatar-dropdown .user-avatar-btn {
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
}

.avatar-dropdown .user-avatar-btn:hover {
  filter: brightness(1.08);
}

.avatar-dropdown .user-avatar-btn:focus-visible {
  outline: 2px solid var(--accent-ice);
  outline-offset: 2px;
}

.dropdown-item-text {
  font-size: 14px;
  margin-left: 2px;
}

.dropdown-item-text--logout {
  color: var(--danger);
}

/* 下拉面板内分隔线对齐 Element Plus 默认内边距 */
.avatar-dropdown :deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
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

@media (max-width: 900px) {
  .desktop-search-box { flex: 0 1 320px; }
}

@media (max-width: 760px) {
  /* 搜索框收进可展开行 */
  .desktop-search-box { display: none; }
  .mobile-search-toggle { display: inline-flex; }
  .mobile-search-row { display: block; }

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
