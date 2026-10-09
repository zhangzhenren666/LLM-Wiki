"""页面数据访问层。"""
from typing import Sequence

from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.page_relation import PageRelation, RelationSource, RelationType
from app.models.page_tag import PageTag
from app.models.wiki_page import PageStatus, WikiPage


def get(db: Session, page_id: int) -> WikiPage | None:
    """按主键获取页面，不存在返回 None。"""
    return db.get(WikiPage, page_id)


def get_by_kb_slug(db: Session, knowledge_base_id: int, slug: str) -> WikiPage | None:
    """按知识库 + slug 获取页面，用于唯一性检查。"""
    stmt = select(WikiPage).where(
        WikiPage.knowledge_base_id == knowledge_base_id,
        WikiPage.slug == slug,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_pages(
    db: Session,
    *,
    knowledge_base_id: int | None = None,
    parent_id: int | None = None,
    status: PageStatus | None = None,
    keyword: str | None = None,
    tag: str | None = None,
) -> Sequence[WikiPage]:
    """按条件查询页面列表。

    约定：parent_id 传 0 表示查询顶层页面（parent_id IS NULL）；
    传具体 id 表示查询该父页面的直接子页面；不传则不过滤。
    tag 传标签名时只返回包含该标签的页面。
    """
    stmt = select(WikiPage)
    if knowledge_base_id is not None:
        stmt = stmt.where(WikiPage.knowledge_base_id == knowledge_base_id)
    if parent_id is not None:
        if parent_id == 0:
            stmt = stmt.where(WikiPage.parent_id.is_(None))
        else:
            stmt = stmt.where(WikiPage.parent_id == parent_id)
    if status is not None:
        stmt = stmt.where(WikiPage.status == status)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(WikiPage.title.ilike(pattern), WikiPage.content.ilike(pattern)))
    if tag:
        stmt = stmt.where(WikiPage.tags.any(PageTag.tag_name == tag))
    stmt = stmt.order_by(WikiPage.created_at.asc(), WikiPage.id.asc())
    return db.execute(stmt).scalars().all()


def create(
    db: Session,
    *,
    knowledge_base_id: int,
    title: str,
    slug: str,
    content: str,
    parent_id: int | None,
    status: PageStatus,
) -> WikiPage:
    """创建页面并返回实例。"""
    page = WikiPage(
        knowledge_base_id=knowledge_base_id,
        title=title,
        slug=slug,
        content=content,
        parent_id=parent_id,
        status=status,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def update(db: Session, page: WikiPage, **fields) -> WikiPage:
    """更新传入的可变字段。"""
    mutable = {"title", "slug", "parent_id", "content", "status"}
    for key, value in fields.items():
        if key in mutable:
            setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return page


def delete(db: Session, page: WikiPage) -> None:
    """删除页面（子页面/关系由数据库级联删除）。"""
    db.delete(page)
    db.commit()


def get_kb(db: Session, knowledge_base_id: int) -> KnowledgeBase | None:
    """获取知识库实例，用于存在性校验。"""
    return db.get(KnowledgeBase, knowledge_base_id)


def add_tags(db: Session, page: WikiPage, tag_names: list[str]) -> list[str]:
    """为页面添加标签，自动去重（大小写不敏感）并跳过已存在的标签。

    返回最终新增的标签名列表。
    """
    existing = {t.tag_name for t in page.tags}
    index = {name.lower(): name for name in existing if name}
    added: list[str] = []
    for raw in tag_names:
        name = raw.strip()
        if not name:
            continue
        key = name.lower()
        if key in index:
            continue
        index[key] = name
        db.add(PageTag(page_id=page.id, tag_name=name))
        added.append(name)
    if added:
        db.commit()
        db.refresh(page)
    return added


def remove_tags(db: Session, page: WikiPage, tag_names: list[str]) -> list[str]:
    """从页面移除指定标签（大小写不敏感），返回实际移除的标签名列表。"""
    targets = {name.strip().lower() for name in tag_names if name.strip()}
    removed: list[str] = []
    keep: list[PageTag] = []
    for tag in page.tags:
        if tag.tag_name.lower() in targets:
            db.delete(tag)
            removed.append(tag.tag_name)
        else:
            keep.append(tag)
    page.tags = keep
    if removed:
        db.commit()
        db.refresh(page)
    return removed


def list_tags(db: Session, knowledge_base_id: int) -> list[str]:
    """查询某知识库下出现过的所有标签（去重、排序稳定）。"""
    stmt = (
        select(distinct(PageTag.tag_name))
        .join(WikiPage, WikiPage.id == PageTag.page_id)
        .where(WikiPage.knowledge_base_id == knowledge_base_id)
        .order_by(PageTag.tag_name.asc())
    )
    return [row[0] for row in db.execute(stmt).all()]


def get_pages_by_title(db: Session, knowledge_base_id: int, title: str) -> Sequence[WikiPage]:
    """按精确标题查询同知识库下的页面（用于内部链接定位）。"""
    stmt = select(WikiPage).where(
        WikiPage.knowledge_base_id == knowledge_base_id,
        WikiPage.title == title,
    )
    return db.execute(stmt).scalars().all()


def get_backlink_relations(
    db: Session, target_page_id: int
) -> Sequence[PageRelation]:
    """查询指向该页面的反向引用关系（只取自动识别的内部链接）。"""
    stmt = (
        select(PageRelation)
        .where(
            PageRelation.target_page_id == target_page_id,
            PageRelation.source == RelationSource.BACKLINK,
            PageRelation.relation_type == RelationType.LINK,
        )
        .order_by(PageRelation.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


def replace_backlinks(
    db: Session,
    source_page: WikiPage,
    target_pages: Sequence[WikiPage],
) -> None:
    """重建某源页面自动识别的反向链接关系。

    先删除该源页现有的 BACKLINK 关系，再为给定目标页面重建，
    保证正文改动后链接关系与内容一致。
    """
    # 删除旧的自识别反向链接
    existing = (
        db.execute(
            select(PageRelation).where(
                PageRelation.source_page_id == source_page.id,
                PageRelation.source == RelationSource.BACKLINK,
                PageRelation.relation_type == RelationType.LINK,
            )
        )
        .scalars()
        .all()
    )
    for rel in existing:
        db.delete(rel)
    # 重建（同一源页、目标页、类型唯一，天然去重）
    for target in target_pages:
        if target.id == source_page.id:
            continue
        db.add(
            PageRelation(
                knowledge_base_id=source_page.knowledge_base_id,
                source_page_id=source_page.id,
                target_page_id=target.id,
                relation_type=RelationType.LINK,
                source=RelationSource.BACKLINK,
            )
        )
    db.commit()
