"""知识库模型。"""
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.wiki_page import WikiPage


class KnowledgeBase(Base, TimestampMixin):
    """知识库实体。

    权限扩展预留：
    - owner_id 字段为后续用户隔离预留（当前始终为 NULL）。
    - name 的 unique 约束后续需改为 (owner_id, name) 联合唯一。
    """

    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, comment="知识库名称（后续需改为 owner_id+name 联合唯一）"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="描述"
    )
    # 权限扩展预留：后续改为 ForeignKey("user.id")，当前允许为空
    owner_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, comment="所有者 ID（权限扩展预留）"
    )

    pages: Mapped[list["WikiPage"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KnowledgeBase id={self.id} name={self.name!r}>"
