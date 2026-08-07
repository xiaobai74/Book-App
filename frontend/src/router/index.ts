/* ═══════════════════════════════════════════════════════
   小说管理App · 路由配置
   ═══════════════════════════════════════════════════════ */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
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
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
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
