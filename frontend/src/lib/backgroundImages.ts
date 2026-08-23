/* ═══════════════════════════════════════════════════
   小说管理App · 背景图片本地存储（IndexedDB，v1.8）
   用户上传的 App 背景图片以 Blob 形式存入 IndexedDB：
   · 不经过 base64（无 33% 体积膨胀）
   · 不受 localStorage 5MB 上限约束
   · 完全离线可用，刷新/重启后仍能恢复
   · 移动端（Capacitor WebView）同样支持

   存储结构：
   DB: app_backgrounds
   ObjectStore: images（keyPath: 'id'）
   记录: { id: string, name: string, blob: Blob, savedAt: number }

   图片由用户自己上传并在本地渲染（object URL 由本模块
   生成，仅用于自身 <img> 元素），不构成外部内容注入风险。
   ═══════════════════════════════════════════════════ */

const DB_NAME = 'app_backgrounds'
const DB_VERSION = 1
const STORE_NAME = 'images'

export interface StoredBackgroundImage {
  id: string
  name: string
  blob: Blob
  savedAt: number
}

let dbPromise: Promise<IDBDatabase> | null = null

/** 打开（或首次创建）数据库连接，单例复用 */
function getDb(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)
      request.onupgradeneeded = () => {
        const db = request.result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        }
      }
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error ?? new Error('打开背景图片数据库失败'))
    })
  }
  return dbPromise
}

/** 生成图片 id（时间戳 + 随机串，无需密码学强度） */
export function generateImageId(): string {
  return `bg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

/** 保存图片 Blob（同 id 覆盖写） */
export async function saveBackgroundImage(
  id: string,
  name: string,
  blob: Blob
): Promise<void> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put({
      id,
      name,
      blob,
      savedAt: Date.now()
    } satisfies StoredBackgroundImage)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error ?? new Error('保存背景图片失败'))
  })
}

/** 按 id 读取图片（不存在返回 null） */
export async function getBackgroundImage(id: string): Promise<StoredBackgroundImage | null> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(id)
    request.onsuccess = () => resolve((request.result as StoredBackgroundImage | undefined) ?? null)
    request.onerror = () => reject(request.error ?? new Error('读取背景图片失败'))
  })
}

/** 按 id 删除图片 */
export async function deleteBackgroundImage(id: string): Promise<void> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error ?? new Error('删除背景图片失败'))
  })
}

/** 列出全部已保存图片（当前仅保留单张自定义背景，备用） */
export async function listBackgroundImages(): Promise<StoredBackgroundImage[]> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).getAll()
    request.onsuccess = () => resolve(request.result as StoredBackgroundImage[])
    request.onerror = () => reject(request.error ?? new Error('读取背景图片列表失败'))
  })
}
