"""页面关系数据访问层。"""
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.page_relation import PageRelation, RelationSource, RelationType
from app.models.wiki_page import WikiPage


def get(db: Session, relation_id: int) -> PageRelation | None:
    """按主键获取关系，不存在返回 None。"""
    return db.get(PageRelation, relation_id)


def get_page(db: Session, page_id: int) -> WikiPage | None:
    """获取页面实例，用于存在性校验。"""
    return db.get(WikiPage, page_id)


def create(
    db: Session,
    *,
    knowledge_base_id: int,
    source_page_id: int,
    target_page_id: int,
    relation_type: RelationType,
) -> PageRelation:
    """创建页面关系并返回实例。

    调用方需确保源/目标页面存在、同知识库、非自引用、无重复。
    """
    rel = PageRelation(
        knowledge_base_id=knowledge_base_id,
        source_page_id=source_page_id,
        target_page_id=target_page_id,
        relation_type=relation_type,
        source=RelationSource.MANUAL,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def create_auto(
    db: Session,
    *,
    knowledge_base_id: int,
    source_page_id: int,
    target_page_id: int,
    relation_type: RelationType,
    reason: str | None = None,
    evidence: str | None = None,
) -> PageRelation:
    """创建自动识别的关系（source=AUTO，记录理由和依据）。

    调用方需确保源/目标页面存在、同知识库、非自引用、无重复。
    """
    rel = PageRelation(
        knowledge_base_id=knowledge_base_id,
        source_page_id=source_page_id,
        target_page_id=target_page_id,
        relation_type=relation_type,
        source=RelationSource.AUTO,
        relation_reason=(reason or "")[:500] if reason else None,
        relation_evidence=(evidence or "")[:2000] if evidence else None,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def check_duplicate(
    db: Session,
    source_page_id: int,
    target_page_id: int,
    relation_type: RelationType,
) -> PageRelation | None:
    """检查是否已存在相同关系（返回已有实例或 None）。"""
    stmt = select(PageRelation).where(
        PageRelation.source_page_id == source_page_id,
        PageRelation.target_page_id == target_page_id,
        PageRelation.relation_type == relation_type,
    )
    return db.execute(stmt).scalar_one_or_none()


def delete(db: Session, relation: PageRelation) -> None:
    """删除关系。"""
    db.delete(relation)
    db.commit()


def list_relations(
    db: Session,
    *,
    knowledge_base_id: int | None = None,
    page_id: int | None = None,
    relation_type: RelationType | None = None,
) -> Sequence[PageRelation]:
    """按条件查询关系列表。

    page_id 同时匹配 source_page_id 和 target_page_id。
    """
    stmt = select(PageRelation)
    if knowledge_base_id is not None:
        stmt = stmt.where(PageRelation.knowledge_base_id == knowledge_base_id)
    if page_id is not None:
        stmt = stmt.where(
            or_(
                PageRelation.source_page_id == page_id,
                PageRelation.target_page_id == page_id,
            )
        )
    if relation_type is not None:
        stmt = stmt.where(PageRelation.relation_type == relation_type)
    stmt = stmt.order_by(PageRelation.created_at.asc(), PageRelation.id.asc())
    return db.execute(stmt).scalars().all()


def get_page_relations(
    db: Session,
    page_id: int,
) -> dict[str, Sequence[PageRelation]]:
    """获取某页面的所有关系（出向 + 入向）。

    返回 {"outgoing": [...], "incoming": [...]}。
    """
    outgoing = db.execute(
        select(PageRelation)
        .where(PageRelation.source_page_id == page_id)
        .order_by(PageRelation.created_at.asc())
    ).scalars().all()
    incoming = db.execute(
        select(PageRelation)
        .where(PageRelation.target_page_id == page_id)
        .order_by(PageRelation.created_at.asc())
    ).scalars().all()
    return {"outgoing": outgoing, "incoming": incoming}