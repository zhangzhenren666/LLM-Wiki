"""搜索 API 接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.search import PaginatedSearchResponse
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=ApiResponse[PaginatedSearchResponse])
def search_pages(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    knowledge_base_id: int | None = Query(None, description="限定知识库 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
) -> ApiResponse[PaginatedSearchResponse]:
    """搜索 Wiki 页面（标题、标签、正文）。"""
    result = search_service.search(
        db,
        query=q,
        knowledge_base_id=knowledge_base_id,
        page=page,
        page_size=page_size,
    )
    return success(data=result)