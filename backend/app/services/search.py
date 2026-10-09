"""搜索业务逻辑层。

搜索范围：页面标题、标签、正文内容。
返回匹配类型和内容摘要片段。
"""

import logging

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.page_tag import PageTag
from app.models.wiki_page import WikiPage
from app.schemas.search import PaginatedSearchResponse, SearchResult

logger = logging.getLogger("app.services.search")

# 摘要片段长度（关键词前后各取字符数）
_SNIPPET_HALF = 40


def _find_case_insensitive(text: str, keyword: str) -> int:
    """在 text 中查找 keyword（不区分大小写），返回首次匹配位置。"""
    lower_text = text.lower()
    lower_kw = keyword.lower()
    idx = lower_text.find(lower_kw)
    return idx


def _generate_snippet(content: str, keyword: str) -> str | None:
    """从正文中提取关键词附近的摘要片段。

    关键词用 **keyword** 包裹，前后各取 ~40 字符。
    如果未找到关键词或内容为空则返回 None。
    """
    if not content or not keyword:
        return None

    idx = _find_case_insensitive(content, keyword)
    if idx < 0:
        return None

    kw_len = len(keyword)
    start = max(0, idx - _SNIPPET_HALF)
    end = min(len(content), idx + kw_len + _SNIPPET_HALF)

    snippet = content[start:end]
    # 在 snippet 中将关键词用 ** 包裹（保留原标题大小写）
    snippet_idx = idx - start
    snippet = (
        snippet[:snippet_idx]
        + "**"
        + snippet[snippet_idx : snippet_idx + kw_len]
        + "**"
        + snippet[snippet_idx + kw_len :]
    )

    # 省略号标记
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{snippet}{suffix}"


def _determine_match_type(
    page: WikiPage, keyword: str, matched_tags: list[str], matched_title: bool, matched_content: bool
) -> str:
    """确定搜索结果的最佳匹配类型。

    优先级：title > tag > content。
    """
    if matched_title:
        return "title"
    if matched_tags:
        return "tag"
    if matched_content:
        return "content"
    return "content"  # fallback


def search(
    db: Session,
    *,
    query: str,
    knowledge_base_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedSearchResponse:
    """执行关键词搜索，返回分页结果。

    搜索范围：
    - 页面标题（LIKE 不区分大小写）
    - 页面标签（PageTag.tag_name LIKE）
    - 正文内容（LIKE）

    每个结果包含页面基本信息、匹配类型和内容摘要。
    """
    keyword = query.strip()
    if not keyword:
        raise ValueError("搜索关键词不能为空")

    pattern = f"%{keyword}%"

    # 搜索 title / content 匹配的页面
    stmt = select(WikiPage).where(
        or_(
            WikiPage.title.ilike(pattern),
            WikiPage.content.ilike(pattern),
        )
    )

    if knowledge_base_id is not None:
        stmt = stmt.where(WikiPage.knowledge_base_id == knowledge_base_id)

    # 搜索标签匹配的页面（union）
    tag_stmt = (
        select(WikiPage)
        .join(PageTag, PageTag.page_id == WikiPage.id)
        .where(PageTag.tag_name.ilike(pattern))
        .distinct()
    )
    if knowledge_base_id is not None:
        tag_stmt = tag_stmt.where(WikiPage.knowledge_base_id == knowledge_base_id)

    # 合并两种匹配
    title_content_pages = db.execute(stmt).scalars().all()
    tag_pages = db.execute(tag_stmt).scalars().all()

    # 用 dict 去重合并
    page_map: dict[int, WikiPage] = {}
    title_match_ids: set[int] = set()
    content_match_ids: set[int] = set()

    for p in title_content_pages:
        page_map[p.id] = p
        if keyword.lower() in p.title.lower():
            title_match_ids.add(p.id)
        if p.content and keyword.lower() in p.content.lower():
            content_match_ids.add(p.id)

    # 标签匹配的页面
    tag_match_ids: set[int] = set()
    for p in tag_pages:
        if p.id not in page_map:
            page_map[p.id] = p
        tag_match_ids.add(p.id)

    # 收集匹配标签名
    page_matched_tags: dict[int, list[str]] = {}
    for p in page_map.values():
        matched = [t.tag_name for t in p.tags if keyword.lower() in t.tag_name.lower()]
        if matched:
            page_matched_tags[p.id] = matched

    # 转为结果列表
    results: list[SearchResult] = []
    for p in page_map.values():
        match_type = _determine_match_type(
            p, keyword,
            matched_tags=page_matched_tags.get(p.id, []),
            matched_title=p.id in title_match_ids,
            matched_content=p.id in content_match_ids,
        )
        snippet = _generate_snippet(p.content or "", keyword)

        kb_name = p.knowledge_base.name if p.knowledge_base else None

        results.append(
            SearchResult(
                page_id=p.id,
                title=p.title,
                slug=p.slug,
                knowledge_base_id=p.knowledge_base_id,
                knowledge_base_name=kb_name,
                match_type=match_type,
                snippet=snippet,
                tags=[t.tag_name for t in p.tags],
            )
        )

    # 排序：先按匹配类型优先级 > title > tag > content，同类型按标题
    type_order = {"title": 0, "tag": 1, "content": 2}
    results.sort(key=lambda r: (type_order.get(r.match_type, 9), r.title.lower()))

    total = len(results)

    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_items = results[start_idx:end_idx]

    return PaginatedSearchResponse(
        items=paged_items,
        total=total,
        page=page,
        page_size=page_size,
        query=query,
    )