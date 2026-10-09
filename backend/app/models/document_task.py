"""文档 AI 处理任务与处理记录模型。"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
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
    from app.models.knowledge_base import KnowledgeBase
    from app.models.knowledge_item import KnowledgeItem


class TaskStatus(str, enum.Enum):
    """文档处理任务状态。

    命名遵循任务文件语义：pending / processing / completed / failed / needs_attention。
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"


class StepStatus(str, enum.Enum):
    """处理记录步骤状态。"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentTask(Base, TimestampMixin):
    """文档 AI 处理任务。

    每个文档对应一个处理任务（document_id 唯一），
    记录状态流转、重试次数、时间与错误信息，供后续阶段扩展知识提取/关系生成。
    注意：不要把完整敏感文档正文写入日志。
    """

    __tablename__ = "document_task"
    __table_args__ = {"comment": "文档 AI 处理任务"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="关联文档（一个文档一个处理任务）",
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
        comment="幂等请求 ID（可选），用于防止重复提交产生重复任务",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
        comment="任务状态",
    )
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="已执行次数（含重试）"
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="最大执行次数"
    )
    progress: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="进度 0-100"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="结束时间"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误摘要（不包含完整文档正文）"
    )
    # 预留：后续阶段关联模型配置
    model_config_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="使用的模型配置 ID（预留）"
    )

    document: Mapped["Document"] = relationship()
    knowledge_base: Mapped["KnowledgeBase"] = relationship()
    steps: Mapped[list["TaskStep"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStep.id",
    )
    knowledge_items: Mapped[list["KnowledgeItem"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="KnowledgeItem.id",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentTask id={self.id} doc={self.document_id} status={self.status.value}>"


class TaskStep(Base, TimestampMixin):
    """处理记录步骤：记录文档处理各步骤的状态、原因及产出标识（预留）。"""

    __tablename__ = "task_step"
    __table_args__ = {"comment": "处理记录步骤"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("document_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属任务",
    )
    step_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="步骤名称（如：解析、AI 提取）"
    )
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, native_enum=False, length=20),
        default=StepStatus.RUNNING,
        nullable=False,
        comment="步骤状态",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="步骤开始时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="步骤结束时间"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="失败原因（不包含完整文档正文）"
    )
    # 后续阶段生成的产出标识（预留）
    page_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="关联 Wiki 页面 ID（预留）"
    )
    relation_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="关联关系 ID（预留）"
    )

    task: Mapped["DocumentTask"] = relationship(back_populates="steps")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaskStep id={self.id} step={self.step_name!r}>"
