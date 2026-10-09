"""页面 CRUD 接口。"""
from typing import Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.models.wiki_page import PageStatus, WikiPage
from app.schemas.common import ApiResponse
from app.schemas.page import (
    BacklinkRead,
    PageCreate,
    PageMove,
    PageRead,
    PageTagUpdate,
    PageUpdate,
)
from app.services import page as page_service

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("", response_model=ApiResponse[list[PageRead]])
def list_pages(
    knowledge_base_id: int | None = None,
    parent_id: int | None = None,
    status: PageStatus | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    pages: Sequence[WikiPage] = page_service.list_pages(
        db,
        knowledge_base_id=knowledge_base_id,
        parent_id=parent_id,
        status=status,
        keyword=keyword,
        tag=tag,
    )
    return success(data=[PageRead.model_validate(p) for p in pages])


@router.post("", response_model=ApiResponse[PageRead])
def create_page(
    body: PageCreate,
    db: Session = Depends(get_db),
):
    page = page_service.create_page(
        db,
        knowledge_base_id=body.knowledge_base_id,
        title=body.title,
        slug=body.slug,
        content=body.content,
        parent_id=body.parent_id,
        status=body.status,
    )
    return success(data=PageRead.model_validate(page), message="创建成功")


@router.get("/{page_id}", response_model=ApiResponse[PageRead])
def get_page(page_id: int, db: Session = Depends(get_db)):
    page = page_service.get_page(db, page_id)
    return success(data=PageRead.model_validate(page))


@router.put("/{page_id}", response_model=ApiResponse[PageRead])
def update_page(
    page_id: int,
    body: PageUpdate,
    db: Session = Depends(get_db),
):
    payload = body.model_dump(exclude_unset=True)
    # 显式传入 content:null 时按清空处理（content 列不允许 NULL）
    if "content" in payload and payload["content"] is None:
        payload["content"] = ""
    page = page_service.update_page(db, page_id, **payload)
    return success(data=PageRead.model_validate(page), message="更新成功")


@router.delete("/{page_id}", response_model=ApiResponse[dict])
def delete_page(page_id: int, db: Session = Depends(get_db)):
    page_service.delete_page(db, page_id)
    return success(data={"id": page_id}, message="删除成功")


@router.post("/{page_id}/tags", response_model=ApiResponse[PageRead])
def add_page_tags(
    page_id: int,
    body: PageTagUpdate,
    db: Session = Depends(get_db),
):
    page = page_service.add_page_tags(db, page_id, body.tags)
    return success(data=PageRead.model_validate(page), message="标签添加成功")


@router.delete("/{page_id}/tags", response_model=ApiResponse[PageRead])
def remove_page_tags(
    page_id: int,
    tags: list[str] = Query(..., description="要移除的标签名列表"),
    db: Session = Depends(get_db),
):
    page = page_service.remove_page_tags(db, page_id, tags)
    return success(data=PageRead.model_validate(page), message="标签移除成功")


@router.put("/{page_id}/move", response_model=ApiResponse[PageRead])
def move_page(
    page_id: int,
    body: PageMove,
    db: Session = Depends(get_db),
):
    page = page_service.move_page(db, page_id, body.parent_id)
    return success(data=PageRead.model_validate(page), message="移动成功")


@router.get("/{page_id}/backlinks", response_model=ApiResponse[list[BacklinkRead]])
def get_page_backlinks(page_id: int, db: Session = Depends(get_db)):
    """查询指向当前页面的反向引用（内部链接自动识别）。"""
    backlinks = page_service.list_backlinks(db, page_id)
    return success(data=[BacklinkRead(**bl) for bl in backlinks], message="ok")


@router.get("/{page_id}/relations", response_model=ApiResponse[dict])
def get_page_relations(page_id: int, db: Session = Depends(get_db)):
    """查询某页面的所有关系（出向 + 入向）。"""
    from app.services import relation as relation_service

    result = relation_service.get_page_relations(db, page_id)
    return success(data=result, message="ok")
