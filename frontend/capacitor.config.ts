import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.novelmanager.app',
  appName: '小说管理App',
  webDir: 'dist',
  server: {
    // Android WebView 源固定为 http://localhost，后端 CORS 白名单需包含该源
    androidScheme: 'http',
  },
}

export default config
