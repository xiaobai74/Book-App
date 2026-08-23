/* ═══════════════════════════════════════════════════════
   小说管理App · Pinia 统一出口
   ═══════════════════════════════════════════════════════ */
export { useAuthStore } from './auth'
export { useBooksStore } from './books'
export { useThemeStore } from './theme'
export { useShelfSearchStore } from './shelfSearch'
export type { BackgroundScene, BackgroundPalette, ThemePreset, ActiveBackground } from './theme'
