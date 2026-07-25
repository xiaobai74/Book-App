"""
安全工具模块

提供密码哈希、JWT 令牌生成/验证、Token 哈希等安全相关功能。
"""

import hashlib
import re
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

# bcrypt salt rounds
_SALT_ROUNDS = 12


# ============================================================
# 密码处理
# ============================================================

def hash_password(plain: str) -> str:
    """使用 bcrypt 对明文密码做哈希（saltRounds=12）"""
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=_SALT_ROUNDS),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    校验密码强度。
    规则: 8-64 位，必须同时包含字母和数字。
    返回 (是否通过, 错误信息)。
    """
    if len(password) < 8 or len(password) > 64:
        return False, "密码长度需为 8-64 位"
    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含至少一个字母"
    if not re.search(r"\d", password):
        return False, "密码必须包含至少一个数字"
    return True, None


# ============================================================
# JWT Token 处理
# ============================================================

def create_access_token(user_id: str) -> str:
    """签发 Access Token（有效期 2 小时）"""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """签发 Refresh Token（有效期 7 天）"""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT Token。

    抛出:
        jwt.ExpiredSignatureError: Token 已过期
        jwt.InvalidTokenError: Token 无效
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


def get_token_expiry(token: str) -> datetime | None:
    """
    从 JWT Token 中提取过期时间（不验证签名）。
    用于存储 Refresh Token 的 expires_at。
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        exp = payload.get("exp")
        if exp is not None:
            return datetime.fromtimestamp(exp, tz=UTC)
    except jwt.InvalidTokenError:
        pass
    return None


# ============================================================
# Token 哈希
# ============================================================

def hash_token(token: str) -> str:
    """对 token 做 SHA-256 哈希，用于安全存储到 refresh_tokens 表"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
