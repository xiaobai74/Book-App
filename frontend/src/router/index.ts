/* ═══════════════════════════════════════════════════════
   小说管理App · 路由配置
   ═══════════════════════════════════════════════════════ */
import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'

// 原生容器环境（Electron 桌面 / Capacitor 移动）用 hash 模式，Web 用 history 模式
const isNative =
  !!(window as any).electronAPI?.isElectron ||
  !!(window as any).Capacitor?.isNative ||
  window.location.origin === 'http://localhost' ||
  window.location.origin === 'https://localhost'

const router = createRouter({
  history: isNative ? createWebHashHistory() : createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/shelf'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/shelf',
      name: 'Shelf',
      component: () => import('@/views/ShelfView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('@/views/SearchView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/detail/:id',
      name: 'BookDetail',
      component: () => import('@/views/BookDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/crawl-sources',
      name: 'CrawlSources',
      component: () => import('@/views/CrawlSourcesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/reader/:id/:chapterIndex',
      name: 'Reader',
      component: () => import('@/views/ReaderView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

/** 全局路由守卫：未登录重定向到登录页 */
router.beforeEach((to, _from, next) => {
  const accessToken = localStorage.getItem('access_token')
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !accessToken) {
    next('/login')
  } else if (!requiresAuth && accessToken && (to.path === '/login' || to.path === '/register')) {
    next('/shelf')
  } else {
    next()
  }
})

export default router
