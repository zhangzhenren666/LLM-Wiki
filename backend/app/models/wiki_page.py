"""Wiki 页面模型。"""
import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase
    from app.models.page_relation import PageRelation
    from app.models.page_tag import PageTag


class PageStatus(str, enum.Enum):
    """页面状态。"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WikiPage(Base, TimestampMixin):
    """Wiki 页面实体，支持父子层级。

    权限扩展预留：owner_id 字段为后续用户隔离预留。
    """

    __tablename__ = "wiki_page"
    __table_args__ = (
        # 同一知识库内 slug 唯一
        UniqueConstraint("knowledge_base_id", "slug", name="uq_wiki_page_kb_slug"),
        {"comment": "Wiki 页面"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="父页面 ID，为空表示顶层页面",
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="页面标题"
    )
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="URL 标识"
    )
    content: Mapped[str] = mapped_column(
        Text, default="", nullable=False, comment="Markdown 内容"
    )
    status: Mapped[PageStatus] = mapped_column(
        Enum(PageStatus, native_enum=False, length=20),
        default=PageStatus.DRAFT,
        nullable=False,
        index=True,
        comment="页面状态",
    )
    # 权限扩展预留：后续改为 ForeignKey("user.id")，当前允许为空
    owner_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, comment="所有者 ID（权限扩展预留）"
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        back_populates="pages"
    )
    parent: Mapped[Optional["WikiPage"]] = relationship(
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["WikiPage"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["PageTag"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
    )
    outgoing_relations: Mapped[list["PageRelation"]] = relationship(
        foreign_keys="PageRelation.source_page_id",
        back_populates="source_page",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list["PageRelation"]] = relationship(
        foreign_keys="PageRelation.target_page_id",
        back_populates="target_page",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WikiPage id={self.id} title={self.title!r}>"
