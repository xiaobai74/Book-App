"""统一 API 响应模型

所有接口返回统一格式:
{
    "success": true,
    "data": { ... },
    "meta": { "page": 1, "total": 100 },
    "error": null
}
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    success: bool = True
    data: T | None = None
    meta: PaginationMeta | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T = None, meta: PaginationMeta | None = None) -> "ApiResponse[T]":
        """成功响应"""
        return cls(success=True, data=data, meta=meta, error=None)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse":
        """失败响应"""
        return cls(success=False, data=None, meta=None, error=error)
