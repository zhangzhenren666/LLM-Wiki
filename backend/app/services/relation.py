"""页面关系业务逻辑层。"""
import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.page_relation import PageRelation, RelationType
from app.repositories import relation as relation_repo

logger = logging.getLogger("app.services.relation")


def _ensure_page_exists(db: Session, page_id: int, label: str) -> None:
    """校验页面存在，否则抛出 404。"""
    page = relation_repo.get_page(db, page_id)
    if page is None:
        raise NotFoundError(f"{label}不存在: id={page_id}")


def create_relation(
    db: Session,
    *,
    source_page_id: int,
    target_page_id: int,
    relation_type: RelationType,
) -> PageRelation:
    """创建页面关系。

    校验：
    1. 源页面和目标页面必须存在
    2. 默认要求两个页面属于同一知识库
    3. 禁止页面与自身建立关系
    4. 防止重复关系（同源、目标、类型唯一）
    """
    # 校验页面存在
    _ensure_page_exists(db, source_page_id, "源页面")
    _ensure_page_exists(db, target_page_id, "目标页面")

    source_page = relation_repo.get_page(db, source_page_id)
    target_page = relation_repo.get_page(db, target_page_id)

    # 禁止自引用
    if source_page_id == target_page_id:
        raise AppError("不能与自身建立关系", code=400, status_code=400)

    # 同知识库校验
    if source_page.knowledge_base_id != target_page.knowledge_base_id:
        raise AppError(
            "源页面和目标页面必须属于同一知识库", code=400, status_code=400
        )

    # 防止重复
    existing = relation_repo.check_duplicate(
        db, source_page_id, target_page_id, relation_type
    )
    if existing is not None:
        raise ConflictError(
            f"关系已存在: {source_page_id} -> {target_page_id} ({relation_type.value})"
        )

    return relation_repo.create(
        db,
        knowledge_base_id=source_page.knowledge_base_id,
        source_page_id=source_page_id,
        target_page_id=target_page_id,
        relation_type=relation_type,
    )


def delete_relation(db: Session, relation_id: int) -> None:
    """删除关系。"""
    rel = relation_repo.get(db, relation_id)
    if rel is None:
        raise NotFoundError(f"关系不存在: id={relation_id}")
    relation_repo.delete(db, rel)


def list_relations(
    db: Session,
    *,
    knowledge_base_id: int | None = None,
    page_id: int | None = None,
    relation_type: RelationType | None = None,
) -> list[PageRelation]:
    """按条件查询关系列表。"""
    return list(
        relation_repo.list_relations(
            db,
            knowledge_base_id=knowledge_base_id,
            page_id=page_id,
            relation_type=relation_type,
        )
    )


def get_page_relations(
    db: Session,
    page_id: int,
) -> dict[str, list[dict]]:
    """获取某页面的所有关系（出向 + 入向）。

    返回 {"outgoing": [...], "incoming": [...]}。
    """
    _ensure_page_exists(db, page_id, "页面")
    raw = relation_repo.get_page_relations(db, page_id)

    def _serialize(rel: PageRelation) -> dict:
        target = rel.target_page if rel.source_page_id == page_id else rel.source_page
        return {
            "id": rel.id,
            "source_page_id": rel.source_page_id,
            "target_page_id": rel.target_page_id,
            "relation_type": rel.relation_type.value,
            "source": rel.source.value,
            "related_page": {
                "id": target.id,
                "title": target.title,
                "slug": target.slug,
            } if target else None,
            "created_at": rel.created_at.isoformat(),
        }

    return {
        "outgoing": [_serialize(r) for r in raw["outgoing"]],
        "incoming": [_serialize(r) for r in raw["incoming"]],
    }