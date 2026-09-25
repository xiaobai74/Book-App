/* ═══════════════════════════════════════════════════════
   小说管理App · 路由配置
   ═══════════════════════════════════════════════════════ */
import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'

// 原生容器环境（Electron 桌面 / Capacitor 移动）用 hash 模式，Web 用 history 模式
// 注意：Capacitor 8 起全局对象无 isNative 布尔属性，只有 isNativePlatform() 方法
const isNative =
  !!(window as any).electronAPI?.isElectron ||
  !!(window as any).Capacitor?.isNativePlatform?.() ||
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
      meta: { requiresAuth: true, showTabBar: true }
    },
    {
      path: '/ranking',
      name: 'Ranking',
      component: () => import('@/views/RankingView.vue'),
      meta: { requiresAuth: true, showTabBar: true }
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true, showTabBar: true }
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

/* ── v2.7 阶段4：路由 chunk 空闲预取 ──────────────────────
   hover / pointerdown 时提前加载目标视图的懒加载 chunk，
   真实导航时模块已就绪，页面切换不再等待 chunk 下载。
   import() 与路由表定义使用同一模块 specifier，Vite 模块图
   天然去重，导航时复用同一 Promise。                      */
const routePreloaders: Record<string, () => Promise<unknown>> = {
  '/shelf': () => import('@/views/ShelfView.vue'),
  '/ranking': () => import('@/views/RankingView.vue'),
  '/profile': () => import('@/views/ProfileView.vue'),
  '/search': () => import('@/views/SearchView.vue'),
  '/detail': () => import('@/views/BookDetailView.vue'),
  '/reader': () => import('@/views/ReaderView.vue'),
  '/crawl-sources': () => import('@/views/CrawlSourcesView.vue'),
}
const preloadedRoutes = new Set<string>()

/** 预加载 path 对应（或前缀匹配）的路由 chunk，每个前缀只发一次 */
export function preloadRoute(path: string) {
  const key = Object.keys(routePreloaders).find(
    k => path === k || path.startsWith(k + '/') || path.startsWith(k + '?')
  )
  if (!key || preloadedRoutes.has(key)) return
  preloadedRoutes.add(key)
  routePreloaders[key]().catch(() => preloadedRoutes.delete(key))
}

/** 全局委托：锚点（router-link / TabBar）或带 data-preload-route 的元素
    （书架卡片等 div 导航项）hover 即预取目标路由 */
export function installRoutePreload() {
  const handler = (e: Event) => {
    const el = (e.target as Element | null)?.closest?.('a[href], [data-preload-route]')
    if (!el) return
    const route = el.getAttribute('data-preload-route') || el.getAttribute('href')
    if (route && route.startsWith('/')) preloadRoute(route)
  }
  document.addEventListener('pointerover', handler, { passive: true })
  document.addEventListener('pointerdown', handler, { passive: true })
}

export default router
