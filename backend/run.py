"""
PyInstaller 入口脚本（桌面版后端）

运行方式:
    开发模式:  python run.py
    打包后:    novel-backend.exe（由 Electron 主进程以子进程方式启动，
               通过环境变量 BACKEND_PORT 指定监听端口）
"""

import os
import sys

if getattr(sys, "frozen", False):
    # frozen 模式：切换 CWD 到临时解压目录，避免误读源码目录下的 .env
    os.chdir(sys._MEIPASS)

import uvicorn


def main() -> None:
    # 直接导入 app 对象传给 uvicorn，避免 frozen 模式下字符串导入失败
    from app.main import app

    port = int(os.environ.get("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
