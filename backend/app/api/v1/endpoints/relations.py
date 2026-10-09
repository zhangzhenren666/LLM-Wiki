"""页面关系 CRUD 接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.models.page_relation import RelationType
from app.schemas.common import ApiResponse
from app.schemas.relation import RelationCreate, RelationRead
from app.services import relation as relation_service

router = APIRouter(prefix="/relations", tags=["relations"])


@router.get("", response_model=ApiResponse[list[RelationRead]])
def list_relations(
    knowledge_base_id: int | None = Query(None, description="知识库 ID"),
    page_id: int | None = Query(None, description="页面 ID（同时匹配源和目标）"),
    relation_type: RelationType | None = Query(None, description="关系类型"),
    db: Session = Depends(get_db),
):
    """查询关系列表，可按知识库、页面、类型筛选。"""
    relations = relation_service.list_relations(
        db,
        knowledge_base_id=knowledge_base_id,
        page_id=page_id,
        relation_type=relation_type,
    )
    return success(data=[RelationRead.model_validate(r) for r in relations])


@router.post("", response_model=ApiResponse[RelationRead], status_code=201)
def create_relation(
    body: RelationCreate,
    db: Session = Depends(get_db),
):
    """创建页面关系。"""
    rel = relation_service.create_relation(
        db,
        source_page_id=body.source_page_id,
        target_page_id=body.target_page_id,
        relation_type=body.relation_type,
    )
    return success(data=RelationRead.model_validate(rel), message="创建成功")


@router.delete("/{relation_id}", response_model=ApiResponse[dict])
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    """删除指定关系。"""
    relation_service.delete_relation(db, relation_id)
    return success(data={"id": relation_id}, message="删除成功")