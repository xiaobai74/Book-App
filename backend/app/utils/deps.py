"""
FastAPI 依赖注入

提供数据库会话、当前用户身份认证等可复用依赖。
"""

from fastapi import Depends, Header
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从请求头 Authorization 中提取并验证 JWT Access Token，返回当前登录用户。

    用法:
        @app.get("/books")
        async def list_books(current_user: User = Depends(get_current_user)):
            ...

    异常:
        401: Token 缺失、格式错误、已过期或无效
        401: 用户不存在或已被软删除
    """
    # 校验 Bearer 格式
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证方式错误，请使用 Bearer Token")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token 不能为空")

    # 解码 Token
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token 无效或已过期，请重新登录")

    # 检查 token 类型
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="请使用 Access Token 而非 Refresh Token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 格式无效")

    # 查找用户（排除已软删除）
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已注销")

    return user
