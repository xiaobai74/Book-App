<!-- ═══════════════════════════════════════════════════════════════
     小说管理App · 顶部导航栏组件
     ═══════════════════════════════════════════════════════════════ -->
<template>
  <header class="topnav">
    <div class="topnav-inner">
      <router-link to="/shelf" class="logo-area">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          <line x1="8" y1="7" x2="16" y2="7"/>
          <line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
        我的书架
      </router-link>

      <el-input
        v-if="showSearch"
        v-model="searchQuery"
        :placeholder="searchPlaceholder"
        :prefix-icon="Search"
        class="search-input"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prepend>
          <el-select
            v-model="searchTarget"
            size="small"
            style="width:100px"
          >
            <el-option label="书架内" value="shelf" />
            <el-option label="全网搜索" value="web" />
          </el-select>
        </template>
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>

      <div class="nav-right">
        <router-link v-if="showSettingsBtn" to="/settings">
          <el-button text size="small">设置</el-button>
        </router-link>

        <router-link v-if="showBackToShelf" to="/shelf">
          <el-button text size="small">← 返回书架</el-button>
        </router-link>

        <span class="user-avatar">{{ authStore.avatarLetter }}</span>
        <el-button text size="small" @click="handleLogout">退出</el-button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores'
import { ElMessageBox } from 'element-plus'

withDefaults(defineProps<{
  showSearch?: boolean
  showSettingsBtn?: boolean
  showBackToShelf?: boolean
  searchPlaceholder?: string
}>(), {
  showSearch: true,
  showSettingsBtn: true,
  showBackToShelf: false,
  searchPlaceholder: '输入书名，全网搜索…'
})

const authStore = useAuthStore()
const router = useRouter()
const searchQuery = ref('')
const searchTarget = ref<'shelf' | 'web'>('web')

function handleSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  if (searchTarget.value === 'web') {
    router.push(`/search?q=${encodeURIComponent(q)}`)
  } else {
    router.push(`/search?q=${encodeURIComponent(q)}&mode=shelf`)
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
.search-input {
  flex: 0 1 520px;
}

@media (max-width: 768px) {
  .search-input { flex: 0 1 280px; }
}

@media (max-width: 640px) {
  .topnav-inner { flex-wrap: wrap; gap: 8px; }
  .search-input { flex: 0 0 100%; order: 3; }
}
</style>
