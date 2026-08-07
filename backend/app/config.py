"""
应用配置管理

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 数据库
    database_url: str = "mysql+aiomysql://root:123456@localhost:3306/book"

    # JWT
    jwt_secret: str = "dev-secret-key-change-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # Access Token 2 小时
    refresh_token_expire_days: int = 7      # Refresh Token 7 天

    # Dify AI
    dify_api_url: str = "http://localhost:5001/v1"
    dify_api_key: str = ""
    dify_summary_api_key: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    class Config:
        # 自动从 backend/.env 加载
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局单例
settings = Settings()
