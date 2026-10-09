"""知识提取条目 Pydantic 模型。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KnowledgeItemRead(BaseModel):
    """知识条目响应（单条）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    document_id: int
    title: str
    content: str
    tags: Optional[str] = None
    evidence_text: Optional[str] = None
    page_number: Optional[str] = None
    chapter: Optional[str] = None
    paragraph: Optional[str] = None
    uncertainty_note: Optional[str] = None
    duplicate_candidate_id: Optional[int] = None
    anomaly_reason: Optional[str] = None
    status: str
    wiki_page_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class KnowledgeItemListResponse(BaseModel):
    """知识条目列表响应。"""

    items: list[KnowledgeItemRead]
    total: int
    auto_created_count: int
    needs_attention_count: int
    duplicate_count: int
    skipped_count: int