<!-- ═══════════════════════════════════════════════════════
     小说管理App · 「我的」页面
     v1.0 — 展示用户信息 + App 设置入口（自定义背景 / AI 搜索开关 /
            修改密码 / 退出登录），功能由原顶栏头像下拉菜单迁入（v2.4）。
            页面内不设标题；移动端经底部 TabBar 导航，桌面端提供
            「返回书架」入口。
     ═══════════════════════════════════════════════════════ -->
<template>
  <div class="profile-page">
    <TopNav :show-search="false" />
    <main class="profile-main">
      <div class="profile-card">
        <!-- 桌面端返回书架入口（移动端走底部 TabBar；v2.5.1 水墨玻璃按钮） -->
        <router-link to="/shelf" class="profile-back-link back-btn">← 返回书架</router-link>

        <!-- 用户信息 -->
        <section class="profile-user">
          <div class="profile-avatar">{{ authStore.avatarLetter }}</div>
          <div class="profile-user-meta">
            <p class="profile-email">{{ authStore.userEmail || '未登录' }}</p>
            <p class="profile-role">当前账号</p>
          </div>
        </section>

        <!-- App 设置（原顶栏头像下拉菜单功能迁入） -->
        <section class="profile-settings">
          <button type="button" class="setting-item" @click="themeStore.openSettings()">
            <el-icon :size="18" class="setting-icon"><Picture /></el-icon>
            <span class="setting-label">自定义背景</span>
            <el-icon :size="14" class="setting-arrow"><ArrowRight /></el-icon>
          </button>

          <div class="setting-item">
            <el-icon :size="18" class="setting-icon"><MagicStick /></el-icon>
            <span class="setting-label">AI 搜索</span>
            <el-switch
              :model-value="shelfSearch.aiEnabled"
              size="small"
              :aria-label="`AI 搜索功能${shelfSearch.aiEnabled ? '已开启' : '已关闭'}`"
              @update:model-value="shelfSearch.setAiEnabled"
            />
          </div>

          <button type="button" class="setting-item" @click="changePasswordVisible = true">
            <el-icon :size="18" class="setting-icon"><Key /></el-icon>
            <span class="setting-label">修改个人密码</span>
            <el-icon :size="14" class="setting-arrow"><ArrowRight /></el-icon>
          </button>

          <button type="button" class="setting-item setting-item--danger" @click="handleLogout">
            <el-icon :size="18" class="setting-icon"><SwitchButton /></el-icon>
            <span class="setting-label">退出登录</span>
          </button>
        </section>
      </div>
    </main>

    <!-- 修改密码弹窗（由设置项唤起，原顶栏挂载点迁入） -->
    <ChangePasswordDialog v-model="changePasswordVisible" />
    <!-- 自定义背景设置弹窗（显隐由 theme store 驱动） -->
    <ThemeSettingsDialog />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Key, MagicStick, Picture, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import TopNav from '@/components/TopNav.vue'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'
import ThemeSettingsDialog from '@/components/ThemeSettingsDialog.vue'
import { useAuthStore, useShelfSearchStore } from '@/stores'
import { useThemeStore } from '@/stores/theme'

const authStore = useAuthStore()
const themeStore = useThemeStore()
/** AI 搜索开关（v2.0 原挂顶栏头像菜单，v2.4 迁入本页） */
const shelfSearch = useShelfSearchStore()
const router = useRouter()
const changePasswordVisible = ref(false)

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
.profile-main {
  min-height: calc(100vh - 64px);
  display: flex;
  justify-content: center;
  padding: 24px 16px;
}

.profile-card {
  width: 100%;
  max-width: 520px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 桌面端返回书架入口（移动端隐藏，走底部 TabBar）；样式由全局 .back-btn 提供 */
.profile-back-link {
  align-self: flex-start;
}

.profile-back-link:hover {
  text-decoration: none;
}

/* 用户信息卡片（v2.0：玻璃面，模糊/墨影由全局规则提供） */
.profile-user {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 20px;
  background: var(--surface);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
}

/* v2.0：朱砂印章头像，白圈描边突出层次 */
.profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--seal);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: 22px;
  font-weight: 600;
  font-family: var(--font-heading);
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.7), 0 4px 12px rgba(176, 58, 46, 0.35);
}

.profile-email {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.profile-role {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--muted);
}

/* App 设置列表（v2.0：玻璃面） */
.profile-settings {
  background: var(--surface);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  overflow: hidden;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 20px;
  min-height: 48px;                 /* 触摸目标 ≥ 48px */
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  font-family: inherit;
  font-size: 14px;
  color: var(--fg);
  text-align: left;
}

.setting-item:last-child {
  border-bottom: none;
}

button.setting-item {
  cursor: pointer;
}

button.setting-item:hover {
  background: var(--hover, rgba(0, 0, 0, 0.03));
}

/* v2.0：设置项图标加黛蓝水墨圆角垫，功能入口更醒目 */
.setting-icon {
  color: var(--accent-ice);
  background: var(--accent-soft);
  border-radius: 8px;
  padding: 5px;
  flex-shrink: 0;
}

.setting-label {
  flex: 1;
}

.setting-arrow {
  color: var(--muted);
  flex-shrink: 0;
}

.setting-item--danger .setting-icon {
  color: var(--danger);
  background: var(--danger-soft);
}
.setting-item--danger .setting-label {
  color: var(--danger);
  font-weight: 600;
}

@media (max-width: 760px) {
  /* 移动端底部 TabBar 已覆盖导航，隐藏页内返回书架入口 */
  .profile-back-link { display: none; }
  .profile-main { padding: 16px 12px; }
}
</style>
