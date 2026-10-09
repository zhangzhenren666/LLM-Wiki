"""页面标签模型。"""
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.wiki_page import WikiPage


class PageTag(Base, TimestampMixin):
    """页面标签实体：一页可挂多个标签。"""

    __tablename__ = "page_tag"
    __table_args__ = (
        # 同一页面上标签名唯一
        UniqueConstraint("page_id", "tag_name", name="uq_page_tag_page_name"),
        {"comment": "页面标签"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_page.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属页面",
    )
    tag_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="标签名称"
    )

    page: Mapped["WikiPage"] = relationship(back_populates="tags")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PageTag page_id={self.page_id} tag={self.tag_name!r}>"
