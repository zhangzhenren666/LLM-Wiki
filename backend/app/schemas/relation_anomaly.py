"""关系异常记录 Pydantic 模型。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RelationAnomalyRead(BaseModel):
    """关系异常记录响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    knowledge_base_id: int
    anomaly_type: str
    source_page_id: Optional[int] = None
    target_page_id: Optional[int] = None
    reason: str
    evidence: Optional[str] = None
    suggestion: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class RelationAnomalyListResponse(BaseModel):
    """关系异常列表响应。"""

    items: list[RelationAnomalyRead]
    total: int