"""认证相关 Pydantic Schemas"""

import re

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """注册请求"""
    # 注意：长度约束不放在 Field(min_length/max_length) 中，否则 Pydantic 会
    # 先抛出英文原生错误消息（如 "String should have at least 8 characters"），
    # 绕过下方自定义验证器的中文文案。长度校验统一在 field_validator 中完成。
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码（8-64位，需包含字母和数字）")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 5 or len(v) > 255:
            raise ValueError("邮箱长度需为 5-255 位")
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 64:
            raise ValueError("密码长度需为 8-64 位")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="已签发的 Refresh Token")


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1, description="当前密码")
    # 长度约束放在验证器中而非 Field，保证返回中文错误文案（同 RegisterRequest）
    new_password: str = Field(..., description="新密码（8-64位，需包含字母和数字）")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 64:
            raise ValueError("密码长度需为 8-64 位")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("密码必须包含至少一个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        return v
