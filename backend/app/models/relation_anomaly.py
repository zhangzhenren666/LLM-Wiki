"""关系异常记录模型。

记录关系构建过程中发现的异常：疑似重复、内容冲突、关系不明确、缺少依据等。"""
import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_task import DocumentTask
    from app.models.wiki_page import WikiPage


class AnomalyType(str, enum.Enum):
    """异常类型。"""

    DUPLICATE_PAGE = "duplicate_page"        # 疑似重复页面
    CONTENT_CONFLICT = "content_conflict"    # 内容冲突
    RELATION_UNCLEAR = "relation_unclear"    # 关系不明确
    MISSING_EVIDENCE = "missing_evidence"    # 缺少依据
    MODEL_OUTPUT_ERROR = "model_output_error"  # 模型输出异常


class AnomalyStatus(str, enum.Enum):
    """异常处理状态。"""

    PENDING = "pending"    # 待处理
    REVIEWED = "reviewed"  # 已查看
    IGNORED = "ignored"    # 已忽略


class RelationAnomaly(Base, TimestampMixin):
    """关系构建过程中发现的异常记录。

    与处理任务关联，供用户在结果视图中查看和判断。
    """

    __tablename__ = "relation_anomaly"
    __table_args__ = {"comment": "关系异常记录"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("document_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属处理任务",
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )

    anomaly_type: Mapped[AnomalyType] = mapped_column(
        Enum(AnomalyType, native_enum=False, length=30),
        nullable=False,
        index=True,
        comment="异常类型",
    )

    # 涉及的页面
    source_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="源页面（新生成的页面）",
    )
    target_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="目标页面（疑似相关/冲突的页面）",
    )

    # 详细说明
    reason: Mapped[str] = mapped_column(
        Text, nullable=False, comment="触发原因"
    )
    evidence: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="原文证据"
    )
    suggestion: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="处理建议"
    )

    # 处理状态
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus, native_enum=False, length=20),
        default=AnomalyStatus.PENDING,
        nullable=False,
        index=True,
        comment="处理状态",
    )

    # 关联
    task: Mapped["DocumentTask"] = relationship()
    source_page: Mapped["WikiPage | None"] = relationship(
        foreign_keys=[source_page_id]
    )
    target_page: Mapped["WikiPage | None"] = relationship(
        foreign_keys=[target_page_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RelationAnomaly id={self.id} type={self.anomaly_type.value} "
            f"status={self.status.value}>"
        )