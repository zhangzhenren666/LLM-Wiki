"""知识提取条目接口。

提供知识提取结果的查询能力，可按任务或文档筛选，
查看自动创建的页面、异常条目及异常原因。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import success
from app.schemas.common import ApiResponse
from app.schemas.knowledge_item import KnowledgeItemListResponse, KnowledgeItemRead
from app.services.knowledge_extraction import KnowledgeExtractionService

router = APIRouter(prefix="/knowledge-items", tags=["knowledge-items"])


def _service(db: Session = Depends(get_db)) -> KnowledgeExtractionService:
    return KnowledgeExtractionService(db)


@router.get("/tasks/{task_id}", response_model=ApiResponse[KnowledgeItemListResponse])
def list_items_by_task(
    task_id: int,
    service: KnowledgeExtractionService = Depends(_service),
) -> ApiResponse[KnowledgeItemListResponse]:
    """查询某任务的所有知识提取条目。"""
    items = service.get_items_for_task(task_id)

    reads = [KnowledgeItemRead.model_validate(item) for item in items]
    stats = _count_stats(items)

    return success(
        data=KnowledgeItemListResponse(
            items=reads,
            total=len(reads),
            auto_created_count=stats["auto_created"],
            needs_attention_count=stats["needs_attention"],
            duplicate_count=stats["duplicate"],
            skipped_count=stats["skipped"],
        ),
        message="ok",
    )


@router.get("/documents/{document_id}", response_model=ApiResponse[KnowledgeItemListResponse])
def list_items_by_document(
    document_id: int,
    service: KnowledgeExtractionService = Depends(_service),
) -> ApiResponse[KnowledgeItemListResponse]:
    """查询某文档的所有知识提取条目。"""
    from sqlalchemy import select
    from app.models.knowledge_item import KnowledgeItem

    stmt = (
        select(KnowledgeItem)
        .where(KnowledgeItem.document_id == document_id)
        .order_by(KnowledgeItem.id)
    )
    items = list(service._db.execute(stmt).scalars().all())

    reads = [KnowledgeItemRead.model_validate(item) for item in items]
    stats = _count_stats(items)

    return success(
        data=KnowledgeItemListResponse(
            items=reads,
            total=len(reads),
            auto_created_count=stats["auto_created"],
            needs_attention_count=stats["needs_attention"],
            duplicate_count=stats["duplicate"],
            skipped_count=stats["skipped"],
        ),
        message="ok",
    )


def _count_stats(items) -> dict[str, int]:
    """统计各状态条目数量。"""
    from app.models.knowledge_item import KnowledgeItemStatus

    stats = {"auto_created": 0, "needs_attention": 0, "duplicate": 0, "skipped": 0}
    for item in items:
        key = item.status.value if hasattr(item.status, "value") else item.status
        if key in stats:
            stats[key] += 1
    return stats