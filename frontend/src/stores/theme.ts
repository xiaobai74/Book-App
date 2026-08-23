/* ═══════════════════════════════════════════════════
   小说管理App · 自定义背景主题状态管理 (Pinia)
   v1.8 新增 — 参考「参考项目/Colorful-master」动态换肤思路：
   预设主题包 + 运行时切换 + 自定义调色板 + 用户图片背景，
   全部由 CSS 变量 / object URL 驱动，实时生效，本地持久化。

   主题数据流：
     store → useThemeStore() 初始化 → applyActive()
            → document.documentElement.style.setProperty(--theme-*)
            → ThemeBackground / InkSnowBackground / 设置弹窗读取同一批变量
     设置弹窗 → previewBackground()（实时预览，不落盘）
            → saveCustom() 转正并持久化 / closeSettings() 撤销

   图片背景：
     图片 Blob 存 IndexedDB（见 lib/backgroundImages.ts），
     运行时生成 object URL 供 <img> 渲染；主题持久化
     （localStorage）只存图片 id + 文件名，启动时异步恢复。

   对象 URL 生命周期：
     · 新图替换 / 图片移除 → revokeObjectURL 旧 URL（不再增长）
     · 切到预设 / 自定义调色板 → URL 保留（缩略图 + 一键切回复用）
     · 启动恢复 → 从 IndexedDB 重建 URL
   ═══════════════════════════════════════════════════ */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  generateImageId,
  getBackgroundImage,
  saveBackgroundImage,
  deleteBackgroundImage
} from '@/lib/backgroundImages'

/** 自定义背景的场景标识（水墨雪景 / 星夜 / 无场景纯色 / 用户图片） */
export type BackgroundScene = 'inkSnow' | 'starryNight' | 'none' | 'image'

/** 场景预设（预设主题直接复用其完整色板，保持观感统一） */
export interface ThemePreset {
  id: string
  label: string
  /** 一句话描述，设置弹窗卡片上展示 */
  description: string
  scene: BackgroundScene
  palette: BackgroundPalette
}

/**
 * 自定义背景色板（CSS 变量 --theme-* 的语义化定义）
 * 仅承载"装饰性"信息，对比度不影响功能可用性：
 * 前景卡片/表单始终渲染在 surface 纯色之上，任何背景
 * 变体下正文均满足 WCAG 2.2 AA 对比度要求。
 */
export interface BackgroundPalette {
  /** 背景整体基调（场景之外铺底渐变的底色） */
  bg: string
  /** 场景主体色：水墨=远山淡墨；星夜=夜空深蓝 */
  scene: string
  /** 场景层次深色：水墨=前景山体；星夜=夜色下边缘 */
  sceneDeep: string
  /** 点缀色：水墨=梅花；星夜=星光 */
  accent: string
  /** 点缀副色：水墨=白梅；星夜=暖星 */
  accentSoft: string
  /** 地面/底部色：水墨=雪地；星夜=夜色地面 */
  ground: string
  /** 远景剪影：水墨=雾中树影；星夜=山脊剪影 */
  silhouette: string
  /** 雾层色：水墨=留白渐隐；星夜=夜空上缘渐隐 */
  mist: string
}

/** 当前生效的自定义背景（含来源，用于设置弹窗高亮） */
export interface ActiveBackground {
  /** 'preset' = 预设；'custom' = 用户自定义调色板；'image' = 用户上传图片 */
  source: 'preset' | 'custom' | 'image'
  presetId: string | null
  scene: BackgroundScene
  palette: BackgroundPalette
  /** 雪花 / 星光粒子开关 */
  particles: boolean
  particleCount: number
  /** 图片背景（scene === 'image' 时有值）：IndexedDB 中的 id / 文件名 */
  imageId: string | null
  imageName: string | null
  /** 运行时生成的 object URL（不持久化，启动时异步恢复） */
  imageUrl: string | null
}

export const PARTICLE_MIN = 0
export const PARTICLE_MAX = 48
const STORAGE_KEY = 'app_background_theme_v1'

