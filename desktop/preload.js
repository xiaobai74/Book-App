/**
 * Preload 脚本：把后端端口安全地暴露给渲染进程
 */
const { contextBridge } = require('electron')

// 从主进程 additionalArguments 解析后端端口
const portArg = process.argv.find((a) => a.startsWith('--backend-port='))
const backendPort = portArg ? portArg.split('=')[1] : '8000'

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  apiBaseUrl: `http://127.0.0.1:${backendPort}`,
  backendPort,
})
