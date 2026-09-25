/* ═══════════════════════════════════════════════════════
   小说管理App · 应用入口 (main.ts)
   ═══════════════════════════════════════════════════════ */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router, { installRoutePreload } from './router'
import './styles/global.css'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { size: 'default' })
app.mount('#app')

// v2.7 阶段4：hover/pointerdown 预取路由 chunk，页面切换零等待
installRoutePreload()
