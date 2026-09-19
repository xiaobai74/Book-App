/* ═══════════════════════════════════════════════════════
   小说管理App · 移动端设备文件扫描（Capacitor Filesystem）

   仅在原生（Android）环境调用：递归扫描公共存储目录，
   列出 .txt/.epub/.pdf/.docx 小说文件供用户勾选导入。
   Web/桌面端通过动态 import 隔离，不会执行本模块。
   ═══════════════════════════════════════════════════════ */
import { Filesystem, Directory } from '@capacitor/filesystem'
import type { ScannedFile } from '@/types'

/** 视为小说文件的扩展名 */
const NOVEL_EXTS = ['.txt', '.epub', '.pdf', '.docx']

/** 扫描根目录（公共存储）
 *
 * Capacitor v8 无 Downloads 枚举：Android 的 Download/ 位于 ExternalStorage 根下，
 * 递归扫描 ExternalStorage 即可覆盖 Download/Documents/Books 等目录；
 * 额外扫描 Documents 作为未授予「所有文件访问」时的兜底。
 */
const SCAN_ROOTS: Directory[] = [
  Directory.Documents,
  Directory.ExternalStorage,
]

/** 结果封顶，避免全盘扫描返回过多 */
const MAX_RESULTS = 500
/** 递归深度上限 */
const MAX_DEPTH = 6
/** 跳过的系统/缓存目录（小写） */
const SKIP_DIRS = new Set([
  'android', 'data', '.thumbnails', '.cache', 'lostandfound',
  '.android', 'backup', '.nomedia', 'tencent', 'miui',
])

const MIME_MAP: Record<string, string> = {
  '.txt': 'text/plain',
  '.epub': 'application/epub+zip',
  '.pdf': 'application/pdf',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

function extOf(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

/** 检查并申请存储权限，返回是否已授权 */
export async function ensurePermissions(): Promise<boolean> {
  try {
    let status = await Filesystem.checkPermissions()
    if (status.publicStorage === 'granted') return true
    status = await Filesystem.requestPermissions()
    return status.publicStorage === 'granted'
  } catch {
    return false
  }
}

/** 递归扫描设备公共目录，返回匹配的小说文件列表（按修改时间倒序、去重、封顶） */
export async function scanNovelFiles(): Promise<ScannedFile[]> {
  const results: ScannedFile[] = []
  const seen = new Set<string>()

  async function walk(dir: Directory, path: string, depth: number) {
    if (depth > MAX_DEPTH || results.length >= MAX_RESULTS) return
    let entries: any[] = []
    try {
      const res = await Filesystem.readdir({ directory: dir, path })
      entries = (res.files as any[]) || []
    } catch {
      return // 无权限/不存在的目录直接跳过
    }
    for (const entry of entries) {
      if (results.length >= MAX_RESULTS) return
      const name: string = entry.name
      if (!name) continue
      const childPath = path ? `${path}/${name}` : name

      if (entry.type === 'directory') {
        const lower = name.toLowerCase()
        if (name.startsWith('.') || SKIP_DIRS.has(lower)) continue
        await walk(dir, childPath, depth + 1)
      } else {
        const ext = extOf(name)
        if (!NOVEL_EXTS.includes(ext)) continue
        const size = entry.size || 0
        const mtime = entry.mtime ? new Date(entry.mtime).getTime() : undefined
        // 跨根目录去重（同名同大小同修改时间视为同一文件）
        const key = `${name}|${size}|${mtime || 0}`
        if (seen.has(key)) continue
        seen.add(key)
        results.push({ name, path: childPath, size, ext, mtime, directory: dir })
      }
    }
  }

  for (const root of SCAN_ROOTS) {
    if (results.length >= MAX_RESULTS) break
    await walk(root, '', 0)
  }

  results.sort((a, b) => (b.mtime || 0) - (a.mtime || 0))
  return results.slice(0, MAX_RESULTS)
}

/** base64 → Uint8Array（原生 readFile 返回 base64 字符串） */
function base64ToBytes(base64: string): Uint8Array {
  const clean = base64.includes(',') ? base64.split(',')[1] : base64
  const binary = atob(clean)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

/** 读取扫描到的文件为 Blob（用于 multipart 上传） */
export async function readFileAsBlob(file: ScannedFile): Promise<Blob> {
  const res = await Filesystem.readFile({
    directory: (file.directory as Directory) || Directory.ExternalStorage,
    path: file.path,
  })
  const data = res.data
  // 原生返回 base64 字符串；Web 返回 Blob（本模块仅原生调用，做兼容兜底）
  if (data instanceof Blob) return data
  const bytes = base64ToBytes(data as string)
  return new Blob([bytes.buffer as ArrayBuffer], { type: MIME_MAP[file.ext] || 'application/octet-stream' })
}
