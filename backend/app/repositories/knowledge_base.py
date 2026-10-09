"""知识库数据访问层。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeBase


class KnowledgeBaseRepository:
    """知识库仓储，封装对 knowledge_base 表的访问。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, kb_id: int) -> KnowledgeBase | None:
        """按主键查询知识库。"""
        return self._db.get(KnowledgeBase, kb_id)

    def get_by_name(self, name: str) -> KnowledgeBase | None:
        """按名称查询知识库（名称唯一）。"""
        return self._db.execute(
            select(KnowledgeBase).where(KnowledgeBase.name == name)
        ).scalar_one_or_none()

    def list(self) -> list[KnowledgeBase]:
        """查询全部知识库，按 id 升序。"""
        return list(
            self._db.execute(
                select(KnowledgeBase).order_by(KnowledgeBase.id.asc())
            ).scalars()
        )

    def create(self, name: str, description: str | None) -> KnowledgeBase:
        """创建知识库。"""
        kb = KnowledgeBase(name=name, description=description)
        self._db.add(kb)
        self._db.flush()
        return kb

    def update(
        self,
        kb: KnowledgeBase,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBase:
        """更新知识库字段（仅更新传入的字段）。"""
        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        self._db.flush()
        return kb

    def delete(self, kb: KnowledgeBase) -> None:
        """删除知识库（级联删除页面/标签/关系由数据库与 ORM 处理）。"""
        self._db.delete(kb)
        self._db.flush()
