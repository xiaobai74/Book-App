/* ═══════════════════════════════════════════════════════
   小说管理App · 电子书下载工具（详情页 / 搜索页共用）
   ═══════════════════════════════════════════════════════ */
import { ElMessage } from 'element-plus'
import { getDownloadUrl } from '@/api/books'

/**
 * 带鉴权下载 EPUB/TXT 并触发浏览器保存
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
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `${filename}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(downloadUrl)
    ElMessage.success(successMsg ?? '已开始下载')
  } catch (err: any) {
    ElMessage.error(err.message || '下载失败')
  }
}
