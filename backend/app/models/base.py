"""模型基类与通用字段。

统一时间字段：所有实体使用 created_at / updated_at，
updated_at 在更新时自动维护。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    """返回当前 UTC 时间（带时区信息，便于后期迁移 PostgreSQL）。"""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """通用时间戳混入类。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


__all__ = ["Base", "TimestampMixin", "utcnow"]
