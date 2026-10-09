"""统一异常定义与异常处理器。"""
import logging
from typing import Optional, Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorResponse

logger = logging.getLogger("app.exceptions")


class AppError(Exception):
    """业务异常基类。

    code: 业务错误码（非 0）
    status_code: HTTP 状态码
    message: 用户可读的错误信息
    """

    def __init__(
        self,
        message: str,
        *,
        code: int = 1,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", code: int = 404) -> None:
        super().__init__(message, code=code, status_code=404)


class ConflictError(AppError):
    def __init__(
        self, message: str = "资源冲突", code: int = 409
    ) -> None:
        super().__init__(message, code=code, status_code=409)


class UnauthorizedError(AppError):
    """认证失败（未登录或 token 无效）。"""

    def __init__(self, message: str = "未登录或认证已过期", code: int = 401) -> None:
        super().__init__(message, code=code, status_code=401)


class ForbiddenError(AppError):
    """权限不足。"""

    def __init__(self, message: str = "无权执行此操作", code: int = 403) -> None:
        super().__init__(message, code=code, status_code=403)


def _error_payload(
    code: int, message: str, detail: Optional[str] = None
) -> dict:
    return ErrorResponse(code=code, message=message, detail=detail).model_dump(
        exclude_none=True
    )


def _install_handlers(app: FastAPI) -> None:
    """向 FastAPI 应用注册统一异常处理器。"""

    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request, exc: AppError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                exc.status_code, str(exc.detail) or "请求错误"
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        msg = first.get("msg", "参数校验失败")
        detail = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=422,
            content=_error_payload(422, "参数校验失败", detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_payload(500, "服务器内部错误"),
        )


def install_exception_handlers(app: FastAPI) -> None:
    """供 main.py 调用以安装统一异常处理器。"""
    _install_handlers(app)
