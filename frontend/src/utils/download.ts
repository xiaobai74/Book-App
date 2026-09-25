/* ═══════════════════════════════════════════════════════
   小说管理App · 电子书下载工具（详情页 / 搜索页共用）
   ═══════════════════════════════════════════════════════ */
import { ElMessage } from 'element-plus'
import { getDownloadUrl } from '@/api/books'
import { isCapacitorPlatform } from '@/api/http'

/** Blob → base64 字符串（Capacitor Filesystem.writeFile 需要） */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const result = reader.result as string
      // dataURL 形如 "data:...;base64,xxxx"，取逗号后的纯 base64 部分
      const comma = result.indexOf(',')
      resolve(comma >= 0 ? result.slice(comma + 1) : result)
    }
    reader.onerror = () => reject(reader.error ?? new Error('文件读取失败'))
    reader.readAsDataURL(blob)
  })
}

/**
 * 带鉴权下载 EPUB/TXT 并保存到本地
 * - Web/桌面：blob + <a download> 触发浏览器保存
 * - 移动端(Capacitor)：Android WebView 未注册 DownloadListener，blob 下载会被静默忽略，
 *   改用 Filesystem.writeFile 落盘到 Documents 目录（可被「本地导入」扫描到）
 * @param successMsg 成功提示；不传时使用默认文案
 */
export async function downloadEbook(
  bookId: string,
  format: 'epub' | 'txt',
  filename: string,
  successMsg?: string
) {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const response = await fetch(getDownloadUrl(bookId, format), {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.error || '下载失败')
    }
    const blob = await response.blob()
    const safeName = `${filename.replace(/[\\/:*?"<>|]/g, '_')}.${format}`

    if (isCapacitorPlatform) {
      // 写入公共 Documents 目录在 Android 11+ 需要「所有文件访问」权限；
      // Filesystem.checkPermissions 在 13+ 恒报 granted 不可信，用原生真实状态预检
      const scan = await import('@/utils/deviceScan')
      if (!(await scan.hasAllFilesAccess())) {
        ElMessage.warning('保存文件需要「所有文件访问」权限，请在系统设置中开启后重试')
        scan.openAllFilesAccessSettings()
        return
      }
      const { Filesystem, Directory } = await import('@capacitor/filesystem')
      const data = await blobToBase64(blob)
      try {
        await Filesystem.writeFile({ path: safeName, data, directory: Directory.Documents })
      } catch (writeErr: any) {
        // Android 9 及以下写公共目录需要存储权限；申请后重试一次
        if (String(writeErr?.message || writeErr).includes('permission')) {
          const status = await Filesystem.requestPermissions()
          if (status.publicStorage !== 'granted') throw new Error('未授予存储权限，无法保存文件')
          await Filesystem.writeFile({ path: safeName, data, directory: Directory.Documents })
        } else {
          throw writeErr
        }
      }
      ElMessage.success(successMsg ?? `已保存到 Documents/${safeName}`)
      return
    }

    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = safeName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
    ElMessage.success(successMsg ?? '已开始下载')
  } catch (err: any) {
    ElMessage.error(err.message || '下载失败')
  }
}
