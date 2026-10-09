"""模型配置模型。"""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ModelConfig(Base, TimestampMixin):
    """大模型调用配置实体。

    用于存储可连接到 OpenAI Chat Completions 兼容接口的模型配置。
    注意：
    - api_key 以 Fernet 加密后存储，切勿在日志或响应中明文输出。
    - 同时最多存在一个 is_default=True 的配置。
    """

    __tablename__ = "model_config"
    __table_args__ = {"comment": "大模型配置"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="配置名称"
    )
    base_url: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="OpenAI Chat Completions 兼容的 API Base URL"
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="加密后的 API Key（响应与日志中绝不返回明文）"
    )
    model_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="模型名称"
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False, comment="请求超时时间（秒）"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否为默认配置"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ModelConfig id={self.id} name={self.name!r}>"