/** 预设主题包（Colorful 思路：出厂内置，一键切换） */
export const THEME_PRESETS: ThemePreset[] = [
  {
    id: 'snow-ink',
    label: '水墨雪景',
    description: 'v1.7 经典：淡墨远山 · 梅花 · 落雪',
    scene: 'inkSnow',
    palette: {
      bg: '#e9eef2',
      scene: '#aebcc8',
      sceneDeep: '#93a5b4',
      accent: '#e7c2cd',
      accentSoft: '#f7f1ee',
      ground: '#e9eef3',
      silhouette: '#9fb0bd',
      mist: '#e8edf1'
    }
  },
  {
    id: 'snow-dusk',
    label: '暮色红梅',
    description: '暮霭暖调：山色染黛 · 红梅傲雪',
    scene: 'inkSnow',
    palette: {
      bg: '#eee7e4',
      scene: '#b8a49c',
      sceneDeep: '#a58e85',
      accent: '#c97a63',
      accentSoft: '#f6e9e5',
      ground: '#efe4e0',
      silhouette: '#a89388',
      mist: '#ece1dd'
    }
  },
  {
    id: 'star-night',
    label: '静谧星夜',
    description: '深蓝夜幕：星子闪烁 · 山影如黛',
    scene: 'starryNight',
    palette: {
      bg: '#101726',
      scene: '#18233a',
      sceneDeep: '#0b1120',
      accent: '#dbe6f5',
      accentSoft: '#f6e9c9',
      ground: '#10192c',
      silhouette: '#0e1626',
      mist: '#101726'
    }
  },
  {
    id: 'star-dawn',
    label: '拂晓流霜',
    description: '破晓紫蓝：晨星将隐 · 霜色未消',
    scene: 'starryNight',
    palette: {
      bg: '#1c2038',
      scene: '#2a2c52',
      sceneDeep: '#15172e',
      accent: '#cfd8ea',
      accentSoft: '#f2cdb6',
      ground: '#191d38',
      silhouette: '#141630',
      mist: '#1c2038'
    }
  },
  {
    id: 'snow-classic',
    label: '素白留影',
    description: '极简留白：浅灰淡影 · 纸感素净',
    scene: 'inkSnow',
    palette: {
      bg: '#f1f3f5',
      scene: '#c9d2da',
      sceneDeep: '#b7c2cc',
      accent: '#dfe6ec',
      accentSoft: '#fafbfc',
      ground: '#e8ecf0',
      silhouette: '#c2ccd4',
      mist: '#f1f3f5'
    }
  },
  {
    id: 'plain-light',
    label: '素色留白',
    description: '无场景纯色底 · 极简沉浸',
    scene: 'none',
    palette: {
      bg: '#eef1f4',
      scene: '#ffffff',
      sceneDeep: '#e4e9ee',
      accent: '#dfe6ec',
      accentSoft: '#fafbfc',
      ground: '#e8ecf0',
      silhouette: '#c2ccd4',
      mist: '#eef1f4'
    }
  }
]

/** 默认背景（首次访问 / 存储损坏时兜底） */
export const DEFAULT_BACKGROUND: ActiveBackground = {
  source: 'preset',
  presetId: 'snow-ink',
  scene: 'inkSnow',
  palette: { ...THEME_PRESETS[0].palette },
  particles: true,
  particleCount: 9,
  imageId: null,
  imageName: null,
  imageUrl: null
}

/** 按预设 id 查预设（找不到返回 undefined） */
export function findPreset(id: string): ThemePreset | undefined {
  return THEME_PRESETS.find((p) => p.id === id)
}

/** 主题设置持久化结构（图片 Blob 不在此，仅存 id + 文件名） */
interface PersistedBackground {
  source: 'preset' | 'custom' | 'image'
  presetId: string | null
  scene: BackgroundScene
  palette: BackgroundPalette
  particles: boolean
  particleCount: number
  imageId: string | null
  imageName: string | null
}

function isBackgroundPalette(v: unknown): v is BackgroundPalette {
  if (!v || typeof v !== 'object') return false
  const p = v as Record<string, unknown>
  return typeof p.bg === 'string' && typeof p.scene === 'string'
}

function isPersistedBackground(v: unknown): v is PersistedBackground {
  if (!v || typeof v !== 'object') return false
  const p = v as Record<string, unknown>
  return (
    (p.source === 'preset' || p.source === 'custom' || p.source === 'image') &&
    (p.scene === 'inkSnow' || p.scene === 'starryNight' || p.scene === 'none' || p.scene === 'image') &&
    isBackgroundPalette(p.palette) &&
    typeof p.particles === 'boolean' &&
    typeof p.particleCount === 'number'
  )
}

