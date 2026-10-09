"""模型配置业务逻辑层。"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logger import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.repositories.model_config import ModelConfigRepository
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigRead,
    ModelConfigTestResult,
    ModelConfigUpdate,
)
from app.services.llm import LLMClient, ModelCallError

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 60


class ModelConfigService:
    """模型配置业务服务。"""

    def __init__(self, db: Session) -> None:
        self._repo = ModelConfigRepository(db)
        self._db = db

    def _to_read(self, cfg) -> ModelConfigRead:
        """将 ORM 对象转为响应模型，不泄露 API Key 明文。"""
        read = ModelConfigRead.model_validate(cfg)
        read.api_key_configured = bool(cfg.api_key_encrypted)
        return read

    def list(self) -> list[ModelConfigRead]:
        """查询全部配置。"""
        return [self._to_read(c) for c in self._repo.list()]

    def get(self, config_id: int) -> ModelConfigRead:
        cfg = self._repo.get(config_id)
        if cfg is None:
            raise NotFoundError(f"模型配置不存在: id={config_id}")
        return self._to_read(cfg)

    def create(self, payload: ModelConfigCreate) -> ModelConfigRead:
        """创建配置（支持设置默认，保持默认唯一）。"""
        if self._repo.get_by_name(payload.name) is not None:
            raise ConflictError(f"模型配置名称已存在: {payload.name}")

        timeout = payload.timeout_seconds or DEFAULT_TIMEOUT
        is_default = payload.is_default or False

        # 若设为默认，先清除其它默认
        if is_default:
            self._repo.clear_default()

        cfg = self._repo.create(
            name=payload.name,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_secret(payload.api_key) if payload.api_key else None,
            model_name=payload.model_name,
            timeout_seconds=timeout,
            is_active=payload.is_active if payload.is_active is not None else True,
            is_default=is_default,
        )
        self._db.commit()
        self._db.refresh(cfg)
        logger.info("创建模型配置 id=%s name=%s", cfg.id, cfg.name)
        return self._to_read(cfg)

    def update(
        self, config_id: int, payload: ModelConfigUpdate
    ) -> ModelConfigRead:
        """更新配置。"""
        cfg = self._repo.get(config_id)
        if cfg is None:
            raise NotFoundError(f"模型配置不存在: id={config_id}")

        if payload.name is not None:
            existing = self._repo.get_by_name(payload.name)
            if existing is not None and existing.id != config_id:
                raise ConflictError(f"模型配置名称已存在: {payload.name}")

        # 设置默认时保持唯一
        if payload.is_default:
            self._repo.clear_default()

        # API Key：仅传入非空值才更新；空/None 表示保留原值
        api_key_encrypted = None
        if payload.api_key:
            api_key_encrypted = encrypt_secret(payload.api_key)

        cfg = self._repo.update(
            cfg,
            name=payload.name,
            base_url=payload.base_url,
            api_key_encrypted=api_key_encrypted,
            model_name=payload.model_name,
            timeout_seconds=payload.timeout_seconds,
            is_active=payload.is_active,
            is_default=payload.is_default,
        )
        self._db.commit()
        self._db.refresh(cfg)
        logger.info("更新模型配置 id=%s name=%s", cfg.id, cfg.name)
        return self._to_read(cfg)

    def delete(self, config_id: int) -> None:
        cfg = self._repo.get(config_id)
        if cfg is None:
            raise NotFoundError(f"模型配置不存在: id={config_id}")
        self._repo.delete(cfg)
        self._db.commit()
        logger.info("删除模型配置 id=%s name=%s", cfg.id, cfg.name)

    def test_connection(self, config_id: int) -> ModelConfigTestResult:
        """测试指定配置的连接可用性。

        只向模型发送一条最小对话请求，验证地址/密钥/模型是否可用，
        不保存测试响应中的任何内容。
        """
        cfg = self._repo.get(config_id)
        if cfg is None:
            raise NotFoundError(f"模型配置不存在: id={config_id}")

        api_key = decrypt_secret(cfg.api_key_encrypted)
        if not api_key:
            return ModelConfigTestResult(
                success=False, message="该配置未设置 API Key，无法测试连接"
            )

        client = LLMClient(
            base_url=cfg.base_url,
            api_key=api_key,
            model=cfg.model_name,
            timeout=cfg.timeout_seconds,
        )

        try:
            reply = client.chat(
                [{"role": "user", "content": "连接测试，请只回复：OK"}]
            )
        except ModelCallError as exc:
            logger.info("测试连接失败 config_id=%s reason=%s", config_id, exc.message)
            # 不给前端暴露配置明细，仅返回可读错误
            return ModelConfigTestResult(success=False, message=exc.message)

        logger.info("测试连接成功 config_id=%s", config_id)
        return ModelConfigTestResult(
            success=True, message="连接成功", reply=reply
        )

    def get_default(self) -> ModelConfigRead | None:
        """查询默认配置（供后续阶段获取用于调用的模型）。"""
        cfg = self._repo.get_default()
        return self._to_read(cfg) if cfg else None
