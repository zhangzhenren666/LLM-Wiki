"""知识提取条目模型。

记录从文档中提取的每条知识，包含来源证据、状态及生成的 Wiki 页面关联。
"""
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


class KnowledgeItemStatus(str, enum.Enum):
    """知识条目状态。"""

    AUTO_CREATED = "auto_created"        # 已自动创建 Wiki 页面
    NEEDS_ATTENTION = "needs_attention"  # 需要关注（证据不足/异常/疑似重复等）
    DUPLICATE = "duplicate"              # 与现有页面高度疑似重复
    SKIPPED = "skipped"                  # 已跳过（如内容为空）


class KnowledgeItem(Base, TimestampMixin):
    """从文档中提取的单条知识。

    每条知识可自动生成一个 Wiki 页面（status=auto_created），
    或标记为需要关注（status=needs_attention/duplicate/skipped）。
    """

    __tablename__ = "knowledge_item"
    __table_args__ = {"comment": "知识提取条目"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("document_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属处理任务",
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="来源文档",
    )

    # 知识内容
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="知识标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="知识正文（Markdown）"
    )
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="标签（JSON 数组字符串）"
    )

    # 来源证据
    evidence_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="原文证据片段"
    )
    page_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="页码"
    )
    chapter: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="章节标识"
    )
    paragraph: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="段落标识"
    )

    # 异常与重复
    uncertainty_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="不确定说明或疑似重复线索"
    )
    duplicate_candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="SET NULL"),
        nullable=True,
        comment="疑似重复的目标页面 ID",
    )
    anomaly_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="异常原因（程序校验判定，非模型自报）"
    )

    # 状态与产出
    status: Mapped[KnowledgeItemStatus] = mapped_column(
        Enum(KnowledgeItemStatus, native_enum=False, length=20),
        nullable=False,
        index=True,
        comment="条目状态",
    )
    wiki_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="自动生成的 Wiki 页面 ID",
    )

    # 关系
    task: Mapped["DocumentTask"] = relationship(
        back_populates="knowledge_items"
    )
    document: Mapped["Document"] = relationship()
    wiki_page: Mapped["WikiPage | None"] = relationship(
        foreign_keys=[wiki_page_id]
    )
    duplicate_candidate: Mapped["WikiPage | None"] = relationship(
        foreign_keys=[duplicate_candidate_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KnowledgeItem id={self.id} title={self.title!r} status={self.status.value}>"