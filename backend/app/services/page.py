"""页面业务逻辑层。"""
import logging
import re

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.knowledge_base import KnowledgeBase
from app.models.wiki_page import PageStatus, WikiPage
from app.repositories import page as page_repo

logger = logging.getLogger("app.services.page")

# slug 允许的字符：小写字母、数字、中文、连字符
_SLUG_KEEP = re.compile(r"[^a-z0-9\u4e00-\u9fa5-]")


def _slugify(text: str) -> str:
    """将标题转为 slug。"""
    normalized = text.strip().lower()
    normalized = _SLUG_KEEP.sub("-", normalized)
    return re.sub(r"-{2,}", "-", normalized).strip("-") or "page"


def _build_unique_slug(db: Session, kb_id: int, title: str) -> str:
    """为标题生成一个在同知识库内唯一的 slug。"""
    base = _slugify(title)
    slug = base
    counter = 2
    while page_repo.get_by_kb_slug(db, kb_id, slug) is not None:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _ensure_kb_exists(db: Session, kb_id: int) -> KnowledgeBase:
    kb = page_repo.get_kb(db, kb_id)
    if kb is None:
        raise NotFoundError(f"知识库不存在: id={kb_id}")
    return kb


def _resolve_parent(db: Session, kb_id: int, parent_id: int) -> WikiPage:
    """校验父页面存在且属于同一知识库，返回父页面。"""
    parent = page_repo.get(db, parent_id)
    if parent is None:
        raise NotFoundError(f"父页面不存在: id={parent_id}")
    if parent.knowledge_base_id != kb_id:
        raise AppError(
            "父页面必须属于同一知识库",
            code=400,
            status_code=400,
        )
    return parent


def _assert_not_in_own_ancestry(db: Session, page: WikiPage, new_parent_id: int) -> None:
    """校验 new_parent_id 不能是 page 自身或其后裔（防止形成环）。"""
    current = page_repo.get(db, new_parent_id)
    while current is not None:
        if current.id == page.id:
            raise AppError("不能将页面挂载到自身或其子页面下", code=400, status_code=400)
        current = page_repo.get(db, current.parent_id) if current.parent_id else None


# 内部链接语法：[[页面标题]]
_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_link_targets(db: Session, page: WikiPage) -> list[WikiPage]:
    """扫描页面正文中的 [[标题]] 内部链接，定位同知识库内精确匹配的页面。

    为避免通过模糊标题匹配造成错误跳转：
    - 标题在同知识库内精确命中且唯一，才建立关系；
    - 命中 0 个或多个（同名歧义）时跳过该链接。
    """
    if not page.content:
        return []
    targets: list[WikiPage] = []
    seen: set[int] = set()
    for raw in _LINK_RE.findall(page.content):
        title = raw.strip()
        if not title:
            continue
        matched = page_repo.get_pages_by_title(db, page.knowledge_base_id, title)
        if len(matched) != 1:
            # 不存在或同名歧义，不建立关系
            continue
        target = matched[0]
        if target.id in seen:
            continue
        seen.add(target.id)
        targets.append(target)
    return targets


def _sync_page_backlinks(db: Session, page: WikiPage) -> None:
    """保存页面内容后重建其自动识别的内部链接关系。"""
    targets = _extract_link_targets(db, page)
    page_repo.replace_backlinks(db, page, targets)


def list_pages(
    db: Session,
    *,
    knowledge_base_id: int | None = None,
    parent_id: int | None = None,
    status: PageStatus | None = None,
    keyword: str | None = None,
    tag: str | None = None,
) -> list[WikiPage]:
    """按条件查询页面列表。"""
    return list(page_repo.list_pages(
        db,
        knowledge_base_id=knowledge_base_id,
        parent_id=parent_id,
        status=status,
        keyword=keyword,
        tag=tag,
    ))


def get_page(db: Session, page_id: int) -> WikiPage:
    """获取单个页面，不存在抛出 404。"""
    page = page_repo.get(db, page_id)
    if page is None:
        raise NotFoundError(f"页面不存在: id={page_id}")
    return page


