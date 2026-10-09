"""通用 Pydantic 模型。

定义统一响应包裹格式和相关通用模型。

统一响应格式：
    {
      "code": 0,          # 0 表示成功，非 0 表示业务错误码
      "message": "ok",    # 提示信息
      "data": ...         # 具体数据
    }
"""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包裹。"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    code: int
    message: str
    detail: Optional[str] = None
