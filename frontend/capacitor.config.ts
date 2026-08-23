import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.novelmanager.app',
  appName: '小说管理App',
  webDir: 'dist',
  server: {
    // Android WebView 使用 https://localhost 作为源
    androidScheme: 'http',
  },
}

export default config
