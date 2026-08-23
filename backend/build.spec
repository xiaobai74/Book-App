# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：把 FastAPI 后端打包为单文件 novel-backend.exe"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 第三方库内置数据文件（certifi CA 证书、ebooklib 模板等）
datas = collect_data_files('ebooklib') + collect_data_files('certifi') + collect_data_files('lxml')
datas.append(('rules/*.json', 'rules'))

hiddenimports = (
    collect_submodules('app')
    + collect_submodules('rules')
    + collect_submodules('platformdirs')
    + [
        # uvicorn 运行时动态导入的模块
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # 第三方库动态导入
        'aiosqlite',
        'anyio._backends._asyncio',
        'h11',
        'httpcore',
        'httpx',
        'multipart',
        'jwt',
        'bcrypt',
        'cryptography',
        'lxml',
        'lxml.etree',
        'lxml.html',
        'bs4',
        'ebooklib',
        'pydantic',
        'pydantic_settings',
        'sqlalchemy.sql.default_comparator',
    ]
)

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 桌面版用 SQLite，排除 MySQL 驱动等无关大包
    excludes=['aiomysql', 'mysqlclient', 'pymysql', 'tkinter', 'matplotlib', 'numpy', 'pandas', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assembly=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='novel-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # 控制台输出便于排错；Electron 以 windowsHide 方式启动不会显示黑窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
