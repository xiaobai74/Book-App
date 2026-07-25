"""
认证路由

POST   /api/v1/auth/register  → 注册
POST   /api/v1/auth/login     → 登录
POST   /api/v1/auth/refresh   → 刷新 Token
PUT    /api/v1/auth/password  → 修改密码（需认证）
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService
from app.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """邮箱 + 密码注册"""
    user = await AuthService.register(db, data)
    return ApiResponse.ok(
        data={
            "id": user.id,
            "email": user.email,
        }
    )


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """邮箱 + 密码登录，返回 JWT Token Pair"""
    tokens = await AuthService.login(db, data)
    return ApiResponse.ok(data=tokens)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="刷新 Token",
)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """使用 Refresh Token 获取新的 Token Pair（旧 Token 自动吊销）"""
    tokens = await AuthService.refresh(db, data)
    return ApiResponse.ok(data=tokens)


@router.put(
    "/password",
    response_model=ApiResponse[None],
    summary="修改密码",
)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前登录用户的密码"""
    await AuthService.change_password(db, current_user, data)
    return ApiResponse.ok(data=None)
