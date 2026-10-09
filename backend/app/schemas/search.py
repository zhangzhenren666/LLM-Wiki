"""搜索功能 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class SearchResult(BaseModel):
    """单条搜索结果。"""

    model_config = ConfigDict(from_attributes=True)

    page_id: int
    title: str
    slug: str
    knowledge_base_id: int
    knowledge_base_name: str | None = None
    match_type: str  # "title" | "tag" | "content"
    snippet: str | None = None  # 正文中关键词附近的摘要片段
    tags: list[str] = []


class PaginatedSearchResponse(BaseModel):
    """分页搜索结果。"""

    items: list[SearchResult]
    total: int
    page: int
    page_size: int
    query: str