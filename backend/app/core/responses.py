"""统一响应构建辅助函数。"""
from typing import Optional, TypeVar

from app.schemas.common import ApiResponse

T = TypeVar("T")


def success(
    data: Optional[T] = None, message: str = "ok", code: int = 0
) -> ApiResponse[T]:
    """构建统一成功响应。"""
    return ApiResponse[T](code=code, message=message, data=data)
