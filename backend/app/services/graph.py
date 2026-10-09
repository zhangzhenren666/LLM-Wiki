"""知识图谱业务逻辑层。"""
import logging
import re
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.knowledge_base import KnowledgeBase
from app.models.page_relation import PageRelation
from app.models.wiki_page import WikiPage
from app.repositories import page as page_repo
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse

logger = logging.getLogger("app.services.graph")

# 内部链接正则：匹配 [[页面标题]]
_INTERNAL_LINK_RE = re.compile(r"\[\[([^[\]]+)\]\]")

# 关系类型枚举值 → 中文标签
RELATION_TYPE_LABELS: dict[str, str] = {
    "link": "内部链接",
    "reference": "引用",
    "related": "相关知识",
    "references": "参考资料",
    "depends_on": "依赖关系",
    "parent": "上级知识",
    "part_of": "组成部分",
    "explains": "解释说明",
}


def _build_node(page: WikiPage) -> GraphNode:
    return GraphNode(
        id=page.id,
        label=page.title,
        title=page.title,
        slug=page.slug,
        knowledge_base_id=page.knowledge_base_id,
    )


def _build_edge_from_relation(rel: PageRelation) -> GraphEdge:
    """从 PageRelation 记录构建边，保留原始枚举值作为 relation_type。"""
    rt = rel.relation_type.value
    label = RELATION_TYPE_LABELS.get(rt, rt)
    return GraphEdge(
        id=rel.id,
        source=rel.source_page_id,
        target=rel.target_page_id,
        relation_type=rt,
        label=label,
    )


def _parse_wiki_links(pages: Sequence[WikiPage]) -> list[GraphEdge]:
    """从页面内容中提取 [[页面标题]] 内部链接并转为图谱边。

    使用自增负数 ID 区分于数据库中的 PageRelation ID。
    """
    title_to_id: dict[str, int] = {p.title: p.id for p in pages}
    edges: list[GraphEdge] = []
    edge_id = -1  # 自增负数 ID

    for page in pages:
        for match in _INTERNAL_LINK_RE.finditer(page.content or ""):
            target_title = match.group(1).strip()
            target_id = title_to_id.get(target_title)
            if target_id is not None and target_id != page.id:
                edges.append(
                    GraphEdge(
                        id=edge_id,
                        source=page.id,
                        target=target_id,
                        relation_type="link",
                        label="内部链接",
                    )
                )
                edge_id -= 1

    return edges


def _parse_parent_relations(pages: Sequence[WikiPage]) -> list[GraphEdge]:
    """从页面 parent_id 字段中提取父子关系，生成「上级知识」边。

    使用自增负数 ID（与 wiki link ID 段区分开），从 -100000 开始递减。
    """
    page_ids = {p.id for p in pages}
    edges: list[GraphEdge] = []
    edge_id = -100000

    for page in pages:
        if page.parent_id is not None and page.parent_id in page_ids:
            edges.append(
                GraphEdge(
                    id=edge_id,
                    source=page.id,
                    target=page.parent_id,
                    relation_type="parent",
                    label="上级知识",
                )
            )
            edge_id -= 1

    return edges


def _deduplicate_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    """去重：相同 (source, target, relation_type) 的边只保留一条。"""
    seen: set[tuple[int, int, str]] = set()
    result: list[GraphEdge] = []
    for e in edges:
        key = (e.source, e.target, e.relation_type)
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


def get_page_graph(db: Session, page_id: int, depth: int = 1) -> GraphResponse:
    """获取单页面的关联图谱。

    以该页面为中心，收集与其直接关联的所有手动关系 + wiki 内部链接（出向+入向），
    构建 1-hop 邻域图。depth 参数预留，当前仅支持 depth=1。
    """
    page = page_repo.get(db, page_id)
    if page is None:
        raise NotFoundError(f"页面不存在: id={page_id}")

    if depth < 1:
        depth = 1

    # 收集与该页面直接关联的手动关系
    stmt = select(PageRelation).where(
        or_(
            PageRelation.source_page_id == page_id,
            PageRelation.target_page_id == page_id,
        )
    )
    relations: Sequence[PageRelation] = db.execute(stmt).scalars().all()

    # 收集所有涉及的页面 ID（手动关系 + 父子关系）
    page_ids: set[int] = {page.id}
    for rel in relations:
        page_ids.add(rel.source_page_id)
        page_ids.add(rel.target_page_id)
    # 纳入父页面和子页面
    if page.parent_id is not None:
        page_ids.add(page.parent_id)
    child_ids = db.execute(
        select(WikiPage.id).where(
            WikiPage.knowledge_base_id == page.knowledge_base_id,
            WikiPage.parent_id == page.id,
        )
    ).scalars().all()
    page_ids.update(child_ids)

    # 加载页面
    pages_map: dict[int, WikiPage] = {}
    if page_ids:
        stmt = select(WikiPage).where(WikiPage.id.in_(page_ids))
        for p in db.execute(stmt).scalars().all():
            pages_map[p.id] = p

    # 手动关系边
    relation_edges = [_build_edge_from_relation(rel) for rel in relations]

    # 内部链接边（仅保留涉及已加载页面的边）
    wiki_edges = _parse_wiki_links(list(pages_map.values()))
    wiki_edges = [
        e
        for e in wiki_edges
        if e.source in pages_map and e.target in pages_map
    ]

    # 父子关系边（parent_id）
    parent_edges = _parse_parent_relations(list(pages_map.values()))
    parent_edges = [
        e
        for e in parent_edges
        if e.source in pages_map and e.target in pages_map
    ]

    edges = _deduplicate_edges(relation_edges + wiki_edges + parent_edges)
    nodes = [_build_node(p) for p in pages_map.values()]

    return GraphResponse(nodes=nodes, edges=edges)


def get_kb_graph(
    db: Session,
    kb_id: int,
    max_nodes: int | None = None,
) -> GraphResponse:
    """获取知识库整体图谱。

    包含：手动关系 + wiki 内部链接。max_nodes 不为 None 时限制节点数。
    """
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise NotFoundError(f"知识库不存在: id={kb_id}")

    # 获取所有页面
    stmt = select(WikiPage).where(WikiPage.knowledge_base_id == kb_id)
    pages: Sequence[WikiPage] = db.execute(stmt).scalars().all()

    limited_page_ids: set[int] | None = None
    if max_nodes is not None and len(pages) > max_nodes:
        pages = pages[:max_nodes]
        limited_page_ids = {p.id for p in pages}

    # 获取该知识库下的所有手动关系
    stmt = select(PageRelation).where(PageRelation.knowledge_base_id == kb_id)
    relations: Sequence[PageRelation] = db.execute(stmt).scalars().all()

    # 若有限制，过滤边
    if limited_page_ids is not None:
        relations = [
            r
            for r in relations
            if r.source_page_id in limited_page_ids
            and r.target_page_id in limited_page_ids
        ]

    # 内部链接边
    wiki_edges = _parse_wiki_links(pages)
    if limited_page_ids is not None:
        wiki_edges = [
            e
            for e in wiki_edges
            if e.source in limited_page_ids and e.target in limited_page_ids
        ]

    # 父子关系边
    parent_edges = _parse_parent_relations(pages)
    if limited_page_ids is not None:
        parent_edges = [
            e
            for e in parent_edges
            if e.source in limited_page_ids and e.target in limited_page_ids
        ]

    relation_edges = [_build_edge_from_relation(rel) for rel in relations]
    edges = _deduplicate_edges(relation_edges + wiki_edges + parent_edges)

    nodes = [_build_node(p) for p in pages]

    return GraphResponse(nodes=nodes, edges=edges)