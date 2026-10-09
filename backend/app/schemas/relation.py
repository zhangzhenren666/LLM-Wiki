"""页面关系 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.page_relation import RelationType


class RelationCreate(BaseModel):
    """创建页面关系请求。"""

    source_page_id: int = Field(..., description="源页面 ID")
    target_page_id: int = Field(..., description="目标页面 ID")
    relation_type: RelationType = Field(..., description="关系类型")


class RelationRead(BaseModel):
    """页面关系响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    source_page_id: int
    target_page_id: int
    relation_type: str
    source: str
    relation_reason: str | None = None
    relation_evidence: str | None = None
    created_at: datetime
    updated_at: datetime