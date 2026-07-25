"""
全局异常处理

提供自定义业务异常类和全局异常处理器。
所有异常返回统一 ApiResponse 格式。
"""

import logging

from fastapi import Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """自定义业务异常，携带 HTTP 状态码和中文错误详情"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理自定义业务异常 → 返回统一 {success, data, meta, error} 格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "meta": None,
            "error": exc.detail,
        },
    )


async def http_exception_handler(request: Request, exc: FastAPIHTTPException) -> JSONResponse:
    """处理 FastAPI 内置 HTTPException → 统一格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "meta": None,
            "error": exc.detail,
        },
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理 Pydantic 请求体验证错误 → 中文友好提示"""
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        messages = []
        for err in exc.errors():
            field = " → ".join(str(loc) for loc in err["loc"])
            messages.append(f"{field}: {err['msg']}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "meta": None,
                "error": f"请求参数验证失败: {'; '.join(messages)}",
            },
        )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局兜底异常处理 → 500 内部错误"""
    logger.exception("未处理的异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "meta": None,
            "error": "服务器内部错误",
        },
    )
