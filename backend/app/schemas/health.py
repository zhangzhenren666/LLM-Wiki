"""健康检查相关 Pydantic 模型。"""
from pydantic import BaseModel


class HealthData(BaseModel):
    """健康检查数据。"""

    status: str
    version: str
