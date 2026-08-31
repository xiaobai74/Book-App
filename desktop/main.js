/**
 * Electron 主进程
 *
 * 流程：找空闲端口 → 启动后端 exe → 健康检查 → 加载前端页面 → 退出时优雅关闭后端
 */
const { app, BrowserWindow, Menu, shell } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')
const net = require('net')
const fs = require('fs')

let backendProcess = null
let mainWindow = null
let backendPort = 0

/** 找一个可用端口 */
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

/** 后端 exe 路径：打包版在 resources/backend，开发版在仓库的 backend/dist（desktop 与 backend 同级） */
function getBackendExePath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'backend', 'novel-backend.exe')
    : path.join(__dirname, '..', 'backend', 'dist', 'novel-backend.exe')
}

/** 前端入口页面：打包版在 resources/frontend，开发版在仓库的 frontend/dist（desktop 与 frontend 同级） */
function getFrontendIndexPath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'frontend', 'index.html')
    : path.join(__dirname, '..', 'frontend', 'dist', 'index.html')
}

/** 启动 Python 后端子进程 */
function startBackend(port) {
  const exePath = getBackendExePath()
  if (!fs.existsSync(exePath)) {
    console.error('[main] backend exe not found:', exePath)
    return null
  }
  backendProcess = spawn(exePath, [], {
    env: { ...process.env, BACKEND_PORT: String(port) },
    windowsHide: true, // 隐藏后端控制台黑窗
  })
  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString().trim()))
  backendProcess.on('exit', (code) => console.log('[backend] exited, code=', code))
  return backendProcess
}

/** 轮询等待后端就绪 */
function waitForBackend(port, timeoutMs = 30000) {
  const startTime = Date.now()
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) return resolve()
        retry()
      })
      req.on('error', retry)
      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }
    const retry = () => {
      if (Date.now() - startTime > timeoutMs) return reject(new Error('backend start timeout'))
      setTimeout(check, 500)
    }
    check()
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--backend-port=${backendPort}`],
    },
  })

  // 移除 Electron 默认菜单栏（含 Toggle Developer Tools 等调试入口）
  Menu.setApplicationMenu(null)

  // 无菜单后手动保留常用剪贴板/编辑快捷键
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown' || !(input.control || input.meta)) return
    const wc = mainWindow.webContents
    switch (input.key.toLowerCase()) {
      case 'c': wc.copy(); break
      case 'v': wc.paste(); break
      case 'x': wc.cut(); break
      case 'a': wc.selectAll(); break
      case 'z': wc.undo(); break
      case 'y': wc.redo(); break
    }
  })

  // 外链交给系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.once('ready-to-show', () => mainWindow.show())
  mainWindow.loadFile(getFrontendIndexPath())
}

function stopBackend() {
  if (backendProcess) {
    try {
      backendProcess.kill()
    } catch (e) {
      /* ignore */
    }
    backendProcess = null
  }
}

app.whenReady().then(async () => {
  try {
    backendPort = await findFreePort()
    startBackend(backendPort)
    await waitForBackend(backendPort)
  } catch (err) {
    console.error('[main] backend start failed:', err)
  }
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', stopBackend)
app.on('window-all-closed', () => {
  stopBackend()
  app.quit()
})