/** 从 localStorage 读取持久化背景（缺省/损坏时回退默认） */
function loadPersisted(): ActiveBackground {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed: unknown = JSON.parse(raw)
      if (isPersistedBackground(parsed)) {
        return {
          source: parsed.source,
          presetId: parsed.presetId,
          scene: parsed.scene,
          palette: parsed.palette,
          particles: parsed.particles,
          particleCount: Math.min(PARTICLE_MAX, Math.max(PARTICLE_MIN, parsed.particleCount)),
          imageId: parsed.imageId,
          imageName: parsed.imageName,
          imageUrl: null // 运行时由 restoreImage() 异步恢复
        }
      }
    }
  } catch {
    /* 存储损坏：静默回退默认背景 */
  }
  return { ...DEFAULT_BACKGROUND, palette: { ...DEFAULT_BACKGROUND.palette } }
}

export const useThemeStore = defineStore('theme', () => {
  const active = ref<ActiveBackground>(loadPersisted())

  /** 设置弹窗实时预览态（未保存的草稿优先于 active 显示） */
  const preview = ref<{ scene: BackgroundScene; palette: BackgroundPalette } | null>(null)

  /** 背景层实际显示的背景：预览态优先，否则正式生效值 */
  const displayed = computed<{ scene: BackgroundScene; palette: BackgroundPalette }>(() =>
    preview.value ?? { scene: active.value.scene, palette: active.value.palette }
  )

  /** 设置弹窗是否打开 */
  const settingsVisible = ref(false)

  /** 按 key 应用单条 CSS 变量 */
  function applyVar(key: keyof BackgroundPalette, value: string) {
    document.documentElement.style.setProperty(`--theme-${key}`, value)
  }

  /** 将整个色板写入 CSS 变量 */
  function applyPalette(palette: BackgroundPalette) {
    ;(Object.keys(palette) as (keyof BackgroundPalette)[]).forEach((key) => {
      applyVar(key, palette[key])
    })
  }

  /** 应用当前背景（色板 + 场景） */
  function applyActive() {
    applyPalette(active.value.palette)
    document.documentElement.style.setProperty('--theme-scene', active.value.scene)
  }

  /** 释放旧图片 object URL（防止内存泄漏；仅释放本 store 创建的 blob: URL） */
  function revokeImageUrl(url: string | null) {
    if (url && url.startsWith('blob:')) {
      URL.revokeObjectURL(url)
    }
  }

  /** 用 blob 构建 object URL 并挂到 active */
  function buildImageUrl(blob: Blob): string {
    revokeImageUrl(active.value.imageUrl)
    const url = URL.createObjectURL(blob)
    active.value.imageUrl = url
    return url
  }

  /** 启动恢复：若持久化主题为图片背景，从 IndexedDB 取回 Blob 重建 URL。
     失败（数据被清）时回退到默认预设，避免背景永远不可用 */
  async function restoreImage() {
    if (active.value.source !== 'image' || !active.value.imageId) return
    try {
      const record = await getBackgroundImage(active.value.imageId)
      if (record) {
        buildImageUrl(record.blob)
      } else {
        resetToDefault()
      }
    } catch {
      resetToDefault()
    }
  }

  /** 预览草稿背景到背景层（不持久化，取消时恢复） */
  function previewBackground(scene: BackgroundScene, palette: BackgroundPalette) {
    preview.value = { scene, palette: { ...palette } }
    applyPalette(palette)
    document.documentElement.style.setProperty('--theme-scene', scene)
  }

  /** 清除预览，恢复正式生效背景 */
  function clearPreview() {
    preview.value = null
    applyActive()
  }

  /** 保存自定义色板草稿：预览态转正 + 持久化（palette 场景）。
     图片字段原样保留（URL 生命周期：仅替换/移除时撤销） */
  function saveCustom(scene: BackgroundScene, palette: BackgroundPalette) {
    active.value = {
      ...active.value,
      source: 'custom',
      presetId: null,
      scene,
      palette: { ...palette }
    }
    preview.value = null
    applyActive()
    persist()
  }

  /** 用户上传新图片并立即设为 App 背景（核心入口）。
     先落库再切换状态，避免"界面已是图片背景但刷新即丢"；
     旧图 Blob 记录删除，URL 撤销（单张图片策略） */
  async function applyImageFile(file: File): Promise<void> {
    const id = generateImageId()
    await saveBackgroundImage(id, file.name, file)
    const oldId = active.value.imageId
    buildImageUrl(file)
    active.value = {
      ...active.value,
      source: 'image',
      presetId: null,
      scene: 'image',
      imageId: id,
      imageName: file.name
    }
    preview.value = null
    applyActive()
    persist()
    if (oldId && oldId !== id) {
      deleteBackgroundImage(oldId).catch(() => {})
    }
  }

  /** 移除图片背景：删库 + 撤销 URL + 回退默认预设 */
  async function removeImageBackground(): Promise<void> {
    const id = active.value.imageId
    const url = active.value.imageUrl
    active.value.imageId = null
    active.value.imageName = null
    active.value.imageUrl = null
    resetToDefault()
    revokeImageUrl(url)
    if (id) {
      deleteBackgroundImage(id).catch(() => {})
    }
  }

  /** 持久化到 localStorage（图片 Blob 存 IndexedDB，这里只存引用信息） */
  function persist() {
    const payload: PersistedBackground = {
      source: active.value.source,
      presetId: active.value.presetId,
      scene: active.value.scene,
      palette: active.value.palette,
      particles: active.value.particles,
      particleCount: active.value.particleCount,
      imageId: active.value.imageId,
      imageName: active.value.imageName
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch {
      /* 存储满/隐私模式：仅内存生效 */
    }
  }

  /** 选择预设主题（Colorful 一键换肤思路）。
      object URL 保留：设置弹窗缩略图与「切回图片」即时复用，
      仅在新图替换 / 图片移除时撤销（buildImageUrl / removeImageBackground） */
  function applyPreset(preset: ThemePreset) {
    active.value = {
      source: 'preset',
      presetId: preset.id,
      scene: preset.scene,
      palette: { ...preset.palette },
      particles: active.value.particles,
      particleCount: active.value.particleCount,
      imageId: active.value.imageId,
      imageName: active.value.imageName,
      imageUrl: active.value.imageUrl
    }
    preview.value = null
    applyActive()
    persist()
  }

  /** 应用自定义调色板（MicaForEveryone 细粒度调参思路，外部直改场景） */
  function applyCustom(scene: BackgroundScene, palette: BackgroundPalette) {
    saveCustom(scene, palette)
  }

  /** 重新切回图片背景（图片记录仍在时复用/重建 URL，
     供设置弹窗「设为背景」使用） */
  async function reapplyImage(): Promise<boolean> {
    if (!active.value.imageId) return false
    if (active.value.imageUrl) {
      // URL 仍在（未移除/替换过），直接切回
      active.value = { ...active.value, source: 'image', scene: 'image' }
      preview.value = null
      applyActive()
      persist()
      return true
    }
    try {
      const record = await getBackgroundImage(active.value.imageId)
      if (!record) return false
      active.value = {
        ...active.value,
        source: 'image',
        scene: 'image',
        imageName: record.name,
        imageUrl: URL.createObjectURL(record.blob)
      }
      preview.value = null
      applyActive()
      persist()
      return true
    } catch {
      return false
    }
  }

  /** 重置为默认预设（水墨雪景）。
      applyPreset 会保留 imageId/imageName 并释放 URL，图片记录仍在，
      用户可在设置弹窗一键切回自己的图片 */
  function resetToDefault() {
    applyPreset(THEME_PRESETS[0])
  }

  /** 切换粒子开关并持久化 */
  function setParticles(enabled: boolean) {
    active.value.particles = enabled
    persist()
  }

  /** 设置粒子数量（边界裁剪 + 持久化） */
  function setParticleCount(count: number) {
    const clamped = Math.min(PARTICLE_MAX, Math.max(PARTICLE_MIN, Math.round(count)))
    active.value.particleCount = clamped
    persist()
  }

  /** 打开设置弹窗（清除上次未保存的预览） */
  function openSettings() {
    preview.value = null
    settingsVisible.value = true
  }

  /** 关闭设置弹窗：撤销未保存的预览改动 */
  function closeSettings() {
    clearPreview()
    settingsVisible.value = false
  }

  // 模块加载时立即应用（App 挂载前生效，避免首帧闪烁）
  applyActive()
  // 异步恢复图片背景 URL（IndexedDB 读取不阻塞首帧）
  void restoreImage()

  return {
    active,
    preview,
    displayed,
    settingsVisible,
    applyActive,
    applyPalette,
    previewBackground,
    clearPreview,
    saveCustom,
    applyPreset,
    applyCustom,
    applyImageFile,
    removeImageBackground,
    reapplyImage,
    resetToDefault,
    setParticles,
    setParticleCount,
    openSettings,
    closeSettings
  }
})
