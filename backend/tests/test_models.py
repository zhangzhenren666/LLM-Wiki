"""数据库模型功能测试。

使用独立的内存 SQLite 验证模型定义、关系、唯一约束与级联删除行为。
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base,
    KnowledgeBase,
    PageRelation,
    PageStatus,
    PageTag,
    RelationSource,
    RelationType,
    WikiPage,
)

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _make_kb_and_page(db: Session) -> tuple[KnowledgeBase, WikiPage]:
    kb = KnowledgeBase(name="默认知识库", description="测试")
    db.add(kb)
    db.flush()
    page = WikiPage(
        knowledge_base_id=kb.id,
        title="首页",
        slug="home",
        content="# 首页",
        status=PageStatus.DRAFT,
    )
    db.add(page)
    db.flush()
    return kb, page


def test_create_knowledge_base_and_page() -> None:
    db = TestSession()
    try:
        kb, page = _make_kb_and_page(db)
        db.commit()

        loaded = db.get(KnowledgeBase, kb.id)
        assert loaded is not None
        assert loaded.name == "默认知识库"
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        assert len(loaded.pages) == 1
        assert loaded.pages[0].slug == "home"
    finally:
        db.close()


def test_page_parent_child_relationship() -> None:
    db = TestSession()
    try:
        kb, parent = _make_kb_and_page(db)
        child = WikiPage(
            knowledge_base_id=kb.id,
            parent_id=parent.id,
            title="子页面",
            slug="child",
        )
        db.add(child)
        db.commit()

        loaded_parent = db.get(WikiPage, parent.id)
        assert loaded_parent is not None
        assert len(loaded_parent.children) == 1
        assert loaded_parent.children[0].slug == "child"
        assert loaded_parent.children[0].parent_id == parent.id
    finally:
        db.close()


def test_page_tag_and_relation() -> None:
    db = TestSession()
    try:
        kb, page = _make_kb_and_page(db)
        other = WikiPage(
            knowledge_base_id=kb.id,
            title="目标页",
            slug="target",
        )
        db.add(other)
        db.flush()

        db.add(PageTag(page_id=page.id, tag_name="前端"))
        db.add(
            PageRelation(
                knowledge_base_id=kb.id,
                source_page_id=page.id,
                target_page_id=other.id,
                relation_type=RelationType.LINK,
                source=RelationSource.MANUAL,
            )
        )
        db.commit()

        loaded_page = db.get(WikiPage, page.id)
        assert loaded_page is not None
        assert [t.tag_name for t in loaded_page.tags] == ["前端"]
        assert len(loaded_page.outgoing_relations) == 1
        assert loaded_page.outgoing_relations[0].target_page_id == other.id
    finally:
        db.close()


def test_slug_unique_within_knowledge_base() -> None:
    db = TestSession()
    try:
        _, page = _make_kb_and_page(db)
        # 同一知识库中 slug 相同应冲突
        dup = WikiPage(
            knowledge_base_id=page.knowledge_base_id,
            title="重复",
            slug="home",
        )
        db.add(dup)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_page_tag_unique() -> None:
    db = TestSession()
    try:
        _, page = _make_kb_and_page(db)
        db.add(PageTag(page_id=page.id, tag_name="标签"))
        db.flush()
        db.add(PageTag(page_id=page.id, tag_name="标签"))
        with pytest.raises(Exception):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_delete_page_cascades_tags() -> None:
    db = TestSession()
    try:
        _, page = _make_kb_and_page(db)
        db.add(PageTag(page_id=page.id, tag_name="标签"))
        db.commit()

        db.delete(page)
        db.commit()

        tags = db.execute(
            select(PageTag).where(PageTag.page_id == page.id)
        ).scalars().all()
        assert tags == []
    finally:
        db.close()


def test_delete_knowledge_base_cascades_pages_and_relations() -> None:
    db = TestSession()
    try:
        kb, page = _make_kb_and_page(db)
        other = WikiPage(
            knowledge_base_id=kb.id,
            title="目标页",
            slug="target",
        )
        db.add(other)
        db.flush()
        db.add(
            PageRelation(
                knowledge_base_id=kb.id,
                source_page_id=page.id,
                target_page_id=other.id,
            )
        )
        db.commit()

        db.delete(kb)
        db.commit()

        pages = db.execute(select(WikiPage)).scalars().all()
        relations = db.execute(select(PageRelation)).scalars().all()
        assert pages == []
        assert relations == []
    finally:
        db.close()
