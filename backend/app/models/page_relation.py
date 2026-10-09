"""页面关系模型。"""
import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase
    from app.models.wiki_page import WikiPage


class RelationType(str, enum.Enum):
    """关系类型。"""

    LINK = "link"  # 内部链接 [[xxx]]
    REFERENCE = "reference"  # 通用引用/关联
    RELATED = "related"  # 相关知识
    REFERENCES = "references"  # 参考资料
    DEPENDS_ON = "depends_on"  # 依赖关系
    PARENT = "parent"  # 上级知识
    PART_OF = "part_of"  # 组成部分
    EXPLAINS = "explains"  # 解释说明


class RelationSource(str, enum.Enum):
    """关系来源。"""

    MANUAL = "manual"  # 手动建立
    BACKLINK = "backlink"  # 反向引用自动生成
    AUTO = "auto"  # 系统自动识别


class PageRelation(Base, TimestampMixin):
    """页面关系实体，关联源页面与目标页面。"""

    __tablename__ = "page_relation"
    __table_args__ = (
        # 同一源页、目标页、类型下唯一
        UniqueConstraint(
            "source_page_id",
            "target_page_id",
            "relation_type",
            name="uq_page_relation_src_tgt_type",
        ),
        {"comment": "页面关系"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    source_page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="源页面",
    )
    target_page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标页面",
    )
    relation_type: Mapped[RelationType] = mapped_column(
        Enum(RelationType, native_enum=False, length=20),
        default=RelationType.LINK,
        nullable=False,
        comment="关系类型",
    )
    source: Mapped[RelationSource] = mapped_column(
        Enum(RelationSource, native_enum=False, length=20),
        default=RelationSource.MANUAL,
        nullable=False,
        comment="关系来源",
    )
    relation_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="关系创建理由（简短说明）"
    )
    relation_evidence: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="支持关系的文本依据"
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship()

    source_page: Mapped["WikiPage"] = relationship(
        foreign_keys=[source_page_id],
        back_populates="outgoing_relations",
    )
    target_page: Mapped["WikiPage"] = relationship(
        foreign_keys=[target_page_id],
        back_populates="incoming_relations",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PageRelation {self.source_page_id} -> "
            f"{self.target_page_id} ({self.relation_type.value})>"
        )
