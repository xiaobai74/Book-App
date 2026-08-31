"""
应用配置管理

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
桌面版（Electron + PyInstaller）默认使用 SQLite，数据存于用户目录（%AppData%/NovelManager）；
Web 部署可通过 .env 的 DATABASE_URL 覆盖回 MySQL。
"""

from pathlib import Path

from platformdirs import user_data_dir
from pydantic_settings import BaseSettings


def _get_data_dir() -> Path:
    """用户数据目录：Windows 下为 %AppData%/NovelManager，自动创建"""
    path = Path(user_data_dir("NovelManager", appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


# 全局用户数据目录（数据库、导出电子书等）
DATA_DIR = _get_data_dir()


class Settings(BaseSettings):
    """应用全局配置"""

    # 数据库（默认 SQLite，.env 可用 DATABASE_URL 覆盖为 MySQL）
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'novel_manager.db'}"

    # JWT
    jwt_secret: str = "dev-secret-key-change-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # Access Token 2 小时
    refresh_token_expire_days: int = 7      # Refresh Token 7 天

    # Dify AI
    dify_api_url: str = "http://localhost:5001/v1"
    dify_api_key: str = ""
    dify_summary_api_key: str = ""

    # 导出目录（桌面版存用户数据目录，避免写入安装目录）
    epub_output_dir: str = str(DATA_DIR / "epub_output")
    txt_output_dir: str = str(DATA_DIR / "txt_output")

    # CORS（桌面版前端来自 file:// 或本地动态端口）
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "file://",
        "null",
        # Capacitor WebView 源：androidScheme 为 http 时是 http://localhost，
        # 为 https 时是 https://localhost（iOS 用 capacitor://localhost），全部放行
        "http://localhost",         # Capacitor Android WebView 源（androidScheme: 'http'）
        "https://localhost",        # Capacitor Android WebView 源（androidScheme: 'https'）
        "capacitor://localhost",    # Capacitor iOS WebView 源
    ]

    class Config:
        # 自动从 backend/.env 加载
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局单例
settings = Settings()
