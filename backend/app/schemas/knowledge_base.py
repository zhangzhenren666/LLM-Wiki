"""知识库 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""

    name: str = Field(..., description="知识库名称")
    description: str | None = Field(None, description="描述")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("知识库名称不能为空")
        return stripped


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求（所有字段可选，至少提供一个）。"""

    name: str | None = Field(None, description="知识库名称")
    description: str | None = Field(None, description="描述")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("知识库名称不能为空")
        return stripped


class KnowledgeBaseRead(BaseModel):
    """知识库响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
