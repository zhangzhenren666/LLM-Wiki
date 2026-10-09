"""知识库 CRUD 接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logger import get_logger
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base import KnowledgeBaseService
from app.services import page as page_service

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

logger = get_logger(__name__)


def _service(db: Session = Depends(get_db)) -> KnowledgeBaseService:
    return KnowledgeBaseService(db)


@router.get("", response_model=ApiResponse[list[KnowledgeBaseRead]])
def list_knowledge_bases(
    service: KnowledgeBaseService = Depends(_service),
) -> ApiResponse[list[KnowledgeBaseRead]]:
    """查询全部知识库。"""
    items = service.list()
    return success(data=items, message="ok")


@router.post("", response_model=ApiResponse[KnowledgeBaseRead])
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    service: KnowledgeBaseService = Depends(_service),
) -> ApiResponse[KnowledgeBaseRead]:
    """创建知识库。"""
    item = service.create(payload)
    return success(data=item, message="创建成功")


@router.get("/{kb_id}", response_model=ApiResponse[KnowledgeBaseRead])
def get_knowledge_base(
    kb_id: int,
    service: KnowledgeBaseService = Depends(_service),
) -> ApiResponse[KnowledgeBaseRead]:
    """查询单个知识库。"""
    item = service.get(kb_id)
    return success(data=item, message="ok")


@router.put("/{kb_id}", response_model=ApiResponse[KnowledgeBaseRead])
def update_knowledge_base(
    kb_id: int,
    payload: KnowledgeBaseUpdate,
    service: KnowledgeBaseService = Depends(_service),
) -> ApiResponse[KnowledgeBaseRead]:
    """更新知识库。"""
    item = service.update(kb_id, payload)
    return success(data=item, message="更新成功")


@router.delete("/{kb_id}", response_model=ApiResponse[dict])
def delete_knowledge_base(
    kb_id: int,
    service: KnowledgeBaseService = Depends(_service),
) -> ApiResponse[dict]:
    """删除知识库。"""
    service.delete(kb_id)
    return success(data={"id": kb_id}, message="删除成功")


@router.get("/{kb_id}/tags", response_model=ApiResponse[list[str]])
def list_knowledge_base_tags(
    kb_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[str]]:
    """查询某知识库下出现过的所有标签（去重、按名称排序）。"""
    tags = page_service.list_tags(db, kb_id)
    return success(data=tags, message="ok")
