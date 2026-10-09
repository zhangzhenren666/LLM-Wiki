"""模型配置数据访问层。"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ModelConfig


class ModelConfigRepository:
    """模型配置仓储，封装对 model_config 表的访问。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, config_id: int) -> ModelConfig | None:
        """按主键查询。"""
        return self._db.get(ModelConfig, config_id)

    def get_by_name(self, name: str) -> ModelConfig | None:
        """按名称查询（名称唯一）。"""
        return self._db.execute(
            select(ModelConfig).where(ModelConfig.name == name)
        ).scalar_one_or_none()

    def list(self) -> list[ModelConfig]:
        """查询全部配置，默认排在前面，其余按 id 升序。"""
        return list(
            self._db.execute(
                select(ModelConfig).order_by(
                    ModelConfig.is_default.desc(),
                    ModelConfig.id.asc(),
                )
            ).scalars()
        )

    def get_default(self) -> ModelConfig | None:
        """查询默认配置。"""
        return self._db.execute(
            select(ModelConfig).where(ModelConfig.is_default.is_(True))
        ).scalar_one_or_none()

    def clear_default(self) -> None:
        """清除所有配置的默认标记。"""
        self._db.execute(
            update(ModelConfig).values(is_default=False)
        )

    def create(
        self,
        *,
        name: str,
        base_url: str,
        api_key_encrypted: str | None,
        model_name: str,
        timeout_seconds: int,
        is_active: bool,
        is_default: bool,
    ) -> ModelConfig:
        """创建配置。"""
        cfg = ModelConfig(
            name=name,
            base_url=base_url,
            api_key_encrypted=api_key_encrypted,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            is_active=is_active,
            is_default=is_default,
        )
        self._db.add(cfg)
        self._db.flush()
        return cfg

    def update(
        self,
        cfg: ModelConfig,
        *,
        name: str | None = None,
        base_url: str | None = None,
        api_key_encrypted: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
    ) -> ModelConfig:
        """更新配置字段（仅更新传入的字段，api_key_encrypted None 表示不修改）。"""
        if name is not None:
            cfg.name = name
        if base_url is not None:
            cfg.base_url = base_url
        if api_key_encrypted is not None:
            cfg.api_key_encrypted = api_key_encrypted
        if model_name is not None:
            cfg.model_name = model_name
        if timeout_seconds is not None:
            cfg.timeout_seconds = timeout_seconds
        if is_active is not None:
            cfg.is_active = is_active
        if is_default is not None:
            cfg.is_default = is_default
        self._db.flush()
        return cfg

    def delete(self, cfg: ModelConfig) -> None:
        """删除配置。"""
        self._db.delete(cfg)
        self._db.flush()
