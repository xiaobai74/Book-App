"""
认证业务逻辑

处理注册、登录、Token 刷新、密码修改等认证相关操作。
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)


class AuthService:
    """认证服务"""

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> User:
        """
        注册新用户。

        校验:
            - 邮箱唯一性（重复 → 409）
            - 密码强度（后端二次校验）

        返回: 新创建的用户对象
        """
        # 检查邮箱唯一性
        result = await db.execute(
            select(User).where(User.email == data.email, User.deleted_at.is_(None))
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=409, detail="该邮箱已注册")

        # 后端二次校验密码强度
        valid, err_msg = validate_password_strength(data.password)
        if not valid:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=422, detail=err_msg)

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        db.add(user)
        await db.flush()  # 触发 MySQL UUID 触发器获取 id
        return user

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
        """
        邮箱 + 密码登录。

        安全设计: 不区分"邮箱不存在"和"密码错误"（防枚举攻击）。
        统一返回 "邮箱或密码错误"。

        返回: Access Token + Refresh Token
        """
        # 查找用户
        result = await db.execute(
            select(User).where(User.email == data.email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # 统一错误信息，不区分邮箱不存在还是密码错误（防枚举）
        auth_error_msg = "邮箱或密码错误"

        if user is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail=auth_error_msg)

        if not verify_password(data.password, user.password_hash):
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail=auth_error_msg)

        # 签发 Token
        access_token = create_access_token(user.id)
        refresh_token_str = create_refresh_token(user.id)

        # 存储 Refresh Token 哈希到数据库
        expires_at = get_token_expiry(refresh_token_str)
        if expires_at is None:
            # 兜底：无法解析则用配置默认值
            expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token_str),
            expires_at=expires_at,
        )
        db.add(token_record)
        await db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        )

    @staticmethod
    async def refresh(db: AsyncSession, data: RefreshTokenRequest) -> TokenResponse:
        """
        刷新 Token（轮转策略）。

        流程:
            1. 解码 refresh token 获取 user_id
            2. 查库验证 token hash 存在且未吊销
            3. 吊销旧 token（set revoked_at）
            4. 签发新的 access + refresh token pair
        """
        # 解码 Refresh Token
        try:
            payload = decode_token(data.refresh_token)
        except Exception:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail="Refresh Token 无效或已过期，请重新登录")

        if payload.get("type") != "refresh":
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail="请使用 Refresh Token 刷新")

        user_id = payload.get("sub")
        if not user_id:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail="Token 格式无效")

        # 查找未吊销的 Refresh Token 记录
        token_hash = hash_token(data.refresh_token)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        token_record = result.scalar_one_or_none()

        if token_record is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail="Refresh Token 已被吊销或不存在，请重新登录")

        # 验证用户仍存在
        user_result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=401, detail="用户不存在或已注销")

        # 吊销旧 Refresh Token（轮转）
        token_record.revoked_at = datetime.now(UTC)

        # 签发新 Token
        new_access_token = create_access_token(user.id)
        new_refresh_token_str = create_refresh_token(user.id)

        new_expires_at = get_token_expiry(new_refresh_token_str)
        if new_expires_at is None:
            new_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token_str),
            expires_at=new_expires_at,
        )
        db.add(new_token_record)
        await db.flush()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
        )

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        data: PasswordChangeRequest,
    ) -> None:
        """
        修改密码。

        要求:
            - 验证旧密码正确
            - 新密码强度校验
        """
        # 验证旧密码
        if not verify_password(data.old_password, user.password_hash):
            from app.middleware.error_handler import AppException
            raise AppException(status_code=400, detail="当前密码不正确")

        # 校验新密码强度
        valid, err_msg = validate_password_strength(data.new_password)
        if not valid:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=422, detail=err_msg)

        # 更新密码哈希
        user.password_hash = hash_password(data.new_password)
        await db.flush()
