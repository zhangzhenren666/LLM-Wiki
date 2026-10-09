"""文档导入模型。"""
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase
    from app.models.wiki_page import WikiPage


class ImportStatus(str, enum.Enum):
    """导入状态。"""

    PENDING = "pending"
    IMPORTING = "importing"
    SUCCESS = "success"
    FAILED = "failed"


class Document(Base, TimestampMixin):
    """文档实体：记录导入的原始文件及导入结果。

    权限扩展预留：owner_id 字段为后续用户隔离预留。
    """

    __tablename__ = "document"
    __table_args__ = {"comment": "导入文档"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    file_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="文件名"
    )
    file_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="文件类型（扩展名）"
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="存储路径（相对路径，基于 UPLOAD_DIR）"
    )
    page_id: Mapped[int | None] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="生成的 Wiki 页面 ID",
    )
    import_status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False, length=20),
        default=ImportStatus.PENDING,
        nullable=False,
        index=True,
        comment="导入状态",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="失败原因"
    )
    # 权限扩展预留
    owner_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, comment="所有者 ID（权限扩展预留）"
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship()
    page: Mapped["WikiPage | None"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document id={self.id} file={self.file_name!r}>"