"""知识库业务逻辑层。"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logger import get_logger
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)

logger = get_logger(__name__)


class KnowledgeBaseService:
    """知识库业务服务。"""

    def __init__(self, db: Session) -> None:
        self._repo = KnowledgeBaseRepository(db)
        self._db = db

    def create(
        self, payload: KnowledgeBaseCreate
    ) -> KnowledgeBaseRead:
        """创建知识库。"""
        if self._repo.get_by_name(payload.name) is not None:
            raise ConflictError(f"知识库名称已存在: {payload.name}")

        kb = self._repo.create(payload.name, payload.description)
        self._db.commit()
        self._db.refresh(kb)
        logger.info("创建知识库 id=%s name=%s", kb.id, kb.name)
        return KnowledgeBaseRead.model_validate(kb)

    def get(self, kb_id: int) -> KnowledgeBaseRead:
        """按 id 查询知识库。"""
        kb = self._repo.get(kb_id)
        if kb is None:
            raise NotFoundError(f"知识库不存在: id={kb_id}")
        return KnowledgeBaseRead.model_validate(kb)

    def list(self) -> list[KnowledgeBaseRead]:
        """查询全部知识库。"""
        kbs = self._repo.list()
        return [KnowledgeBaseRead.model_validate(kb) for kb in kbs]

    def update(
        self, kb_id: int, payload: KnowledgeBaseUpdate
    ) -> KnowledgeBaseRead:
        """更新知识库。"""
        kb = self._repo.get(kb_id)
        if kb is None:
            raise NotFoundError(f"知识库不存在: id={kb_id}")

        if payload.name is not None:
            existing = self._repo.get_by_name(payload.name)
            if existing is not None and existing.id != kb_id:
                raise ConflictError(f"知识库名称已存在: {payload.name}")

        kb = self._repo.update(
            kb, name=payload.name, description=payload.description
        )
        self._db.commit()
        self._db.refresh(kb)
        logger.info("更新知识库 id=%s", kb.id)
        return KnowledgeBaseRead.model_validate(kb)

    def delete(self, kb_id: int) -> None:
        """删除知识库（级联删除关联页面/标签/关系）。"""
        kb = self._repo.get(kb_id)
        if kb is None:
            raise NotFoundError(f"知识库不存在: id={kb_id}")

        self._repo.delete(kb)
        self._db.commit()
        logger.info("删除知识库 id=%s", kb_id)
