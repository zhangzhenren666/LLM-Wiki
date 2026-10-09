"""页面 Pydantic 模型。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.wiki_page import PageStatus


class PageCreate(BaseModel):
    """创建页面请求。"""

    knowledge_base_id: int = Field(..., description="所属知识库 ID")
    title: str = Field(..., description="页面标题")
    slug: str | None = Field(None, description="URL 标识，为空则自动生成")
    parent_id: int | None = Field(None, description="父页面 ID，为空表示顶层页面")
    content: str = Field("", description="Markdown 内容，允许为空")
    status: PageStatus = Field(PageStatus.DRAFT, description="页面状态")

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("页面标题不能为空")
        return stripped

    @field_validator("slug")
    @classmethod
    def slug_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("slug 不能为空字符串")
        return stripped


class PageUpdate(BaseModel):
    """更新页面请求（所有字段可选，至少提供一个）。"""

    title: str | None = Field(None, description="页面标题")
    slug: str | None = Field(None, description="URL 标识")
    parent_id: int | None = Field(None, description="父页面 ID，传入 null 表示置为顶层")
    content: str | None = Field(None, description="Markdown 内容")
    status: PageStatus | None = Field(None, description="页面状态")

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("页面标题不能为空")
        return stripped

    @field_validator("slug")
    @classmethod
    def slug_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("slug 不能为空字符串")
        return stripped


class PageRead(BaseModel):
    """页面响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    parent_id: int | None
    title: str
    slug: str
    content: str
    status: PageStatus
    tags: list[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, v: Any) -> list[str]:
        """接收 PageTag 对象列表或字符串列表，统一转为标签名列表。"""
        if isinstance(v, (list, tuple)):
            names: list[str] = []
            for item in v:
                if isinstance(item, str):
                    names.append(item)
                elif hasattr(item, "tag_name"):
                    names.append(item.tag_name)  # type: ignore[union-attr]
            return names
        return []


class PageTagUpdate(BaseModel):
    """页面标签增删请求。"""

    tags: list[str] = Field(..., min_length=1, description="标签名称列表")


class PageMove(BaseModel):
    """页面移动请求。"""

    parent_id: int | None = Field(
        None, description="目标父页面 ID，传 null 表示置为顶层页面"
    )


class BacklinkRead(BaseModel):
    """反向引用：指向当前页面的源页面摘要。"""

    id: int
    title: str
    slug: str
    knowledge_base_id: int
    source: str
