<!-- ═══════════════════════════════════════════════════════
     小说管理App · 移动端底部导航栏
     仅 ≤760px 显示（与现有移动端断点一致）；
     显隐由 App.vue 按路由 meta.showTabBar 控制。
     v2.0 — 毛玻璃化（模糊由全局 .tabbar 规则提供）；选中态改为
     黛蓝图标 + 笔锋短线指示，提升层次与对比。
     ═══════════════════════════════════════════════════════ -->
<template>
  <nav class="tabbar" aria-label="主导航">
    <router-link to="/shelf" class="tab-item" active-class="active">
      <el-icon :size="22"><Collection /></el-icon>
      <span>书架</span>
    </router-link>
    <router-link to="/ranking" class="tab-item" active-class="active">
      <el-icon :size="22"><Trophy /></el-icon>
      <span>排行榜</span>
    </router-link>
    <router-link to="/profile" class="tab-item" active-class="active">
      <el-icon :size="22"><User /></el-icon>
      <span>我的</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { Collection, Trophy, User } from '@element-plus/icons-vue'
</script>

<style scoped>
.tabbar {
  display: none;                          /* 桌面端隐藏，仅移动端显示 */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: calc(56px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  background: rgba(255, 255, 255, 0.62);   /* v2.0 毛玻璃底，模糊由全局规则提供 */
  border-top: 1px solid var(--border);
  z-index: 100;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 11px;
  color: var(--ink-soft);                  /* 未选中：淡墨，对比度提升 */
  text-decoration: none;
  min-height: 48px;                       /* 触摸目标 ≥ 48px */
  position: relative;
}

/* v2.0 选中态：黛蓝 + 图标上方笔锋短线（水墨指示） */
.tab-item.active {
  color: var(--accent);
  font-weight: 600;
}
.tab-item.active::before {
  content: '';
  position: absolute;
  top: 3px;
  width: 18px;
  height: 3px;
  border-radius: 1px 3px 2px 3px;
  background: linear-gradient(90deg, var(--accent), transparent);
}

@media (max-width: 760px) {
  .tabbar { display: flex; }
}
</style>