def create_page(
    db: Session,
    *,
    knowledge_base_id: int,
    title: str,
    slug: str | None,
    content: str,
    parent_id: int | None,
    status: PageStatus,
) -> WikiPage:
    """创建页面。"""
    _ensure_kb_exists(db, knowledge_base_id)
    if parent_id is not None:
        _resolve_parent(db, knowledge_base_id, parent_id)

    if slug and slug.strip():
        # 显式传 slug：校验唯一
        if page_repo.get_by_kb_slug(db, knowledge_base_id, slug.strip()) is not None:
            raise ConflictError(f"同知识库下 slug 已存在: {slug.strip()}")
        final_slug = slug.strip()
    else:
        final_slug = _build_unique_slug(db, knowledge_base_id, title)

    page = page_repo.create(
        db,
        knowledge_base_id=knowledge_base_id,
        title=title,
        slug=final_slug,
        content=content,
        parent_id=parent_id,
        status=status,
    )
    _sync_page_backlinks(db, page)
    return page


# 用于区分“未传入 parent_id”与“显式传入 null（置为顶层）”
_UNSET = object()


def update_page(
    db: Session,
    page_id: int,
    *,
    title: str | None = None,
    slug: str | None = None,
    parent_id: int | None | object = _UNSET,
    content: str | None = None,
    status: PageStatus | None = None,
) -> WikiPage:
    """更新页面字段。parent_id 显式传 None 表示置为顶层页面。"""
    page = get_page(db, page_id)

    fields: dict = {}

    if title is not None:
        fields["title"] = title
    if content is not None:
        fields["content"] = content
    if status is not None:
        fields["status"] = status

    if slug is not None:
        s = slug.strip()
        if not s:
            raise AppError("slug 不能为空字符串", code=400, status_code=400)
        conflict = page_repo.get_by_kb_slug(db, page.knowledge_base_id, s)
        if conflict is not None and conflict.id != page.id:
            raise ConflictError(f"同知识库下 slug 已存在: {s}")
        fields["slug"] = s

    if parent_id is not _UNSET:
        if parent_id is None:
            fields["parent_id"] = None
        else:
            _resolve_parent(db, page.knowledge_base_id, parent_id)
            _assert_not_in_own_ancestry(db, page, parent_id)
            fields["parent_id"] = parent_id

    if not fields:
        return page

    updated = page_repo.update(db, page, **fields)
    # 内容变化时重建内部链接关系
    if "content" in fields:
        _sync_page_backlinks(db, updated)
    return updated


def delete_page(db: Session, page_id: int) -> None:
    """删除页面。"""
    page = get_page(db, page_id)
    page_repo.delete(db, page)


def list_tags(db: Session, knowledge_base_id: int) -> list[str]:
    """查询某知识库下出现过的所有标签（去重）。"""
    _ensure_kb_exists(db, knowledge_base_id)
    return page_repo.list_tags(db, knowledge_base_id)


def add_page_tags(
    db: Session,
    page_id: int,
    tag_names: list[str],
) -> WikiPage:
    """为页面添加标签（自动去重，不重复）。"""
    page = get_page(db, page_id)
    page_repo.add_tags(db, page, tag_names)
    return page


def remove_page_tags(
    db: Session,
    page_id: int,
    tag_names: list[str],
) -> WikiPage:
    """从页面移除指定标签。"""
    page = get_page(db, page_id)
    page_repo.remove_tags(db, page, tag_names)
    return page


def move_page(
    db: Session,
    page_id: int,
    parent_id: int | None,
) -> WikiPage:
    """将页面移动到新的父页面下（parent_id 为空表示置为顶层）。

    移动前校验目标父页面存在、属于同一知识库，且不发生循环引用。
    不影响页面内容与已有关系。
    """
    page = get_page(db, page_id)
    if parent_id is None:
        # 仅当父页面变化时才写入，避免无意义更新
        if page.parent_id is None:
            return page
        return page_repo.update(db, page, parent_id=None)
    _resolve_parent(db, page.knowledge_base_id, parent_id)
    _assert_not_in_own_ancestry(db, page, parent_id)
    if page.parent_id == parent_id:
        return page
    return page_repo.update(db, page, parent_id=parent_id)


def list_backlinks(
    db: Session,
    page_id: int,
) -> list[dict]:
    """查询引用当前页面的页面列表（反向引用，仅内部链接自动识别）。

    返回形如 [{"page": {…页面摘要…}, "source": "backlink"}]。
    源页面不存在时关系已由数据库级联删除，不会产生无效引用。
    """
    get_page(db, page_id)  # 页面不存在则 404
    relations = page_repo.get_backlink_relations(db, page_id)
    result: list[dict] = []
    for rel in relations:
        if rel.source_page is None:
            continue
        sp = rel.source_page
        result.append(
            {
                "id": sp.id,
                "title": sp.title,
                "slug": sp.slug,
                "knowledge_base_id": sp.knowledge_base_id,
                "source": rel.source.value,
            }
        )
    return result
